"""Native Download dispatcher without a browser, plus original Sheets read/write paths."""
import asyncio
from types import SimpleNamespace

import pytest
from playwright.sync_api import Download as NativeDownload
from playwright.sync_api import sync_playwright

from src.launcher import google_web as module
from src.launcher.google_quote_update import _same_read_sheet_selection
from src.sheets import WorksheetIdentity
from src.sheets.google_reader import GoogleSheetsReadUnavailable, GoogleSheetsRowReader
from src.workflow.v12_faults import FaultScope, V12Fault
from src.workflow.v13_quote_update import UpdateAttemptUnconfirmed
from tests.launcher.test_google_web import GridLocator
from tests.launcher.test_google_web import web as web_fixture


@pytest.fixture(scope="module")
def dispatcher():
    # Starts only the bundled protocol dispatcher. No browser launch/CDP/site.
    with sync_playwright() as playwright:
        yield playwright._impl_obj


def native_artifact(dispatcher, original, *, hang=None, cancel_failure=False):
    calls, cancelled = [], []
    async def operation(name):
        calls.append(name)
        if name == hang or isinstance(hang, tuple) and name in hang:
            try:
                await asyncio.sleep(3600)
            except asyncio.CancelledError:
                cancelled.append(name)
                raise
        if name == 'failure':
            return None
        if name == 'path':
            return original.file
        if name == 'delete':
            original.file.unlink(missing_ok=True)
        if name == 'cancel' and cancel_failure:
            raise RuntimeError('synthetic artifact cancel not confirmed')
    impl = SimpleNamespace(_loop=dispatcher._loop, _dispatcher_fiber=dispatcher._dispatcher_fiber)
    for name in ('failure', 'path', 'delete', 'cancel'):
        setattr(impl, name, lambda name=name: operation(name))
    return NativeDownload(impl), calls, cancelled


@pytest.mark.parametrize('fragment', ['gid=17&range=A1', 'range=%24AA%242%3AAB30&gid=17'])
def test_read_identity_allows_only_explicit_valid_selection(fragment):
    assert _same_read_sheet_selection(fragment, 'gid=17')
    assert _same_read_sheet_selection('gid=17', fragment)


@pytest.mark.parametrize('fragment', ['gid=18&range=A1', 'gid=17&gid=18',
    'gid=17&range=A1&range=B2', 'gid=17&other=1', 'gid=17&range=',
    'gid=17&range=Other!A1', 'gid=17&range=A0', 'gid=17&range=A1;bad',
    'range=A1', 'gid=&range=A1', 'gid=17&range=A1&', 'gid=017&range=A1'])
def test_unconfirmed_hash_or_other_sheet_still_rejected(fragment):
    assert not _same_read_sheet_selection(fragment, 'gid=17')


def test_valid_range_change_completes_original_read_once(tmp_path, monkeypatch):
    service, browser, _, _ = web_fixture.__wrapped__(tmp_path)
    download, calls = service._download, []
    def selected(page, actions):
        calls.append(True)
        page.url += '&range=A1'
        return download(page, actions)
    monkeypatch.setattr(service, '_download', selected)
    rows = GoogleSheetsRowReader(service).read_rows(WorksheetIdentity('test', '2026'))
    assert rows and len(calls) == 1
    assert not browser.contexts[0].pages[-1].typed


def test_write_surface_keeps_strict_guard_after_same_sheet_selection(tmp_path, monkeypatch):
    service, browser, rows, _ = web_fixture.__wrapped__(tmp_path)
    download = service._download
    def selected(page, actions):
        page.url += '&range=A1'
        return download(page, actions)
    monkeypatch.setattr(service, '_download', selected)
    before = [list(row) for row in rows['2026']]
    with pytest.raises(UpdateAttemptUnconfirmed):
        service.update(spreadsheetId='test', range="'2026'!F2", valueInputOption='RAW',
                       body={'values': [['NEW']]}).execute()
    assert rows['2026'] == before and not browser.contexts[0].pages[-1].typed


@pytest.mark.parametrize('hang', ['failure', 'path', 'delete', None])
def test_real_sync_dispatcher_artifact_waits_are_bounded(dispatcher, tmp_path, hang):
    original = SimpleNamespace(file=tmp_path / 'owned.tsv')
    original.file.write_text('synthetic')
    download, calls, cancelled = native_artifact(dispatcher, original, hang=hang)
    operation = hang or 'failure'
    if hang:
        with pytest.raises(module._GoogleDownloadWaitTimeout):
            module._download_call(download, operation, timeout=0.03)
        assert cancelled == [hang]
    else:
        assert module._download_call(download, operation, timeout=0.03) is None
    assert calls == [operation]


