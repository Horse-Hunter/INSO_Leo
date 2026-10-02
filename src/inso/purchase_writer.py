"""Purchase draft preparation using the existing INSO action boundary.

Save Data stays closed. Owner-authorized Save-and-Send is durable-before-click;
generic Send remains forbidden.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, ClassVar, Protocol
from urllib.parse import urlsplit

from .session import OperationPage, SecurityViolation
from .write_safety import (
    ControlCandidate,
    ControlSemantics,
    FeatureGate,
    InsoDraftActions,
    OwnerAuthorizedSaveAndSendGate,
    ProductionWriteGate,
    SelectorRegistry,
    WriteAction,
)

AI_ENTRY_PATH = "/skins/etaoerp/product/Import_ai.aspx"
_QUOTATION_TYPES = frozenset({"需要问全价格", "普通询价"})
_CUSTOMERS = frozenset({"Win Source Elec. Tech. Ltd"})
_PURCHASERS = frozenset({"颜浩坚", "陈熙"})

_log = logging.getLogger("inso.purchase_writer")


@dataclass(frozen=True, slots=True)
class AiRecognitionResult:
    """Read-only value shape from the verified single-row AI result area.

    Live shape (2026-10-01): the ERP's own AI录单 preview table is
    ``# / 产品编码 / 型号 / 品牌 / 数量`` and it resolves 产品编码 (``ProductID``)
    from its product master -- ``STM8L051F3P6`` came back as ``P216328``. That
    code is server-side data (``/api/ai/extract-erp-table``) which cannot be
    derived locally, so it is carried through rather than recomputed.
    """

    product_id: str
    model: str
    brand: str
    quantity: int
    ready: bool


class AiResultReader(Protocol):
    def read(self) -> AiRecognitionResult | None: ...


class ParentProductFields(Protocol):
    """Read-only view of the parent form's product row.

    There are deliberately no setters. The 采购临时询价 form is the operator's
    surface and the ERP fills its 编码/型号/品牌/数量 row itself when the AI录单
    panel commits (``pasteImport`` -> ``ai_appendRow``); typing those cells was
    a process defect (Owner finding, 2026-10-01), not a shortcut this seam may
    offer.
    """

    def wait_for_row(self, expected_product_id: str, timeout_seconds: float) -> bool: ...

    def read_product_id(self) -> str | None: ...

    def read_model(self) -> str | None: ...

    def read_brand(self) -> str | None: ...

    def read_quantity(self) -> int | None: ...


class PlaywrightParentProductFields:
    """The four verified product inputs in the leased parent inquiry form.

    The first grid column is ``编码/型号`` and is bound to ``ProductID``; the
    型号 column is a separate ``PartNo`` cell. Both are filled by the ERP when
    the AI录单 panel commits its row.

    This seam is read-only by design: no row creation, no cell writing, no
    import, Save, or Send behaviour. It exists to prove what the ERP put in the
    row, not to manufacture it. ``wait_for_row`` absorbs the one genuine
    asynchrony -- ``ai_appendRow`` reloads the grid through ``layui.table``, so
    a read issued the instant the dialog closes can still see the old body.
    """

    _FORM_FRAME_SELECTOR = "iframe#winIframealert_enquiry"
    _FIELD_SELECTORS: ClassVar[dict[str, str]] = {
        "product_id": '#_id_dg td[data-field="ProductID"]',
        "model": '#_id_dg td[data-field="PartNo"]',
        "brand": '#_id_dg td[data-field="Brand"]',
        "quantity": '#_id_dg td[data-field="Qty"]',
    }
    _POLL_MILLISECONDS = 150

    def __init__(self, form_page: OperationPage) -> None:
        self._form_page = form_page

    def wait_for_row(self, expected_product_id: str, timeout_seconds: float) -> bool:
        """Wait until the grid has rendered the row the ERP just handed back.

        The condition is the row itself -- the 编码 the recognition produced --
        rather than a delay, so a slow reload is waited out and a row that never
        arrives still fails closed on the caller's own read-back.
        """

        if not isinstance(expected_product_id, str) or not expected_product_id:
            raise SecurityViolation("expected parent product code is invalid")
        deadline = time.monotonic() + timeout_seconds
        while True:
            if self.read_product_id() == expected_product_id:
                return True
            if time.monotonic() >= deadline:
                return False
            self._form_page.page.wait_for_timeout(self._POLL_MILLISECONDS)

    def read_product_id(self) -> str | None:
        return self._read_text("product_id")

    def read_model(self) -> str | None:
        return self._read_text("model")

    def read_brand(self) -> str | None:
        return self._read_text("brand")

    def read_quantity(self) -> int | None:
        value = self._read_text("quantity")
        if value is None or not value.isdecimal():
            return None
        quantity = int(value)
        return quantity if quantity > 0 else None

    def _read_text(self, field: str) -> str | None:
        try:
            cell = self._field(field)
            editor = cell.locator("input")
            if editor.count() == 1:
                if not editor.is_visible() or not editor.is_enabled():
                    return None
                return editor.input_value()
            if editor.count() != 0:
                return None
            rendered = cell.locator(".layui-table-cell")
            if rendered.count() != 1 or not rendered.is_visible():
                return None
            return rendered.inner_text()
        except Exception:  # noqa: BLE001 - browser ambiguity fails closed
            return None

    def _field(self, field: str) -> Any:
        frame = self._verified_form_frame()
        locator = frame.locator(self._FIELD_SELECTORS[field])
        if locator.count() != 1 or not locator.is_visible() or not locator.is_enabled():
            raise SecurityViolation("parent product field is not uniquely actionable")
        return locator

    def _verified_form_frame(self) -> Any:
        page = self._form_page.page
        _require_inso_origin(page.url)
        try:
            element = page.locator(self._FORM_FRAME_SELECTOR)
            if element.count() != 1 or not element.is_visible():
                raise SecurityViolation("parent form frame is not unique")
            # Locator.content_frame is a FrameLocator property, not the Frame
            # itself, so the owning element handle is used to reach the real
            # Frame this seam must read and write through.
            handle = element.element_handle()
            frame = None if handle is None else handle.content_frame()
        except SecurityViolation:
            raise
        except Exception as exc:
            raise SecurityViolation("parent form frame is unavailable") from exc
        if frame is None or not _is_verified_inso_url(str(getattr(frame, "url", ""))):
            raise SecurityViolation("parent form frame is not unique")
        return frame


class SaveDispatchStore(Protocol):
    """Narrow Workflow persistence seam; the INSO module owns no state rules."""

    def begin_save_dispatch(
        self, inquiry_id: str, *, at: datetime, save_and_send: bool = False,
    ) -> None: ...


class AiFrameProvider(Protocol):
    """Anything that can hand back the verified AI entry frame."""

    def frame(self) -> Any: ...


class AiEntryPanel:
    """The purchase form's own AI录单 dialog; an in-page frame, not a tab.

    The verified entry is the form's ``#ai_import_`` control (labelled "AI录单"),
    which opens a ``details-dialog`` layer holding an ``Import_ai.aspx`` iframe
    inside the same serial ERP page -- exactly what the Phase A read-only
    verification recorded. Nothing here creates or navigates a page, because
    the live product never opens one.
    """

    def __init__(
        self,
        form_page: OperationPage,
        *,
        wait_seconds: float | None = None,
        poll_milliseconds: int | None = None,
    ) -> None:
        self._form_page = form_page
        self._frame: Any | None = None
        self._wait_seconds = (
            _AI_ENTRY_WAIT_SECONDS if wait_seconds is None else wait_seconds
        )
        self._poll_milliseconds = (
            _AI_ENTRY_POLL_MILLISECONDS
            if poll_milliseconds is None
            else poll_milliseconds
        )

    def open(self) -> None:
        page = self._form_page.page
        _require_inso_origin(page.url)
        entry = page.frame_locator(_FORM_SCOPE_FRAME).locator(_AI_ENTRY_CONTROL)
        if (
            entry.count() != 1
            or not entry.is_visible()
            or not entry.is_enabled()
            or (entry.inner_text() or "").strip() != _AI_ENTRY_LABEL
        ):
            raise SecurityViolation("AI entry control is not uniquely actionable")
        entry.click()
        self._frame = self._await_frame(page)

    def frame(self) -> Any:
        frame = self._frame
        if frame is None or _frame_is_detached(frame):
            raise SecurityViolation("AI entry panel is not open")
        _require_ai_entry_url(str(getattr(frame, "url", "")))
        return frame

    def close(self) -> bool:
        """Close only this AI录单 panel; the draft form stays open for Save.

        Anchored on the dialog that actually contains the verified AI frame
        (the Phase A read-only recipe), so no unrelated dialog can be dismissed
        by mistake. The frame-scoped selector is a fallback for the case where
        the frame handle is already gone.

        Returns whether the panel was dismissed, and never claims a dismissal it
        did not observe: a leftover dialog the ERP keeps hidden has no clickable
        close control, so that case is reported instead of being mistaken for a
        closed panel.
        """

        frame = self._frame
        self._frame = None
        try:
            page = self._form_page.page
            _require_inso_origin(page.url)
        except SecurityViolation:
            _log.warning(
                "AI entry panel was not dismissed: INSO page identity is not verified"
            )
            return False
        if frame is not None and self._close_frame_dialog(frame):
            return True
        button = page.locator(_AI_ENTRY_CLOSE_CONTROL)
        if button.count() == 1 and button.is_visible():
            button.click()
            return True
        if frame is not None:
            _log.warning(
                "AI entry panel was not dismissed: its dialog has no clickable close control"
            )
        return False

    @staticmethod
    def _close_frame_dialog(frame: Any) -> bool:
        """Close the unique dialog containing this exact AI frame.

        This is the Phase A read-only close recipe: resolve the dialog by the
        frame it holds, then click that dialog's own close control.
        """

        try:
            parent = frame.parent_frame
            handle = frame.frame_element()
            dialog = parent.locator("details-dialog._dialog1").filter(has=handle)
            if dialog.count() != 1:
                return False
            close = dialog.locator('button[title="关闭窗口"]')
            if close.count() != 1 or not close.is_visible() or not close.is_enabled():
                return False
            close.click(timeout=10_000)
            return True
        except Exception:  # noqa: BLE001 - browser ambiguity fails closed
            return False

    def _await_frame(self, page: Any) -> Any:
        deadline = time.monotonic() + self._wait_seconds
        while True:
            for frame in page.frames:
                if _is_verified_ai_entry_url(str(getattr(frame, "url", ""))):
                    return frame
            if time.monotonic() >= deadline:
                raise SecurityViolation("AI entry panel did not open")
            page.wait_for_timeout(self._poll_milliseconds)


class PlaywrightAiResultReader:
    """Read the verified one-row AI preview and ready button state.

    Recognition arrives asynchronously, so ``read`` polls the exact readiness
    predicate until it holds or ``_AI_READY_WAIT_SECONDS`` elapses. It still
    returns ``None`` for any state that never becomes a clean single ready row,
    which keeps the caller's fail-closed contract intact.
    """

    def __init__(
        self,
        ai_panel: AiFrameProvider,
        *,
        wait_seconds: float | None = None,
        poll_milliseconds: int | None = None,
    ) -> None:
        self._ai_panel = ai_panel
        self._wait_seconds = (
            _AI_READY_WAIT_SECONDS if wait_seconds is None else wait_seconds
        )
        self._poll_milliseconds = (
            _AI_READY_POLL_MILLISECONDS
            if poll_milliseconds is None
            else poll_milliseconds
        )

    def read(self) -> AiRecognitionResult | None:
        frame = self._ai_panel.frame()
        deadline = time.monotonic() + self._wait_seconds
        while True:
            result = self._read_once(frame)
            if result is not None:
                return result
            if time.monotonic() >= deadline:
                return None
            frame.wait_for_timeout(self._poll_milliseconds)

    def _read_once(self, frame: Any) -> AiRecognitionResult | None:
        ready = frame.locator("button#ai-recognize")
        if ready.count() != 1 or ready.inner_text().strip() != "重新识别":
            return None
        rows = frame.locator("#preview-body > tr")
        if rows.count() != 1:
            return None
        row = rows.nth(0)
        fields = {
            name: row.locator(f'input[data-f="{field}"]')
            for name, field in (
                ("product_id", "ProductID"),
                ("model", "PartNo"),
                ("brand", "Brand"),
                ("quantity", "Qty"),
            )
        }
        if any(locator.count() != 1 for locator in fields.values()):
            return None
        product_id = fields["product_id"].input_value()
        model = fields["model"].input_value()
        brand = fields["brand"].input_value()
        quantity_text = fields["quantity"].input_value()
        if not product_id or not model or not brand or not quantity_text.isdecimal():
            return None
        quantity = int(quantity_text)
        if quantity <= 0:
            return None
        return AiRecognitionResult(product_id, model, brand, quantity, ready=True)


@dataclass(frozen=True, slots=True)
class _Binding:
    selector_id: str
    scope_id: str
    selector: str
    semantics: ControlSemantics
    frame: str


#: Actions whose control is a bare ``<button>``. A button without a type
#: attribute reports ``type="submit"``, and "submit" is a denied semantic, so
#: these are identified by their verified id alone instead.
_ID_ONLY_ACTIONS = frozenset({
    WriteAction.SAVE_DATA, WriteAction.AI_ENTRY_COMMIT, WriteAction.SAVE_AND_SEND,
})

#: Scopes that only exist while the verified AI录单 panel is open.
_AI_SCOPES = frozenset({"ai", "ai-dialog"})

_BINDINGS: dict[WriteAction, _Binding] = {
    WriteAction.NEW_DRAFT: _Binding(
        "product_add_control",
        "inquiry-list",
        "button#product_add_",
        ControlSemantics(
            "button", "新增", "新增", (("id", "product_add_"), ("type", "button"))
        ),
        "list",
    ),
    WriteAction.SET_CUSTOMER: _Binding(
        "customer-name-input",
        "purchase-form",
        "input#CompanyName",
        ControlSemantics(
            "textbox",
            "",
            "",
            (("id", "CompanyName"), ("type", "text")),
        ),
        "form",
    ),
    WriteAction.SET_PURCHASER: _Binding(
        "purchaser-input",
        "purchase-form",
        "input#UserName_text",
        ControlSemantics(
            "textbox",
            "",
            "",
            (("id", "UserName_text"), ("type", "text")),
        ),
        "form",
    ),
    WriteAction.SET_QUOTATION_TYPE: _Binding(
        "quotation-routing-input",
        "purchase-form",
        "input#ImpValueF",
        ControlSemantics(
            "textbox",
            "",
            "",
            (("id", "ImpValueF"), ("type", "text")),
        ),
        "form",
    ),
    WriteAction.SET_AI_INPUT: _Binding(
        "ai-input",
        "ai-entry",
        "textarea#paste-area",
        ControlSemantics(
            "textbox",
            "",
            "",
            (("id", "paste-area"), ("type", "textarea")),
        ),
        "ai",
    ),
    WriteAction.RUN_AI_RECOGNITION: _Binding(
        "ai-recognition-button",
        "ai-entry",
        "button#ai-recognize",
        ControlSemantics(
            "button",
            "AI 智能识别",
            "AI 智能识别",
            (("id", "ai-recognize"), ("type", "button")),
        ),
        "ai",
    ),
    WriteAction.AI_ENTRY_COMMIT: _Binding(
        "ai-entry-commit",
        "ai-entry-dialog",
        'button:has-text("保存数据")',
        # Bound by id alone, exactly like SAVE_DATA: a bare <button> reports
        # type="submit", and a "type=submit" attribute would trip the denied
        # semantics guard even though this control is the client-side hand-back.
        ControlSemantics(
            "button", "保存数据", "保存数据", (("id", "win_btn__dialog11"),)
        ),
        "ai-dialog",
    ),
    WriteAction.SAVE_DATA: _Binding(
        "save-data-control",
        "purchase-form",
        "button#btnSave",
        ControlSemantics(
            "button", "保存", "保存", (("id", "btnSave"),)
        ),
        "form",
    ),
    WriteAction.SAVE_AND_SEND: _Binding(
        "final-inquiry-control", "purchase-form", "button#btnSave2",
        ControlSemantics(
            "button", "保存并发送", "保存并发送", (("id", "btnSave2"),)
        ),
        "form",
    ),
}


# Deployment-specific wrapper frames. The Owner's real environment renders the
# business-inquiry list as the verified document itself, so the list id does not
# exist there; it remains only as a fallback. The purchase form is always its own
# frame, so it keeps its own scope either way.
_LIST_SCOPE_FRAME = "iframe#iframe_YeWuXJ_frame"
_FORM_SCOPE_FRAME = "iframe#winIframealert_enquiry"

# INSO renders the code and entity fields (customer, purchaser, quotation type)
# as a select box: the input only holds text, and the real selection happens by
# clicking the option row the site itself rendered. Writing text into the input
# left the menu hanging open over the rest of the form, so the next field could
# not be clicked at all. The option text must equal the requested value exactly
# and appear exactly once, otherwise the port refuses to click anything.
#
# The customer menu closes itself once an option is picked, but the purchaser
# menu does not: after 颜浩坚 is chosen the menu is still open and its own table
# cells keep covering #ai_import_, so the AI录单 control can never be clicked
# (verified live). The site closes that menu on a document click, so a pick is
# always followed by the site's own dismiss click and a fail-closed check.
# The purchaser control is a checkbox multi-select: its own ``data-options``
# declares ``checkbox:true``, and the ERP re-checks the previously used
# purchaser whenever a draft opens. Clearing the search text therefore does not
# clear that state. Live evidence (2026-09-30): one order selected 颜浩坚 and
# the next order routed to 陈熙 ran against a field that ended holding both
# (text ``陈熙,颜浩坚``, ids ``7432,16665``), so the exact read-back guard
# rejected the step and the whole thing surfaced only as ``CONTROL_NOT_FOUND``.
# The checked rows stay checked while the popup is hidden, so dismissing the
# popup is not enough: every option the site renders as already selected is
# cleared before the routed one is picked.
_OPEN_SELECT_MENU = "details-menu.select-menu-modal:visible, .select-menu-modal:visible"
_MENU_ROW = "tr"
_MENU_ITEM = ".select-menu-item, [data-value]"
_MENU_CHECKBOX = 'input[type="checkbox"]'
_MENU_WAIT_SECONDS = 6.0

# The AI entry is the purchase form's own control, exactly as the Phase A
# read-only verification recorded it: #ai_import_ ("AI录单") opens a
# details-dialog layer holding an Import_ai.aspx iframe inside the same ERP
# page. It is an in-page panel, never a new tab, so nothing in this module
# creates a page. The recognition controls then live in that frame.
_AI_ENTRY_CONTROL = "#ai_import_"
_AI_ENTRY_LABEL = "AI录单"
_AI_ENTRY_CLOSE_CONTROL = 'details-dialog._dialog1 button[title="关闭窗口"]'
# The AI录单 dialog's own commit control. Live read (2026-10-01): its handler is
# ``pasteImport()`` -- literally ``AiImport.doImport()`` -- which is the same
# action as the panel's in-frame 导入到单据 button. It calls
# ``returnSet(buildResult())`` + ``windowsClose()``; the dialog's close callback
# (``alertboxs[1].closeMtd = function(){ ai_appendRow() }``) then reloads the bill
# grid with the recognized row. Purely client-side: ``doImport``, ``windowsClose``
# and ``ai_appendRow`` contain no request call, unlike the form's 保存
# (``button#btnSave`` -> ``bill_save_auto``), which stays denied.
_AI_ENTRY_COMMIT_CONTROL = 'button:has-text("保存数据")'
_AI_ENTRY_COMMIT_ID = "win_btn__dialog11"

# The 采购临时询价 window is its own dialog and the AI录单 panel is a sibling
# dialog of it. Both live on the INSO home page rather than on a page of their
# own, so clearing them returns the session to the home page and its 业务询价
# list without navigating anywhere.
#
# Closing a dialog here only sets ``display:none``. The dialog, its close control
# and its iframe document all stay in the DOM (read-only live read,
# 2026-09-30: ``iframe#winIframealert_enquiry`` count stayed 1 with the hosting
# ``details-dialog.alert_enquiry`` at ``display:none``, and the same held for the
# AI panel). Presence therefore can never prove a window is gone -- an earlier
# version of this module used ``count() == 0`` as its cleared check and so
# reported every surface as unclearable, which would have refused every order at
# the purchase step with ``CONTROL_NOT_FOUND``. Only visibility can, and a window
# that is already hidden is a success, not a failure.
_ORDER_WINDOW_DIALOG = "details-dialog"
_AI_ENTRY_DIALOG = "details-dialog._dialog1"
_DIALOG_CLOSE_CONTROL = 'button[title="关闭窗口"]'
_DIALOG_CLOSE_TIMEOUT_MS = 10_000
_AI_ENTRY_WAIT_SECONDS = 15.0
_AI_ENTRY_POLL_MILLISECONDS = 200

# The AI entry runs recognition asynchronously. Immediately after the click the
# button still carries a progress caption ("🔗 正在连接 AI 服务... 0%", then
# "✅ 正在校验品牌与物料库... 66%", "✨ 即将完成，请稍候... 95%") and the preview
# has no rows at all; only ~1s later does it become "重新识别" with one
# populated row. A single immediate read therefore always saw "not ready". The
# reader now polls the exact same predicate until it holds or the deadline
# passes. A genuine failure -- no unique row, or a field mismatch -- still
# fails closed, it just is not mistaken for the in-flight state.
_AI_READY_WAIT_SECONDS = 20.0
_AI_READY_POLL_MILLISECONDS = 250


class _PlaywrightActionPort:
    """Private exact-selector bridge; callers only receive business methods."""

    def __init__(self, form_page: OperationPage, ai_panel: AiFrameProvider) -> None:
        self._form_page = form_page
        self._ai_panel = ai_panel

    def _locator(self, binding: _Binding) -> Any:
        if binding.frame == "list":
            _require_inso_origin(self._form_page.page.url)
            # The list controls live inside the very document the session already
            # verified, whether that is its own tab or the wrapper's iframe. The
            # read path resolves its page the same way; the write path used to
            # look up a hard-coded wrapper frame, which matched nothing in
            # production and made 新增 look missing.
            shell_frame = getattr(self._form_page, "shell_frame", None)
            if shell_frame is not None:
                return shell_frame.locator(binding.selector)
            return self._form_page.page.frame_locator(_LIST_SCOPE_FRAME).locator(
                binding.selector
            )
        if binding.frame == "form":
            _require_inso_origin(self._form_page.page.url)
            return self._form_page.page.frame_locator(_FORM_SCOPE_FRAME).locator(
                binding.selector
            )
        if binding.frame == "ai":
            # The recognition controls live in the form's own AI录单 frame, so
            # the frame is re-verified on every use rather than trusted once.
            frame = self._ai_panel.frame()
            _require_ai_entry_url(str(getattr(frame, "url", "")))
            return frame.locator(binding.selector)
        if binding.frame == "ai-dialog":
            # The commit control sits in the dialog that *hosts* the AI frame,
            # not in the frame itself. It is resolved through that same frame, so
            # the control can only ever be reached while the verified panel is
            # open, and a dialog that is not the panel's own fails closed.
            frame = self._ai_panel.frame()
            _require_ai_entry_url(str(getattr(frame, "url", "")))
            dialog = frame.parent_frame.locator(_AI_ENTRY_DIALOG)
            if dialog.count() != 1:
                raise SecurityViolation("AI entry dialog is not unique")
            return dialog.locator(binding.selector)
        raise SecurityViolation("unknown INSO selector scope")

    def _unique_menu_option(self, menu: Any, value: str) -> Any | None:
        """The one rendered option carrying ``value`` in one of its own cells.

        The ERP's menus are tables, and which column holds the name differs per
        field: the company menu leads with the company, while the purchaser menu
        leads with a blank column and puts the person's name third. Matching one
        whole cell exactly -- rather than a column position or a substring --
        keeps the click bound to a single verified option.
        """

        matches: list[Any] = []
        rows = menu.locator(_MENU_ROW)
        for index in range(rows.count()):
            row = rows.nth(index)
            cells = row.locator("td")
            cell_count = cells.count()
            texts = [
                (cells.nth(cell).inner_text() or "").strip()
                for cell in range(cell_count)
            ]
            if not any(texts):
                texts = [(row.inner_text() or "").strip()]
            if value in texts:
                matches.append(row)
        if not matches:
            items = menu.locator(_MENU_ITEM)
            for index in range(items.count()):
                item = items.nth(index)
                if (item.inner_text() or "").strip() == value:
                    matches.append(item)
        return matches[0] if len(matches) == 1 else None

    def _pick_menu_option(self, field: Any, value: str) -> None:
        """Select ``value`` the way the site itself does: click its own option.

        Filling the input alone selects nothing in this ERP and leaves the menu
        covering the form, which is why the following step could never be
        clicked. The click stays bound to the site-rendered option and fails
        closed unless that option is present exactly once. The pick is then
        followed by the site's own dismiss click, because the purchaser menu
        does not close itself and keeps covering the next control.
        """

        page = self._form_page.page
        _require_inso_origin(page.url)
        field.fill("")
        field.click()
        menu = page.frame_locator(_FORM_SCOPE_FRAME).locator(_OPEN_SELECT_MENU)
        deadline = time.monotonic() + _MENU_WAIT_SECONDS
        while time.monotonic() < deadline:
            if menu.count() == 1:
                self._clear_checked_options(menu)
                option = self._unique_menu_option(menu, value)
                if option is not None:
                    option.click()
                    self._dismiss_select_menu()
                    return
            page.wait_for_timeout(150)
        raise SecurityViolation("select menu option is missing or ambiguous")

    def _clear_checked_options(self, menu: Any) -> None:
        """Clear every option the site already renders as selected.

        Only rows the site itself rendered as checked are touched, and they are
        clicked exactly the way a pick is clicked, so nothing is selected that
        the site did not already offer. A row that stays checked is reported but
        not fatal: the routed purchaser being the only checked one is a correct
        outcome either way, and the exact read-back guard still owns the
        invariant that exactly one purchaser ends up selected.
        """

        rows = menu.locator(_MENU_ROW)
        for index in range(rows.count()):
            row = rows.nth(index)
            box = row.locator(_MENU_CHECKBOX)
            if box.count() != 1 or not box.is_checked():
                continue
            row.click()
            if box.is_checked():
                _log.warning("a selected option did not clear when its own row was clicked")

    def _dismiss_select_menu(self) -> None:
        """Close a leftover select menu the way the site itself does.

        Verified live: the customer menu closes on its own once an option is
        picked, but the purchaser menu stays open and its own table cells keep
        covering ``#ai_import_``, so the AI录单 control can never be clicked.
        The site dismisses that menu on a document click, so this issues the
        same click and then insists, fail-closed, that no menu is left open.
        """

        page = self._form_page.page
        _require_inso_origin(page.url)
        scope = page.frame_locator(_FORM_SCOPE_FRAME)
        menu = scope.locator(_OPEN_SELECT_MENU)
        deadline = time.monotonic() + _MENU_WAIT_SECONDS
        while menu.count():
            scope.locator("body").evaluate("(body) => body.click()")
            if time.monotonic() >= deadline:
                raise SecurityViolation("select menu did not close")
            page.wait_for_timeout(150)

    def _ai_panel_is_ready(self) -> bool:
        try:
            self._ai_panel.frame()
        except SecurityViolation:
            return False
        return True

    def dismiss_select_menu(self) -> None:
        """Public entry to the site's own select-menu dismissal (fail-closed)."""

        self._dismiss_select_menu()

    def _candidate(self, action: WriteAction) -> tuple[ControlCandidate, ...]:
        binding = _BINDINGS[action]
        locator = self._locator(binding)
        metadata = locator.evaluate_all(
            """elements => elements.map(e => {
                const tag = e.tagName.toLowerCase();
                const text = tag === 'button' ? (e.innerText || '').trim() : '';
                const labels = e.labels ? [...e.labels].map(l => (l.innerText || '').trim()) : [];
                const label = labels.find(Boolean) || '';
                const labelledBy = (e.getAttribute('aria-labelledby') || '')
                    .split(/\\s+/).filter(Boolean)
                    .map(id => e.ownerDocument.getElementById(id)?.innerText?.trim() || '')
                    .filter(Boolean).join(' ');
                const role = tag === 'button' ? 'button' : 'textbox';
                return {
                    role,
                    accessibleName: e.getAttribute('aria-label') || labelledBy || label || text,
                    visibleText: text,
                    id: e.id || '',
                    type: e.type || tag,
                    enabled: !e.disabled,
                    visible: !!(e.offsetWidth || e.offsetHeight || e.getClientRects().length)
                        && getComputedStyle(e).visibility !== 'hidden'
                        && getComputedStyle(e).display !== 'none'
                };
            })"""
        )
        return tuple(
            ControlCandidate(
                binding.selector_id,
                binding.scope_id,
                ControlSemantics(
                    item["role"],
                    item["accessibleName"],
                    item["visibleText"],
                    (("id", item["id"]),)
                    if action in _ID_ONLY_ACTIONS
                    else (("id", item["id"]), ("type", item["type"])),
                ),
                enabled=item["enabled"],
                visible=item["visible"],
            )
            for item in metadata
        )

    def candidates(self) -> tuple[ControlCandidate, ...]:
        return tuple(
            candidate
            for action in _BINDINGS
            if _BINDINGS[action].frame not in _AI_SCOPES or self._ai_panel_is_ready()
            for candidate in self._candidate(action)
        )

    def dispatch_validated(
        self, action: WriteAction, control: ControlCandidate, value: str | None
    ) -> None:
        binding = _BINDINGS.get(action)
        if binding is None:
            raise SecurityViolation("action has no live INSO dispatch binding")
        current = self._candidate(action)
        if len(current) != 1 or current[0] != control:
            raise SecurityViolation("INSO control changed before dispatch")
        locator = self._locator(binding)

        if action is WriteAction.NEW_DRAFT:
            locator.click()
            # The native menu opens an asynchronous iframe. Candidate metadata
            # reads do not auto-wait, so do not inspect customer controls until
            # the actual unsaved form has rendered. Missing/ambiguous stays closed.
            self._form_page.page.frame_locator(_FORM_SCOPE_FRAME).locator(
                "input#CompanyName"
            ).wait_for(state="visible", timeout=15_000)
            return
        if action is WriteAction.SET_CUSTOMER:
            if value is None:
                raise SecurityViolation("field value is required")
            self._pick_menu_option(locator, value)
            if locator.input_value() != value:
                raise SecurityViolation("field read-back did not match input")
            return
        if action is WriteAction.SET_PURCHASER:
            if value is None:
                raise SecurityViolation("field value is required")
            self._pick_menu_option(locator, value)
            if locator.input_value() != value:
                raise SecurityViolation("field read-back did not match input")
            purchaser_id = self._form_page.page.frame_locator(
                _FORM_SCOPE_FRAME
            ).locator("input#UserName")
            if purchaser_id.count() != 1 or not purchaser_id.input_value():
                raise SecurityViolation("purchaser selection was not confirmed")
            return
        if action is WriteAction.SET_AI_INPUT:
            if value is None:
                raise SecurityViolation("field value is required")
            locator.fill(value)
            if locator.input_value() != value:
                raise SecurityViolation("field read-back did not match input")
            return
        if action is WriteAction.SET_QUOTATION_TYPE:
            if value not in _QUOTATION_TYPES:
                raise SecurityViolation("quotation type is not allowlisted")
            self._pick_menu_option(locator, value)
            if locator.input_value() != value:
                raise SecurityViolation("quotation type read-back did not match")
            return
        if action is WriteAction.RUN_AI_RECOGNITION:
            locator.click()
            return
        if action is WriteAction.AI_ENTRY_COMMIT:
            # Client-side hand-back: the panel returns the recognized row and
            # closes itself, so this click must not be mistaken for a Save. The
            # recognized row landing in the bill grid is verified separately by
            # the caller's read-back, never assumed from this click.
            locator.click()
            return
        if action in {WriteAction.SAVE_DATA, WriteAction.SAVE_AND_SEND}:
            locator.click()
            return
        raise SecurityViolation("action is not available in the purchase writer")


