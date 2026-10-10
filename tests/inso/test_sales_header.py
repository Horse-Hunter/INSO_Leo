from types import SimpleNamespace

import pytest

from src.inso.sales_header import (
    EXPECTED,
    HeaderStop,
    PlaywrightSalesHeaderPage,
    fill_sales_header,
)

PI = "SHAWN20260101-01"


class HeaderPage:
    def __init__(self, currency="RMB", wrong=None, late=None, customers=None):
        self.values = dict(EXPECTED, currency=currency, customer="", order_no="", exchange="preserved")
        self.wrong, self.late = wrong, late
        self.customers = customers if customers is not None else ["无关测试客户", "阿尔克测试甲", "阿尔克测试乙"]
        self.calls, self.reads = [], {}
        self.preserved = False

    def open_for_header(self):
        self.calls.append(("open",))

    def select_first_customer(self, needle):
        matches = [name for name in self.customers if needle in name]
        if not matches:
            raise HeaderStop("customer", "CUSTOMER_NOT_FOUND")
        self.values["customer"] = matches[0]
        self.calls.append(("customer", matches[0]))
        return matches[0]

    def read(self, field):
        self.reads[field] = self.reads.get(field, 0) + 1
        if field == self.wrong or field == self.late and self.reads[field] >= 2:
            return "synthetic mismatch"
        return self.values[field]

    def select(self, field, value):
        self.calls.append(("select", field, value))
        self.values[field] = value

    def fill(self, field, value):
        assert field in {"destination", "order_no"}
        self.calls.append(("fill", field))
        self.values[field] = value

    def preserve_for_owner(self):
        self.preserved = True


@pytest.mark.parametrize("initial", ["RMB", "USD"])
def test_all_header_readbacks_and_rmb_always_selected_once(initial):
    page = HeaderPage(currency=initial)
    result = fill_sales_header(page, PI)
    assert result.status == "WAITING_OWNER" and result.checked_controls == 8 and page.preserved
    assert page.values["customer"] == "阿尔克测试甲"
    assert page.values["order_no"] == PI and page.values["exchange"] == "preserved"
    assert page.calls.count(("select", "currency", "RMB")) == 1
    assert [call for call in page.calls if call[0] == "fill"] == [("fill", "destination"), ("fill", "order_no")]


@pytest.mark.parametrize("field", ["customer", "currency", "payment", "freight", "delivery", "shipping", "destination", "order_no"])
@pytest.mark.parametrize("final", [False, True])
def test_each_mismatch_stops_specific_field_without_repair(field, final):
    page = HeaderPage(**({"late": field} if final else {"wrong": field}))
    result = fill_sales_header(page, PI)
    assert result.status == "STOPPED" and result.field == field and not page.preserved
    assert result.reason == ("FINAL_READBACK_MISMATCH" if final else "READBACK_MISMATCH")
    assert all(page.calls.count(call) == 1 for call in page.calls)


def test_missing_customer_and_invalid_pi_never_guess():
    page = HeaderPage(customers=["非目标测试客户"])
    result = fill_sales_header(page, PI)
    assert result.reason == "CUSTOMER_NOT_FOUND" and not page.preserved
    invalid = HeaderPage()
    assert fill_sales_header(invalid, "not PI").status == "STOPPED" and not invalid.calls


def test_page_adapter_cannot_fill_customer_or_unauthorized_fields():
    adapter = PlaywrightSalesHeaderPage(None, owns_page=lambda p: True)
    for field in ["customer", "currency", "model", "brand", "quantity", "price", "pdf", "save", "submit"]:
        with pytest.raises(HeaderStop, match="FIELD_NOT_AUTHORIZED"):
            adapter.fill(field, "blocked")
    with pytest.raises(HeaderStop, match="FIELD_NOT_AUTHORIZED"):
        adapter.select("save", "blocked")


class Action:
    def __init__(self, callback=lambda: None, text="", children=None):
        self.callback, self.text, self.children = callback, text, children or {}

    def count(self): return 1
    def is_enabled(self): return True
    def is_visible(self): return True
    def click(self, **kwargs): self.callback()
    def inner_text(self): return self.text
    def locator(self, selector): return self.children[selector]
    def nth(self, i): return self


