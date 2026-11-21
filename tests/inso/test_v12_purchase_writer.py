from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import ClassVar

import pytest

import src.inso.purchase_writer as purchase_writer_module
from src.inso.purchase_writer import (
    _PASTE_DIALOG,
    _BINDINGS,
    _ID_ONLY_ACTIONS,
    _MENU_CHECKBOX,
    _OPEN_SELECT_MENU,
    PasteImportPanel,
    InsoPurchaseWriter,
    PlaywrightPastePreviewReader,
    PlaywrightParentProductFields,
    _PlaywrightActionPort,
)
from src.inso.session import SecurityViolation
from src.inso.write_safety import (
    ControlSemantics,
    FakeWriteGate,
    ProductionWriteGate,
    WriteAction,
    assert_safe_control_semantics,
)

NOW = datetime(2026, 9, 26, tzinfo=UTC)


class _OperationPage:
    def __init__(self, page):
        self.page = page


_FIELD_ATTRIBUTES = {
    "input#ImpValueF": "importance",
    "input#CompanyName": "customer",
    "input#UserName_text": "purchaser",
}


class _Locator:
    def __init__(
        self,
        page,
        selector: str,
        *,
        text: str = "",
        value: str = "",
        parent: _Locator | None = None,
        index: int | None = None,
    ):
        self.page = page
        self.selector = selector
        self.text = text
        self.value = value
        self.parent = parent
        self.index = index

    # -- structure ---------------------------------------------------------
    def locator(self, selector: str) -> _Locator:
        return _Locator(self.page, selector, parent=self)

    def nth(self, index: int) -> _Locator:
        return _Locator(self.page, self.selector, parent=self.parent, index=index)

    @property
    def first(self) -> _Locator:
        return self.nth(0)

    def _option_text(self) -> str:
        options = self.page.menu_options(self.page.open_menu)
        if self.index is None or self.index >= len(options):
            return ""
        return options[self.index]

    def count(self):
        selector = self.selector
        if selector == _OPEN_SELECT_MENU:
            return 1 if self.page.open_menu else 0
        if self.parent is not None and self.parent.selector == _OPEN_SELECT_MENU:
            return len(self.page.menu_options(self.page.open_menu))
        if selector == "td":
            return 1 if (self.parent is not None and self.parent.selector == "tr") else 0
        if _MENU_CHECKBOX == selector:
            return 1 if (self.parent is not None and self.parent.selector == "tr") else 0
        # Live behaviour (2026-09-30): the ERP only sets ``display:none`` when a
        # dialog closes. The iframe element and its document stay in the DOM, so
        # count stays 1 for the rest of the session once the window was opened.
        if selector == "iframe#winIframealert_enquiry":
            return 1 if self.page.form_in_dom else 0
        if selector == "details-dialog":
            return int(self.page.form_in_dom) + int(self.page.paste_in_dom)
        if selector == _PASTE_DIALOG:
            return 1 if self.page.paste_in_dom else 0
        if selector in _FIELD_ATTRIBUTES:
            return 1
        if selector == "input#UserName":
            return 1
        if selector == "_PASTE_IMPORT":
            return 1
        if selector == "button#btnSave":
            return self.page.save_count
        if selector.startswith('input[data-f="'):
            return 1
        return 0

    def is_visible(self) -> bool:
        if self.selector == _PASTE_DIALOG:
            return self.page.paste_open
        return True

    def evaluate_all(self, _script):
        if self.selector == "button#btnSave":
            return [
                {
                    "role": "button",
                    "accessibleName": self.page.save_text,
                    "visibleText": self.page.save_text,
                    "id": "btnSave",
                    "type": "submit",
                    "enabled": self.page.save_enabled,
                    "visible": self.page.save_visible,
                }
                for _ in range(self.page.save_count)
            ]
        if self.selector not in _FIELD_ATTRIBUTES:
            return []
        return [
            {
                "role": "textbox",
                "accessibleName": "",
                "visibleText": "",
                "id": self.selector.split("#", 1)[1],
                "type": "text",
                "enabled": True,
                "visible": True,
            }
        ]

    def click(self):
        selector = self.selector
        if selector in _FIELD_ATTRIBUTES:
            if self.page.open_menu not in (None, selector):
                # Exactly the live symptom: the still-open select menu covers
                # the next control, so its click never lands.
                raise TimeoutError("covered by an open select menu")
            self.page.open_menu = selector
        elif self.parent is not None and self.parent.selector == _OPEN_SELECT_MENU:
            self.page.pick(self.page.open_menu, self._option_text())
        elif selector == "button#btnSave":
            self.page.events.append("click")

    def evaluate(self, _script, _arg=None):
        # The site closes a leftover select menu on a document click; the fake
        # mirrors that by clearing the open menu when the body is clicked.
        if self.selector == "body":
            if not self.page.dismiss_resistant:
                self.page.open_menu = None
            self.page.body_clicks += 1

    def fill(self, value: str = ""):
        attribute = _FIELD_ATTRIBUTES.get(self.selector)
        if attribute is not None:
            setattr(self.page, attribute, value)

    def input_value(self):
        if self.selector.startswith('input[data-f="'):
            return self.value
        attribute = _FIELD_ATTRIBUTES.get(self.selector)
        if attribute is not None:
            return getattr(self.page, attribute)
        if self.selector == "input#UserName":
            return self.page.purchaser_id
        return self.page.value

    def inner_text(self):
        if self.parent is not None and self.parent.selector == _OPEN_SELECT_MENU:
            return self._option_text()
        if self.parent is not None and self.parent.selector == "tr":
            return self.parent._option_text()
        return self.text

    def all(self):
        return [
            _Locator(self.page, self.selector, text=option, index=index)
            for index, option in enumerate(self.page.options)
        ]

    def is_checked(self) -> bool:
        if self.selector == _MENU_CHECKBOX and self.parent is not None:
            return self.page.is_row_checked(self.page.open_menu, self.parent.index)
        return False

    def filter(self, has=None):
        """The dialog lookup used to reach the 采购临时询价 window itself."""
        return _Window(self.page)


class _CloseControl:
    """The window's own close control.

    Live behaviour: it stays in the DOM after the window closes, but it is not
    visible then, so a hidden leftover must never be read as "still open".
    """

    def __init__(self, page):
        self.page = page

    def count(self):
        return 1 if (self.page.form_in_dom and self.page.window_close_available) else 0

    def is_visible(self):
        return self.page.form_window_open and self.page.window_close_available

    def is_enabled(self):
        return True

    def click(self, timeout=None):
        # Closing hides the dialog; the ERP does not remove it, so the iframe
        # and this control both stay in the DOM.
        self.page.form_window_open = False
        self.page.events.append("close-inquiry-window")


class _Window:
    """The 采购临时询价 window, resolved by the form iframe it holds.

    It is found by the iframe it contains, so it exists for as long as that
    iframe is in the DOM -- which is after the window closes, too. Openness is
    ``is_visible``, never presence.
    """

    def __init__(self, page):
        self.page = page

    def count(self):
        if self.page.order_window_ambiguous:
            return 2
        return 1 if self.page.form_in_dom else 0

    def is_visible(self):
        return self.page.form_window_open

    def locator(self, _selector: str):
        return _CloseControl(self.page)


