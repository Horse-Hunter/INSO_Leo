"""Original Google scopes and quotation-to-TP path; no external services."""
from contextlib import contextmanager

import pytest

from src.launcher.browser_bootstrap import BrowserHandle
from src.launcher.google_quote_update import GoogleQuotationUpdateActions
from src.workflow.v12_faults import V12Fault
from tests.launcher.test_google_web import web as web_fixture
from tests.launcher.test_tp_safe_quotation_yield import assembly


def rotating_service(tmp_path, monkeypatch):
    service, browser, _, original = web_fixture.__wrapped__(tmp_path)
    service._retained_pages = {}
    generation, sessions, closed = [0], [], []
    @contextmanager
    def session():
        handle = BrowserHandle(owned=False, browser=browser)
        handle.generation = generation[0]
        sessions.append(handle)
        try:
            yield handle
        finally:
            closed.append(handle)
    service._session = session
    close = GoogleQuotationUpdateActions.close
    def checked_close(actions):
        # A stopped old sync client cannot execute final settlement/target proof.
        assert actions._handle.generation == generation[0], 'STALE_CLIENT_USED_FOR_GOOGLE_SETTLEMENT'
        return close(actions)
    monkeypatch.setattr(GoogleQuotationUpdateActions, 'close', checked_close)
    return service, generation, sessions, closed, original


def read(service):
    return service.get(spreadsheetId='test', range="'2026'!A1:G").execute()


def test_suspension_ends_page_borrows_before_nested_reconnect(tmp_path, monkeypatch):
    service, generation, sessions, closed, original = rotating_service(tmp_path, monkeypatch)
    with service.poll_scope():
        read(service)
        outer = service._poll_handle.get()
        with service.suspend_idle_poll():
            assert closed == sessions and service._poll_handle.get() is None
            with service.poll_scope():
                assert service._poll_handle.get() is not outer
                read(service)
            generation[0] += 1  # Original TP cleanup/recovery replaces its client.
        assert service._poll_handle.get() is outer and outer['handle'] is None
        read(service)
    assert len(sessions) == 3 and closed == sessions and not original.closed


def test_old_borrowed_scope_reproduces_stale_cleanup_on_reconnect(tmp_path, monkeypatch):
    service, generation, _, _, _ = rotating_service(tmp_path, monkeypatch)
    with pytest.raises(AssertionError, match='STALE_CLIENT'), service.poll_scope():
        read(service)
        with service.poll_scope():
            read(service)
        generation[0] += 1


@pytest.mark.parametrize('problem', ['outside', 'busy', 'stop', 'auth'])
def test_suspension_cannot_discard_unsafe_pages(tmp_path, monkeypatch, problem):
    service, _, _, _, _ = rotating_service(tmp_path, monkeypatch)
    if problem == 'outside':
        with pytest.raises(V12Fault, match='GOOGLE_OPERATION_NOT_CLOSED'), service.suspend_idle_poll():
            pytest.fail('unsafe handoff')
        return
    with service.poll_scope():
        read(service)
        entry = service._poll_handle.get()['handle']
        if problem == 'stop':
            service._stop_requested = lambda: True
        elif problem == 'auth':
            entry.browser.contexts[0].pages[-1].login_markers.add('登录')
        else:
            entry.browser.contexts[0].pages[-1].refresh_pending = True
        with pytest.raises(V12Fault), service.suspend_idle_poll():
            pytest.fail('unsafe handoff')


def test_real_quotation_tp_return_reacquires_google_scope(tmp_path, monkeypatch):
    a = assembly(tmp_path / 'flow', monkeypatch)
    service, generation, sessions, closed, original = rotating_service(tmp_path / 'grid', monkeypatch)
    (tmp_path / 'grid').mkdir(exist_ok=True)
    a.backend._manual_write_service = lambda: service
    research = a.tp.research.hook
    def nested_research():
        with service.poll_scope():
            read(service)
        generation[0] += 1
        research()
    a.tp.research.hook = nested_research
    with service.poll_scope():
        read(service)
        a.run()
        read(service)
    assert [e[0] for e in a.events][:4] == ['quote_read', 'settled', 'brief', 'quote_read']
    assert len(sessions) >= 3 and closed == sessions
    assert not a.runtime.module_resource_failed and not original.closed
