"""Real asyncio timing on the original sync SDK port; no Chrome/CDP/network."""
import asyncio
import threading
import time
from contextlib import nullcontext
from types import SimpleNamespace

from greenlet import greenlet
from playwright.sync_api import CDPSession

from src.research.cdp_pages import (
    PageResourceAdmission,
    PageTargetCreationUncertain,
    new_background_page,
)


def test_native_create_command_cannot_outlive_deadline_or_close_unproven_target():
    entered=threading.Event();release=threading.Event();done=threading.Event()
    outcomes=[];calls=[];owner=[]
    admission=PageResourceAdmission()
    def run():
        loop=asyncio.new_event_loop()
        dispatcher=greenlet(loop.run_forever)
        class Impl:
            _loop=loop
            _dispatcher_fiber=dispatcher
            async def send(self,method,params=None):
                owner.append(threading.get_ident());calls.append(method)
                if method=="Target.createTarget":
                    entered.set()
                    while not release.is_set():await asyncio.sleep(.005)
                    return {"targetId":"synthetic-late-target"}
                return {"success":True}
            async def detach(self):pass
        port=CDPSession(Impl())
        browser=SimpleNamespace(new_browser_cdp_session=lambda:port,_inso_page_admission=admission)
        context=SimpleNamespace(pages=[object()],expect_event=lambda *a,**k:nullcontext(SimpleNamespace(value=None)))
        try:new_background_page(browser,context,timeout_ms=20,owner="google-operation")
        except Exception as error:  # noqa: BLE001 - collect worker outcome for explicit assertions
            outcomes.append(error)
        finally:
            if not dispatcher.dead:
                loop.call_soon(loop.stop);dispatcher.switch()
            asyncio._set_running_loop(None)
            loop.close();done.set()
    thread=threading.Thread(target=run)
    started=time.monotonic();thread.start()
    try:
        assert entered.wait(1)
        assert done.wait(.3),"Native CDP command ignored the page timeout"
        assert time.monotonic()-started<.5
        assert len(outcomes)==1 and isinstance(outcomes[0],PageTargetCreationUncertain)
        assert admission.failed_locally
        assert "Target.closeTarget" not in calls
        assert len(set(owner))==1 and owner[0]==thread.ident
    finally:release.set();thread.join(2)
    assert not thread.is_alive()


def test_ownership_marker_command_has_native_deadline(monkeypatch):
    from playwright.sync_api import Page

    from src.research.cdp_pages import mark_owned_page
    monkeypatch.setattr("src.research.cdp_pages.NATIVE_PROTOCOL_TIMEOUT_MS",20)
    entered=threading.Event();release=threading.Event();done=threading.Event();outcomes=[]
    def run():
        loop=asyncio.new_event_loop();dispatcher=greenlet(loop.run_forever)
        class Impl:
            _loop=loop
            _dispatcher_fiber=dispatcher
            async def evaluate(self,*args,**kwargs):
                entered.set()
                while not release.is_set():await asyncio.sleep(.005)
        try:mark_owned_page(Page(Impl()),"google-operation")
        except Exception as error:outcomes.append(error)  # noqa: BLE001
        finally:
            loop.call_soon(loop.stop);dispatcher.switch()
            asyncio._set_running_loop(None);loop.close();done.set()
    thread=threading.Thread(target=run);thread.start()
    try:
        assert entered.wait(1)
        assert done.wait(.3),"Ownership marker ignored native deadline"
        assert len(outcomes)==1 and isinstance(outcomes[0],TimeoutError)
    finally:release.set();thread.join(2)
    assert not thread.is_alive()

import pytest


@pytest.mark.parametrize('port_name,method,args',[
    ('Keyboard','type',('synthetic',)),
    ('Locator','count',()),
    ('Locator','evaluate',('element => true',)),
])
def test_native_write_metadata_and_keyboard_have_owner_thread_deadline(port_name,method,args):
    import playwright.sync_api as api

    from src.research.cdp_pages import bounded_browser_call
    entered=threading.Event();done=threading.Event();outcomes=[];owners=[]
    def run():
        loop=asyncio.new_event_loop();dispatcher=greenlet(loop.run_forever)
        class Impl:
            _loop=loop
            _dispatcher_fiber=dispatcher
        async def stalled(*a,**kw):
            entered.set();owners.append(threading.get_ident())
            await asyncio.Event().wait()
        impl=Impl();setattr(impl,method,stalled)
        try:bounded_browser_call(getattr(api,port_name)(impl),method,*args,timeout_ms=20)
        except Exception as error:outcomes.append(error)  # noqa: BLE001
        finally:
            loop.call_soon(loop.stop);dispatcher.switch()
            asyncio._set_running_loop(None);loop.close();done.set()
    thread=threading.Thread(target=run);thread.start()
    try:
        assert entered.wait(1) and done.wait(.3)
        assert len(outcomes)==1 and isinstance(outcomes[0],TimeoutError)
        assert owners==[thread.ident]
    finally:thread.join(2)
    assert not thread.is_alive()

@pytest.mark.parametrize('method',['goto','wait_for_url'])
def test_real_page_wrapper_maps_public_navigation_keywords_to_native_signature(method):
    from playwright._impl._page import Page as NativePage
    from playwright.sync_api import Page

    from src.research.cdp_pages import bounded_browser_call
    loop=asyncio.new_event_loop();dispatcher=greenlet(loop.run_forever);seen=[]
    class Impl:
        _loop=loop
        _dispatcher_fiber=dispatcher
        async def goto(self,url,*,timeout=None,waitUntil=None):
            seen.append((url,timeout,waitUntil))
        async def wait_for_url(self,url,*,timeout=None,waitUntil=None):
            seen.append((url,timeout,waitUntil))
    try:
        native=object.__new__(NativePage)
        native._loop=loop;native._dispatcher_fiber=dispatcher;native._main_frame=Impl()
        bounded_browser_call(Page(native),method,'https://example.invalid/',
            timeout=20,wait_until='domcontentloaded',timeout_ms=100)
        assert seen==[('https://example.invalid/',20,'domcontentloaded')]
    finally:
        loop.call_soon(loop.stop);dispatcher.switch()
        asyncio._set_running_loop(None);loop.close()
