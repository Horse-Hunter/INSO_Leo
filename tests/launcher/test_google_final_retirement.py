"""Final retained-page cleanup on the original Owner; no Chrome/network."""
from contextlib import nullcontext
from threading import Thread, get_ident
from types import SimpleNamespace

import pytest

from src.gui.contracts import RunState
from src.launcher.backend import ProductionBackend
from src.launcher.browser_bootstrap import BrowserHandle
from src.launcher.google_web import build_google_web_service
from src.workflow.v12_faults import FaultScope, V12Fault
from tests.launcher.test_google_web import web as web  # noqa: PLC0414


def acquire(web):
    service, browser, _, _ = web
    service._retained_pages = {}
    with service.poll_scope():
        for title in ('2026', 'SHAHAB'):
            service.get(spreadsheetId='test', range=f"'{title}'!A1:G").execute()
    return service, browser.contexts[0].pages[-2:]


def test_final_stop_closes_only_known_settled_pages_and_never_downloads_again(web):
    service, pages = acquire(web)
    _, browser, _, human = web
    orphan = browser.contexts[0].new_page()
    orphan.owner_name = 'INSO_OWNER_TAB:google-operation'
    orphan.url = 'https://docs.google.com/spreadsheets/d/test/edit#gid=0'
    downloads = sum(len(p.downloads) for p in pages)
    service._stop_requested = lambda: True
    service.release_retained_pages()
    assert all(p.closed for p in pages) and service._retained_pages == {}
    assert not human.closed and not orphan.closed and browser.connected
    assert downloads == sum(len(p.downloads) for p in pages)


@pytest.mark.parametrize('problem', ['dialog', 'dirty', 'pending', 'worksheet', 'protected'])
def test_final_stop_preserves_unsettled_or_manually_changed_pages(web, problem, monkeypatch):
    service, pages = acquire(web)
    page = pages[0]
    if problem == 'dialog': page.popup = 'visible'
    elif problem == 'dirty':
        from src.launcher.google_quote_update import _UNSAFE_POLL_PAGE
        evaluate = page.evaluate
        monkeypatch.setattr(page, 'evaluate', lambda script, arg=None:
                            True if script == _UNSAFE_POLL_PAGE else evaluate(script, arg))
    elif problem == 'pending': page.refresh_pending = True
    elif problem == 'worksheet': page.title = 'SHAHAB'
    else:
        key = next(iter(service._retained_pages))
        native, _, reopenable = service._retained_pages[key]
        service._retained_pages[key] = (native, True, reopenable)
    service.release_retained_pages()
    assert not page.closed and pages[1].closed
    assert len(service._retained_pages) == 1
    assert next(iter(service._retained_pages.values()))[1] is True


@pytest.mark.parametrize('problem', ['auth', 'document', 'owner', 'native', 'close'])
def test_cleanup_faults_remain_shared_faults_and_do_not_discard_ownership(web, problem, monkeypatch):
    service, pages = acquire(web)
    page = pages[0]
    if problem == 'auth': page.login_markers.add('登录')
    elif problem == 'document': page.url = page.url.replace('/d/test/', '/d/other/')
    elif problem == 'owner': page.owner_name = 'INSO_OWNER_TAB:manual'
    elif problem == 'native':
        monkeypatch.setattr(page.context, 'new_cdp_session', lambda _p: (_ for _ in ()).throw(ValueError('proof')))
    else: monkeypatch.setattr(page, 'close', lambda: (_ for _ in ()).throw(ValueError('close')))
    with pytest.raises(V12Fault) as fault:
        service.release_retained_pages()
    assert fault.value.scope is FaultScope.GLOBAL_STOP
    assert not page.closed and not pages[1].closed and service._retained_pages


def test_missing_known_page_is_not_recreated_and_active_poll_cannot_retire(web):
    service, pages = acquire(web)
    with service.poll_scope(), pytest.raises(V12Fault, match='GOOGLE_OPERATION_NOT_CLOSED'):
        service.release_retained_pages()
    pages[0].close()
    count = len(web[1].contexts[0].pages)
    service.release_retained_pages()
    assert len(web[1].contexts[0].pages) == count and pages[1].closed
    assert service._retained_pages == {}


def test_shared_admission_failure_never_attaches_for_cleanup(web):
    service, pages = acquire(web)
    attached = []
    service._retire_session = lambda: attached.append(True)
    service._read_guard = lambda: (_ for _ in ()).throw(V12Fault(FaultScope.GLOBAL_STOP, 'SAFETY'))
    with pytest.raises(V12Fault, match='SAFETY'):
        service.release_retained_pages()
    assert not attached and all(not p.closed for p in pages)


def test_repeated_normal_runtime_lifetimes_do_not_add_live_orphans(web):
    for _ in range(5):
        service, pages = acquire(web)
        assert sum(not p.closed for p in web[1].contexts[0].pages) == 3
        service.release_retained_pages()
        assert all(p.closed for p in pages)
        assert sum(not p.closed for p in web[1].contexts[0].pages) == 1


def test_retire_factory_never_calls_business_bootstrap_provider(web, monkeypatch):
    from src.launcher import google_web
    supplied = []
    browser = web[1]
    fake = SimpleNamespace(chromium=SimpleNamespace(connect_over_cdp=lambda *a, **kw: browser))
    def factory(provider):
        supplied.append(provider)
        return lambda: nullcontext(fake)
    monkeypatch.setattr(google_web, 'shared_playwright_factory', factory)
    service = build_google_web_service(provider=lambda: pytest.fail('must not bootstrap on stop'))
    with service._retire_session() as handle:
        assert handle.browser is browser and not handle.owned
    assert supplied == [None]


@pytest.mark.parametrize('state', [RunState.GLOBAL_STOP, RunState.MODULE_PAUSED, RunState.MANUAL_REVIEW])
def test_backend_preserves_all_human_recovery_surfaces(tmp_path, state):
    backend = ProductionBackend(root=tmp_path)
    backend._state = state
    backend._retire_google_pages(SimpleNamespace(release_retained_pages=lambda **kw: pytest.fail('human page')))
    backend.shutdown()


def test_backend_retire_propagates_failure_through_original_runtime_error(tmp_path):
    backend = ProductionBackend(root=tmp_path)
    backend._state = RunState.RUNNING
    faults = []
    backend._runtime_error = faults.append
    service = SimpleNamespace(release_retained_pages=lambda **kw: (_ for _ in ()).throw(ValueError('close')))
    backend._retire_google_pages(service)
    assert len(faults) == 1 and faults[0].scope is FaultScope.GLOBAL_STOP
    assert faults[0].reason == 'GOOGLE_OPERATION_NOT_CLOSED'
    backend.shutdown()


def test_backend_does_not_send_owner_objects_to_another_thread(tmp_path):
    backend = ProductionBackend(root=tmp_path)
    backend._state = RunState.RUNNING
    handle = BrowserHandle(owned=False, browser=SimpleNamespace(is_connected=lambda: True))
    backend._browser_handle = handle
    faults = []
    backend._runtime_error = faults.append
    worker = Thread(target=lambda: backend._retire_google_pages(SimpleNamespace(
        release_retained_pages=lambda **kw: pytest.fail('cross thread'))))
    worker.start(); worker.join(timeout=3)
    assert not worker.is_alive() and faults[0].reason == 'GOOGLE_TAB_IDENTITY_UNCONFIRMED'
    assert handle._owner_thread == get_ident()
    backend._browser_handle = None
    backend.shutdown()
