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
        self.events = []
        self.state = BusinessState.PURCHASE_RECORDED if outcome is PurchaseOutcome.SAVED else BusinessState.PURCHASE_EXCEPTION
    def business_state(self, _iid): return self.state
    def set_business_state(self, _iid, state, _event): self.state = state
    def submit_click_proven(self, _iid): return self.outcome is PurchaseOutcome.SUBMIT_UNCONFIRMED
    def purchase_state(self, _iid): return self.outcome
    def event_history(self, _iid): return tuple(self.events)
    def append_event(self, event): self.events.append(event)
    def notification_already_created(self, cid, *_args): return cid in self.commands
    def enqueue_notification(self, cmd): self.commands[cmd.command_id] = cmd


def actions(outcome, *, writer_fails=False):
    identity = SheetRecordIdentity(WorksheetIdentity("test", "2026"), 4,
                                  IdentifyingSnapshot("未发", "A", "TEST-MPN", "Brand", 8))
    item = SimpleNamespace(inquiry_id="synthetic-inquiry", mpn="TEST-MPN", brand="Brand",
                           resolved_brand=None, brand_update_status=None, quantity=8, record_identity=identity,
                           status=SimpleNamespace(value="COMPLETED"), last_error=None)
    class Sheet:
        def __init__(self):
            self.calls = 0
            self.rows = [WorksheetRow(4, {"A":"未发", "C":"A", "E":"TEST-MPN", "F":"Brand", "G":8})]
        def read_rows(self, _worksheet): return self.rows
        def write_purchase_status(self, _worksheet, _row):
            self.calls += 1
            if writer_fails: raise RuntimeError("sensitive-provider-message")
            self.rows = [WorksheetRow(4, {"A":"发给采购", "C":"A", "E":"TEST-MPN", "F":"Brand", "G":8})]
    sheet, state = Sheet(), V12(outcome)
    class Episodes:
        def __init__(self): self.records = []
        def record_confirmed(self, inquiry_id, *, confirmed_at):
            self.records.append((inquiry_id, confirmed_at))
    episodes = Episodes()
    handler = PurchaseCompletionActions(workflow_store=SimpleNamespace(get_by_inquiry_id=lambda _i:item),
        v12_store=state, reader=sheet, writer_factory=lambda:sheet, follow_up_store=episodes)
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
    assert handler.process(flow(PurchaseOutcome.SAVED), at=NOW) is True
    assert state.state is BusinessState.STATUS_WRITE_PENDING
    assert state.outcome is PurchaseOutcome.SAVED and sheet.calls == 1
    body = next(iter(state.commands.values())).text_body
    assert "表格状态写回未能确认" in body and "保持原状态" in body and "RuntimeError" in body
    assert "sensitive-provider-message" not in body


def test_saved_status_recovery_never_reenters_purchase_and_stops_after_success():
    handler, sheet, state = actions(PurchaseOutcome.SAVED, writer_fails=True)
    handler.workflow_store.all_items = lambda: [handler.workflow_store.get_by_inquiry_id("synthetic-inquiry")]
    handler.process(flow(PurchaseOutcome.SAVED), at=NOW)
    assert sheet.calls == 1 and state.outcome is PurchaseOutcome.SAVED
    sheet.rows = [WorksheetRow(4, {"A":"发给采购", "C":"A", "E":"TEST-MPN", "F":"Brand", "G":8})]
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


def test_no_price_exception_mail_explains_five_sources_and_is_idempotent():
    handler, sheet, state = actions(PurchaseOutcome.PRE_SAVE_READY)
    item = handler.workflow_store.get_by_inquiry_id("synthetic-inquiry")
    item.status = SimpleNamespace(value="FAILED")
    item.last_error = "NO_MATCHING_PRODUCT"
    result = flow(None)
    result.business_state = BusinessState.RESEARCH_FAILED
    handler.process(result, at=NOW)
    handler.process(result, at=NOW)
    assert sheet.calls == 0 and len(state.commands) == 1
    command = next(iter(state.commands.values()))
    assert "五个价格来源均无报价" in command.text_body
    assert "未进入采购提交" in command.text_body
    assert "不等于型号一定填错" in command.text_body
    assert [r.address for r in command.recipients] == ["linan229@qq.com", "shawn@inso-hk.com"]