class _Frame:
    def __init__(self, page):
        self.page = page

    def locator(self, selector: str):
        return _Locator(self.page, selector)


class _FakeFormPage:
    """Fake ERP form: entity fields are picked from the site's own menu.

    The purchaser control is modelled as what the live ERP really renders: a
    checkbox multi-select whose own ``data-options`` declares ``checkbox:true``.
    A pick there *toggles one box* and the widget then writes every checked
    name, so a pick can leave two purchasers selected.
    """

    url = "https://yingsuo.alperp.cn/"
    options = ("需要问全价格", "普通询价")
    company_rows = ("RS TRADING", "深圳阿尔克贸易有限公司")
    purchaser_rows = ("陈熙", "颜浩坚")
    # The ids the live controlled menu renders (read-only live read, 2026-09-30).
    purchaser_ids: ClassVar[dict[str, str]] = {"陈熙": "7432", "颜浩坚": "16665"}

    def __init__(self):
        self.value = ""
        self.importance = ""
        self.customer = ""
        self.purchaser = ""
        self.purchaser_id = ""
        # What the widget renders as already checked. The ERP re-checks the
        # previously used purchaser when a draft opens, and the hidden id field
        # stays blank until a pick writes it -- exactly as observed live.
        self.purchaser_checked: list[str] = []
        # The 采购临时询价 window hosting the form, and whether its own close
        # control is reachable at all. ``form_in_dom`` is separate because the
        # ERP only hides a closed window: the iframe stays behind, so presence
        # can never stand in for openness.
        self.form_window_open = True
        self.form_in_dom = True
        self.window_close_available = True
        self.order_window_ambiguous = False
        # The sibling AI录单 dialog behaves the same way.
        self.paste_in_dom = True
        self.paste_open = False
        self.open_menu = None
        self.body_clicks = 0
        self.dismiss_resistant = False
        self.save_count = 1
        self.save_text = "保存"
        self.save_enabled = True
        self.save_visible = True
        self.events = []

    def frame_locator(self, _selector: str):
        return _Frame(self)

    def locator(self, selector: str):
        return _Locator(self, selector)

    def is_row_checked(self, menu, index) -> bool:
        if menu != "input#UserName_text" or index is None:
            return False
        if index >= len(self.purchaser_rows):
            return False
        return self.purchaser_rows[index] in self.purchaser_checked

    def wait_for_timeout(self, _milliseconds: int) -> None:
        return None

    def menu_options(self, menu):
        return {
            "input#CompanyName": self.company_rows,
            "input#UserName_text": self.purchaser_rows,
            "input#ImpValueF": self.options,
        }.get(menu, ())

    def pick(self, menu, text: str) -> None:
        """The site's own selection: it sets the field.

        Live behaviour: the customer menu closes itself after the pick, but the
        purchaser menu stays open, so the fake leaves that one open too. Only
        the subsequent document click (``_dismiss_select_menu``) closes it.

        The purchaser pick toggles one checkbox and the widget writes every
        checked name, which is how a second order ended up with both
        ``陈熙`` and ``颜浩坚`` selected.
        """

        if menu == "input#UserName_text":
            if text in self.purchaser_checked:
                self.purchaser_checked.remove(text)
            elif text:
                self.purchaser_checked.append(text)
            self.purchaser = ",".join(self.purchaser_checked)
            self.purchaser_id = ",".join(
                self.purchaser_ids[name] for name in self.purchaser_checked
            )
        else:
            attribute = _FIELD_ATTRIBUTES.get(menu or "")
            if attribute is not None:
                setattr(self, attribute, text)
        self.value = self.importance
        self.open_menu = None if menu != "input#UserName_text" else menu


DEFAULT_PREVIEW_ROW = {
    "PartNo": "LM358",
    "Brand": "Texas Instruments",
    "Qty": "123",
    "ProductID": "P216328",
}


class _FakePasteFrame:
    """The 粘贴 dialog frame: its textarea, commit state and row cache.

    Modelled on the live page (2026-11-21): the dialog holds
    ``textarea#pasteData``, the 保存数据 control lives in the hosting dialog's
    footer and starts disabled, and the parsed rows live in
    ``layui.table.cache['dg']`` -- not in the rendered cells, which elide long
    part numbers.
    """

    url = (
        "https://yingsuo.alperp.cn/skins/etaoerp/product/Import.aspx"
        "?BillPage=Enquiry&VendorID=&h=510"
    )

    def __init__(
        self,
        *,
        rows=None,
        ready: bool = True,
        commit_enabled: bool | None = None,
        settle_after: int = 0,
        never_settles: bool = False,
    ):
        self.final_rows = [dict(r) for r in (rows if rows is not None else [DEFAULT_PREVIEW_ROW])]
        self.ready = ready
        self.commit_enabled = ready if commit_enabled is None else commit_enabled
        self.settle_after = settle_after
        self.never_settles = never_settles
        self.text = ""
        self.polls = 0
        # The commit control lives in the hosting dialog, not in the frame.
        self.parent_frame = _DialogFooter(commit_enabled=self.commit_enabled)

    def is_detached(self) -> bool:
        return False

    def wait_for_timeout(self, _milliseconds: int) -> None:
        self.polls += 1
        if self.never_settles or self.ready:
            return
        if self.polls >= self.settle_after:
            self.ready = True
            self.commit_enabled = True
            # The footer is the dialog's, not the frame's: keep it in step with
            # the parse that just succeeded.
            self.parent_frame.commit_enabled = True

    def locator(self, selector: str):
        if selector == "textarea#pasteData":
            return _Locator(self, selector, value=self.text)
        return _Locator(self, selector)

    def evaluate(self, _script: str):
        return [dict(row) for row in self.final_rows] if self.ready else []

    def frame_element(self):
        return self


class _FakePastePanel:
    """The form's 粘贴 entry: opening it yields the in-page dialog frame.

    It deliberately has no page of its own -- the live product opens a dialog
    inside the purchase ERP page, never a new tab.
    """

    def __init__(
        self,
        *,
        rows=None,
        ready: bool = True,
        commit_enabled: bool | None = None,
        settle_after: int = 0,
        never_settles: bool = False,
        opens: bool = True,
        on_close=None,
    ):
        self.frame_obj = _FakePasteFrame(
            rows=rows,
            ready=ready,
            commit_enabled=commit_enabled,
            settle_after=settle_after,
            never_settles=never_settles,
        )
        self.opens = opens
        self.opened = False
        self.close_calls = 0
        self.fresh_checks = 0
        self._on_close = on_close
        self.host_obj = None

    def open(self) -> None:
        if not self.opens:
            raise SecurityViolation("paste dialog did not open")
        self.opened = True

    def frame(self):
        if not self.opened:
            raise SecurityViolation("paste dialog is not open")
        return self.frame_obj

    def host(self):
        if not self.opened:
            raise SecurityViolation("paste dialog is not open")
        if self.host_obj is None:
            return SimpleNamespace(
                locator=lambda _selector: _DialogButton(
                    enabled=self.frame_obj.commit_enabled
                )
            )
        if self.host_obj.count() != 1:
            raise SecurityViolation("paste dialog is not unique")
        return self.host_obj

    def assert_fresh(self) -> None:
        self.fresh_checks += 1
        frame = self.frame()
        if frame.ready:
            raise SecurityViolation("paste preview already held rows before import")
        if frame.commit_enabled:
            raise SecurityViolation("paste commit control was enabled before import")

    def close(self) -> None:
        self.close_calls += 1
        self.opened = False
        if self._on_close is not None:
            self._on_close()