class PromptPage:
    def __init__(self):
        self.prompt, self.bill = False, False
        self.adds, self.cancels = 0, 0
        self.pending = False
        self.listeners = {}
        self.add = Action(self.add_document)
        self.cancel = Action(self.cancel_document, "取消")
        self.dialog = Action(children={".layui-layer-btn1": self.cancel})
        self.list = SimpleNamespace(locator=lambda selector: self.add)
        self.form = SimpleNamespace(locator=lambda selector: Action())
        self.frames = [SimpleNamespace(locator=self.dialogs)]

    def is_closed(self): return False
    def on(self, event, callback): self.listeners[event] = callback
    def remove_listener(self, event, callback): self.listeners.pop(event)
    def wait_for_timeout(self, ms): pass
    def evaluate(self, script):
        if '=== true' in script: return self.pending
        if '= false' in script: self.pending = False
    def add_document(self):
        self.adds += 1
        self.prompt = True
    def cancel_document(self):
        self.cancels += 1
        self.prompt, self.bill = False, True
    def dialogs(self, selector):
        return self.dialog if self.prompt else SimpleNamespace(count=lambda: 0)


def test_existing_document_prompt_only_cancel_and_reuse():
    page = PromptPage()
    adapter = PlaywrightSalesHeaderPage(page, owns_page=lambda p: True)
    adapter._frames = lambda kind: [page.form] if kind == "bill" and page.bill else [page.list] if kind == "list" else []
    adapter.open_for_header()
    assert page.adds == 1 and page.cancels == 1 and adapter.cancelled_existing_prompt
    assert adapter.frame is page.form and not page.listeners


def test_owner_waiting_form_must_not_be_reopened_or_overwritten():
    page = PromptPage()
    page.pending, page.bill = True, True
    adapter = PlaywrightSalesHeaderPage(page, owns_page=lambda p: True)
    adapter._frames = lambda kind: [page.form] if kind == "bill" else []
    with pytest.raises(HeaderStop, match="OWNER_RETURN_REQUIRED"):
        adapter.open_for_header()
    assert not page.adds and not page.cancels


class LoadingPage(PromptPage):
    def __init__(self):
        super().__init__()
        self.elapsed=0;self.menu_clicks=0;self.list_after=300;self.button_after=600
        self.menu=Action(self.open_menu)
        self.add.count=lambda: int(self.elapsed >= self.button_after)
    def open_menu(self): self.menu_clicks+=1
    def locator(self,selector):
        if selector=='a#iframe_XiaoShou_menu': return self.menu
        if selector=='iframe#iframe_XiaoShou_frame': return SimpleNamespace(wait_for=lambda **kw:None)
        raise AssertionError(selector)
    def wait_for_timeout(self,ms): self.elapsed+=ms
    def loaded_frames(self,kind):
        if kind=='bill': return [self.form] if self.bill else []
        return [self.list] if self.elapsed >= self.list_after else []


def test_cold_shell_waits_for_list_navigation_and_add_control_once(monkeypatch):
    from src.inso import sales_header
    page=LoadingPage()
    monkeypatch.setattr(sales_header,'monotonic',lambda:page.elapsed/1000)
    adapter=PlaywrightSalesHeaderPage(page,owns_page=lambda p:True)
    adapter._frames=page.loaded_frames
    adapter.open_for_header()
    assert page.elapsed>=600 and page.menu_clicks==1 and page.adds==1
    assert page.cancels==1 and adapter.frame is page.form and not page.listeners


def test_already_open_list_waits_for_button_without_menu_click(monkeypatch):
    from src.inso import sales_header
    page=LoadingPage();page.list_after=0
    monkeypatch.setattr(sales_header,'monotonic',lambda:page.elapsed/1000)
    adapter=PlaywrightSalesHeaderPage(page,owns_page=lambda p:True);adapter._frames=page.loaded_frames
    adapter.open_for_header()
    assert page.menu_clicks==0 and page.adds==1 and page.elapsed>=600


def test_list_load_timeout_never_clicks_add(monkeypatch):
    from src.inso import sales_header
    page=LoadingPage();page.list_after=20000
    monkeypatch.setattr(sales_header,'monotonic',lambda:page.elapsed/1000)
    adapter=PlaywrightSalesHeaderPage(page,owns_page=lambda p:True);adapter._frames=page.loaded_frames
    with pytest.raises(HeaderStop,match='SALES_LIST_UNCONFIRMED'): adapter.open_for_header()
    assert page.menu_clicks==1 and page.adds==0 and page.elapsed==15000


def test_ambiguous_list_and_ownership_loss_do_not_add():
    page=LoadingPage();adapter=PlaywrightSalesHeaderPage(page,owns_page=lambda p:False)
    with pytest.raises(HeaderStop,match='TAB_OWNERSHIP_LOST'): adapter.open_for_header()
    adapter._owns_page=lambda p:True
    adapter._frames=lambda kind: [page.list,page.list] if kind=='list' else []
    with pytest.raises(HeaderStop,match='SALES_LIST_UNCONFIRMED'): adapter.open_for_header()
    assert not page.adds and not page.menu_clicks