@pytest.mark.parametrize("phase,reason", [
    ("RESEARCH", "RESEARCH_FAILED"), ("RESEARCH", "SOURCE_UNAVAILABLE"),
    ("PURCHASE", "NO_MATCHING_PRODUCT"), ("SESSION", "LOGIN_REQUIRED"),
    ("SHEETS_WRITE_BACK", "GoogleSheetsReadError"),
])
def test_only_all_no_result_research_exception_adds_shawn(phase, reason):
    handler, sheet, state = actions(PurchaseOutcome.PRE_SAVE_READY)
    handler.notify("synthetic-inquiry", phase, reason, at=NOW)
    command = next(iter(state.commands.values()))
    assert [r.address for r in command.recipients] == ["linan229@qq.com"]
    assert not command.command_id.endswith(":recipients-v2") and sheet.calls == 0


def test_status_write_records_actual_confirmation_timestamp_once():
    from datetime import timedelta

    handler, sheet, state = actions(PurchaseOutcome.SAVED)
    after_write = NOW + timedelta(seconds=8)
    handler._clock = lambda: after_write
    handler.process(flow(PurchaseOutcome.SAVED), at=NOW)
    handler.process(flow(PurchaseOutcome.SAVED), at=NOW)
    assert sheet.calls == 1
    assert not state.events
    assert handler.follow_up_store.records == [("synthetic-inquiry", after_write)]


def test_legacy_already_sent_status_does_not_backfill_a_timestamp():
    handler, sheet, state = actions(PurchaseOutcome.SAVED)
    sheet.rows = [WorksheetRow(4, {"A":"发给采购", "C":"A", "E":"TEST-MPN", "F":"Brand", "G":8})]
    handler.process(flow(PurchaseOutcome.SAVED), at=NOW)
    assert not state.events and sheet.calls == 0
    assert not handler.follow_up_store.records


def test_failed_status_write_does_not_start_follow_up_clock():
    handler, _sheet, state = actions(PurchaseOutcome.SAVED, writer_fails=True)
    handler.process(flow(PurchaseOutcome.SAVED), at=NOW)
    assert not state.events and not handler.follow_up_store.records
    assert state.state is BusinessState.STATUS_WRITE_PENDING


def test_sidecar_failure_after_confirmed_status_is_global_stop_not_purchase_requeue():
    from src.workflow.v12_faults import FaultScope, V12Fault
    handler, sheet, state = actions(PurchaseOutcome.SAVED)
    def failed(*args, **kwargs):
        raise V12Fault(FaultScope.GLOBAL_STOP, "WORKFLOW_LEDGER_UNAVAILABLE")
    handler.follow_up_store.record_confirmed = failed
    with pytest.raises(V12Fault) as error:
        handler.process(flow(PurchaseOutcome.SAVED), at=NOW)
    assert error.value.scope is FaultScope.GLOBAL_STOP
    assert error.value.reason == "WORKFLOW_LEDGER_UNAVAILABLE"
    assert state.state is BusinessState.PURCHASE_RECORDED
    assert state.outcome is PurchaseOutcome.SAVED
    assert sheet.rows[0].cells["A"] == "发给采购" and sheet.calls == 1
    # Same source is already sent: even status settlement does not replay dispatch.
    handler.process(flow(PurchaseOutcome.SAVED), at=NOW)
    assert sheet.calls == 1 and not state.commands


def test_unconfirmed_google_readback_does_not_create_episode():
    handler, sheet, state = actions(PurchaseOutcome.SAVED)
    sheet.write_purchase_status = lambda *args: None  # API returned, source never changed.
    handler.process(flow(PurchaseOutcome.SAVED), at=NOW)
    assert not handler.follow_up_store.records
    assert state.state is BusinessState.STATUS_WRITE_PENDING


def quoted(handler, sheet, state, *, pending=False):
    item = handler.workflow_store.get_by_inquiry_id("synthetic-inquiry")
    handler.workflow_store.all_items = lambda: [item]
    sheet.rows = [WorksheetRow(4, {"A": "采购已报价", "C": "A", "E": "TEST-MPN", "F": "Brand", "G": 8})]
    if pending:
        state.state = BusinessState.STATUS_WRITE_PENDING
    return item


def test_restart_saved_quoted_order_never_writes_notifies_or_creates_episode():
    handler, sheet, state = actions(PurchaseOutcome.SAVED)
    quoted(handler, sheet, state)
    handler.writer_factory = lambda: pytest.fail("quoted row must not even construct writer")
    handler.retry_saved_statuses(at=NOW)
    assert state.state is BusinessState.PURCHASE_RECORDED and not state.commands
    assert sheet.calls == 0 and handler.follow_up_store.records == []
    # Restart, with no in-memory settled cache, remains idempotent.
    handler._settled_status_ids.clear()
    handler.retry_saved_statuses(at=NOW)
    assert sheet.calls == 0 and not state.commands