class _DialogButton:
    """A footer control that only answers count/is_enabled."""

    def __init__(self, *, enabled: bool = True) -> None:
        self.enabled = enabled

    def count(self):
        return 1

    def is_enabled(self) -> bool:
        return self.enabled

    def is_visible(self) -> bool:
        return True

    def click(self, **_kwargs) -> None:
        self.enabled = True

@pytest.mark.parametrize("value", ["需要问全价格", "普通询价"])
def test_quotation_type_maps_to_exact_importance_control(value: str) -> None:
    form_page = _FakeFormPage()
    writer = InsoPurchaseWriter(
        form_page=_OperationPage(form_page),
        paste_panel=_FakePastePanel(),
        gate=FakeWriteGate(enabled=True),
    )

    writer.set_quotation_type(value)

    assert form_page.value == value


def test_quotation_type_rejects_values_outside_the_two_business_routes() -> None:
    writer = InsoPurchaseWriter(
        form_page=_OperationPage(_FakeFormPage()),
        paste_panel=_FakePastePanel(),
        gate=FakeWriteGate(enabled=True),
    )

    with pytest.raises(SecurityViolation):
        writer.set_quotation_type("意向单询价")


def test_production_gate_is_closed_and_generic_send_methods_do_not_exist() -> None:
    form_page = _FakeFormPage()
    writer = InsoPurchaseWriter(
        form_page=_OperationPage(form_page),
        paste_panel=_FakePastePanel(),
    )

    assert hasattr(writer, "save_data")
    assert callable(writer.save_and_send)
    assert not {"send", "submit"} & set(dir(writer))
    store = _SaveStore()
    with pytest.raises(SecurityViolation):
        writer.save_and_send(store, "synthetic-inquiry", at=NOW)
    # Default production authorization still forbids both irreversible actions.
    with pytest.raises(SecurityViolation):
        writer.save_data(type("Store", (), {"begin_save_dispatch": lambda *_a, **_k: None})(), "inq-1", at=NOW)
    assert form_page.value == ""
    assert store.calls == []
    assert form_page.events == []


def test_only_owner_authorized_save_and_send_has_a_binding_not_generic_send() -> None:
    source = Path("src/inso/purchase_writer.py").read_text(encoding="utf-8")

    bindings = source.split("_BINDINGS:", 1)[1].split("class _PlaywrightActionPort", 1)[0]
    assert _BINDINGS[WriteAction.SAVE_AND_SEND].selector == "button#btnSave2"
    assert _BINDINGS[WriteAction.SAVE_AND_SEND].semantics.accessible_name == "保存并发送"
    assert "#bcSend" not in bindings


class _DialogFooter:
    """The 粘贴 dialog's own footer, mirroring the live DOM (2026-11-21).

    导入 is ``#win_btn__dialog11`` (always enabled) and 保存数据 is
    ``#win_btn__dialog12`` (disabled until a parse succeeds).
    """

    def __init__(
        self,
        *,
        dialog_count: int = 1,
        buttons: int = 1,
        commit_enabled: bool = True,
    ) -> None:
        self.dialog_count = dialog_count
        self.buttons = buttons
        self.commit_enabled = commit_enabled
        self.outer: list[str] = []
        self.inner: list[str] = []
        self.clicks: list[str] = []

    def locator(self, selector):
        self.outer.append(selector)
        if selector in ('button[title="关闭窗口"]', 'button:has-text("取消")'):
            return _DialogButtons(self.host_of(selector))
        return _DialogLocator(self)

    def host_of(self, selector):
        return self

    def filter(self, **_kwargs):
        return self

    def count(self):
        return self.dialog_count

    def is_visible(self) -> bool:
        return True


class _DialogLocator:
    def __init__(self, host: _DialogFooter) -> None:
        self.host = host

    def count(self):
        return self.host.dialog_count

    def is_enabled(self) -> bool:
        return self.host.commit_enabled

    def filter(self, **_kwargs):
        return self

    def locator(self, selector):
        self.host.inner.append(selector)
        return _DialogButtons(self.host)


class _DialogButtons:
    def __init__(self, host: _DialogFooter) -> None:
        self.host = host

    def count(self):
        return self.host.buttons

    def is_visible(self) -> bool:
        return True

    def is_enabled(self) -> bool:
        return True

    def click(self, **_kwargs) -> None:
        self.host.clicks.append("click")


class _DialogPasteFrame(_FakePasteFrame):
    """The panel frame, hosted by the dialog that owns its footer."""

    def __init__(self, dialog: _DialogFooter, **kwargs) -> None:
        super().__init__(**kwargs)
        self.parent_frame = dialog


def _commit_port(dialog: _DialogFooter) -> _PlaywrightActionPort:
    panel = _FakePastePanel()
    panel.frame_obj = _DialogPasteFrame(dialog)
    panel.host_obj = dialog
    panel.open()
    return _PlaywrightActionPort(_OperationPage(SimpleNamespace()), panel)


def test_paste_commit_binding_targets_the_dialogs_own_commit_control() -> None:
    """保存数据 hands the preview rows back; it is not the form's 保存.

    A bare ``<button>`` reports ``type="submit"``, and "submit" is a denied
    semantic, so the control is bound by its verified id alone -- the same
    concession SAVE_DATA makes for the same reason. Live 2026-11-21: the parse
    control is ``#win_btn__dialog11`` (导入) and the hand-back is
    ``#win_btn__dialog12`` (保存数据); they must never be confused.
    """

    binding = _BINDINGS[WriteAction.PASTE_ENTRY_COMMIT]

    assert binding.frame == "paste-dialog"
    assert binding.selector == "#win_btn__dialog12"
    assert binding.semantics == ControlSemantics(
        "button", "保存数据", "保存数据", (("id", "win_btn__dialog12"),)
    )
    assert WriteAction.PASTE_ENTRY_COMMIT in _ID_ONLY_ACTIONS
    assert_safe_control_semantics(binding.semantics)


def test_paste_import_binding_is_the_parse_control_not_the_commit() -> None:
    binding = _BINDINGS[WriteAction.RUN_PASTE_IMPORT]

    assert binding.frame == "paste-dialog"
    assert binding.selector == "#win_btn__dialog11"
    assert binding.semantics == ControlSemantics(
        "button", "导入", "导入", (("id", "win_btn__dialog11"),)
    )
    assert WriteAction.RUN_PASTE_IMPORT in _ID_ONLY_ACTIONS
    assert binding.selector != _BINDINGS[WriteAction.PASTE_ENTRY_COMMIT].selector


def test_paste_data_binding_is_the_dialog_textarea() -> None:
    binding = _BINDINGS[WriteAction.SET_PASTE_DATA]

    assert binding.frame == "paste"
    assert binding.selector == "textarea#pasteData"


def test_paste_commit_resolves_only_inside_the_dialogs_own_footer() -> None:
    dialog = _DialogFooter()

    locator = _commit_port(dialog)._locator(_BINDINGS[WriteAction.PASTE_ENTRY_COMMIT])

    assert locator.count() == 1
    assert dialog.outer == ["#win_btn__dialog12"]


