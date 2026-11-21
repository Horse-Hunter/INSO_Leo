"""Purchase draft preparation using the existing INSO action boundary.

Draft entry is the ERP's own native paste import: the 粘贴 dialog parses
``型号|数量|品牌`` server-side, hands the rows back client-side, and the ERP's
``appendRow()`` writes them into the bill grid. No AI recognition service is
used anywhere on the production path.

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

#: The purchase form's own 粘贴 dialog. Verified live 2026-11-21: the form's
#: ``product_import()`` opens ``windows('粘贴导入', 1050, 600,
#: 'product/Import.aspx?BillPage=…&VendorID=…', …, appendRow)``.
PASTE_ENTRY_PATH = "/skins/etaoerp/product/Import.aspx"

#: The business-inquiry LIST page's bulk import. Same dialog title, different
#: handler: its 保存数据 binds ``Import()`` -> ``$.post(?action=Import)`` and
#: requires a returned ``BillID``, so it creates server-side bills. Owner
#: 2026-11-21: this path must never be used for the draft flow, so it is
#: rejected by identity rather than merely avoided.
BULK_IMPORT_PATH = "/skins/etaoerp/innerenquiry/yewuxj/import.aspx"

_QUOTATION_TYPES = frozenset({"需要问全价格", "普通询价"})
_CUSTOMERS = frozenset({"深圳阿尔克贸易有限公司"})
_PURCHASERS = frozenset({"颜浩坚", "陈熙"})

# The ERP now carries two separate customer records with the identical display
# name, phone, contact and owner; only their record id differs. A name-only pick
# is therefore ambiguous and correctly fails closed. The Owner identified the
# intended record on 2026-11-14 (the first row of the site's own menu), and this
# id pins that exact record so the click never depends on menu ordering: the
# option row must carry both the allowlisted name and this id, or nothing is
# clicked. Replace the former customer ``Win Source Elec. Tech. Ltd``, which the
# ERP no longer offers at all (verified live, 2026-11-14 11:31).
_CUSTOMER_ROW_MARKERS = {"深圳阿尔克贸易有限公司": "4526000"}

_log = logging.getLogger("inso.purchase_writer")


@dataclass(frozen=True, slots=True)
class DraftPreviewResult:
    """One verified paste-preview row: model, brand, quantity and the ERP code.

    ``product_id`` is the 编码/型号 the ERP resolved for this model. It is read
    as evidence only: the Owner contract validates exactly model, brand and
    quantity, and nothing on the draft path may write or invent that code.
    """

    product_id: str
    model: str
    brand: str
    quantity: int
    ready: bool


class DraftPreviewReader(Protocol):
    def read(self) -> DraftPreviewResult | None: ...


class PastePanel(Protocol):
    """Anything that can hand back the verified 粘贴 dialog frame."""

    def frame(self) -> Any: ...

    def assert_fresh(self) -> None: ...


class ParentProductFields(Protocol):
    """Read-only view of the parent form's product row.

    There are deliberately no setters. The 采购临时询价 form is the operator's
    surface and the ERP fills its 编码/型号/品牌/数量 row itself when the 粘贴
    dialog commits (``pasteImport(1)`` -> ``appendRow``); typing those cells was
    a process defect (Owner finding, 2026-10-01), not a shortcut this seam may
    offer.
    """

    def wait_for_row(self, expected_product_id: str, timeout_seconds: float) -> bool: ...

    def wait_for_model(self, expected_model: str, timeout_seconds: float) -> bool: ...

    def read_product_id(self) -> str | None: ...

    def read_model(self) -> str | None: ...

    def read_brand(self) -> str | None: ...

    def read_quantity(self) -> int | None: ...


class PlaywrightParentProductFields:
    """The four verified product inputs in the leased parent inquiry form.

    The first grid column is ``编码/型号`` and is bound to ``ProductID``; the
    型号 column is a separate ``PartNo`` cell. Both are filled by the ERP when
    the 粘贴 dialog commits its rows.

    This seam is read-only by design: no row creation, no cell writing, no
    import, Save, or Send behaviour. It exists to prove what the ERP put in the
    row, not to manufacture it. ``wait_for_row`` absorbs the one genuine
    asynchrony -- ``appendRow`` updates the grid through ``layui.table``, so a
    read issued the instant the dialog closes can still see the old body.
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

    def wait_for_model(self, expected_model: str, timeout_seconds: float) -> bool:
        """Wait for ERP's imported model, never require or validate its code."""
        if not isinstance(expected_model, str) or not expected_model:
            raise SecurityViolation("expected parent model is invalid")
        deadline = time.monotonic() + timeout_seconds
        while True:
            if self.read_model() == expected_model:
                return True
            if time.monotonic() >= deadline:
                return False
            self._form_page.page.wait_for_timeout(self._POLL_MILLISECONDS)

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

    def record_submit_click(self, inquiry_id: str, *, at: datetime) -> None: ...

    def begin_save_dispatch(
        self, inquiry_id: str, *, at: datetime, save_and_send: bool = False,
    ) -> None: ...


