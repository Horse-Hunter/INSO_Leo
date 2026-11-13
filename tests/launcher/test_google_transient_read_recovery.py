"""RFQ-016 batch 1: a transient Google read must stay a transient read.

Owner rule (2026-11-13, `docs/modules/SHEETS.md`): a stalled download, a
temporary read page or one failed poll is a program-side operation issue until
proven otherwise. It must be retried locally and isolated to the affected task,
never reported as a Google-wide outage, a global stop or a nuisance email. Real
write-uncertainty, authentication and page-ownership faults keep their stops.
"""
import json
from types import SimpleNamespace

import pytest

from src.gui.contracts import RunState
from src.sheets import WorksheetIdentity
from src.sheets.google_reader import (
    GoogleSheetsReadError,
    GoogleSheetsReadUnavailable,
    GoogleSheetsRowReader,
)
from src.workflow.service import WorkflowRuntime
from src.workflow.v12_faults import FaultScope, V12Fault
from tests.launcher.test_google_web import GridPage
from tests.launcher.test_google_web import web as web  # noqa: PLC0414
from tests.launcher.test_runtime_safety_notice import harness
from tests.workflow.test_v12_notifications import NOW

ERROR_PAGE = "chrome-error://chromewebdata/"


def _browser_error_page(monkeypatch, *, failing=1):
    """Model a real detached read page: it lands on Chrome's error page.

    Chrome renders `chrome-error://chromewebdata/` for a failed main-frame load
    and exposes no script context there, so every document probe (window.name,
    active tab, unsafe-DOM) fails while the native target still exists.
    """
    original_goto = GridPage.goto
    original_evaluate = GridPage.evaluate
    navigations = []

    def goto(page, url, **kwargs):
        navigations.append(page)
        if len(navigations) <= failing:
            page.url = ERROR_PAGE
            return None
        return original_goto(page, url, **kwargs)

    def evaluate(page, script, arg=None):
        if page.url == ERROR_PAGE:
            raise RuntimeError("synthetic browser error page has no script context")
        return original_evaluate(page, script, arg)

    monkeypatch.setattr(GridPage, "goto", goto)
    monkeypatch.setattr(GridPage, "evaluate", evaluate)
    return navigations


def test_browser_error_page_read_recovers_on_the_next_owned_attempt(web, monkeypatch):
    service, browser, _, human = web
    navigations = _browser_error_page(monkeypatch)
    waits = []
    reader = GoogleSheetsRowReader(service, retry_wait=lambda seconds: waits.append(seconds) or False)

    with service.poll_scope():
        rows = reader.read_rows(WorksheetIdentity("test", "2026"))

    assert rows[1].cells["E"] == "000123"
    assert waits == [2]
    assert len(navigations) == 2
    assert navigations[0].closed  # Our own pure-read page was released, not leaked.
    assert navigations[1] is not navigations[0]
    assert not human.closed and browser.connected
    assert service.live_read_revision == 1  # Only the verified acquisition counts.


def test_exhausted_browser_error_page_reads_defer_instead_of_global_stop(web, monkeypatch):
    service, _, _, human = web
    _browser_error_page(monkeypatch, failing=99)
    waits = []

    with service.poll_scope(), pytest.raises(GoogleSheetsReadUnavailable) as caught:
        GoogleSheetsRowReader(service, retry_wait=lambda seconds: waits.append(seconds) or False).read_rows(
            WorksheetIdentity("test", "2026"))

    assert waits == [2, 4, 6, 8]  # Existing bounded attempt budget, no new waiting.
    chain, seen = caught.value, set()
    while chain is not None and id(chain) not in seen:
        seen.add(id(chain))
        assert not isinstance(chain, V12Fault), "a read-side page loss is not a shared safety fault"
        chain = chain.__cause__ or chain.__context__
    assert not human.closed


def test_write_on_a_browser_error_page_still_fails_closed(web, monkeypatch):
    service, _, _, human = web
    navigations = _browser_error_page(monkeypatch)

    with service.poll_scope(), pytest.raises(V12Fault) as caught:
        service.update(spreadsheetId="test", range="'2026'!F2:F2", valueInputOption="RAW",
                       body={"values": [["NEW"]]}).execute()

    assert caught.value.scope is FaultScope.GLOBAL_STOP
    assert caught.value.reason == "GOOGLE_SPREADSHEET_UNAVAILABLE"
    assert len(navigations) == 1 and not navigations[0].typed
    assert not human.closed


def test_login_loss_is_still_a_global_stop_and_keeps_its_surface(web, monkeypatch):
    service, _, _, human = web
    original_goto = GridPage.goto

    def goto(page, url, **kwargs):
        original_goto(page, url, **kwargs)
        page.url = "https://accounts.google.com/signin/v2/identifier"

    monkeypatch.setattr(GridPage, "goto", goto)
    with service.poll_scope(), pytest.raises(V12Fault) as caught:
        service.get(spreadsheetId="test", range="'2026'!A1:G").execute()

    assert caught.value.scope is FaultScope.GLOBAL_STOP
    assert caught.value.reason == "GOOGLE_AUTHENTICATION_REQUIRED"
    assert not human.closed


