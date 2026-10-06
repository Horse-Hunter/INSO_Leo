from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from src.launcher.purchase_completion import PurchaseCompletionActions
from src.sheets import (
    IdentifyingSnapshot,
    SheetRecordIdentity,
    WorksheetIdentity,
    WorksheetRow,
)
from src.workflow.v12_contracts import BusinessState, NotificationKind, PurchaseOutcome

NOW = datetime(2026, 10, 6, tzinfo=UTC)


class V12:
    def __init__(self, outcome):
        self.outcome = outcome
        self.commands = {}
    def purchase_state(self, _iid): return self.outcome
    def event_history(self, _iid): return ()
    def notification_already_created(self, cid, *_args): return cid in self.commands
    def enqueue_notification(self, cmd): self.commands[cmd.command_id] = cmd


def actions(outcome, *, writer_fails=False):
    identity = SheetRecordIdentity(WorksheetIdentity("test", "2026"), 4,
                                  IdentifyingSnapshot("未发", "A", "TEST-MPN", "Brand", 8))
    item = SimpleNamespace(inquiry_id="synthetic-inquiry", mpn="TEST-MPN", brand="Brand",
                           resolved_brand=None, quantity=8, record_identity=identity,
                           status=SimpleNamespace(value="COMPLETED"), last_error=None)
    class Sheet:
        def __init__(self):
            self.calls = 0
            self.rows = [WorksheetRow(4, {"A":"未发", "C":"A", "E":"TEST-MPN", "G":8})]
        def read_rows(self, _worksheet): return self.rows
        def write_purchase_status(self, _worksheet, _row):
            self.calls += 1
            if writer_fails: raise RuntimeError("sensitive-provider-message")
            self.rows = [WorksheetRow(4, {"A":"发给采购", "C":"A", "E":"TEST-MPN", "G":8})]
    sheet, state = Sheet(), V12(outcome)
    handler = PurchaseCompletionActions(workflow_store=SimpleNamespace(get_by_inquiry_id=lambda _i:item),
        v12_store=state, reader=sheet, writer_factory=lambda:sheet)
    return handler, sheet, state


def flow(outcome):
    return SimpleNamespace(inquiry_id="synthetic-inquiry", purchase_outcome=outcome,
        business_state=BusinessState.PURCHASE_RECORDED if outcome is PurchaseOutcome.SAVED
        else BusinessState.PURCHASE_EXCEPTION, waiting_reason=None)


def test_only_durable_saved_writes_status():
    handler, sheet, state = actions(PurchaseOutcome.SAVED)
    assert handler.process(flow(PurchaseOutcome.SAVED), at=NOW) is True
    assert sheet.calls == 1 and not state.commands


def test_claimed_success_without_durable_success_cannot_write():
    handler, sheet, _ = actions(PurchaseOutcome.MANUAL_REVIEW)
    with pytest.raises(ValueError): handler.process(flow(PurchaseOutcome.SAVED), at=NOW)
    assert sheet.calls == 0


@pytest.mark.parametrize("outcome", [PurchaseOutcome.VALIDATION_FAILED, PurchaseOutcome.MANUAL_REVIEW,
                                    PurchaseOutcome.UNKNOWN_WRITE_OUTCOME])
def test_failure_only_notifies_owner_once_and_never_writes(outcome):
    handler, sheet, state = actions(outcome)
    handler.process(flow(outcome), at=NOW)
    handler.process(flow(outcome), at=NOW)
    assert sheet.calls == 0 and len(state.commands) == 1
    cmd = next(iter(state.commands.values()))
    assert cmd.kind is NotificationKind.PURCHASE_EXCEPTION
    assert [r.address for r in cmd.recipients] == ["linan229@qq.com"]
    assert "TEST-MPN" in cmd.text_body and "synthetic-inquiry" in cmd.text_body
    if outcome is not PurchaseOutcome.VALIDATION_FAILED:
        assert "可能已经发送" in cmd.text_body and "禁止直接重跑" in cmd.text_body


def test_sheet_failure_preserves_saved_and_sends_safe_specific_mail():
    handler, sheet, state = actions(PurchaseOutcome.SAVED, writer_fails=True)
    assert handler.process(flow(PurchaseOutcome.SAVED), at=NOW) is False
    assert state.outcome is PurchaseOutcome.SAVED and sheet.calls == 1
    body = next(iter(state.commands.values())).text_body
    assert "表格状态写回失败" in body and "RuntimeError" in body
    assert "sensitive-provider-message" not in body


def test_saved_status_recovery_never_reenters_purchase_and_stops_after_success():
    handler, sheet, state = actions(PurchaseOutcome.SAVED, writer_fails=True)
    handler.workflow_store.all_items = lambda: [handler.workflow_store.get_by_inquiry_id("synthetic-inquiry")]
    handler.process(flow(PurchaseOutcome.SAVED), at=NOW)
    assert sheet.calls == 1 and state.outcome is PurchaseOutcome.SAVED
    sheet.rows = [WorksheetRow(4, {"A":"发给采购", "C":"A", "E":"TEST-MPN", "G":8})]
    # An acknowledged/unknown network response can still have completed the cell write.
    handler.retry_saved_statuses(at=NOW)
    handler.retry_saved_statuses(at=NOW)
    assert sheet.calls == 1 and state.outcome is PurchaseOutcome.SAVED
    assert len(state.commands) == 1


def test_research_exception_mail_does_not_claim_a_purchase_submission():
    handler, sheet, state = actions(PurchaseOutcome.PRE_SAVE_READY)
    result = flow(PurchaseOutcome.PRE_SAVE_READY)
    result.business_state = BusinessState.RESEARCH_RETRY_WAIT
    result.waiting_reason = "RESEARCH_RETRY_WAIT"
    handler.process(result, at=NOW)
    assert sheet.calls == 0
    body = next(iter(state.commands.values())).text_body
    assert "调研异常" in body and "未完成采购提交" in body