def test_paste_commit_fails_closed_when_the_host_dialog_is_not_unique() -> None:
    with pytest.raises(SecurityViolation):
        _commit_port(_DialogFooter(dialog_count=2))._locator(
            _BINDINGS[WriteAction.PASTE_ENTRY_COMMIT]
        )


def test_writer_lets_the_erp_fill_the_row_and_offers_no_way_to_type_it() -> None:
    writer = InsoPurchaseWriter(
        form_page=_OperationPage(SimpleNamespace()),
        paste_panel=_FakePastePanel(),
        gate=FakeWriteGate(enabled=False),
    )

    assert hasattr(writer, "commit_paste_entry")
    for name in ("set_product_id", "set_model", "set_brand", "set_quantity"):
        assert not hasattr(writer, name)


def _opened_panel(**kwargs) -> _FakePastePanel:
    panel = _FakePastePanel(**kwargs)
    panel.open()
    return panel


def test_paste_reader_returns_the_parsed_row_and_the_erp_code() -> None:
    reader = PlaywrightPastePreviewReader(_opened_panel())

    result = reader.read()
    assert result is not None
    assert (
        result.product_id,
        result.model,
        result.brand,
        result.quantity,
        result.ready,
    ) == (
        "P216328",
        "LM358",
        "Texas Instruments",
        123,
        True,
    )


@pytest.mark.parametrize("product_id", [None, "", "P216328", "P999999"])
def test_paste_reader_accepts_business_fields_without_a_product_code(product_id) -> None:
    """Owner contract: only model, brand and quantity gate the commit.

    The ERP resolves 编码/型号 itself; a missing or unexpected code is evidence,
    never a reason to invent one or to block the draft.
    """

    row = {"PartNo": "LM358", "Brand": "Texas Instruments", "Qty": "123"}
    if product_id is not None:
        row["ProductID"] = product_id
    reader = PlaywrightPastePreviewReader(
        _opened_panel(rows=[row]),
        wait_seconds=0.05,
        poll_milliseconds=1,
    )

    result = reader.read()
    assert result is not None
    assert (result.model, result.brand, result.quantity, result.ready) == (
        "LM358", "Texas Instruments", 123, True,
    )
    assert result.product_id == (product_id or "")


def test_paste_reader_waits_for_the_async_parse_before_reading() -> None:
    """The parse is a server round-trip: rows and enablement arrive later.

    A single immediate read sees an empty grid and a disabled 保存数据, so the
    reader must poll on page state rather than on a fixed delay.
    """

    panel = _opened_panel(ready=False, settle_after=3)
    reader = PlaywrightPastePreviewReader(panel)

    result = reader.read()

    assert result is not None
    assert (result.model, result.brand, result.quantity) == (
        "LM358", "Texas Instruments", 123,
    )
    assert panel.frame_obj.polls == 3


def test_paste_reader_fails_closed_until_the_parse_settles() -> None:
    reader = PlaywrightPastePreviewReader(
        _opened_panel(ready=False, never_settles=True),
        wait_seconds=0.05,
        poll_milliseconds=1,
    )

    assert reader.read() is None


def test_paste_reader_requires_an_open_dialog() -> None:
    """Reading before the dialog exists is misuse, not a preview state."""

    reader = PlaywrightPastePreviewReader(
        _FakePastePanel(), wait_seconds=0.05, poll_milliseconds=1
    )

    with pytest.raises(SecurityViolation):
        reader.read()


@pytest.mark.parametrize("quantity", ["123.0", "1e3", "123 个", "", "0", "-5", " ", True, 123])
def test_paste_reader_rejects_any_quantity_that_is_not_exactly_positive_integer(quantity) -> None:
    """Truncating ``"123.0"`` would let a wrong quantity pass; only digits do."""

    row = {"PartNo": "LM358", "Brand": "Texas Instruments", "Qty": quantity}
    reader = PlaywrightPastePreviewReader(
        _opened_panel(rows=[row]),
        wait_seconds=0.05,
        poll_milliseconds=1,
    )

    assert reader.read() is None


@pytest.mark.parametrize("rows", [[], [DEFAULT_PREVIEW_ROW, dict(DEFAULT_PREVIEW_ROW)]])
def test_paste_reader_requires_exactly_one_preview_row(rows) -> None:
    """One order is one row: an empty or multi-row preview is not this draft."""

    reader = PlaywrightPastePreviewReader(
        _opened_panel(rows=rows),
        wait_seconds=0.05,
        poll_milliseconds=1,
    )

    assert reader.read() is None


def test_paste_reader_requires_the_commit_control_to_be_enabled() -> None:
    """Rows without an enabled 保存数据 means the parse did not succeed."""

    reader = PlaywrightPastePreviewReader(
        _opened_panel(rows=[DEFAULT_PREVIEW_ROW], commit_enabled=False),
        wait_seconds=0.05,
        poll_milliseconds=1,
    )

    assert reader.read() is None


def test_paste_panel_refuses_to_import_on_top_of_a_previous_preview() -> None:
    """The only stale-row risk this flow has, closed by the ERP itself."""

    fresh = _opened_panel(ready=False, commit_enabled=False)
    fresh.assert_fresh()
    assert fresh.fresh_checks == 1

    stale = _opened_panel(ready=True)
    with pytest.raises(SecurityViolation):
        stale.assert_fresh()

class _SaveStore:
    def __init__(self, *, recognized: bool = True, events=None):
        self.recognized = recognized
        self.calls = []
        self.events = events if events is not None else []

    def begin_save_dispatch(self, inquiry_id: str, *, at: datetime) -> None:
        self.events.append("begin")
        self.calls.append((inquiry_id, at))
        if not self.recognized:
            raise RuntimeError("purchase is not AI_RECOGNIZED")


def test_save_persists_unknown_before_the_only_fake_save_dispatch() -> None:
    form = _FakeFormPage()
    store = _SaveStore(events=form.events)
    writer = InsoPurchaseWriter(
        form_page=_OperationPage(form),
        paste_panel=_FakePastePanel(),
        gate=FakeWriteGate(enabled=True),
    )

    writer.save_data(store, "synthetic-inquiry", at=NOW)

    assert store.calls == [("synthetic-inquiry", NOW)]
    assert form.events == ["begin", "click"]


def test_save_preflights_unique_visible_enabled_exact_control() -> None:
    form = _FakeFormPage()
    store = _SaveStore()
    writer = InsoPurchaseWriter(
        form_page=_OperationPage(form),
        paste_panel=_FakePastePanel(),
        gate=FakeWriteGate(enabled=True),
    )

    for attribute, value in (
        ("save_count", 2),
        ("save_visible", False),
        ("save_enabled", False),
        ("save_text", "保存并发送"),
    ):
        setattr(form, attribute, value)
        with pytest.raises(SecurityViolation):
            writer.save_data(store, "synthetic-inquiry", at=NOW)
        assert store.calls == []
        assert form.events == []
        setattr(form, attribute, 1 if attribute == "save_count" else True if attribute in {"save_visible", "save_enabled"} else "保存")


def test_closed_production_gate_never_reaches_store_or_save_control() -> None:
    form = _FakeFormPage()
    store = _SaveStore()
    writer = InsoPurchaseWriter(
        form_page=_OperationPage(form),
        paste_panel=_FakePastePanel(),
        gate=ProductionWriteGate(),
    )

    with pytest.raises(SecurityViolation):
        writer.save_data(store, "synthetic-inquiry", at=NOW)

    assert store.calls == []
    assert form.events == []


