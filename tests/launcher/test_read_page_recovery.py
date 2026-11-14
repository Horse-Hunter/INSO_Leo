"""A lost read-only page is not evidence of an unknown Google write."""
import pytest
from playwright.sync_api import Error as PageError
from playwright.sync_api import TimeoutError as PageTimeout

from src.sheets import WorksheetIdentity
from src.sheets.google_reader import GoogleSheetsRowReader
from tests.launcher.test_google_web import GridPage
from tests.launcher.test_google_web import web as web  # noqa: PLC0414


@pytest.mark.parametrize("sheet",["2026","SHAHAB"])
def test_retained_read_closed_during_download_reopens_only_its_read_without_false_write_hold(web,monkeypatch,sheet):
    service,browser,_rows,human=web;service._retained_pages={}
    reader=GoogleSheetsRowReader(service,retry_wait=lambda _:False)
    ws=WorksheetIdentity("test",sheet)
    with service.poll_scope():expected=reader.read_rows(ws)
    old=browser.contexts[0].pages[-1]
    original_evaluate=GridPage.evaluate
    def strict_evaluate(page,*args,**kwargs):
        if page.closed:raise PageError("Target page, context or browser has been closed")
        return original_evaluate(page,*args,**kwargs)
    monkeypatch.setattr(GridPage,"evaluate",strict_evaluate)
    original_download=service._download;failures=[]
    def interrupted(page,actions):
        if not failures:
            assert actions._poll_entry is not None
            failures.append(page);page.closed=True
            raise PageTimeout("synthetic owned READ disappeared during download")
        return original_download(page,actions)
    monkeypatch.setattr(service,"_download",interrupted)
    with service.poll_scope():assert reader.read_rows(ws)==expected
    assert old.closed and not human.closed
    assert sum(not p.closed for p in browser.contexts[0].pages[1:])==1
    assert all(not entry[1] for entry in service._retained_pages.values())


def test_repeated_read_timeouts_retire_only_program_created_read_pages(web, monkeypatch):
    service, browser, _, human = web
    service._retained_pages = {}
    failed = []
    def busy(page, actions):
        failed.append(page)
        page.popup = "synthetic download dialog"
        raise PageTimeout("synthetic read timeout")
    monkeypatch.setattr(service, "_download", busy)
    for _ in range(10):
        with service.poll_scope(), pytest.raises(TimeoutError):
            service.get(spreadsheetId="test", range="'2026'!A1:G").execute()
    assert len(failed) == 10 and all(page.closed for page in failed)
    assert not human.closed and browser.is_connected()
    assert sum(not page.closed for page in browser.contexts[0].pages) == 1


def test_failed_read_never_closes_page_with_changed_ownership(web, monkeypatch):
    service, browser, _, human = web
    service._retained_pages = {}
    failed = []
    def adopted(page, actions):
        failed.append(page)
        page.owner_name = "OWNER_ADOPTED"
        raise PageTimeout("synthetic read timeout")
    monkeypatch.setattr(service, "_download", adopted)
    with service.poll_scope(), pytest.raises(TimeoutError):
        service.get(spreadsheetId="test", range="'2026'!A1:G").execute()
    assert len(failed) == 1 and not failed[0].closed
    assert not human.closed and browser.is_connected()


def test_failed_read_with_expired_login_is_preserved(web, monkeypatch):
    from src.workflow.v12_faults import V12Fault

    service, browser, _, human = web
    service._retained_pages = {}
    failed = []
    def expired(page, actions):
        failed.append(page)
        page.login_markers.add("登录")
        raise PageTimeout("synthetic read timeout")
    monkeypatch.setattr(service, "_download", expired)
    with service.poll_scope(), pytest.raises(V12Fault, match="GOOGLE_AUTHENTICATION_REQUIRED"):
        service.get(spreadsheetId="test", range="'2026'!A1:G").execute()
    assert len(failed) == 1 and not failed[0].closed
    assert not human.closed and browser.is_connected()


@pytest.mark.parametrize("same_scope", [False, True])
def test_closed_protected_pure_read_does_not_become_unknown_write(web, monkeypatch, same_scope):
    service, _browser, _rows, human = web
    service._retained_pages = {}
    original = service._download
    failed = []
    def busy_once(page, actions):
        if not failed:
            failed.append(page)
            page.popup = "synthetic read dialog"
            raise PageTimeout("synthetic read timeout")
        return original(page, actions)
    monkeypatch.setattr(service, "_download", busy_once)
    def fail_and_close():
        with pytest.raises(TimeoutError):
            service.get(spreadsheetId="test", range="'2026'!A1:G").execute()
        failed[0].closed = True  # Exact read-only target disappeared.
    if same_scope:
        with service.poll_scope():
            fail_and_close()
            assert service.get(spreadsheetId="test", range="'2026'!A1:G").execute()["values"]
    else:
        with service.poll_scope():
            fail_and_close()
        with service.poll_scope():
            assert service.get(spreadsheetId="test", range="'2026'!A1:G").execute()["values"]
    assert not human.closed and not failed[0].typed


