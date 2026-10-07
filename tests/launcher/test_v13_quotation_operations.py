from types import SimpleNamespace

import pytest

from src.inso.session import BrowserOwnership
from src.launcher.browser_bootstrap import BrowserHandle
from src.launcher.v13_quotation import V13QuotationOperations
from src.workflow.v12_faults import FaultScope, V12Fault
from tests.inso.test_v12_session import make_lease
from tests.launcher.test_inso_session import (
    FakeBrowser,
    FakeContext,
    FakePlaywright,
    _Login,
    _LoginPage,
)
from tests.workflow.test_v13_quotation import WS, cycle


def test_adapter_reuses_owned_lease_and_closes_only_order_page():
    leases, calls = [], []
    handle = SimpleNamespace(owned=False)
    def attach(endpoint, received, **kwargs):
        assert endpoint == "http://127.0.0.1:9222" and received is handle
        assert kwargs["fresh_page"] and kwargs["login"] is login
        lease, browser, context, page = make_lease(BrowserOwnership.REUSED, owns_operation_page=True)
        leases.append((lease, browser, context, page))
        calls.append(kwargs["cycle_id"])
        return SimpleNamespace(owns_operation_page=True,
            operation_access=lambda: lease.adapter_access("quotation"),
            close_owned_operation_tab=lambda: lease.adapter_access("quotation").close_owned_operation_tab())
    login = object()
    operations = V13QuotationOperations(browser_handle=handle, login=login, attach=attach)
    for inquiry_id in ("original-1", "original-2"):
        access = operations.open(inquiry_id)
        assert access.operation_page().page is leases[-1][3]
        operations.close()
    assert calls == ["original-1", "original-2"]
    assert leases[0][3] is not leases[1][3]
    for _, browser, context, page in leases:
        assert page.closed
        assert browser.connected and browser.close_count == 0
        assert not context.closed and not context.pages[1].closed


@pytest.mark.parametrize("challenge", ["CAPTCHA", "手机验证码", "设备验证"])
def test_actual_rfq002_authentication_keeps_human_page_in_v13_cycle(monkeypatch, challenge):
    context = FakeContext()
    existing = tuple(context.pages)
    page = _LoginPage(context, body_text=challenge)
    def fresh():
        context.pages.append(page)
        return page
    monkeypatch.setattr(context, "new_page", fresh)
    browser = FakeBrowser([context])
    playwright = FakePlaywright(browser)
    closures = []
    handle = BrowserHandle(owned=False, browser=browser, playwright=playwright,
                           close_fn=lambda: closures.append("browser"),
                           cleanup_fn=lambda: closures.append("profile"))
    operations = V13QuotationOperations(browser_handle=handle, login=_Login())
    service, _, quotes, waits = cycle([])
    service._operations = operations
    with pytest.raises(V12Fault) as raised:
        service.run(WS)
    assert raised.value.scope is FaultScope.GLOBAL_STOP
    assert raised.value.reason == "INSO_AUTHENTICATION_REQUIRED"
    operations.close()
    assert page in context.pages and not page.closed and page.clicks == 0
    assert all(not p.closed for p in existing)
    assert browser.connected and browser.contexts == [context]
    assert closures == [] and playwright.stop_count == 1
    assert quotes.calls == [] and waits == []


def test_midquery_session_guard_failure_keeps_existing_owned_page():
    from src.inso.quotation_read import InsoQuotationReader
    lease, browser, context, page = make_lease(BrowserOwnership.REUSED, owns_operation_page=True)
    class History:
        def __init__(self, frame):
            pass
        def query_exact_response(self, target, **kwargs):
            page.valid = False  # Challenge/login invalidates the shared leased shell.
            return {"rows": []}
    operations = V13QuotationOperations(browser_handle=SimpleNamespace(owned=False), login=object(),
        attach=lambda *a, **kw: SimpleNamespace(owns_operation_page=True,
            operation_access=lambda: lease.adapter_access("quotation"),
            close_owned_operation_tab=lambda: lease.adapter_access("quotation").close_owned_operation_tab()))
    service, _, _, waits = cycle([])
    service._operations, service._quotes = operations, InsoQuotationReader(page_factory=History)
    with pytest.raises(V12Fault) as raised:
        service.run(WS)
    assert raised.value.scope is FaultScope.GLOBAL_STOP
    assert raised.value.reason == "INSO_AUTHENTICATION_REQUIRED"
    operations.close()
    assert not page.closed and browser.connected and not context.closed
    assert waits == []


def test_adapter_rejects_owned_browser_and_overlapping_operations():
    with pytest.raises(ValueError):
        V13QuotationOperations(browser_handle=SimpleNamespace(owned=True), login=object())
    operations = V13QuotationOperations(browser_handle=SimpleNamespace(owned=False), login=object())
    operations._session = object()
    with pytest.raises(V12Fault) as raised:
        operations.open("next-order")
    assert raised.value.reason == "INSO_OPERATION_NOT_CLOSED"


def test_failed_owned_tab_close_blocks_the_next_order():
    lease, _, _, page = make_lease(BrowserOwnership.REUSED, owns_operation_page=True)
    operations = V13QuotationOperations(browser_handle=SimpleNamespace(owned=False), login=object(),
        attach=lambda *a, **kw: SimpleNamespace(owns_operation_page=True,
            operation_access=lambda: lease.adapter_access("quotation"),
            close_owned_operation_tab=lambda: None))
    operations.open("original-1")
    with pytest.raises(V12Fault) as raised:
        operations.close()
    assert raised.value.scope is FaultScope.GLOBAL_STOP
    assert raised.value.reason == "INSO_OPERATION_NOT_CLOSED"
    with pytest.raises(V12Fault):
        operations.open("original-2")
    assert not page.closed