def test_non_ai_recognized_store_state_never_dispatches_save() -> None:
    form = _FakeFormPage()
    store = _SaveStore(recognized=False)
    writer = InsoPurchaseWriter(
        form_page=_OperationPage(form),
        paste_panel=_FakePastePanel(),
        gate=FakeWriteGate(enabled=True),
    )

    with pytest.raises(RuntimeError):
        writer.save_data(store, "synthetic-inquiry", at=NOW)

    assert form.events == []
    assert callable(writer.save_and_send)
    calls_before = list(store.calls)
    with pytest.raises(SecurityViolation):
        writer.save_and_send(store, "synthetic-inquiry", at=NOW)
    assert store.calls == calls_before
    assert form.events == []


class _ParentLocator:
    def __init__(self, frame, selector):
        self.frame = frame
        self.selector = selector

    def count(self):
        return self.frame.counts.get(self.selector, 0)

    def is_visible(self):
        return self.frame.visible

    def is_enabled(self):
        return self.frame.enabled

    def dblclick(self):
        self.frame.editing = self.selector

    def locator(self, selector):
        if selector == "input":
            return _ParentEditor(self.frame, self.selector)
        assert selector == ".layui-table-cell"
        return _ParentRendered(self.frame, self.selector)


class _ParentEditor:
    def __init__(self, frame, selector):
        self.frame = frame
        self.selector = selector

    def count(self):
        return 1 if self.frame.editing == self.selector else 0

    def is_visible(self):
        return self.count() == 1 and self.frame.visible

    def is_enabled(self):
        return self.count() == 1 and self.frame.enabled

    def fill(self, value):
        self.frame.values[self.selector] = value

    def input_value(self):
        return self.frame.values.get(self.selector, "")


class _ParentRendered:
    def __init__(self, frame, selector):
        self.frame = frame
        self.selector = selector

    def count(self):
        return 1

    def is_visible(self):
        return self.frame.visible

    def inner_text(self):
        return self.frame.values.get(self.selector, "")


class _ParentFrame:
    name = "winIframealert_enquiry"
    url = "https://yingsuo.alperp.cn/InnerEnquiry/YeWuXJ/Enquiry.aspx"

    def __init__(self):
        self.visible = True
        self.enabled = True
        self.counts = {
            '#_id_dg td[data-field="ProductID"]': 1,
            '#_id_dg td[data-field="PartNo"]': 1,
            '#_id_dg td[data-field="Brand"]': 1,
            '#_id_dg td[data-field="Qty"]': 1,
        }
        self.values = {}
        self.editing = None

    def locator(self, selector):
        return _ParentLocator(self, selector)


class _ParentPage:
    url = "https://yingsuo.alperp.cn/"

    def __init__(self, frames):
        self.frames = frames
        self.polls = 0

    def wait_for_timeout(self, _milliseconds: int) -> None:
        self.polls += 1

    def locator(self, selector):
        assert selector == "iframe#winIframealert_enquiry"
        matching = [frame for frame in self.frames if frame.name == "winIframealert_enquiry"]
        return _ParentFrameElement(matching)


class _ParentFrameElement:
    """Mirrors the real API shape: ``content_frame`` lives on the handle."""

    def __init__(self, frames):
        self.frames = frames

    def count(self):
        return len(self.frames)

    def is_visible(self):
        return len(self.frames) == 1 and self.frames[0].visible

    def element_handle(self):
        if len(self.frames) != 1:
            return None
        return _ParentFrameHandle(self.frames[0])


class _ParentFrameHandle:
    def __init__(self, frame):
        self._frame = frame

    def content_frame(self):
        return self._frame


def _parent_fields(*, frame=None):
    frame = frame or _ParentFrame()
    return PlaywrightParentProductFields(_OperationPage(_ParentPage([frame]))), frame


def _rendered_row(frame, *, product_id="P216328", model="STM32F103", brand="ST", qty="12"):
    frame.values['#_id_dg td[data-field="ProductID"]'] = product_id
    frame.values['#_id_dg td[data-field="PartNo"]'] = model
    frame.values['#_id_dg td[data-field="Brand"]'] = brand
    frame.values['#_id_dg td[data-field="Qty"]'] = qty


def test_parent_product_fields_read_the_row_the_erp_rendered() -> None:
    fields, frame = _parent_fields()
    _rendered_row(frame)

    assert fields.read_product_id() == "P216328"
    assert fields.read_model() == "STM32F103"
    assert fields.read_brand() == "ST"
    assert fields.read_quantity() == 12


def test_parent_product_fields_expose_no_way_to_type_into_the_bill() -> None:
    """Owner rule (2026-10-01): 采购临时询价 must not have these cells filled by us.

    The ERP fills them itself when the AI录单 panel commits (``保存数据`` ->
    ``pasteImport`` -> ``ai_appendRow``). A seam that can write them is the
    process defect, so the capability must not exist at all -- neither on the
    live adapter nor on the protocol the coordinator codes against.
    """

    for name in ("set_product_id", "set_model", "set_brand", "set_quantity", "_set"):
        assert not hasattr(PlaywrightParentProductFields, name)


@pytest.mark.parametrize(
    ("selector", "reader"),
    (
        ('#_id_dg td[data-field="ProductID"]', "read_product_id"),
        ('#_id_dg td[data-field="PartNo"]', "read_model"),
        ('#_id_dg td[data-field="Brand"]', "read_brand"),
        ('#_id_dg td[data-field="Qty"]', "read_quantity"),
    ),
)
def test_parent_product_fields_missing_or_duplicate_cells_read_as_absent(
    selector, reader
) -> None:
    fields, frame = _parent_fields()
    _rendered_row(frame)

    frame.counts[selector] = 0
    assert getattr(fields, reader)() is None
    frame.counts[selector] = 2
    assert getattr(fields, reader)() is None
    frame.counts[selector] = 1


def test_parent_product_fields_wrong_frame_or_origin_reads_as_absent() -> None:
    frame = _ParentFrame()
    frame.url = "https://evil.example.invalid/form"
    fields, _ = _parent_fields(frame=frame)

    assert fields.read_model() is None


def test_parent_product_fields_reject_unusable_quantity() -> None:
    fields, frame = _parent_fields()
    _rendered_row(frame, qty="not-a-number")
    assert fields.read_quantity() is None

    _rendered_row(frame, qty="0")
    assert fields.read_quantity() is None


def test_wait_for_row_returns_as_soon_as_the_erp_renders_the_handed_back_row() -> None:
    fields, frame = _parent_fields()
    _rendered_row(frame)

    assert fields.wait_for_row("P216328", 1.0) is True


def test_wait_for_row_fails_closed_when_the_row_never_arrives() -> None:
    """``ai_appendRow`` reloads the grid asynchronously; the wait is bounded and
    a row that never shows the recognized 编码 is reported as absent, never
    assumed from the commit click."""

    fields, frame = _parent_fields()
    _rendered_row(frame, product_id="P999999")

    assert fields.wait_for_row("P216328", 0.05) is False
    assert frame.visible is True  # the cell is readable; it simply is not the row