class InsoPurchaseWriter:
    """Draft actions and one closed, durable-before-dispatch Save Data path."""

    def __init__(
        self,
        *,
        form_page: OperationPage,
        ai_panel: AiFrameProvider | None = None,
        gate: FeatureGate | None = None,
        ai_result_reader: AiResultReader | None = None,
    ) -> None:
        self._gate = gate or ProductionWriteGate()
        self._form_page = form_page
        self._ai_panel = ai_panel or AiEntryPanel(form_page)
        self._ai_result_reader = ai_result_reader or PlaywrightAiResultReader(
            self._ai_panel
        )
        self._port = _PlaywrightActionPort(form_page, self._ai_panel)
        self._registry = SelectorRegistry()
        for action, binding in _BINDINGS.items():
            if (action is WriteAction.SAVE_AND_SEND
                    and not isinstance(self._gate, OwnerAuthorizedSaveAndSendGate)):
                continue
            self._registry.register(
                action,
                binding.selector_id,
                binding.scope_id,
                binding.semantics,
            )
        self._registry.deny("#bcSend")
        if not isinstance(self._gate, OwnerAuthorizedSaveAndSendGate):
            self._registry.deny("#btnSave2")
        self._actions = InsoDraftActions(
            gate=self._gate,
            registry=self._registry,
            candidate_source=self._port,
            dispatcher=self._port,
        )

    def new_draft(self) -> None:
        self._actions.new_draft()

    def set_customer(self, value: str) -> None:
        if value not in _CUSTOMERS:
            raise SecurityViolation("customer is not allowlisted")
        self._actions.set_customer(value)

    def set_purchaser(self, value: str) -> None:
        if value not in _PURCHASERS:
            raise SecurityViolation("purchaser is not allowlisted")
        purchaser_id = self._form_page.page.frame_locator(
            "iframe#winIframealert_enquiry"
        ).locator("input#UserName")
        if purchaser_id.count() != 1 or purchaser_id.input_value():
            raise SecurityViolation("purchaser field is not blank and unique")
        self._actions.set_purchaser(value)

    def set_quotation_type(self, _value: str) -> None:
        if _value not in _QUOTATION_TYPES:
            raise SecurityViolation("quotation type is not allowlisted")
        self._actions.set_quotation_type(_value)

    def open_ai_entry(self) -> None:
        """Open the form's own AI录单 panel; it is an in-page frame, not a tab.

        The form's select menu can still be open when this runs (the purchaser
        pick leaves its menu covering ``#ai_import_``), so the panel's own
        control check fails closed unless the form is clear first.
        """

        _require_inso_origin(self._form_page.page.url)
        self._ai_panel.open()

    def set_ai_input(self, value: str) -> None:
        self._actions.set_ai_input(value)

    def run_ai_recognition(self) -> None:
        self._actions.run_ai_recognition()

    def read_ai_result(self) -> AiRecognitionResult:
        if self._ai_result_reader is None:
            raise SecurityViolation("AI result selectors are not verified")
        result = self._ai_result_reader.read()
        if result is None or not result.ready:
            raise SecurityViolation("AI recognition is not ready")
        return result

    def close_ai_entry(self) -> None:
        """Close the AI录单 panel; the draft form itself is left open for Save."""

        panel_close = getattr(self._ai_panel, "close", None)
        if callable(panel_close):
            panel_close()

    def commit_ai_entry(self) -> None:
        """Let the ERP fill the bill row itself; nothing is typed into the bill.

        The 采购临时询价 form is the operator's surface, and its 编码/型号/品牌/数量
        cells are not ours to type into. The ERP's own path is the AI录单 panel's
        保存数据, whose handler is ``pasteImport() -> AiImport.doImport()``:
        ``returnSet(buildResult())`` hands the recognized row back and
        ``windowsClose()`` fires the dialog's close callback
        (``ai_appendRow()``), which reloads the bill grid with that row.
        """

        self._actions.commit_ai_entry()

    def dismiss_order_surface(self) -> bool:
        """Return the INSO session to the 业务询价 list between orders.

        Owner rule (2026-09-30): every new order starts from the INSO home page
        entered through 业务询价, with nothing of the previous order left open.
        The ERP keeps the 采购临时询价 window -- customer selector and AI录单
        panel included -- across orders, so the next order ran against the
        previous order's form: the purchaser control ended holding both
        ``陈熙`` and ``颜浩坚``, and the only symptom was ``CONTROL_NOT_FOUND``.

        Returns whether the surface is confirmed clear. "Clear" means nothing of
        the previous order is *showing*: the ERP keeps every closed dialog and
        its iframe in the DOM, so the hidden leftovers that prove the close
        happened must not be mistaken for a window that is still open.
        """

        page = self._form_page.page
        _require_inso_origin(page.url)
        if self._order_form_is_present():
            try:
                self._port.dismiss_select_menu()
            except SecurityViolation:
                return False
        if self._ai_panel_is_open():
            self.close_ai_entry()
        if self._order_window_is_open() and not self._close_order_window():
            return False
        if self._order_window_is_open() or self._ai_panel_is_open():
            return False
        return page.locator(_OPEN_SELECT_MENU).count() == 0

    def _order_form_is_present(self) -> bool:
        """Whether the order form iframe is in the DOM at all.

        Presence is not openness: the iframe stays behind after the window
        closes, so this only decides whether the in-frame select menu can exist.
        """

        return self._form_page.page.locator(_FORM_SCOPE_FRAME).count() == 1

    def _order_window(self) -> Any | None:
        """Return the dialog hosting this order's form iframe, or ``None``.

        ``None`` means the form iframe is not in the DOM, so no window can be
        open. An ambiguous DOM raises instead, so callers fail closed rather
        than close an unrelated dialog.
        """

        form = self._form_page.page.locator(_FORM_SCOPE_FRAME)
        count = form.count()
        if count == 0:
            return None
        if count != 1:
            raise SecurityViolation("order form frame is not unique")
        window = self._form_page.page.locator(_ORDER_WINDOW_DIALOG).filter(has=form)
        if window.count() != 1:
            raise SecurityViolation("order window dialog is not unique")
        return window

    def _order_window_is_open(self) -> bool:
        """Whether the 采购临时询价 window is showing; ambiguity reads as open."""

        try:
            window = self._order_window()
        except SecurityViolation:
            return True
        return window is not None and window.is_visible()

    def _ai_panel_is_open(self) -> bool:
        """Whether the AI录单 panel is showing; ambiguity reads as open."""

        panel = self._form_page.page.locator(_AI_ENTRY_DIALOG)
        count = panel.count()
        if count == 0:
            return False
        if count != 1:
            return True
        return panel.is_visible()

    def _close_order_window(self) -> bool:
        """Close the 采购临时询价 window, resolved by the form it holds.

        The window is the dialog that contains this exact form iframe, so no
        unrelated dialog can be dismissed by mistake and no window that is not
        the current order's can be closed. An already-hidden window counts as
        closed -- the ERP leaves the dialog and its iframe in the DOM, and only
        its visibility says whether it is still up.
        """

        try:
            window = self._order_window()
            if window is None or not window.is_visible():
                return True
            close = window.locator(_DIALOG_CLOSE_CONTROL)
            if close.count() != 1 or not close.is_visible() or not close.is_enabled():
                return False
            close.click(timeout=_DIALOG_CLOSE_TIMEOUT_MS)
        except SecurityViolation:
            return False
        except Exception:  # noqa: BLE001 - browser ambiguity fails closed
            return False
        try:
            window = self._order_window()
        except SecurityViolation:
            return False
        return window is None or not window.is_visible()

    def save_data(
        self, store: SaveDispatchStore, inquiry_id: str, *, at: datetime
    ) -> None:
        """Dispatch only after durable AI_RECOGNIZED state and exact Save control.

        ``begin_save_dispatch`` persists UNKNOWN before the final semantic
        re-check and private click. Any failure after that boundary stays
        UNKNOWN and must be reconciled; this method never retries.
        """

        self._gate.require_open()
        self._registry.resolve(WriteAction.SAVE_DATA, self._port.candidates())
        # The store rejects every state except AI_RECOGNIZED, including a
        # previous UNKNOWN outcome, before the private dispatcher can click.
        store.begin_save_dispatch(inquiry_id, at=at)
        self._actions.save_data()

    def save_and_send(
        self, store: SaveDispatchStore, inquiry_id: str, *, at: datetime,
    ) -> None:
        """One dispatch only; UNKNOWN is committed before any irreversible click."""
        if not isinstance(self._gate, OwnerAuthorizedSaveAndSendGate):
            raise SecurityViolation("save-and-send is not authorized")
        self._gate.require_save_and_send()
        self._registry.resolve(WriteAction.SAVE_AND_SEND, self._port.candidates())
        store.begin_save_dispatch(inquiry_id, at=at, save_and_send=True)
        self._actions.save_and_send()


