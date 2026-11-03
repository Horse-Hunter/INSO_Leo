"""Unrelated targets cannot abort reuse of a positively proven owned target."""
import pytest

from src.workflow.v12_faults import V12Fault
from tests.launcher.test_google_final_retirement import acquire
from tests.launcher.test_google_web import web as web  # noqa: PLC0414


@pytest.mark.parametrize("operation", ["read", "retire"])
def test_unrelated_page_probe_failure_keeps_positive_owned_proof(web, monkeypatch, operation):
    service, pages = acquire(web)
    browser, human = web[1], web[3]
    original = human.context.new_cdp_session
    def probe(page):
        if page is human: raise RuntimeError("synthetic foreign page cannot attach")
        return original(page)
    monkeypatch.setattr(human.context, "new_cdp_session", probe)
    if operation == "read":
        with service.poll_scope():
            service.get(spreadsheetId="test", range="'2026'!A1:G").execute()
        assert all(not p.closed for p in pages)
    else:
        service.release_retained_pages()
        assert all(p.closed for p in pages)
    assert not human.closed and browser.connected


def test_no_positive_target_proof_remains_fail_closed(web, monkeypatch):
    service, pages = acquire(web)
    for page in pages:
        monkeypatch.delattr(page, "_inso_native_page_owner", raising=False)
    monkeypatch.setattr(pages[0].context, "new_cdp_session", lambda page: (_ for _ in ()).throw(RuntimeError("unknown")))
    with pytest.raises(TimeoutError, match="GOOGLE_WEB_READ_UNAVAILABLE"), service.poll_scope():
        service.get(spreadsheetId="test", range="'2026'!A1:G").execute()
    assert all(not p.closed for p in pages) and not web[3].closed


@pytest.mark.parametrize("failure", ["native", "detach"])
def test_positive_match_cannot_hide_owned_or_cleanup_failure(web, monkeypatch, failure):
    service, pages = acquire(web)
    if failure == "native":
        original = web[1].new_browser_cdp_session
        def broken():
            session = original()
            send = session.send
            def proof(method, params=None):
                if params and params.get("targetId") == str(id(pages[0])):
                    raise RuntimeError("owned proof unavailable")
                return send(method, params)
            session.send = proof
            return session
        monkeypatch.setattr(web[1], "new_browser_cdp_session", broken)
    else:
        original = web[3].context.new_cdp_session
        def broken(page):
            session = original(page)
            if page is web[3]:
                session.detach = lambda: (_ for _ in ()).throw(RuntimeError("cleanup unknown"))
            return session
        monkeypatch.setattr(web[3].context, "new_cdp_session", broken)
    with pytest.raises(V12Fault, match="GOOGLE_TAB_IDENTITY_UNCONFIRMED"):
        service.release_retained_pages()
    assert not pages[0].closed and not web[3].closed