class _ScopedShellFrame:
    def __init__(self) -> None:
        self.selectors: list[str] = []

    def locator(self, selector: str):
        self.selectors.append(selector)
        return ("shell", selector)


class _ScopedPageHandle:
    url = "https://yingsuo.alperp.cn/skins/etaoerp//InnerEnquiry/YeWuXJ/List.aspx"

    def __init__(self) -> None:
        self.frame_selectors: list[str] = []

    def frame_locator(self, selector: str):
        self.frame_selectors.append(selector)
        return _ScopedElement(selector)


class _ScopedElement:
    def __init__(self, selector: str) -> None:
        self.selector = selector

    def locator(self, selector: str):
        return ("nested", self.selector, selector)


def test_list_actions_scope_to_the_verified_shell_frame() -> None:
    """The list controls live in the document the session already verified.

    Live failure class (2026-09-29): the Owner's environment renders the
    business-inquiry list as that verified document itself, so the hard-coded
    wrapper frame ``iframe#iframe_YeWuXJ_frame`` matched nothing and 新增 was
    reported as an unknown control (``CONTROL_NOT_FOUND``).
    """

    shell = _ScopedShellFrame()
    handle = _ScopedPageHandle()
    form = SimpleNamespace(page=handle, shell_frame=shell)
    port = _PlaywrightActionPort(form, form)

    binding = _BINDINGS[WriteAction.NEW_DRAFT]
    assert port._locator(binding) == ("shell", binding.selector)
    assert shell.selectors == [binding.selector]
    assert handle.frame_selectors == []


def test_list_actions_fall_back_to_the_wrapper_frame() -> None:
    """Without a verified shell the wrapper frame stays the only scope tried."""

    handle = _ScopedPageHandle()
    form = SimpleNamespace(page=handle)
    port = _PlaywrightActionPort(form, form)

    binding = _BINDINGS[WriteAction.NEW_DRAFT]
    assert port._locator(binding) == (
        "nested",
        "iframe#iframe_YeWuXJ_frame",
        binding.selector,
    )
    assert handle.frame_selectors == ["iframe#iframe_YeWuXJ_frame"]


def _writer(form_page: _FakeFormPage) -> InsoPurchaseWriter:
    return InsoPurchaseWriter(
        form_page=_OperationPage(form_page),
        paste_panel=_FakePastePanel(
            on_close=lambda: setattr(form_page, "paste_open", False)
        ),
        gate=FakeWriteGate(enabled=True),
    )


def test_customer_is_picked_from_the_site_menu_so_the_next_step_is_reachable() -> None:
    """Live failure (2026-09-29): writing text left the menu covering the form.

    ``set_customer`` used to call ``fill`` only. The ERP's select box then kept
    its company menu open over the 重要程度 field, so every later click timed out
    and the whole draft reported CONTROL_NOT_FOUND. The selection has to be the
    site's own option click.
    """

    form_page = _FakeFormPage()
    writer = _writer(form_page)

    writer.set_customer("深圳阿尔克贸易有限公司")

    assert form_page.customer == "深圳阿尔克贸易有限公司"
    assert form_page.open_menu is None
    writer.set_quotation_type("需要问全价格")
    assert form_page.importance == "需要问全价格"


def test_a_select_menu_left_open_blocks_the_next_control() -> None:
    form_page = _FakeFormPage()
    form_page.open_menu = "input#CompanyName"
    with pytest.raises(TimeoutError):
        _writer(form_page).set_quotation_type("需要问全价格")


def test_purchaser_pick_dismisses_the_menu_the_site_leaves_open() -> None:
    """Live failure (2026-09-29): the purchaser menu does not close on its own.

    After 颜浩坚 was picked the menu was still open and its own table cells kept
    covering ``#product_import_``, so the AI录单 control could never be clicked. The
    pick therefore has to be followed by the site's own document-click dismiss.
    """

    form_page = _FakeFormPage()
    writer = _writer(form_page)

    writer.set_purchaser("颜浩坚")

    assert form_page.purchaser == "颜浩坚"
    assert form_page.purchaser_id == "16665"
    assert form_page.open_menu is None
    assert form_page.body_clicks >= 1


def test_a_menu_that_will_not_close_fails_closed(monkeypatch) -> None:
    monkeypatch.setattr(purchase_writer_module, "_MENU_WAIT_SECONDS", 0.05)
    form_page = _FakeFormPage()
    form_page.dismiss_resistant = True

    with pytest.raises(SecurityViolation):
        _writer(form_page).set_purchaser("颜浩坚")


def test_close_paste_entry_closes_only_the_dialog_not_the_draft() -> None:
    form_page = _FakeFormPage()
    panel = _FakePastePanel()
    writer = InsoPurchaseWriter(
        form_page=_OperationPage(form_page),
        paste_panel=panel,
        gate=FakeWriteGate(enabled=True),
    )
    panel.open()

    writer.close_paste_entry()

    assert panel.close_calls == 1
    assert panel.opened is False
    # The draft form stays usable for the separate, still-closed Save path.
    assert form_page.events == []


class _PasteEntryControl:
    def __init__(self, host):
        self.host = host

    def count(self):
        return self.host.control_count

    def is_visible(self):
        return self.host.control_visible

    def is_enabled(self):
        return self.host.control_enabled

    def inner_text(self):
        return self.host.control_label

    def click(self):
        self.host.clicked += 1
        self.host.revealed = True


class _PasteEntryForm:
    def __init__(self, host):
        self.host = host

    def locator(self, selector):
        assert selector == "#product_import_"
        return _PasteEntryControl(self.host)


class _AbsentLocator:
    def count(self):
        return 0

    def is_visible(self):
        return False

    def click(self):
        raise AssertionError("an absent control must never be clicked")


class _PasteEntryHost:
    """The ERP page as the 粘贴 entry sees it: form frame + in-page dialog iframe."""

    url = "https://yingsuo.alperp.cn/"

    def __init__(
        self,
        *,
        control_count: int = 1,
        control_visible: bool = True,
        control_enabled: bool = True,
        control_label: str = "粘贴",
        frame_url: str | None = None,
    ):
        self.control_count = control_count
        self.control_visible = control_visible
        self.control_enabled = control_enabled
        self.control_label = control_label
        self.clicked = 0
        self.revealed = False
        self.entry_frame = SimpleNamespace(
            url=frame_url
            or (
                "https://yingsuo.alperp.cn/skins/etaoerp/product/Import.aspx"
                "?BillPage=Enquiry&VendorID=4525909&h=510"
            )
        )

    def frame_locator(self, selector):
        assert selector == "iframe#winIframealert_enquiry"
        return _PasteEntryForm(self)

    def locator(self, _selector):
        return _AbsentLocator()

    def wait_for_timeout(self, _milliseconds):
        return None

    @property
    def frames(self):
        return [self.entry_frame] if self.revealed else []


def test_paste_entry_opens_the_forms_own_in_page_dialog() -> None:
    """The 粘贴 entry is the form's own dialog, never a new tab."""

    host = _PasteEntryHost()
    panel = PasteImportPanel(_OperationPage(host), wait_seconds=0.05, poll_milliseconds=1)

    panel.open()

    assert host.clicked == 1
    assert panel.frame() is host.entry_frame


