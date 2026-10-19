"""Three worksheet slots and the actual hidden-dialog predicate, fully offline."""
import json
import subprocess

import pytest
from playwright._impl._driver import compute_driver_executable

from src.launcher.google_quote_update import _UNSAFE_POLL_PAGE
from src.sheets.quotation_input import QuotationInputBusy
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
            with pytest.raises(QuotationInputBusy):
                service.get(spreadsheetId='test', range="'2026'!A1:G").execute()
        assert len(browser.contexts[0].pages) == 2
    assert not old.closed and not original.closed


def test_no_fourth_program_google_tab_even_with_prior_orphans(web):
    service, browser, _, original = web
    context = browser.contexts[0]
    for _ in range(3):
        old = context.new_page()
        old.owner_name = 'INSO_OWNER_TAB:google-operation'
        old.url = 'https://docs.google.com/spreadsheets/d/test/edit#gid=0'
    with service.poll_scope(), pytest.raises(QuotationInputBusy):
        service.get(spreadsheetId='test', range="'2026'!A1:G").execute()
    assert len(context.pages) == 4 and not original.closed