def test_closed_protected_page_without_read_provenance_still_blocks(web):
    from src.workflow.v12_faults import V12Fault

    service, browser, _rows, human = web
    service._retained_pages = {}
    with service.poll_scope():
        assert service.get(spreadsheetId="test", range="'2026'!A1:G").execute()["values"]
    page = browser.contexts[0].pages[-1]
    key = next(iter(service._retained_pages))
    native = service._retained_pages[key][0]
    service._retained_pages[key] = (native, True, False, False)  # Prior write cannot be excluded.
    page.closed = True
    with service.poll_scope(), pytest.raises(V12Fault, match="GOOGLE_WRITE_SETTLEMENT_UNCONFIRMED"):
        service.get(spreadsheetId="test", range="'2026'!A1:G").execute()
    assert not human.closed


def test_closed_protected_pure_read_does_not_block_next_verified_write(web, monkeypatch):
    service, _browser, rows, human = web
    service._retained_pages = {}
    failed = []
    def busy(page, actions):
        failed.append(page)
        page.popup = "synthetic read dialog"
        raise PageTimeout("synthetic read timeout")
    monkeypatch.setattr(service, "_download", busy)
    with service.poll_scope(), pytest.raises(TimeoutError):
        service.get(spreadsheetId="test", range="'2026'!A1:G").execute()
    failed[0].closed = True
    monkeypatch.undo()
    with service.poll_scope():
        service.update(spreadsheetId="test", range="'2026'!F2", valueInputOption="RAW",
                       body={"values": [["SYNTHETIC"]]}).execute()
    assert rows["2026"][1][5] == "SYNTHETIC" and not human.closed


def test_closed_legacy_protected_page_without_history_stays_blocked(web):
    from src.workflow.v12_faults import V12Fault

    service, browser, _rows, human = web
    service._retained_pages = {}
    with service.poll_scope():
        assert service.get(spreadsheetId="test", range="'2026'!A1:G").execute()["values"]
    page = browser.contexts[0].pages[-1]
    key = next(iter(service._retained_pages))
    native = service._retained_pages[key][0]
    service._retained_pages[key] = (native, True, False)  # Legacy record has no provenance.
    page.closed = True
    with service.poll_scope(), pytest.raises(V12Fault, match="GOOGLE_WRITE_SETTLEMENT_UNCONFIRMED"):
        service.get(spreadsheetId="test", range="'2026'!A1:G").execute()
    assert not human.closed


def test_quarantined_read_closed_by_owner_allows_later_write(web, monkeypatch):
    from src.launcher.google_quote_update import GoogleQuotationUpdateActions
    monkeypatch.setattr(GoogleQuotationUpdateActions, "close_temporary_failed_read", lambda self: False)
    service, _browser, rows, human = web
    service._retained_pages = {}
    original = service._download
    failed = []
    def busy_once(page, actions):
        if not failed:
            failed.append(page)
            page.popup = "synthetic read dialog"
            raise PageTimeout("synthetic read timeout")
        return original(page, actions)
    monkeypatch.setattr(service, "_download", busy_once)
    with service.poll_scope(), pytest.raises(TimeoutError):
        service.get(spreadsheetId="test", range="'2026'!A1:G").execute()
    failed[0].popup = None
    with service.poll_scope():
        assert service.get(spreadsheetId="test", range="'2026'!A1:G").execute()["values"]
    assert not failed[0].closed
    target = next(value[0] for key, value in service._retained_pages.items()
                  if len(key) >= 5 and key[4] == "quarantine")
    failed[0].closed = True  # Simulate Owner closing only this exact protected read page.
    with service.poll_scope():
        service.update(spreadsheetId="test", range="'2026'!F2", valueInputOption="RAW",
                       body={"values": [["SYNTHETIC"]]}).execute()
    assert rows["2026"][1][5] == "SYNTHETIC" and not human.closed
    assert all(value[0] != target for value in service._retained_pages.values())