@pytest.mark.parametrize(
    "kwargs",
    (
        {"control_count": 0},
        {"control_count": 2},
        {"control_visible": False},
        {"control_enabled": False},
        {"control_label": "识别"},
    ),
)
def test_paste_entry_fails_closed_without_the_verified_control(kwargs) -> None:
    host = _PasteEntryHost(**kwargs)
    panel = PasteImportPanel(_OperationPage(host), wait_seconds=0.05, poll_milliseconds=1)

    with pytest.raises(SecurityViolation):
        panel.open()

    assert host.clicked == 0


def test_paste_entry_refuses_a_frame_on_another_origin() -> None:
    host = _PasteEntryHost(
        frame_url="https://evil.example.invalid/skins/etaoerp/product/Import.aspx"
    )
    panel = PasteImportPanel(_OperationPage(host), wait_seconds=0.05, poll_milliseconds=1)

    with pytest.raises(SecurityViolation):
        panel.open()


def test_paste_entry_refuses_the_list_pages_bulk_import_dialog() -> None:
    """Same title, different handler: that one's 保存数据 creates a server bill.

    ``innerenquiry/yewuxj/Import.aspx`` binds 保存数据 to ``Import()`` ->
    ``$.post(?action=Import)`` and requires a returned ``BillID``. It must never
    be reachable from the draft flow, so the frame identity rejects it even
    though the origin and the page title match.
    """

    host = _PasteEntryHost(
        frame_url=(
            "https://yingsuo.alperp.cn/skins/etaoerp/"
            "innerenquiry/yewuxj/Import.aspx"
        )
    )
    panel = PasteImportPanel(_OperationPage(host), wait_seconds=0.05, poll_milliseconds=1)

    with pytest.raises(SecurityViolation):
        panel.open()