@pytest.mark.parametrize('hang,cancel_failure,reason', [
    ('failure', False, None), ('path', False, None),
    ('failure', True, 'GOOGLE_DOWNLOAD_CANCEL_UNCONFIRMED'),
    (('failure', 'cancel'), False, 'GOOGLE_DOWNLOAD_CANCEL_UNCONFIRMED'),
    ('delete', False, 'GOOGLE_DOWNLOAD_CLEANUP_UNCONFIRMED'),
])
def test_transport_retires_exact_owned_read_before_retry_or_global_stop(
    dispatcher, tmp_path, monkeypatch, hang, cancel_failure, reason,
):
    service, browser, _, original_page = web_fixture.__wrapped__(tmp_path)
    click, wait, artifacts = GridLocator.click, module._download_call, []
    def replace_download(locator, **kwargs):
        click(locator, **kwargs)
        if '.tsv' in getattr(locator.name, 'pattern', ''):
            original = locator.page.pending.value
            artifact, calls, cancelled = native_artifact(dispatcher, original,
                hang=hang, cancel_failure=cancel_failure)
            artifacts.append((original, calls, cancelled))
            locator.page.pending.value = artifact
    monkeypatch.setattr(GridLocator, 'click', replace_download)
    monkeypatch.setattr(module, '_download_call', lambda d, op, **kw: wait(d, op, timeout=0.03))
    if reason:
        with pytest.raises(V12Fault) as caught:
            service.get(spreadsheetId='test', range="'2026'!A1:G").execute()
        assert caught.value.scope is FaultScope.GLOBAL_STOP and caught.value.reason == reason
    else:
        with pytest.raises(TimeoutError):
            service.get(spreadsheetId='test', range="'2026'!A1:G").execute()
    assert len(artifacts) == 1 and 'delete' in artifacts[0][1]
    if hang != 'delete':
        assert 'cancel' in artifacts[0][1]
    if hang == 'failure':
        assert 'path' not in artifacts[0][1]  # Never parse an unfinished artifact.
    assert not original_page.closed and not browser.contexts[0].pages[-1].typed


def test_download_timeout_preserves_original_five_attempt_reader_budget(tmp_path, monkeypatch):
    service, _, _, _ = web_fixture.__wrapped__(tmp_path)
    calls, waits = [], []
    def timeout(*args):
        calls.append(True)
        raise module._GoogleDownloadWaitTimeout('GOOGLE_WEB_READ_DOWNLOAD_TIMEOUT')
    monkeypatch.setattr(service, '_download', timeout)
    with pytest.raises(GoogleSheetsReadUnavailable):
        GoogleSheetsRowReader(service, retry_wait=lambda s: waits.append(s) or False).read_rows(
            WorksheetIdentity('test', '2026'))
    assert len(calls) == 5 and waits == [2, 4, 6, 8]


@pytest.mark.parametrize('problem', ['auth', 'host', 'document', 'gid', 'duplicate_gid', 'unknown_key'])
def test_read_selection_capability_never_hides_auth_or_identity_loss(tmp_path, monkeypatch, problem):
    service, browser, _, _ = web_fixture.__wrapped__(tmp_path)
    download = service._download
    def changed(page, actions):
        page.url += '&range=A1'
        if problem == 'auth':
            page.login_markers.add('登录')
        elif problem == 'host':
            page.url = page.url.replace('docs.google.com', 'not-authorized.invalid')
        elif problem == 'document':
            page.url = page.url.replace('/d/test/', '/d/other/')
        elif problem == 'gid':
            page.url = page.url.replace('gid=0', 'gid=999')
        elif problem == 'duplicate_gid':
            page.url += '&gid=0'
        else:
            page.url += '&unknown=1'
        return download(page, actions)
    monkeypatch.setattr(service, '_download', changed)
    if problem in {'auth', 'host', 'document'}:
        with pytest.raises(V12Fault) as caught:
            service.get(spreadsheetId='test', range="'2026'!A1:G").execute()
        assert caught.value.scope is FaultScope.GLOBAL_STOP
    else:
        with pytest.raises(TimeoutError):
            service.get(spreadsheetId='test', range="'2026'!A1:G").execute()
    assert not browser.contexts[0].pages[-1].typed
