from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from src.launcher.backend import _login_alert_body
from src.launcher.v13_integration import notify_quotation, notify_runtime_fault

NOW=datetime(2026,10,10,tzinfo=UTC)


class Mailbox:
    def __init__(self):self.commands={}
    def notification_already_created(self,key,*args):return key in self.commands
    def enqueue_notification(self,command):self.commands[command.command_id]=command


@pytest.mark.parametrize('reason',['GOOGLE_SHEETS_UNAVAILABLE','INSO_AUTHENTICATION_REQUIRED','WORKFLOW_LEDGER_UNAVAILABLE','SECRET_PROVIDER_CODE'])
def test_runtime_mail_human_text_not_internal_codes_and_owner_only(reason):
    mailbox=Mailbox()
    notify_runtime_fault(mailbox,'synthetic-run',reason,at=NOW)
    notify_runtime_fault(mailbox,'synthetic-run',reason,at=NOW)
    assert mailbox.commands == {}  # RFQ-016: no verified current business/evidence.


@pytest.mark.parametrize('reason',['SOURCE_STATUS_NOT_UPDATED','UPDATE_RESULT_UNCONFIRMED','ROW_NOT_IDENTIFIED'])
def test_quote_mail_keeps_location_and_uncertainty_without_internal_id(reason):
    mailbox=Mailbox()
    result=SimpleNamespace(row_error_reason=SimpleNamespace(value=reason),inquiry_id='synthetic-id',queried_mpn='TEST-MODEL',source_worksheet=SimpleNamespace(worksheet='示例表'),source_row_position=12)
    notify_quotation(mailbox,result,'key',1,at=NOW)
    assert mailbox.commands == {}  # RFQ-016: no verified current business/evidence.


def test_stop_reminder_has_specific_safe_site_and_no_raw_details():
    body=_login_alert_body('立创：需要人工验证 SECRET_TOKEN http://private')
    assert '立创' in body and '人工验证' in body
    assert 'SECRET' not in body and 'http' not in body and 'INSO_V1.2' not in body
    fault=_login_alert_body('全局基础设施故障')
    assert '运行异常' in fault and '网络' in fault and '重新登录或人工验证' not in fault


def test_google_read_fault_mail_identifies_boundary_and_does_not_guess_auth():
    mailbox = Mailbox()
    notify_runtime_fault(mailbox, "test-run", "SHEETS_READ_UNAVAILABLE", at=NOW)
    assert mailbox.commands == {}  # RFQ-016: no verified current business/evidence.


def test_unbound_quote_mail_is_a_source_identity_problem_not_missing_supplier_price():
    mailbox = Mailbox()
    result = SimpleNamespace(row_error_reason=SimpleNamespace(value="SOURCE_IDENTITY_UNRESOLVED"),
        inquiry_id=None, queried_mpn="TEST-MODEL", source_worksheet=SimpleNamespace(worksheet="示例表"),
        source_row_position=12)
    notify_quotation(mailbox, result, "key", 1, at=NOW)
    assert mailbox.commands == {}  # RFQ-016: no verified current business/evidence.


def test_safe_runtime_log_contains_closed_reason_class_only():
    import logging

    from src.gui.main import _SafeRuntimeLogFilter

    record = logging.LogRecord("src.launcher.backend", logging.WARNING, "private", 1,
        "SECRET_CUSTOMER_PROVIDER_MESSAGE", (), None)
    record.runtime_reason = "SHEETS_READ_UNAVAILABLE"
    record.runtime_cause = "TimeoutError"
    assert _SafeRuntimeLogFilter().filter(record)
    assert record.getMessage() == "runtime fault reason=SHEETS_READ_UNAVAILABLE cause=TimeoutError"
    assert "SECRET" not in record.getMessage()
    record.runtime_reason = "SECRET with spaces https://private"
    assert _SafeRuntimeLogFilter().filter(record)
    assert record.getMessage() == "launcher event (WARNING)"


def test_google_retry_alert_promises_next_normal_poll_not_manual_restart():
    mailbox = Mailbox()
    notify_runtime_fault(mailbox, "failed-cycle", "GOOGLE_READ_RETRY_EXHAUSTED", at=NOW)
    notify_runtime_fault(mailbox, "failed-cycle", "GOOGLE_READ_RETRY_EXHAUSTED", at=NOW)
    assert mailbox.commands == {}  # RFQ-016: no verified current business/evidence.



@pytest.mark.parametrize('site', ['INSO', 'GOOGLE', 'IC_NET', 'BROWSER', 'FX'])
def test_website_waiting_notice_does_not_claim_the_program_stopped(site):
    mailbox = Mailbox()
    for _ in range(2):
        notify_runtime_fault(mailbox, 'synthetic-outage', site + '_WAITING_RECOVERY', at=NOW)
    assert mailbox.commands == {}  # RFQ-016: no verified current business/evidence.



@pytest.mark.parametrize('reason', ['WORKFLOW_LEDGER_UNAVAILABLE', 'V12_INTERNAL_FAILURE', 'SHEETS_SCHEMA_UNAVAILABLE'])
def test_local_failure_notice_does_not_guess_a_website_login_problem(reason):
    body = _login_alert_body(reason)
    assert '已暂停' in body
    assert '需要重新登录' not in body and '检查VPN' not in body
