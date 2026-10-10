import sqlite3
from datetime import UTC, datetime, timedelta

from src.workflow.order_notifications import (
    OrderExceptionNotifications,
    exception_command,
)
from src.workflow.v12_contracts import DeliveryOutcome, NotificationKind
from src.workflow.v12_notifications import FakeNotificationTransport

NOW = datetime(2026, 10, 10, tzinfo=UTC)


def args():
    return {'invocation_id':'synthetic-call', 'pi_no':'SHAWN20260101-01', 'part_number':'TEST-PART',
        'situation':'合同中缺少 DC，自动录单已停止。', 'treatment':'请补充或确认合同信息后重新处理。', 'at':NOW}


def test_simple_old_enum_safe_notification_and_per_recipient_retry(tmp_path):
    fake = FakeNotificationTransport({'owner': (DeliveryOutcome.SENT,),
        'shawn': (DeliveryOutcome.RETRYABLE_FAILURE, DeliveryOutcome.SENT)})
    service = OrderExceptionNotifications(tmp_path, transport=fake, background=False)
    command = exception_command(**args())
    assert command.kind is NotificationKind.PURCHASE_EXCEPTION and command.inquiry_id == 'v14-notify:synthetic-call'
    assert command.subject == '订单录单异常｜SHAWN20260101-01'
    assert len(command.text_body.splitlines()) == 4
    assert all(x not in command.text_body for x in ['UID','Message-ID','Traceback','reason','http','retry','DB'])
    service.enqueue(command)
    service.worker.run_due(now=NOW)
    service.enqueue(command)
    service.worker.run_due(now=NOW + timedelta(minutes=1))
    assert [who for _,who in fake.calls] == ['owner','shawn','shawn']
    with sqlite3.connect(service.store.database_path) as db:
        assert db.execute('select status from workflow_items').fetchone()[0] == 'MANUAL_REVIEW'
        assert db.execute('select count(*) from workflow_v12_inquiry_state').fetchone()[0] == 0
        assert db.execute('select count(*) from workflow_v12_notification_commands').fetchone()[0] == 1
    service.close()


def test_multiple_invocations_have_independent_compatible_anchors(tmp_path):
    service = OrderExceptionNotifications(tmp_path, transport=FakeNotificationTransport(), background=False)
    first = exception_command(**args())
    second = exception_command(**dict(args(), invocation_id='synthetic-call-two'))
    service.enqueue(first)
    service.enqueue(second)
    with sqlite3.connect(service.store.database_path) as db:
        assert db.execute('select count(*) from workflow_items').fetchone()[0] == 2
        assert db.execute('select count(*) from workflow_v12_notification_commands').fetchone()[0] == 2
        assert db.execute('select count(*) from workflow_v12_inquiry_state').fetchone()[0] == 0
    service.close()