@pytest.mark.parametrize(
    "rows",
    [
        ("深圳阿尔克贸易有限公司", "深圳阿尔克贸易有限公司"),
        ("RS TRADING", "Systrome Technologies Private Ltd"),
    ],
)
def test_customer_option_must_be_present_exactly_once(
    rows: tuple[str, ...],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(purchase_writer_module, "_MENU_WAIT_SECONDS", 0.05)
    form_page = _FakeFormPage()
    form_page.company_rows = rows
    with pytest.raises(SecurityViolation):
        _writer(form_page).set_customer("深圳阿尔克贸易有限公司")
    assert form_page.open_menu == "input#CompanyName"


def test_customer_menu_that_never_opens_reports_its_own_reason(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Live 2026-11-14: two drafts reported SELECT_OPTION_UNAVAILABLE and nothing
    # said whether the popup opened at all. The two cases carry distinct codes.
    monkeypatch.setattr(purchase_writer_module, "_MENU_WAIT_SECONDS", 0.05)

    class _NeverOpenMenu:
        def count(self) -> int:
            return 0

    class _Scope:
        def locator(self, _selector: str) -> _NeverOpenMenu:
            return _NeverOpenMenu()

    class _Page:
        url = "https://yingsuo.alperp.cn/"

        def frame_locator(self, _selector: str) -> _Scope:
            return _Scope()

        def wait_for_timeout(self, _milliseconds: int) -> None:
            return None

    class _Field:
        def __init__(self) -> None:
            self.clicks = 0

        def fill(self, _value: str) -> None:
            return None

        def click(self) -> None:
            self.clicks += 1

    port = SimpleNamespace(_form_page=SimpleNamespace(page=_Page()))
    field = _Field()

    with pytest.raises(SecurityViolation, match="select menu did not open"):
        _PlaywrightActionPort._pick_menu_option(port, field, "深圳阿尔克贸易有限公司")
    assert field.clicks >= 1


class _Cell:
    def __init__(self, text: str) -> None:
        self.text = text

    def inner_text(self) -> str:
        return self.text


class _Cells:
    def __init__(self, texts: tuple[str, ...]) -> None:
        self.texts = texts

    def count(self) -> int:
        return len(self.texts)

    def nth(self, index: int) -> _Cell:
        return _Cell(self.texts[index])


class _MenuRow:
    def __init__(self, texts: tuple[str, ...]) -> None:
        self.texts = texts

    def locator(self, selector: str) -> _Cells:
        assert selector == "td"
        return _Cells(self.texts)

    def inner_text(self) -> str:
        return " ".join(self.texts)


class _Menu:
    def __init__(self, rows: list[_MenuRow]) -> None:
        self.rows = rows

    def locator(self, selector: str) -> _MenuRows:
        return _MenuRows(self.rows if selector == "tr" else [])


class _MenuRows:
    def __init__(self, rows: list[_MenuRow]) -> None:
        self.rows = rows

    def count(self) -> int:
        return len(self.rows)

    def nth(self, index: int) -> _MenuRow:
        return self.rows[index]


# Live layout read-only on 2026-11-14: the ERP renders two separate customer
# records with the identical name/phone/contact/owner; only the record id cell
# differs (4525995 and 4526000). The Owner chose the first row, which is the
# 4526000 record, so the pick is bound to that id instead of to menu order.
_DUPLICATE_CUSTOMER_ROWS = (
    ("深圳阿尔克贸易有限公司", "+86 18029977831", "Majic", "彭星烁", "4525995"),
    ("深圳阿尔克贸易有限公司", "+86 18029977831", "Majic", "彭星烁", "4526000"),
)


def test_customer_pick_uses_the_owner_marker_not_the_menu_order() -> None:
    rows = [_MenuRow(texts) for texts in _DUPLICATE_CUSTOMER_ROWS]

    option = _PlaywrightActionPort._unique_menu_option(
        None, _Menu(rows), "深圳阿尔克贸易有限公司", "4526000"
    )

    assert option is rows[1]


def test_customer_pick_without_a_matching_marker_stays_closed() -> None:
    rows = [_MenuRow(texts) for texts in _DUPLICATE_CUSTOMER_ROWS]

    assert _PlaywrightActionPort._unique_menu_option(
        None, _Menu(rows), "深圳阿尔克贸易有限公司", "9999999"
    ) is None


def test_purchaser_pick_confirms_the_echoed_identifier() -> None:
    form_page = _FakeFormPage()
    writer = _writer(form_page)

    writer.set_purchaser("颜浩坚")

    assert form_page.purchaser == "颜浩坚"
    assert form_page.purchaser_id == "16665"
    assert form_page.open_menu is None


def test_a_second_order_does_not_leave_two_purchasers_selected() -> None:
    """Live failure (2026-09-30): the purchaser control is a checkbox menu.

    Its own ``data-options`` declares ``checkbox:true``, the ERP re-checks the
    previously used purchaser when a draft opens, and the hidden id field only
    records what a pick writes. The next order therefore ran with 颜浩坚 already
    checked, its pick added 陈熙, and the field ended holding ``陈熙,颜浩坚`` --
    rejected by the exact read-back guard and surfaced only as
    ``CONTROL_NOT_FOUND``. The routed purchaser has to end up as the only
    checked one.
    """

    form_page = _FakeFormPage()
    form_page.purchaser_checked = ["颜浩坚"]

    _writer(form_page).set_purchaser("陈熙")

    assert form_page.purchaser_checked == ["陈熙"]
    assert form_page.purchaser == "陈熙"
    assert form_page.purchaser_id == "7432"


def test_a_purchaser_that_is_already_the_only_selection_still_passes() -> None:
    """Clearing must not turn a correct outcome into a failure."""

    form_page = _FakeFormPage()
    form_page.purchaser_checked = ["陈熙"]

    _writer(form_page).set_purchaser("陈熙")

    assert form_page.purchaser_checked == ["陈熙"]
    assert form_page.purchaser_id == "7432"


def test_every_order_ends_with_the_inquiry_window_gone() -> None:
    """Owner rule (2026-09-30): each order leaves nothing open behind it.

    The 采购临时询价 window, customer selector included, is a dialog on the INSO
    home page, so it has to be closed and *confirmed* closed before the next
    order starts from 业务询价.
    """

    form_page = _FakeFormPage()
    writer = _writer(form_page)

    assert writer.dismiss_order_surface() is True
    assert form_page.form_window_open is False
    assert "close-inquiry-window" in form_page.events


def test_a_window_that_will_not_close_is_reported_and_not_assumed() -> None:
    """A window with no reachable close control must not read as closed."""

    form_page = _FakeFormPage()
    form_page.window_close_available = False
    writer = _writer(form_page)

    assert writer.dismiss_order_surface() is False
    assert form_page.form_window_open is True


def test_an_already_clear_surface_costs_nothing() -> None:
    """With no window open the check must simply pass and touch nothing."""

    form_page = _FakeFormPage()
    form_page.form_window_open = False
    writer = _writer(form_page)

    assert writer.dismiss_order_surface() is True
    assert form_page.events == []


def test_a_closed_window_left_in_the_dom_is_not_a_dirty_surface() -> None:
    """Live behaviour (2026-09-30): the ERP only hides a window it closes.

    The 采购临时询价 dialog, its close control and its ``Bill.aspx`` iframe all
    stay in the DOM (``iframe#winIframealert_enquiry`` kept count 1 with the
    hosting dialog at ``display:none``). Judging "cleared" by presence therefore
    reports every surface as unclearable and refuses every order with
    ``CONTROL_NOT_FOUND`` before the form is even touched -- the exact symptom
    this teardown exists to prevent.
    """

    form_page = _FakeFormPage()
    form_page.form_window_open = False
    form_page.form_in_dom = True
    writer = _writer(form_page)

    assert writer._order_form_is_present() is True
    assert writer.dismiss_order_surface() is True
    assert "close-inquiry-window" not in form_page.events


def test_an_ai_panel_left_open_is_closed_as_well() -> None:
    """The AI录单 panel is a sibling dialog and must be cleared too."""

    form_page = _FakeFormPage()
    form_page.form_window_open = False
    form_page.paste_open = True
    writer = _writer(form_page)

    assert writer.dismiss_order_surface() is True
    assert form_page.paste_open is False


def test_an_ambiguous_window_lookup_refuses_instead_of_guessing() -> None:
    """Two candidate dialogs must never be resolved by picking one."""

    form_page = _FakeFormPage()
    form_page.order_window_ambiguous = True
    writer = _writer(form_page)

    assert writer.dismiss_order_surface() is False
    assert form_page.form_window_open is True


class _CloseButton:
    def __init__(self):
        self.clicks = 0

    def count(self):
        return 1

    def is_visible(self):
        return True

    def is_enabled(self):
        return True

    def click(self, timeout=None):
        self.clicks += 1


class _AiFrameHandle:
    def __init__(self, frame):
        self._frame = frame


class _PasteEntryFrame:
    """The verified Import.aspx frame: it knows its parent document."""

    url = (
        "https://yingsuo.alperp.cn/skins/etaoerp/product/"
        "Import.aspx?BillPage=Enquiry&VendorID=4525909&h=510"
    )

    def __init__(self, parent):
        self._parent = parent

    @property
    def parent_frame(self):
        return self._parent

    def frame_element(self):
        return _AiFrameHandle(self)


class _PasteDialog:
    """The dialog layer: it holds the paste iframe and its own close control."""

    def __init__(self, button):
        self._button = button
        self.looked_up: list[str] = []

    def count(self):
        return 1

    def filter(self, **_kwargs):
        return self

    def locator(self, selector):
        self.looked_up.append(selector)
        if selector == "#winIframe_dialog1":
            return _PresentControl()
        if selector in ('button[title="关闭窗口"]', 'button:has-text("取消")'):
            return self._button
        return _AbsentLocator()


class _PresentControl:
    def count(self):
        return 1


class _ShellFrame:
    """The ERP document that owns the dialog layer containing the AI frame."""

    def __init__(self, dialog):
        self._dialog = dialog
        self.lookups: list[str] = []

    def locator(self, selector):
        self.lookups.append(selector)
        return self._dialog


class _PasteClosePage:
    url = "https://yingsuo.alperp.cn/"

    def __init__(self, shell, fallback):
        self._shell = shell
        self._fallback = fallback
        self.fallback_lookups = 0

    def locator(self, _selector):
        self.fallback_lookups += 1
        return self._fallback


def test_paste_dialog_close_anchors_on_the_dialog_holding_the_paste_frame() -> None:
    """The close must target the paste frame's own dialog, not a selector guess."""

    button = _CloseButton()
    dialog = _PasteDialog(button)
    shell = _ShellFrame(dialog)
    frame = _PasteEntryFrame(shell)
    fallback = _CloseButton()
    page = _PasteClosePage(shell, fallback)

    panel = PasteImportPanel(_OperationPage(page))
    panel._frame = frame
    panel.close()

    assert button.clicks == 1
    assert fallback.clicks == 0
    assert page.fallback_lookups == 0
    # The dialog is proven to be this one by the iframe it holds.
    assert "#winIframe_dialog1" in dialog.looked_up
    assert panel._frame is None


def test_paste_dialog_close_never_falls_back_to_a_page_level_selector() -> None:
    """With no frame to anchor on, guessing a global close control is unsafe.

    The 采购临时询价 window carries its own ``button[title="关闭窗口"]``, so a
    page-wide match could close the draft instead of the paste dialog. When the
    frame is already gone this reports "not dismissed" and clicks nothing; the
    order-surface cleanup closes the window, which disposes of the dialog too.
    """

    button = _CloseButton()
    dialog = _PasteDialog(button)
    shell = _ShellFrame(dialog)
    fallback = _CloseButton()
    page = _PasteClosePage(shell, fallback)

    panel = PasteImportPanel(_OperationPage(page))

    assert panel.close() is False
    assert button.clicks == 0
    assert fallback.clicks == 0
    assert page.fallback_lookups == 0


def test_the_production_draft_path_carries_no_ai_entry_anywhere() -> None:
    """V1.7 replaces AI录单 with native paste; the old path must be gone.

    This is a source guard, not a behavioural one: the failure mode it prevents
    is a future edit quietly re-binding the draft steps to ``#ai_import_`` /
    ``Import_ai.aspx`` and silently re-introducing the external AI dependency the
    Owner asked to remove.
    """

    source = Path(purchase_writer_module.__file__).read_text(encoding="utf-8")
    for forbidden in ("Import_ai.aspx", "#ai_import_", "ai-recognize", "AI录单"):
        assert forbidden not in source, forbidden

    bound = " ".join(binding.selector for binding in _BINDINGS.values())
    for forbidden in ("ai_import", "ai-recognize", "Import_ai"):
        assert forbidden not in bound, forbidden
