"""Existing native page guard/cleanup at the optional same-Owner checkpoint."""
import pytest

from src.launcher.google_quote_update import google_operations_idle
from src.launcher.v13_quotation import (
    quotation_operation_scope,
    quotation_operations,
    settle_quotation_operations,
)
from src.research.cdp_pages import PageTargetOwnershipError
from src.workflow.v12_faults import V12Fault
from tests.launcher.test_google_web import web as web_fixture
from tests.launcher.test_inso_session import _Login
from tests.launcher.test_v13_quotation_operations import (
    retained_browser as browser_fixture,
)


@pytest.mark.parametrize('problem', ['none', 'pending', 'dialog', 'auth', 'owner', 'target'])
def test_existing_google_guard_certifies_idle_and_retains_pages(tmp_path, monkeypatch, problem):
    service, browser, _, original = web_fixture.__wrapped__(tmp_path)
    service._retained_pages = {}
    with service.poll_scope():
        service.get(spreadsheetId='test', range="'2026'!A1:G").execute()
        page = browser.contexts[0].pages[-1]
        if problem == 'pending':
            page.refresh_pending = True
        elif problem == 'dialog':
            page.popup = 'Unexpected dialog'
        elif problem == 'auth':
            page.login_markers.add('登录')
        elif problem == 'owner':
            page.owner_name = ''
        elif problem == 'target':
            monkeypatch.setattr('src.launcher.google_quote_update._google_target_id', lambda _: 'changed')
        if problem == 'auth':
            with pytest.raises(V12Fault, match='GOOGLE_AUTHENTICATION_REQUIRED'):
                service.operations_idle()
        elif problem in {'owner', 'target'}:
            with pytest.raises((PageTargetOwnershipError, V12Fault)):
                service.operations_idle()
        else:
            assert service.operations_idle() is (problem == 'none')
        assert not page.closed and not original.closed
    assert not page.closed and not original.closed


@pytest.mark.parametrize('state', ['closed', 'active', 'protected', 'failed_close', 'expired_auth', 'lost_owner'])
def test_quotation_checkpoint_uses_existing_owned_close_and_preserves_protection(state, monkeypatch):
    handle, context = browser_fixture.__wrapped__()
    original = tuple(context.pages)
    scope = quotation_operation_scope()
    try:
        with scope:
            operation = quotation_operations(browser_handle=handle, login=_Login())
            page = operation.open('synthetic').operation_page().page
            if state == 'protected':
                operation.preserve()
            elif state != 'active':
                operation.close()  # Logical release inside original retained scope.
            if state == 'expired_auth':
                monkeypatch.setattr('src.launcher.v13_quotation.authenticated_inso_shell_available', lambda _: False)
            elif state == 'lost_owner':
                page.owner_name = ''
            if state == 'failed_close':
                monkeypatch.setattr(type(operation._session), 'close_owned_operation_tab', lambda self: None)
                with pytest.raises(V12Fault, match='INSO_OPERATION_NOT_CLOSED'):
                    settle_quotation_operations()
            elif state == 'lost_owner':
                with pytest.raises(PageTargetOwnershipError):
                    settle_quotation_operations()
                assert not page.closed
            else:
                assert settle_quotation_operations() is (state == 'closed')
                assert page.closed is (state == 'closed')
            assert all(not p.closed for p in original)
    except V12Fault:
        assert state == 'failed_close'


def test_checkpoints_default_closed_outside_owner_scopes():
    assert not google_operations_idle()
    assert not settle_quotation_operations()


def test_checkpoint_uses_original_global_lock_and_refuses_foreign_scope(tmp_path):
    import threading

    from src.launcher.google_web import _GOOGLE_GRID_LOCK
    service, _, _, _ = web_fixture.__wrapped__(tmp_path)
    entered, finished = threading.Event(), threading.Event()
    verdict = []
    def check():
        entered.set()
        verdict.append(service.operations_idle())
        finished.set()
    with _GOOGLE_GRID_LOCK:
        thread = threading.Thread(target=check)
        thread.start()
        assert entered.wait(2)
        assert not finished.wait(.05)
    thread.join(2)
    assert not thread.is_alive() and verdict == [False]
