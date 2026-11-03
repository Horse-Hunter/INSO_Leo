"""Transient read proof failures recover without weakening any write gate."""
from types import SimpleNamespace

import pytest

from src.gui.contracts import RunState
from src.sheets import WorksheetIdentity
from src.sheets.google_reader import GoogleSheetsReadUnavailable, GoogleSheetsRowReader
from src.workflow.service import WorkflowRuntime
from src.workflow.v12_faults import V12Fault
from tests.launcher.test_google_final_retirement import acquire
from tests.launcher.test_google_web import web as web  # noqa: PLC0414
from tests.launcher.test_runtime_safety_notice import harness
from tests.workflow.test_v12_notifications import NOW


@pytest.mark.parametrize("phase", ["attach", "proof"])
def test_reattached_read_proof_temporarily_unavailable_recovers_on_original_retry(web, monkeypatch, phase):
    service, pages = acquire(web)
    context = pages[0].context
    for page in pages:
        monkeypatch.delattr(page, "_inso_native_page_owner", raising=False)
    original = context.new_cdp_session
    def unavailable(page):
        if phase == "attach":
            raise RuntimeError("read attach unavailable")
        session = original(page)
        session.send = lambda *a: (_ for _ in ()).throw(RuntimeError("read proof link lost"))
        return session
    monkeypatch.setattr(context, "new_cdp_session", unavailable)
    waits = []
    def retry(seconds):
        waits.append(seconds)
        monkeypatch.setattr(context, "new_cdp_session", original)
        return False
    reader = GoogleSheetsRowReader(service, retry_wait=retry)
    count = len(context.pages)
    with service.poll_scope():
        rows = reader.read_rows(WorksheetIdentity("test", "2026"))
    assert rows and waits == [2]
    assert len(context.pages) == count and all(not p.closed for p in pages) and not web[3].closed


def test_unavailable_read_never_discards_the_retained_identity_or_writes(web, monkeypatch):
    service, pages = acquire(web)
    before = dict(service._retained_pages)
    for page in pages:
        monkeypatch.delattr(page, "_inso_native_page_owner", raising=False)
    monkeypatch.setattr(pages[0].context, "new_cdp_session", lambda _: (_ for _ in ()).throw(RuntimeError("unavailable")))
    waits = []
    reader = GoogleSheetsRowReader(service, retry_wait=lambda seconds: waits.append(seconds) or False)
    with pytest.raises(GoogleSheetsReadUnavailable), service.poll_scope():
        reader.read_rows(WorksheetIdentity("test", "2026"))
    assert waits == [2, 4, 6, 8]
    assert service._retained_pages == before and all(not p.closed for p in pages)


def test_same_unproved_surface_for_write_still_fails_closed(web, monkeypatch):
    service, pages = acquire(web)
    for page in pages:
        monkeypatch.delattr(page, "_inso_native_page_owner", raising=False)
    monkeypatch.setattr(pages[0].context, "new_cdp_session", lambda _: (_ for _ in ()).throw(RuntimeError("unavailable")))
    with pytest.raises(V12Fault), service.poll_scope():
        service.update(spreadsheetId="test", range="'2026'!F2:F2", body={"values": [["NEW"]]}, valueInputOption="RAW").execute()
    assert all(not p.closed for p in pages) and not web[3].closed


@pytest.mark.parametrize("hours", [0, 4, 24])
def test_read_retries_continue_after_hours_and_leave_other_modules_due(tmp_path, monkeypatch, hours):
    backend, worker, smtp = harness(tmp_path, monkeypatch)
    clock = SimpleNamespace(tick=float(hours*3600))
    monkeypatch.setattr("src.launcher.backend.monotonic", lambda: clock.tick)
    runtime = WorkflowRuntime(None, None, ())
    runtime.configure_modules({"inquiry": 7, "quotation": 11, "tp": 13}, timer=lambda: clock.tick)
    backend._module_runtime = runtime
    backend._site_outages["Google Sheets"] = 0
    backend._module_execute = lambda module: (_ for _ in ()).throw(GoogleSheetsReadUnavailable("synthetic exhausted read"))
    assert runtime.claim_due_module() == "inquiry"
    backend._run_independent_job("inquiry")
    assert not backend._stop.is_set() and backend._state is RunState.RUNNING
    assert runtime.module_plans()["inquiry"][0] == clock.tick+7
    assert not runtime.module_plans()["inquiry"][2]
    assert runtime.claim_due_module() == "quotation"
    runtime.complete_module("quotation")
    assert runtime.claim_due_module() == "tp"
    runtime.complete_module("tp")
    worker.run_due(now=NOW)
    assert smtp.send_attempts == 0


def test_read_retention_transport_failure_rejects_data_then_recovers(web, monkeypatch):
    service, pages = acquire(web)
    browser = web[1]
    original_session = browser.new_browser_cdp_session
    original_download = service._download
    reads, waits = [], []
    def download(page, actions):
        data = original_download(page, actions)
        reads.append(True)
        if len(reads) == 1:
            monkeypatch.setattr(browser, "new_browser_cdp_session", lambda: (_ for _ in ()).throw(RuntimeError("read retention link lost")))
        return data
    monkeypatch.setattr(service, "_download", download)
    def retry(seconds):
        waits.append(seconds)
        monkeypatch.setattr(browser, "new_browser_cdp_session", original_session)
        return False
    reader = GoogleSheetsRowReader(service, retry_wait=retry)
    with service.poll_scope():
        result = reader.read_rows(WorksheetIdentity("test", "2026"))
    assert result and len(reads) == 2 and waits == [2]
    assert service.live_read_revision == 3  # Two acquire reads + only one confirmed retry.
    assert all(not p.closed for p in pages) and not web[3].closed