class PasteImportPanel:
    """The purchase form's own 粘贴 dialog; an in-page frame, not a tab.

    Verified live 2026-11-21. The form's ``#product_import_`` control is the one
    labelled "粘贴"; the LIST page has an identically identified control labelled
    "导入" that opens a *different* dialog which creates server-side bills, so
    position and label are both checked and the frame URL is pinned to
    :data:`PASTE_ENTRY_PATH`.

    Clicking it runs ``product_import()``, which calls the ERP's own
    ``windows('粘贴导入', 1050, 600, 'product/Import.aspx?BillPage=…&VendorID=…',
    [导入, 保存数据], appendRow)``. The dialog is an in-page ``details-dialog``
    holding that iframe inside the same serial ERP page, so nothing here creates
    or navigates a page.
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
            _PASTE_ENTRY_WAIT_SECONDS if wait_seconds is None else wait_seconds
        )
        self._poll_milliseconds = (
            _PASTE_ENTRY_POLL_MILLISECONDS
            if poll_milliseconds is None
            else poll_milliseconds
        )

    def open(self) -> None:
        page = self._form_page.page
        _require_inso_origin(page.url)
        entry = page.frame_locator(_FORM_SCOPE_FRAME).locator(_PASTE_ENTRY_CONTROL)
        if (
            entry.count() != 1
            or not entry.is_visible()
            or not entry.is_enabled()
            or (entry.inner_text() or "").strip() != _PASTE_ENTRY_LABEL
        ):
            raise SecurityViolation("paste entry control is not uniquely actionable")
        entry.click()
        self._frame = self._await_frame(page)

    def frame(self) -> Any:
        frame = self._frame
        if frame is None or _frame_is_detached(frame):
            raise SecurityViolation("paste dialog is not open")
        _require_paste_entry_url(str(getattr(frame, "url", "")))
        return frame

    def host(self) -> Any:
        """The dialog element hosting this exact paste frame.

        Resolved through the frame it holds, so no unrelated dialog can be
        mistaken for this one and its footer controls are always the ones that
        belong to the import we just ran.
        """

        frame = self.frame()
        parent = frame.parent_frame
        dialog = parent.locator(_PASTE_DIALOG)
        if dialog.count() != 1:
            raise SecurityViolation("paste dialog is not unique")
        # Anchored by the iframe the dialog must hold. ``filter(has=…)`` cannot
        # be used here: the element handle belongs to the parent frame while the
        # locator would be resolved in it, and Playwright rejects that mix.
        if dialog.locator(_PASTE_DIALOG_IFRAME).count() != 1:
            raise SecurityViolation("paste dialog does not hold the paste frame")
        return dialog

    def assert_fresh(self) -> None:
        """Prove the preview is empty *before* the parse is triggered.

        The single leftover-risk this flow has is reading a previous order's
        rows. The ERP itself closes that door: the 保存数据 control starts
        disabled and the grid is only populated by a parse response. Checking
        both here means the row read later can only come from our own import.
        """

        frame = self.frame()
        rows = _paste_preview_rows(frame)
        if rows is None:
            raise SecurityViolation("paste preview state is unreadable")
        if rows:
            raise SecurityViolation("paste preview already held rows before import")
        button = self._form_page.page.locator(_PASTE_COMMIT_CONTROL)
        if button.count() != 1:
            raise SecurityViolation("paste commit control is not unique")
        if button.is_enabled():
            raise SecurityViolation("paste commit control was enabled before import")

    def close(self) -> bool:
        """Dismiss only this dialog; the draft form stays open for Save.

        Verified live: closing hides the dialog and leaves its iframe in the
        DOM, so a closed dialog is detected by visibility, never by absence.
        """

        frame = self._frame
        self._frame = None
        try:
            page = self._form_page.page
            _require_inso_origin(page.url)
        except SecurityViolation:
            _log.warning(
                "paste dialog was not dismissed: INSO page identity is not verified"
            )
            return False
        if frame is not None and self._close_frame_dialog(frame):
            return True
        if frame is not None:
            try:
                if not frame.frame_element().is_visible():
                    return True
            except Exception:  # noqa: BLE001 - a detached frame means it is gone
                return True
        _log.warning("paste dialog was not dismissed: no clickable close control")
        return False

    @staticmethod
    def _close_frame_dialog(frame: Any) -> bool:
        """Close the unique dialog containing this exact paste frame."""

        try:
            parent = frame.parent_frame
            dialog = parent.locator(_PASTE_DIALOG)
            if dialog.count() != 1:
                return False
            if dialog.locator(_PASTE_DIALOG_IFRAME).count() != 1:
                return False
            for selector in (_PASTE_DIALOG_CLOSE_CONTROL, _PASTE_CANCEL_CONTROL):
                control = dialog.locator(selector)
                if (
                    control.count() == 1
                    and control.is_visible()
                    and control.is_enabled()
                ):
                    control.click(timeout=10_000)
                    return True
            return False
        except Exception:  # noqa: BLE001 - browser ambiguity fails closed
            return False

    def _await_frame(self, page: Any) -> Any:
        deadline = time.monotonic() + self._wait_seconds
        while True:
            for frame in page.frames:
                if _is_verified_paste_entry_url(str(getattr(frame, "url", ""))):
                    return frame
            if time.monotonic() >= deadline:
                raise SecurityViolation("paste dialog did not open")
            page.wait_for_timeout(self._poll_milliseconds)


class PlaywrightPastePreviewReader:
    """Read the verified single-row paste preview and its readiness.

    Readiness is two conditions taken from the page itself, never a delay: the
    ERP's own table cache holds exactly the expected rows, and the 保存数据
    control has been enabled by a successful parse. Either one missing still
    returns ``None`` so the caller fails closed.

    Values are read from ``layui.table.cache['dg']``, not from rendered cells: a
    long MPN is visually elided by the fixed-width table (a real order showed
    ``TRJC476K01...`` while the value was complete), so text is never trusted.
    """

    def __init__(
        self,
        panel: PastePanel,
        *,
        expected_rows: int = 1,
        wait_seconds: float | None = None,
        poll_milliseconds: int | None = None,
    ) -> None:
        self._panel = panel
        self._expected_rows = expected_rows
        self._wait_seconds = (
            _PASTE_READY_WAIT_SECONDS if wait_seconds is None else wait_seconds
        )
        self._poll_milliseconds = (
            _PASTE_READY_POLL_MILLISECONDS
            if poll_milliseconds is None
            else poll_milliseconds
        )

    def read(self) -> DraftPreviewResult | None:
        frame = self._panel.frame()
        deadline = time.monotonic() + self._wait_seconds
        while True:
            result = self._read_once(frame)
            if result is not None:
                return result
            if time.monotonic() >= deadline:
                return None
            frame.wait_for_timeout(self._poll_milliseconds)

    def _read_once(self, frame: Any) -> DraftPreviewResult | None:
        button = frame.parent_frame.locator(_PASTE_COMMIT_CONTROL)
        if button.count() != 1 or not button.is_enabled():
            return None
        rows = _paste_preview_rows(frame)
        if rows is None or len(rows) != self._expected_rows:
            return None
        row = rows[0]
        model = row.get("PartNo")
        brand = row.get("Brand")
        quantity = _strict_positive_int(row.get("Qty"))
        if not isinstance(model, str) or not model:
            return None
        if not isinstance(brand, str) or not brand:
            return None
        if quantity is None:
            return None
        product_id = row.get("ProductID")
        return DraftPreviewResult(
            product_id if isinstance(product_id, str) else "",
            model,
            brand,
            quantity,
            ready=True,
        )


def _paste_preview_rows(frame: Any) -> list[dict[str, Any]] | None:
    """The ERP's own preview row cache, or ``None`` when it is unreadable.

    ``table.cache['dg']`` is what the dialog hands to ``appendRow``; reading it
    is reading the same data the commit will use, not a rendering of it.
    """

    try:
        value = frame.evaluate(
            "() => { const t = window.layui && layui.table && layui.table.cache;"
            " const rows = t ? t['dg'] : null;"
            " return rows ? JSON.parse(JSON.stringify(rows)) : null; }"
        )
    except Exception:  # noqa: BLE001 - an unreadable cache is not an empty one
        return None
    if value is None:
        # Before the first parse the table has never been initialised; the
        # dialog's own disabled commit control is what proves that state.
        return []
    if not isinstance(value, list):
        return None
    return [row for row in value if isinstance(row, dict)]


def _strict_positive_int(value: Any) -> int | None:
    """An exact positive integer, or ``None``.

    Deliberately strict: a quantity that arrives as ``"200.0"``, ``"2e2"`` or
    ``"200 个"`` is not the number we sent, and accepting it would let a wrong
    quantity pass by truncation. Only ASCII digits are an integer here.
    """

    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text or not text.isascii() or not text.isdigit():
        return None
    number = int(text)
    return number if number > 0 else None


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
    WriteAction.SAVE_DATA,
    WriteAction.RUN_PASTE_IMPORT,
    WriteAction.PASTE_ENTRY_COMMIT,
    WriteAction.SAVE_AND_SEND,
})

#: Scopes that only exist while the verified 粘贴 dialog is open.
_PASTE_SCOPES = frozenset({"paste", "paste-dialog"})

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
    WriteAction.SET_PASTE_DATA: _Binding(
        "paste-data-input",
        "paste-import",
        "textarea#pasteData",
        ControlSemantics(
            "textbox",
            "",
            "",
            (("id", "pasteData"), ("type", "textarea")),
        ),
        "paste",
    ),
    WriteAction.RUN_PASTE_IMPORT: _Binding(
        "paste-import-control",
        "paste-import-dialog",
        "#win_btn__dialog11",
        # Bound by id alone, exactly like SAVE_DATA: a bare <button> reports
        # type="submit", and a "type=submit" attribute would trip the denied
        # semantics guard even though this control only runs the ERP's parse.
        ControlSemantics("button", "导入", "导入", (("id", "win_btn__dialog11"),)),
        "paste-dialog",
    ),
    WriteAction.PASTE_ENTRY_COMMIT: _Binding(
        "paste-entry-commit",
        "paste-import-dialog",
        "#win_btn__dialog12",
        # 保存数据 hands the preview rows back to the parent form; it is not a
        # server Save. Verified live 2026-11-21 with a request listener.
        ControlSemantics("button", "保存数据", "保存数据", (("id", "win_btn__dialog12"),)),
        "paste-dialog",
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
# cells keep covering #product_import_, so the 粘贴 control can never be clicked
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
# The ERP renders the company menu from its own list call, which has been seen
# to take several seconds, and the widget can swallow the open click: clearing
# and focusing the input already fires its focus handler, so the following click
# can toggle the popup back shut. Live 2026-11-14: two drafts failed here with
# ``SELECT_OPTION_UNAVAILABLE`` after exactly the old 6 s window even though the
# identical option was present and clickable by hand. The wait is therefore
# longer and bounded, and a menu that never appears is re-opened a few times
# before the step fails closed. Nothing about the pick itself is relaxed.
_MENU_WAIT_SECONDS = 20.0
_MENU_RECLICK_SECONDS = 2.0
_MENU_RECLICKS = 3

# The draft entry is the purchase form's own 粘贴 control, verified live
# 2026-11-21: ``#product_import_`` (labelled "粘贴") runs ``product_import()``,
# which opens ``windows('粘贴导入', 1050, 600,
# 'product/Import.aspx?BillPage=…&VendorID=…', [导入, 保存数据], appendRow)``.
# It is an in-page panel, never a new tab, so nothing in this module creates a
# page.
#
# The same id exists on the business-inquiry LIST page where it is labelled
# "导入" and opens ``innerenquiry/yewuxj/Import.aspx``; that dialog's 保存数据 is
# ``Import()`` -> ``$.post(?action=Import)`` and returns a ``BillID``, i.e. it
# creates server-side bills. Pinning the iframe path below is what keeps the two
# apart, because position and label alone would not.
_PASTE_ENTRY_CONTROL = "#product_import_"
_PASTE_ENTRY_LABEL = "粘贴"
_PASTE_DIALOG = "details-dialog._dialog1"
_PASTE_DIALOG_IFRAME = "#winIframe_dialog1"
_PASTE_DIALOG_CLOSE_CONTROL = 'button[title="关闭窗口"]'
_PASTE_CANCEL_CONTROL = 'button:has-text("取消")'

# The dialog's own footer. Live read 2026-11-21: 导入 is ``#win_btn__dialog11``
# and runs ``pasteImport(0)`` -> ``$.post('/services/product/import.ashx
# ?action=PasteImport…')``, which is the ERP's *parse*; 保存数据 is
# ``#win_btn__dialog12``, starts ``disabled``, and runs ``pasteImport(1)``, which
# is ``returnSet(DetailData)`` + ``windowsClose()`` with no request of any kind.
# The dialog's close callback ``appendRow()`` then writes the rows into the bill
# grid. Neither control is the form's 保存 (``button#btnSave`` -> bill_save_auto),
# which stays gated.
_PASTE_IMPORT_CONTROL = "#win_btn__dialog11"
_PASTE_COMMIT_CONTROL = "#win_btn__dialog12"

# The 采购临时询价 window is its own dialog and the 粘贴 dialog is a sibling
# dialog of it. Both live on the INSO home page rather than on a page of their
# own, so clearing them returns the session to the home page and its 业务询价
# list without navigating anywhere.
#
# Closing a dialog here only sets ``display:none``. The dialog, its close control
# and its iframe document all stay in the DOM (read-only live read,
# 2026-09-30: ``iframe#winIframealert_enquiry`` count stayed 1 with the hosting
# ``details-dialog.alert_enquiry`` at ``display:none``; the 粘贴 dialog behaves
# the same, confirmed 2026-11-21). Presence therefore can never prove a window is
# gone -- an earlier version of this module used ``count() == 0`` as its cleared
# check and so reported every surface as unclearable, which would have refused
# every order at the purchase step with ``CONTROL_NOT_FOUND``. Only visibility
# can, and a window that is already hidden is a success, not a failure.
_ORDER_WINDOW_DIALOG = "details-dialog"
_DIALOG_CLOSE_CONTROL = 'button[title="关闭窗口"]'
_DIALOG_CLOSE_TIMEOUT_MS = 10_000
_PASTE_ENTRY_WAIT_SECONDS = 15.0
_PASTE_ENTRY_POLL_MILLISECONDS = 200

# The parse runs server-side and arrives asynchronously: right after the click
# the grid is still empty and 保存数据 is still disabled, and only a successful
# response populates ``layui.table.cache['dg']`` and enables the commit control.
# Readiness is therefore two page conditions -- expected row count and an
# enabled commit control -- polled until they hold. A fixed delay is never used
# as the condition, and a genuine failure (no row, wrong row count, unreadable
# cache) still fails closed rather than being mistaken for the in-flight state.
_PASTE_READY_WAIT_SECONDS = 30.0
_PASTE_READY_POLL_MILLISECONDS = 250


class _PlaywrightActionPort:
    """Private exact-selector bridge; callers only receive business methods."""

    def __init__(self, form_page: OperationPage, paste_panel: PastePanel) -> None:
        self._form_page = form_page
        self._paste_panel = paste_panel

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
        if binding.frame == "paste":
            # The paste box lives in the form's own 粘贴 dialog frame, so the
            # frame is re-verified on every use rather than trusted once.
            frame = self._paste_panel.frame()
            _require_paste_entry_url(str(getattr(frame, "url", "")))
            return frame.locator(binding.selector)
        if binding.frame == "paste-dialog":
            # The footer controls sit in the dialog that *hosts* the paste frame,
            # not in the frame itself. They are resolved through that same frame,
            # so they can only ever be reached while this dialog is open, and a
            # dialog that is not this one fails closed.
            dialog = self._paste_panel.host()
            return dialog.locator(binding.selector)
        raise SecurityViolation("unknown INSO selector scope")

    def _unique_menu_option(self, menu: Any, value: str, marker: str | None = None) -> Any | None:
        """The one rendered option carrying ``value`` in one of its own cells.

        The ERP's menus are tables, and which column holds the name differs per
        field: the company menu leads with the company, while the purchaser menu
        leads with a blank column and puts the person's name third. Matching one
        whole cell exactly -- rather than a column position or a substring --
        keeps the click bound to a single verified option.

        ``marker`` is supplied only for a field whose site data holds several
        records under the identical visible name (the company menu currently
        does). It must appear in a cell of the same row, so the surviving option
        is proven by data instead of by menu position, and a row that carries the
        name without the marker is never clicked.
        """

        matches: list[tuple[Any, list[str]]] = []
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
                matches.append((row, texts))
        if not matches:
            items = menu.locator(_MENU_ITEM)
            for index in range(items.count()):
                item = items.nth(index)
                if (item.inner_text() or "").strip() == value:
                    matches.append((item, []))
        # The marker only ever breaks a tie between rows that already match the
        # exact name, so a unique name keeps the original single-match contract.
        # Ambiguity that the marker cannot resolve still returns ``None``.
        if marker is not None and len(matches) > 1:
            matches = [match for match in matches if marker in match[1]]
        return matches[0][0] if len(matches) == 1 else None

    def _pick_menu_option(self, field: Any, value: str, marker: str | None = None) -> None:
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
        next_click = time.monotonic() + _MENU_RECLICK_SECONDS
        reclicks, opened = 0, False
        while time.monotonic() < deadline:
            if menu.count() == 1:
                opened = True
                self._clear_checked_options(menu)
                option = self._unique_menu_option(menu, value, marker)
                if option is not None:
                    option.click()
                    self._dismiss_select_menu()
                    return
            elif not opened and reclicks < _MENU_RECLICKS and time.monotonic() >= next_click:
                # A swallowed open click is retried a bounded number of times; the
                # option still has to match exactly (and carry the marker, when the
                # field needs one) before anything is clicked.
                field.click()
                reclicks += 1
                next_click = time.monotonic() + _MENU_RECLICK_SECONDS
            page.wait_for_timeout(150)
        if not opened:
            raise SecurityViolation("select menu did not open")
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
        covering ``#product_import_``, so the 粘贴 control can never be clicked.
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

    def _paste_dialog_is_ready(self) -> bool:
        try:
            self._paste_panel.frame()
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
            if _BINDINGS[action].frame not in _PASTE_SCOPES or self._paste_dialog_is_ready()
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
            self._pick_menu_option(locator, value, _CUSTOMER_ROW_MARKERS.get(value))
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
        if action is WriteAction.SET_PASTE_DATA:
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
        if action is WriteAction.RUN_PASTE_IMPORT:
            locator.click()
            return
        if action is WriteAction.PASTE_ENTRY_COMMIT:
            # Client-side hand-back: the dialog returns the parsed rows and closes
            # itself, so this click must not be mistaken for a Save. The rows
            # landing in the bill grid is verified separately by the caller's
            # read-back, never assumed from this click.
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
        paste_panel: PastePanel | None = None,
        gate: FeatureGate | None = None,
        preview_reader: DraftPreviewReader | None = None,
    ) -> None:
        self._gate = gate or ProductionWriteGate()
        self._form_page = form_page
        self._paste_panel = paste_panel or PasteImportPanel(form_page)
        self._preview_reader = preview_reader or PlaywrightPastePreviewReader(
            self._paste_panel
        )
        self._port = _PlaywrightActionPort(form_page, self._paste_panel)
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

    def open_paste_entry(self) -> None:
        """Open the form's own 粘贴 dialog; it is an in-page frame, not a tab.

        The form's select menu can still be open when this runs (the purchaser
        pick leaves its menu covering the toolbar), so the dialog's own control
        check fails closed unless the form is clear first.
        """

        _require_inso_origin(self._form_page.page.url)
        self._paste_panel.open()

    def assert_paste_preview_fresh(self) -> None:
        """Refuse to import on top of a preview that was not ours."""

        self._paste_panel.assert_fresh()

    def set_paste_data(self, value: str) -> None:
        self._actions.set_paste_data(value)

    def run_paste_import(self) -> None:
        self._actions.run_paste_import()

    def read_paste_preview(self) -> DraftPreviewResult:
        if self._preview_reader is None:
            raise SecurityViolation("paste preview selectors are not verified")
        result = self._preview_reader.read()
        if result is None or not result.ready:
            raise SecurityViolation("paste preview is not ready")
        return result

    def close_paste_entry(self) -> None:
        """Dismiss the 粘贴 dialog; the draft form itself is left open for Save."""

        panel_close = getattr(self._paste_panel, "close", None)
        if callable(panel_close):
            panel_close()

    def commit_paste_entry(self) -> None:
        """Let the ERP fill the bill rows itself; nothing is typed into the bill.

        The 采购临时询价 form is the operator's surface, and its 编码/型号/品牌/数量
        cells are not ours to type into. The ERP's own path is the 粘贴 dialog's
        保存数据, whose handler is ``pasteImport(1)``: ``returnSet(DetailData)``
        hands the parsed rows back and ``windowsClose()`` fires the dialog's
        close callback (``appendRow()``), which writes those rows into the bill
        grid. Verified live 2026-11-21: no request leaves the browser.
        """

        self._actions.commit_paste_entry()

    def dismiss_order_surface(self) -> bool:
        """Return the INSO session to the 业务询价 list between orders.

        Owner rule (2026-09-30): every new order starts from the INSO home page
        entered through 业务询价, with nothing of the previous order left open.
        The ERP keeps the 采购临时询价 window -- customer selector and its sibling
        dialogs included -- across orders, so the next order ran against the
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
        if self._paste_dialog_is_open():
            self.close_paste_entry()
        if self._order_window_is_open() and not self._close_order_window():
            return False
        if self._order_window_is_open() or self._paste_dialog_is_open():
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

    def _paste_dialog_is_open(self) -> bool:
        """Whether the 粘贴 dialog is showing; ambiguity reads as open."""

        dialog = self._form_page.page.locator(_PASTE_DIALOG)
        count = dialog.count()
        if count == 0:
            return False
        if count != 1:
            return True
        return dialog.is_visible()

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
        store.record_submit_click(inquiry_id, at=at)


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


