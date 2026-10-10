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
    command=next(iter(mailbox.commands.values()))
    assert len(mailbox.commands)==1 and [r.address for r in command.recipients]==['linan229@qq.com']
    assert reason not in command.text_body and 'synthetic-run' not in command.text_body
    assert '情况：' in command.text_body and '处理：' in command.text_body
    assert '不要直接重发采购单' in command.text_body


@pytest.mark.parametrize('reason',['SOURCE_STATUS_NOT_UPDATED','UPDATE_RESULT_UNCONFIRMED','ROW_NOT_IDENTIFIED'])
def test_quote_mail_keeps_location_and_uncertainty_without_internal_id(reason):
    mailbox=Mailbox()
    result=SimpleNamespace(row_error_reason=SimpleNamespace(value=reason),inquiry_id='synthetic-id',queried_mpn='TEST-MODEL',source_worksheet=SimpleNamespace(worksheet='示例表'),source_row_position=12)
    notify_quotation(mailbox,result,'key',1,at=NOW)
    command=next(iter(mailbox.commands.values()))
    assert all(value in command.text_body for value in ['TEST-MODEL','示例表','行号12','情况：','处理：'])
    assert 'synthetic-id' not in command.text_body and reason not in command.text_body
    if reason=='UPDATE_RESULT_UNCONFIRMED': assert '无法确认' in command.text_body


def test_stop_reminder_has_specific_safe_site_and_no_raw_details():
    body=_login_alert_body('立创：需要人工验证 SECRET_TOKEN http://private')
    assert '立创' in body and '人工验证' in body
    assert 'SECRET' not in body and 'http' not in body and 'INSO_V1.2' not in body
    fault=_login_alert_body('全局基础设施故障')
    assert '运行异常' in fault and '网络' in fault and '重新登录或人工验证' not in fault