def test_unprovable_read_page_identity_is_never_released(web, monkeypatch):
    service, browser, _, human = web
    navigations = _browser_error_page(monkeypatch, failing=99)

    def native_owner(page):
        raise RuntimeError("native target proof unavailable")

    monkeypatch.setattr("src.launcher.google_quote_update.native_page_owner", native_owner)
    with service.poll_scope(), pytest.raises(GoogleSheetsReadError):
        GoogleSheetsRowReader(service, retry_wait=lambda _seconds: False).read_rows(
            WorksheetIdentity("test", "2026"))

    assert navigations and not any(page.closed for page in navigations)
    assert not human.closed and browser.connected


def _exhausted_google_read():
    """The exact shape the reader raises after its bounded attempts."""
    exhausted = GoogleSheetsReadUnavailable("Google read retry exhausted")
    exhausted.__cause__ = TimeoutError("GOOGLE_WEB_READ_UNAVAILABLE")
    return exhausted


def test_transient_google_read_never_creates_fault_evidence_or_an_alert(tmp_path, monkeypatch):
    from datetime import timedelta

    backend, worker, smtp = harness(tmp_path, monkeypatch)
    faults = []
    monkeypatch.setattr(backend, "_notify_runtime_fault", lambda *a, **k: faults.append((a, k)))

    assert backend._defer_website_poll(_exhausted_google_read(), timedelta(minutes=7))
    assert faults == []  # No Google-wide claim, no nuisance mail for a retried read.
    assert "Google Sheets" in backend._site_outages
    assert backend._state is RunState.RUNNING
    worker.run_due(now=NOW)
    assert smtp.send_attempts == 0


def test_recovered_read_clears_the_temporary_state(tmp_path, monkeypatch):
    backend, worker, smtp = harness(tmp_path, monkeypatch)
    clock = SimpleNamespace(tick=0.0)
    monkeypatch.setattr("src.launcher.backend.monotonic", lambda: clock.tick)
    runtime = WorkflowRuntime(None, None, ())
    runtime.configure_modules({"inquiry": 7, "quotation": 11, "tp": 13}, timer=lambda: clock.tick)
    backend._module_runtime = runtime
    backend._module_execute = lambda module: (_ for _ in ()).throw(_exhausted_google_read())

    assert runtime.claim_due_module() == "inquiry"
    backend._run_independent_job("inquiry")
    assert "Google Sheets" in backend._site_outages
    assert not runtime.module_plans()["inquiry"][2]  # Never a permanent pause.
    assert runtime.module_plans()["inquiry"][0] == clock.tick + 7  # Configured cadence kept.

    backend._site_recovered("Google Sheets")  # What every verified read reports.
    assert "Google Sheets" not in backend._site_outages
    assert runtime.claim_due_module() == "quotation"  # The other modules stay due.
    runtime.complete_module("quotation")
    assert runtime.claim_due_module() == "tp"
    worker.run_due(now=NOW)
    assert smtp.send_attempts == 0


def test_genuine_google_access_fault_still_raises_one_accurate_fault(tmp_path, monkeypatch):
    from datetime import timedelta

    backend, worker, smtp = harness(tmp_path, monkeypatch)
    faults = []
    monkeypatch.setattr(backend, "_notify_runtime_fault", lambda *a, **k: faults.append((a, k)))

    assert backend._defer_website_poll(V12Fault(FaultScope.GLOBAL_STOP, "GOOGLE_AUTHENTICATION_REQUIRED"),
                                       timedelta(minutes=7))
    assert [call[0][1] for call in faults] == ["GOOGLE_WAITING_RECOVERY"]
    worker.run_due(now=NOW)  # No bound order establishes affected business here.
    assert smtp.send_attempts == 0


def test_recovered_site_cannot_replay_an_old_blocked_command(tmp_path, monkeypatch):
    """A queued Google-blocked notice is refused once the read has recovered.

    `_site_outages` is in-memory and empty after a restart, which is exactly the
    "already recovered" state that must not resend a historical false alarm.
    """
    from src.workflow.automatic_admission import binding_key
    from src.workflow.v12_contracts import NotificationKind
    from src.workflow.v12_notifications import NotificationRecipient

    backend, worker, smtp = harness(tmp_path, monkeypatch)
    identity = WorksheetIdentity("test", "2026")
    item = SimpleNamespace(status=SimpleNamespace(value="QUEUED"), record_identity=identity)
    backend._store = SimpleNamespace(get_by_inquiry_id=lambda _inquiry_id: item)
    command = SimpleNamespace(
        command_id="review-pending",
        inquiry_id="inquiry-1",
        kind=NotificationKind.PURCHASE_EXCEPTION,
        recipients=(NotificationRecipient("owner", "linan229@qq.com"),),
        review=json.dumps({"category": "persistent_stop", "module": "Google Sheets",
                           "reason_code": "PROGRAM_OPERATION_BLOCKED",
                           "source_binding": binding_key(identity)}),
    )
    assert backend._review_current_mail(command, NOW) == "EVENT_NOT_CURRENT"
    worker.run_due(now=NOW)
    assert smtp.send_attempts == 0