def _require_inso_origin(url: str) -> None:
    parsed = urlsplit(url)
    if (
        parsed.scheme != "https"
        or parsed.hostname != "yingsuo.alperp.cn"
        or parsed.username
        or parsed.password
    ):
        raise SecurityViolation("INSO origin is not verified")


def _is_verified_inso_url(url: str) -> bool:
    try:
        _require_inso_origin(url)
    except SecurityViolation:
        return False
    return not urlsplit(url).path.casefold().endswith("/login.aspx")


def _require_ai_entry_url(url: str) -> None:
    """The AI录单 frame is the verified entry page on the verified origin.

    The ERP appends its own routing query (``BillPage``, ``VendorID``, ``h``) and
    ``VendorID`` is populated with the real vendor in production, so the query
    is intentionally not pinned; scheme, host, path and the absence of embedded
    credentials/fragment are the identity boundary.
    """

    parsed = urlsplit(url)
    if (
        parsed.scheme != "https"
        or parsed.hostname != "yingsuo.alperp.cn"
        or parsed.path != AI_ENTRY_PATH
        or parsed.username
        or parsed.password
        or parsed.fragment
    ):
        raise SecurityViolation("AI entry frame identity is not verified")


def _is_verified_ai_entry_url(url: str) -> bool:
    try:
        _require_ai_entry_url(url)
    except SecurityViolation:
        return False
    return True


def _frame_is_detached(frame: Any) -> bool:
    is_detached = getattr(frame, "is_detached", None)
    if not callable(is_detached):
        return False
    try:
        return bool(is_detached())
    except Exception:  # noqa: BLE001 - browser ambiguity fails closed
        return True
