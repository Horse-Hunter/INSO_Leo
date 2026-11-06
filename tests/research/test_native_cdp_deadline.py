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