def _require_paste_entry_url(url: str) -> None:
    """The 粘贴 frame is the form's own paste page on the verified origin.

    Two dialogs in this ERP share the title "粘贴导入" and only this one may be
    used: the form's ``product/Import.aspx``, whose 保存数据 is a client-side
    hand-back. The list page's ``innerenquiry/yewuxj/Import.aspx`` looks the same
    but its 保存数据 posts ``action=Import`` and creates server-side bills, so it
    is rejected explicitly rather than merely not linked to.

    The ERP appends its own routing query (``BillPage``, ``VendorID``, ``h``) and
    ``VendorID`` is empty on a fresh draft, so the query is intentionally not
    pinned; scheme, host, path and the absence of embedded credentials/fragment
    are the identity boundary.
    """

    parsed = urlsplit(url)
    if parsed.path.casefold() == BULK_IMPORT_PATH:
        raise SecurityViolation("bulk import dialog is forbidden")
    if (
        parsed.scheme != "https"
        or parsed.hostname != "yingsuo.alperp.cn"
        or parsed.path != PASTE_ENTRY_PATH
        or parsed.username
        or parsed.password
        or parsed.fragment
    ):
        raise SecurityViolation("paste dialog frame identity is not verified")


def _is_verified_paste_entry_url(url: str) -> bool:
    try:
        _require_paste_entry_url(url)
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
