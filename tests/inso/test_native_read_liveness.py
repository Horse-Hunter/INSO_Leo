"""Real SDK owner-loop proof for previously bypassed quotation ports; no network."""
import asyncio
import threading
from types import SimpleNamespace

import pytest
from greenlet import greenlet
from playwright.sync_api import Frame, Response

from src.research.cdp_pages import bounded_browser_call


@pytest.mark.parametrize('kind,method,args',[(Frame,'evaluate',('() => true',)),(Response,'json',())])
def test_quotation_native_ports_obey_same_owner_deadline(kind,method,args):
    entered=threading.Event();release=threading.Event();done=threading.Event();errors=[];owners=[]
    def run():
        loop=asyncio.new_event_loop();dispatcher=greenlet(loop.run_forever)
        async def pending(*a,**kw):
            entered.set();owners.append(threading.get_ident())
            while not release.is_set():await asyncio.sleep(.005)
        impl=SimpleNamespace(_loop=loop,_dispatcher_fiber=dispatcher,**{method:pending})
        try:bounded_browser_call(kind(impl),method,*args,timeout_ms=20)
        except Exception as error:errors.append(error)  # noqa: BLE001
        finally:
            loop.call_soon(loop.stop);dispatcher.switch()
            asyncio._set_running_loop(None);loop.close();done.set()
    thread=threading.Thread(target=run);thread.start()
    try:
        assert entered.wait(1)
        assert done.wait(.3),'Actual SDK port silently bypassed native deadline'
        assert len(errors)==1 and isinstance(errors[0],TimeoutError)
        assert owners==[thread.ident]
    finally:release.set();thread.join(2)
    assert not thread.is_alive()


def test_identity_protocol_timeout_is_not_auth_failure_and_does_not_invalidate_lease():
    from src.core.browser_protocol import NativeProtocolTimeout
    from src.inso.session import BrowserOwnership, LeaseState
    from tests.inso.test_v12_session import make_lease
    lease,_,_,_=make_lease(BrowserOwnership.REUSED)
    def unavailable(_):raise NativeProtocolTimeout('CDP_OPERATION_TIMEOUT')
    lease._operation_page_is_valid=unavailable
    with pytest.raises(NativeProtocolTimeout):lease.adapter_access('synthetic')
    assert lease.state is LeaseState.ACTIVE


def test_actual_quote_capture_is_bounded_and_classified_as_read_failure_not_auth():
    from src.core.browser_protocol import browser_call_budget
    from src.inso.duplicate_history import (
        DuplicateHistoryFailure,
        InsoDuplicateHistoryError,
    )
    from src.inso.quotation_read import InsoQuotationReader
    entered=threading.Event();release=threading.Event();done=threading.Event();errors=[]
    def run():
        loop=asyncio.new_event_loop();dispatcher=greenlet(loop.run_forever)
        async def pending(*a,**kw):
            entered.set()
            while not release.is_set():await asyncio.sleep(.005)
        frame=Frame(SimpleNamespace(_loop=loop,_dispatcher_fiber=dispatcher,evaluate=pending))
        class Factory:
            def __init__(self,value):assert value is frame
            def query_exact_response(self,mpn,*,capture_page):
                return {'rows':capture_page(frame,[])}
        from contextlib import nullcontext
        access=SimpleNamespace(operation_page=lambda:nullcontext(SimpleNamespace(shell_frame=frame)))
        try:
            with browser_call_budget(20):InsoQuotationReader(page_factory=Factory).read(access,'SYNTHETIC')
        except Exception as error:errors.append(error)  # noqa: BLE001
        finally:
            loop.call_soon(loop.stop);dispatcher.switch()
            asyncio._set_running_loop(None);loop.close();done.set()
    thread=threading.Thread(target=run);thread.start()
    try:
        assert entered.wait(1) and done.wait(.3)
        assert len(errors)==1 and isinstance(errors[0],InsoDuplicateHistoryError)
        assert errors[0].code is DuplicateHistoryFailure.QUERY_SETTLEMENT_UNCONFIRMED
    finally:release.set();thread.join(2)
    assert not thread.is_alive()


def test_expired_read_budget_retains_independent_bounded_identity_cleanup(monkeypatch):
    from src.core.browser_protocol import (
        NativeProtocolTimeout,
        bounded_browser_call,
        browser_call_budget,
    )
    from src.inso.session import BrowserOwnership, LeaseState
    from tests.inso.test_v12_session import make_lease
    lease,_,_,_=make_lease(BrowserOwnership.REUSED);checked=[]
    def identity(_):
        bounded_browser_call(SimpleNamespace(count=lambda:checked.append(True) or 1),'count')
        return True
    lease._operation_page_is_valid=identity
    clock=[0.]
    monkeypatch.setattr('src.core.browser_protocol.monotonic',lambda:clock[0])
    with pytest.raises(NativeProtocolTimeout),browser_call_budget(1),lease.adapter_access('synthetic').operation_page():
        clock[0]=1
        bounded_browser_call(SimpleNamespace(count=lambda:1),'count')
    assert len(checked)>=4 and lease.state is LeaseState.ACTIVE