@pytest.mark.parametrize("status", ["发给采购", "采购已报价"])
def test_pending_saved_projection_recovers_only_by_read_no_backward_write(status):
    handler, sheet, state = actions(PurchaseOutcome.SAVED)
    quoted(handler, sheet, state, pending=True)
    sheet.rows[0] = WorksheetRow(4, {**sheet.rows[0].cells, "A": status})
    state.commands["historical-mail"] = object()
    handler.writer_factory = lambda: pytest.fail("pending recovery may never construct writer")
    handler.retry_saved_statuses(at=NOW)
    assert state.state is BusinessState.PURCHASE_RECORDED
    assert list(state.commands) == ["historical-mail"]
    assert sheet.calls == 0 and handler.follow_up_store.records == []


@pytest.mark.parametrize("column,value", [("A", "未发"), ("E", "CHANGED"), ("G", 9),
                                          ("C", "B"), ("F", "OTHER")])
def test_pending_projection_retains_hold_for_pending_or_changed_source(column, value):
    handler, sheet, state = actions(PurchaseOutcome.SAVED)
    quoted(handler, sheet, state, pending=True)
    sheet.rows[0] = WorksheetRow(4, {**sheet.rows[0].cells, column: value})
    handler.retry_saved_statuses(at=NOW)
    assert state.state is BusinessState.STATUS_WRITE_PENDING
    assert sheet.calls == 0 and not state.commands and handler.follow_up_store.records == []


def test_ambiguous_quoted_rows_still_fail_closed_and_alert():
    handler, sheet, state = actions(PurchaseOutcome.SAVED)
    quoted(handler, sheet, state)
    sheet.rows.append(WorksheetRow(5, dict(sheet.rows[0].cells)))
    handler.retry_saved_statuses(at=NOW)
    assert state.state is BusinessState.STATUS_WRITE_PENDING and len(state.commands) == 1
    body = next(iter(state.commands.values())).text_body
    assert "保持原状态" in body and "SheetRecordConflict" in body
    assert sheet.calls == 0


def test_unknown_submit_pending_never_resolves_by_sheet_status_alone():
    handler, sheet, state = actions(PurchaseOutcome.UNKNOWN_WRITE_OUTCOME)
    quoted(handler, sheet, state, pending=True)
    handler.retry_saved_statuses(at=NOW)
    assert state.state is BusinessState.STATUS_WRITE_PENDING and not state.commands
    assert state.outcome is PurchaseOutcome.UNKNOWN_WRITE_OUTCOME and sheet.calls == 0


@pytest.mark.parametrize("updated", [False, True])
def test_quoted_binding_uses_only_the_brand_actually_present_in_source(updated):
    from dataclasses import replace
    handler, sheet, state = actions(PurchaseOutcome.SAVED)
    item = quoted(handler, sheet, state, pending=True)
    item.resolved_brand = "Research display name"
    if updated:
        item.brand_update_status = "UPDATED"
        item.record_identity = replace(item.record_identity,
            identifying_snapshot=replace(item.record_identity.identifying_snapshot, brand=None))
        sheet.rows[0] = WorksheetRow(4, {**sheet.rows[0].cells, "F": item.resolved_brand})
    handler.retry_saved_statuses(at=NOW)
    assert state.state is BusinessState.PURCHASE_RECORDED
    assert sheet.calls == 0 and not state.commands and handler.follow_up_store.records == []


@pytest.mark.parametrize("source_brand", ["hrs", "HRS(hirose)", "  HRS  "])
def test_owner_fuzzy_brand_rule_does_not_create_quoted_status_alarm(source_brand):
    from dataclasses import replace
    handler, sheet, state = actions(PurchaseOutcome.SAVED)
    item = quoted(handler, sheet, state, pending=True)
    item.brand = "HRS"
    item.record_identity = replace(item.record_identity,
        identifying_snapshot=replace(item.record_identity.identifying_snapshot, brand="HRS"))
    sheet.rows[0] = WorksheetRow(4, {**sheet.rows[0].cells, "F": source_brand})
    handler.retry_saved_statuses(at=NOW)
    assert state.state is BusinessState.PURCHASE_RECORDED
    assert sheet.calls == 0 and not state.commands and handler.follow_up_store.records == []
