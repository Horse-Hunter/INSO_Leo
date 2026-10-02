from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import ClassVar

import pytest

import src.inso.purchase_writer as purchase_writer_module
from src.inso.purchase_writer import (
    _AI_ENTRY_DIALOG,
    _BINDINGS,
    _ID_ONLY_ACTIONS,
    _MENU_CHECKBOX,
    _OPEN_SELECT_MENU,
    AiEntryPanel,
    InsoPurchaseWriter,
    PlaywrightAiResultReader,
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
            return int(self.page.form_in_dom) + int(self.page.ai_panel_in_dom)
        if selector == _AI_ENTRY_DIALOG:
            return 1 if self.page.ai_panel_in_dom else 0
        if selector in _FIELD_ATTRIBUTES:
            return 1
        if selector == "input#UserName":
            return 1
        if selector == "button#ai-recognize":
            return 1
        if selector == "button#btnSave":
            return self.page.save_count
        if selector.startswith('input[data-f="'):
            return 1
        return 0

    def is_visible(self) -> bool:
        if self.selector == _AI_ENTRY_DIALOG:
            return self.page.ai_panel_open
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
    company_rows = ("RS TRADING", "Win Source Elec. Tech. Ltd")
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
        self.ai_panel_in_dom = True
        self.ai_panel_open = False
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


class _FakeAiFrame:
    """The AI录单 frame: recognition readiness plus the single preview row."""

    url = (
        "https://yingsuo.alperp.cn/skins/etaoerp/product/Import_ai.aspx"
        "?BillPage=Enquiry&VendorID=4525909&h=510"
    )

    def __init__(self, *, ready: bool = True, values=None, progress=(), endless: bool = False):
        self.ready = ready
        self.values = values or {
            "ProductID": "P216328",
            "PartNo": "LM358",
            "Brand": "Texas Instruments",
            "Qty": "123",
        }
        # Live recognition is asynchronous: the button shows progress captions
        # and the preview stays empty until the final state arrives. ``endless``
        # models a caption that never settles.
        self.progress = list(progress)
        self.endless = endless
        self.polls = 0

    def is_detached(self) -> bool:
        return False

    def wait_for_timeout(self, _milliseconds: int) -> None:
        self.polls += 1
        if self.progress and not self.endless:
            self.progress.pop(0)
            if not self.progress:
                self.ready = True

    def locator(self, selector: str):
        if selector == "button#ai-recognize":
            if self.ready:
                text = "重新识别"
            elif self.progress:
                text = self.progress[0]
            else:
                text = "AI 智能识别"
            return _Locator(self, selector, text=text)
        if selector == "#preview-body > tr":
            return _Rows(self)
        return _Locator(self, selector)


class _FakeAiPanel:
    """The form's AI录单 entry: opening it yields the in-page AI frame.

    It deliberately has no page of its own -- the live product opens an iframe
    inside the purchase form, never a new tab.
    """

    def __init__(
        self,
        *,
        ready: bool = True,
        values=None,
        progress=(),
        endless: bool = False,
        opens: bool = True,
        on_close=None,
    ):
        self.frame_obj = _FakeAiFrame(
            ready=ready, values=values, progress=progress, endless=endless
        )
        self.opens = opens
        self.opened = False
        self.close_calls = 0
        self._on_close = on_close

    def open(self) -> None:
        if not self.opens:
            raise SecurityViolation("AI entry panel did not open")
        self.opened = True

    def frame(self):
        if not self.opened:
            raise SecurityViolation("AI entry panel is not open")
        return self.frame_obj

    def close(self) -> None:
        self.close_calls += 1
        self.opened = False
        if self._on_close is not None:
            self._on_close()


class _Rows:
    def __init__(self, page):
        self.page = page

    def count(self):
        return 1 if self.page.ready else 0

    def nth(self, _index: int):
        return _Row(self.page)


class _Row:
    def __init__(self, page):
        self.page = page

    def locator(self, selector: str):
        field = selector.split('data-f="', 1)[1].split('"', 1)[0]
        return _Locator(self.page, selector, value=self.page.values[field])


@pytest.mark.parametrize("value", ["需要问全价格", "普通询价"])
def test_quotation_type_maps_to_exact_importance_control(value: str) -> None:
    form_page = _FakeFormPage()
    writer = InsoPurchaseWriter(
        form_page=_OperationPage(form_page),
        ai_panel=_FakeAiPanel(),
        gate=FakeWriteGate(enabled=True),
    )

    writer.set_quotation_type(value)

    assert form_page.value == value


def test_quotation_type_rejects_values_outside_the_two_business_routes() -> None:
    writer = InsoPurchaseWriter(
        form_page=_OperationPage(_FakeFormPage()),
        ai_panel=_FakeAiPanel(),
        gate=FakeWriteGate(enabled=True),
    )

    with pytest.raises(SecurityViolation):
        writer.set_quotation_type("意向单询价")


def test_production_gate_is_closed_and_generic_send_methods_do_not_exist() -> None:
    form_page = _FakeFormPage()
    writer = InsoPurchaseWriter(
        form_page=_OperationPage(form_page),
        ai_panel=_FakeAiPanel(),
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
    """The AI录单 dialog's own footer, mirroring the live DOM (2026-10-01)."""

    def __init__(self, *, dialog_count: int = 1, buttons: int = 1) -> None:
        self.dialog_count = dialog_count
        self.buttons = buttons
        self.outer: list[str] = []
        self.inner: list[str] = []

    def locator(self, selector):
        self.outer.append(selector)
        return _DialogLocator(self)


class _DialogLocator:
    def __init__(self, host: _DialogFooter) -> None:
        self.host = host

    def count(self):
        return self.host.dialog_count

    def locator(self, selector):
        self.host.inner.append(selector)
        return _DialogButtons(self.host)


class _DialogButtons:
    def __init__(self, host: _DialogFooter) -> None:
        self.host = host

    def count(self):
        return self.host.buttons


class _DialogAiFrame(_FakeAiFrame):
    """The panel frame, hosted by the dialog that owns its footer."""

    def __init__(self, dialog: _DialogFooter, **kwargs) -> None:
        super().__init__(**kwargs)
        self.parent_frame = dialog


def _commit_port(dialog: _DialogFooter) -> _PlaywrightActionPort:
    panel = _FakeAiPanel()
    panel.frame_obj = _DialogAiFrame(dialog)
    panel.open()
    return _PlaywrightActionPort(_OperationPage(SimpleNamespace()), panel)


def test_ai_entry_commit_binding_targets_the_panels_own_commit_control() -> None:
    """保存数据 lives in the dialog's footer, next to the AI frame.

    A bare ``<button>`` reports ``type="submit"``, and "submit" is a denied
    semantic, so the control is bound by its verified id alone -- exactly the
    concession SAVE_DATA already makes for the same reason.
    """

    binding = _BINDINGS[WriteAction.AI_ENTRY_COMMIT]

    assert binding.frame == "ai-dialog"
    assert binding.selector == 'button:has-text("保存数据")'
    assert binding.semantics == ControlSemantics(
        "button", "保存数据", "保存数据", (("id", "win_btn__dialog11"),)
    )
    assert WriteAction.AI_ENTRY_COMMIT in _ID_ONLY_ACTIONS
    assert_safe_control_semantics(binding.semantics)


def test_ai_entry_commit_resolves_only_inside_the_ai_dialogs_own_footer() -> None:
    dialog = _DialogFooter()

    locator = _commit_port(dialog)._locator(_BINDINGS[WriteAction.AI_ENTRY_COMMIT])

    assert locator.count() == 1
    assert dialog.outer == [_AI_ENTRY_DIALOG]
    assert dialog.inner == ['button:has-text("保存数据")']


def test_ai_entry_commit_fails_closed_when_the_host_dialog_is_not_unique() -> None:
    with pytest.raises(SecurityViolation):
        _commit_port(_DialogFooter(dialog_count=2))._locator(
            _BINDINGS[WriteAction.AI_ENTRY_COMMIT]
        )


def test_writer_lets_the_erp_fill_the_row_and_offers_no_way_to_type_it() -> None:
    writer = InsoPurchaseWriter(
        form_page=_OperationPage(SimpleNamespace()),
        ai_panel=_FakeAiPanel(),
        gate=FakeWriteGate(enabled=False),
    )

    assert hasattr(writer, "commit_ai_entry")
    for name in ("set_product_id", "set_model", "set_brand", "set_quantity"):
        assert not hasattr(writer, name)


def _opened_panel(**kwargs) -> _FakeAiPanel:
    panel = _FakeAiPanel(**kwargs)
    panel.open()
    return panel


def test_ai_reader_returns_only_ready_single_row_result() -> None:
    reader = PlaywrightAiResultReader(_opened_panel())

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


def test_ai_reader_requires_the_product_code_the_erp_resolved() -> None:
    """The ERP's AI preview carries a 产品编码 column (``data-f="ProductID"``).

    Live shape 2026-10-01: the preview table is ``# / 产品编码 / 型号 / 品牌 /
    数量`` and ``STM8L051F3P6`` came back as ``P216328``. Reading only the last
    three fields silently discarded the 编码, so the written draft was missing
    it. An empty 编码 is not a readable row.
    """

    values = {
        "ProductID": "",
        "PartNo": "LM358",
        "Brand": "Texas Instruments",
        "Qty": "123",
    }
    reader = PlaywrightAiResultReader(
        _opened_panel(values=values),
        wait_seconds=0.05,
        poll_milliseconds=1,
    )

    assert reader.read() is None


def test_ai_reader_waits_for_the_async_progress_before_reading() -> None:
    """Live recognition reports progress captions before the preview exists.

    Reading once immediately after the click observed "🔗 正在连接 AI 服务... 0%"
    and zero rows, so every run raised "AI recognition is not ready". The reader
    must poll past the in-flight captions to the final ready row.
    """

    panel = _opened_panel(
        ready=False,
        progress=(
            "🔗 正在连接 AI 服务... 0%",
            "✅ 正在校验品牌与物料库... 66%",
            "✨ 即将完成，请稍候... 95%",
        ),
    )
    reader = PlaywrightAiResultReader(panel)

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
    assert panel.frame_obj.polls == 3


def test_ai_reader_fails_closed_until_ready_state() -> None:
    reader = PlaywrightAiResultReader(
        _opened_panel(ready=False),
        wait_seconds=0.05,
        poll_milliseconds=1,
    )

    assert reader.read() is None


def test_ai_reader_requires_an_open_panel() -> None:
    """Reading before the panel exists is misuse, not an AI state: it must fail."""

    reader = PlaywrightAiResultReader(_FakeAiPanel(), wait_seconds=0.05, poll_milliseconds=1)

    with pytest.raises(SecurityViolation):
        reader.read()


def test_ai_reader_still_fails_closed_when_progress_never_settles() -> None:
    """An endless in-flight caption must time out to None, never to a result."""

    panel = _opened_panel(
        ready=False,
        progress=("🔗 正在连接 AI 服务... 0%",),
        endless=True,
    )
    reader = PlaywrightAiResultReader(
        panel,
        wait_seconds=0.05,
        poll_milliseconds=1,
    )

    assert reader.read() is None


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
        ai_panel=_FakeAiPanel(),
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
        ai_panel=_FakeAiPanel(),
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
        ai_panel=_FakeAiPanel(),
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
        ai_panel=_FakeAiPanel(),
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
        ai_panel=_FakeAiPanel(
            on_close=lambda: setattr(form_page, "ai_panel_open", False)
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

    writer.set_customer("Win Source Elec. Tech. Ltd")

    assert form_page.customer == "Win Source Elec. Tech. Ltd"
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
    covering ``#ai_import_``, so the AI录单 control could never be clicked. The
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


def test_close_ai_entry_closes_only_the_panel_not_the_draft() -> None:
    form_page = _FakeFormPage()
    panel = _FakeAiPanel()
    writer = InsoPurchaseWriter(
        form_page=_OperationPage(form_page),
        ai_panel=panel,
        gate=FakeWriteGate(enabled=True),
    )
    panel.open()

    writer.close_ai_entry()

    assert panel.close_calls == 1
    assert panel.opened is False
    # The draft form stays usable for the separate, still-closed Save path.
    assert form_page.events == []


class _AiEntryControl:
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


class _AiEntryForm:
    def __init__(self, host):
        self.host = host

    def locator(self, selector):
        assert selector == "#ai_import_"
        return _AiEntryControl(self.host)


class _AbsentLocator:
    def count(self):
        return 0

    def is_visible(self):
        return False

    def click(self):
        raise AssertionError("an absent control must never be clicked")


class _AiEntryHost:
    """The ERP page as the AI entry sees it: form frame + in-page panel iframe."""

    url = "https://yingsuo.alperp.cn/"

    def __init__(
        self,
        *,
        control_count: int = 1,
        control_visible: bool = True,
        control_enabled: bool = True,
        control_label: str = "AI录单",
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
                "https://yingsuo.alperp.cn/skins/etaoerp/product/Import_ai.aspx"
                "?BillPage=Enquiry&VendorID=4525909&h=510"
            )
        )

    def frame_locator(self, selector):
        assert selector == "iframe#winIframealert_enquiry"
        return _AiEntryForm(self)

    def locator(self, _selector):
        return _AbsentLocator()

    def wait_for_timeout(self, _milliseconds):
        return None

    @property
    def frames(self):
        return [self.entry_frame] if self.revealed else []


def test_ai_entry_opens_the_forms_own_in_page_panel() -> None:
    """The AI录单 entry is the form's own iframe, never a new tab."""

    host = _AiEntryHost()
    panel = AiEntryPanel(_OperationPage(host), wait_seconds=0.05, poll_milliseconds=1)

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
def test_ai_entry_fails_closed_without_the_verified_control(kwargs) -> None:
    host = _AiEntryHost(**kwargs)
    panel = AiEntryPanel(_OperationPage(host), wait_seconds=0.05, poll_milliseconds=1)

    with pytest.raises(SecurityViolation):
        panel.open()

    assert host.clicked == 0


def test_ai_entry_refuses_a_frame_on_another_origin() -> None:
    host = _AiEntryHost(
        frame_url="https://evil.example.invalid/skins/etaoerp/product/Import_ai.aspx"
    )
    panel = AiEntryPanel(_OperationPage(host), wait_seconds=0.05, poll_milliseconds=1)

    with pytest.raises(SecurityViolation):
        panel.open()


@pytest.mark.parametrize(
    "rows",
    [
        ("Win Source Elec. Tech. Ltd", "Win Source Elec. Tech. Ltd"),
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
        _writer(form_page).set_customer("Win Source Elec. Tech. Ltd")
    assert form_page.open_menu == "input#CompanyName"


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
    form_page.ai_panel_open = True
    writer = _writer(form_page)

    assert writer.dismiss_order_surface() is True
    assert form_page.ai_panel_open is False


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


class _AiEntryFrame:
    """The verified Import_ai.aspx frame: it knows its parent document."""

    url = (
        "https://yingsuo.alperp.cn/skins/etaoerp/product/"
        "Import_ai.aspx?BillPage=Enquiry&VendorID=4525909&h=510"
    )

    def __init__(self, parent):
        self._parent = parent

    @property
    def parent_frame(self):
        return self._parent

    def frame_element(self):
        return _AiFrameHandle(self)


class _AiDialog:
    def __init__(self, button):
        self._button = button
        self.filtered_with = None

    def filter(self, *, has):
        self.filtered_with = has
        return self

    def count(self):
        return 1

    def locator(self, selector):
        assert selector == 'button[title="关闭窗口"]'
        return self._button


class _ShellFrame:
    """The ERP document that owns the dialog layer containing the AI frame."""

    def __init__(self, dialog):
        self._dialog = dialog
        self.lookups: list[str] = []

    def locator(self, selector):
        self.lookups.append(selector)
        return self._dialog


class _AiClosePage:
    url = "https://yingsuo.alperp.cn/"

    def __init__(self, shell, fallback):
        self._shell = shell
        self._fallback = fallback
        self.fallback_lookups = 0

    def locator(self, _selector):
        self.fallback_lookups += 1
        return self._fallback


def test_ai_panel_close_anchors_on_the_dialog_that_contains_the_ai_frame() -> None:
    """The close must target the AI frame's own dialog, not a selector guess."""

    button = _CloseButton()
    dialog = _AiDialog(button)
    shell = _ShellFrame(dialog)
    frame = _AiEntryFrame(shell)
    fallback = _CloseButton()
    page = _AiClosePage(shell, fallback)

    panel = AiEntryPanel(_OperationPage(page))
    panel._frame = frame
    panel.close()

    assert button.clicks == 1
    assert fallback.clicks == 0
    assert page.fallback_lookups == 0
    assert dialog.filtered_with is not None
    assert panel._frame is None


def test_ai_panel_close_falls_back_to_the_scoped_selector_when_the_frame_is_gone() -> None:
    button = _CloseButton()
    dialog = _AiDialog(button)
    shell = _ShellFrame(dialog)
    fallback = _CloseButton()
    page = _AiClosePage(shell, fallback)

    panel = AiEntryPanel(_OperationPage(page))
    panel.close()

    assert button.clicks == 0
    assert fallback.clicks == 1
    assert page.fallback_lookups == 1