def test_unavailable_optional_read_cleanup_preserves_record_and_continues(web, monkeypatch):
    from src.launcher.google_quote_update import GoogleQuotationUpdateActions
    monkeypatch.setattr(GoogleQuotationUpdateActions, "close_temporary_failed_read", lambda self: False)
    from src.launcher import google_quote_update as module

    service, browser, _, human = web
    service._retained_pages = {}
    original_download = service._download
    failed = []
    def busy_once(page, actions):
        if not failed:
            failed.append(page)
            page.popup = "synthetic read dialog"
            raise PageTimeout("synthetic read timeout")
        return original_download(page, actions)
    monkeypatch.setattr(service, "_download", busy_once)
    with service.poll_scope(), pytest.raises(TimeoutError):
        service.get(spreadsheetId="test", range="'2026'!A1:G").execute()
    with service.poll_scope():
        assert service.get(spreadsheetId="test", range="'2026'!A1:G").execute()["values"]
    key = next(key for key in service._retained_pages if len(key) >= 5 and key[4] == "quarantine")
    target = service._retained_pages[key][0]
    unknown_key = ("https", "docs.google.com", "/spreadsheets/d/other/edit", "2026")
    unknown = ("unknown-write-target", True, False, False)
    service._retained_pages[unknown_key] = unknown
    matches = module._retained_google_matches
    def failed_probe(pages, target_id, *, read_only=False):
        if target_id == target:
            raise module.GoogleReadTargetUnavailable("synthetic probe timeout")
        return matches(pages, target_id, read_only=read_only)
    monkeypatch.setattr(module, "_retained_google_matches", failed_probe)
    with service.poll_scope():
        assert service.get(spreadsheetId="test", range="'2026'!A1:G").execute()["values"]
    assert key in service._retained_pages and service._retained_pages[unknown_key] == unknown
    assert not failed[0].closed and not human.closed
    assert browser.is_connected()


# RFQ-018: a closed/absent read target cannot clear a separate unknown write.
# The shared document hold is independent of the page/read target lifetime.
def test_closed_read_target_never_clears_separate_unknown_write(web):
    from src.research.cdp_pages import google_document_key_for_spreadsheet
    from src.sheets.quotation_input import QuotationInputBusy

    service, _browser, _rows, human = web
    document = google_document_key_for_spreadsheet("test")
    service._page_admission.hold_document(document, object(), "GOOGLE_WRITE_UNCONFIRMED")

    with service.poll_scope(), pytest.raises(QuotationInputBusy):
        service.update(spreadsheetId="test", range="'2026'!F2", valueInputOption="RAW",
                       body={"values": [["SYNTHETIC"]]}).execute()
    assert service._page_admission.document_hold(document) == "GOOGLE_WRITE_UNCONFIRMED"
    assert not human.closed


# RFQ-018: a failed target proof cannot release a separate read/write quarantine.
def test_failed_target_proof_never_releases_read_quarantine(web):
    from src.research.cdp_pages import google_document_key_for_spreadsheet
    from src.sheets.quotation_input import QuotationInputBusy

    service, _browser, _rows, human = web
    document = google_document_key_for_spreadsheet("test")
    service._page_admission.hold_document(document, object(), "GOOGLE_READ_QUARANTINE")

    with service.poll_scope(), pytest.raises(QuotationInputBusy):
        service.update(spreadsheetId="test", range="'2026'!F2", valueInputOption="RAW",
                       body={"values": [["SYNTHETIC"]]}).execute()
    assert service._page_admission.document_hold(document) == "GOOGLE_READ_QUARANTINE"
    assert not human.closed


def test_each_client_retires_its_own_closed_read_quarantine(web, monkeypatch):
    from src.launcher.google_web import GoogleSheetsWebService

    first, _browser, rows, human = web
    first._retained_pages = {}
    second = GoogleSheetsWebService(first._session, retain_pages=True)
    original = first._download
    failed = []
    def busy_once(page, actions):
        if not failed:
            failed.append(page)
            page.popup = "synthetic read dialog"
            raise PageTimeout("synthetic timeout")
        return original(page, actions)
    monkeypatch.setattr(first, "_download", busy_once)
    with first.poll_scope(), pytest.raises(TimeoutError):
        first.get(spreadsheetId="test", range="'2026'!A1:G").execute()
    failed[0].popup = None
    with first.poll_scope():
        assert first.get(spreadsheetId="test", range="'2026'!A1:G").execute()["values"]
    failed[0].closed = True
    with second.poll_scope():
        second.update(spreadsheetId="test", range="'2026'!F2", valueInputOption="RAW",
                      body={"values": [["FIRST"]]}).execute()
    with first.poll_scope():
        first.update(spreadsheetId="test", range="'2026'!F2", valueInputOption="RAW",
                     body={"values": [["SECOND"]]}).execute()
    assert rows["2026"][1][5] == "SECOND" and not human.closed
