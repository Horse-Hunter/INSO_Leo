"""Owned worksheet slots and the actual hidden-dialog predicate, fully offline."""
import json
import subprocess

import pytest
from playwright._impl._driver import compute_driver_executable

from src.launcher.google_quote_update import _UNSAFE_POLL_PAGE
from tests.launcher.test_google_web import (
    web as web,  # noqa: PLC0414 - pytest fixture re-export
)


@pytest.mark.parametrize('visibility,display,pending,dirty,expected', [
    ('hidden', 'flex', False, False, False),
    ('visible', 'none', False, False, False),
    ('visible', 'flex', False, False, True),
    ('hidden', 'flex', True, False, True),
    ('hidden', 'flex', False, True, True),
])
def test_real_dialog_predicate_ignores_hidden_callout_but_keeps_real_work(
    visibility, display, pending, dirty, expected,
):
    # Use Playwright's existing Node runtime, without launching any browser/CDP.
    node, _ = compute_driver_executable()
    state = json.dumps({'visibility': visibility, 'display': display,
                        'pending': pending, 'dirty': dirty})
    script = f'''
        const state = {state};
        global.window = {{__insoRefreshPending: state.pending}};
        global.document = {{
            body: {{innerText: ''}},
            querySelectorAll: () => [{{getClientRects: () => [{{}}]}}],
            querySelector: () => ({{getAttribute: () => state.dirty ? 'saving' : null}}),
        }};
        global.getComputedStyle = () => state;
        const predicate = ({_UNSAFE_POLL_PAGE});
        process.stdout.write(JSON.stringify(!!predicate()));
    '''
    result = subprocess.run([str(node), '-e', script], check=True,
                            capture_output=True, text=True, timeout=10)
    assert json.loads(result.stdout) is expected


def test_protected_slot_does_not_spawn_replacement_tabs(web):
    service, browser, _, original = web
    with service.poll_scope():
        service.get(spreadsheetId='test', range="'2026'!A1:G").execute()
        old = browser.contexts[0].pages[-1]
        old.popup = 'Real visible dialog'
        for _ in range(3):
            with pytest.raises(TimeoutError, match='GOOGLE_WEB_READ_UNAVAILABLE'):
                service.get(spreadsheetId='test', range="'2026'!A1:G").execute()
        assert len(browser.contexts[0].pages) == 2
    assert not old.closed and not original.closed


def test_prior_orphans_do_not_block_or_get_adopted_by_retained_slot(web):
    service, browser, _, original = web
    context = browser.contexts[0]
    for _ in range(3):
        old = context.new_page()
        old.owner_name = 'INSO_OWNER_TAB:google-operation'
        old.url = 'https://docs.google.com/spreadsheets/d/test/edit#gid=0'
    prior = tuple(context.pages)
    service._retained_pages = {}
    with service.poll_scope():
        service.get(spreadsheetId='test', range="'2026'!A1:G").execute()
    owned = context.pages[-1]
    assert owned not in prior and not owned.closed
    with service.poll_scope():
        service.get(spreadsheetId='test', range="'2026'!A1:G").execute()
    assert len(context.pages) == 5 and not original.closed
    assert all(not page.closed and not page.clicks for page in prior)


@pytest.mark.parametrize('expires_auth', [False, True])
def test_timeout_busy_read_retires_only_after_settlement_and_keeps_auth_check(
    web, monkeypatch, expires_auth,
):
    from playwright.sync_api import TimeoutError as PageTimeout

    from src.sheets import WorksheetIdentity
    from src.sheets.google_reader import GoogleSheetsReadError, GoogleSheetsRowReader

    service, browser, _, _ = web
    download = service._download
    failed, waits = [], []

    def read(page, actions):
        if not failed:
            failed.append(page)
            page.popup = 'Temporary read dialog'
            raise PageTimeout('Synthetic read timeout')
        return download(page, actions)

    def wait(seconds):
        waits.append(seconds)
        if len(waits) == 2:
            if expires_auth:
                failed[0].login_markers.add('登录')
            else:
                failed[0].popup = ''
        return False

    monkeypatch.setattr(service, '_download', read)
    reader = GoogleSheetsRowReader(service, retry_wait=wait)
    with service.poll_scope():
        if expires_auth:
            with pytest.raises(GoogleSheetsReadError):
                reader.read_rows(WorksheetIdentity('test', '2026'))
            assert not failed[0].closed and len(browser.contexts[0].pages) == 2
        else:
            assert reader.read_rows(WorksheetIdentity('test', '2026'))
            assert failed[0].closed and len(browser.contexts[0].pages) == 3
    assert waits == [2, 4]


def test_uncertain_write_is_neither_read_tagged_nor_closed_as_recovered_read(web):
    from src.sheets.quotation_input import QuotationInputUnavailable

    service, browser, _, _ = web
    context = browser.contexts[0]
    create = context.new_page

    def dirty_page():
        page = create()
        page.save_fails = True
        return page

    context.new_page = dirty_page
    with service.poll_scope():
        with pytest.raises(QuotationInputUnavailable):
            service.update(spreadsheetId='test', range="'2026'!F2",
                           valueInputOption='RAW', body={'values': [['NEW']]}).execute()
        old = context.pages[-1]
        assert not getattr(old, 'read_failed', False)
        with pytest.raises(TimeoutError):
            service.get(spreadsheetId='test', range="'2026'!A1:G").execute()
        assert not old.closed and len(context.pages) == 2



@pytest.mark.parametrize('initial,settled,expected', [(True, False, False), (True, True, True), (False, False, True)])
def test_real_idle_predicate_never_clears_an_unconfirmed_initial_update(initial, settled, expected):
    from src.launcher.google_quote_update import _REFRESH_INPUT_IDLE
    node, _ = compute_driver_executable()
    state = json.dumps({'initial': initial, 'settled': settled})
    script = f"""
        const state = {state};
        global.window = {{__insoQuoteSettlement: {{...state, isRunning: () => false}}, __insoRefreshQuietSince: 0}};
        global.document = {{querySelectorAll: () => []}};
        global.performance = {{now: () => 2000}};
        const predicate = ({_REFRESH_INPUT_IDLE});
        process.stdout.write(JSON.stringify(!!predicate()));
    """
    result = subprocess.run([str(node), '-e', script], check=True, capture_output=True, text=True, timeout=10)
    assert json.loads(result.stdout) is expected
