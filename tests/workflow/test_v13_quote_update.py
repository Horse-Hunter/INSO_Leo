import sqlite3
from dataclasses import replace
from types import SimpleNamespace

import pytest

from src.sheets.quotation_input import (
    QuotationInputAttemptFailed,
    QuotationInputUnavailable,
)
from src.workflow.v12_faults import FaultScope, V12Fault
from src.workflow.v13_quotation import (
    QuotationOutcome,
    RowErrorReason,
    V13QuotationResult,
    V13SourceRowError,
    V13Stopped,
)
from src.workflow.v13_quote_update import (
    UpdateAttemptUnconfirmed,
    V13QuotationUpdater,
    WorkflowQuotationSource,
)
from tests.inso.test_v13_quotation_read import quote
from tests.workflow.test_v13_quotation import WS, Sheets, Store, item, source

POPUP = "报价更新完成\n成功填入：1行"
EXISTS = "报价更新完成\n成功填入：0行\n已有报价：1行"


def found(position=2, model="MPN"):
    original = item(position, model=model)
    return V13QuotationResult(original.inquiry_id, original.record_identity, model,
                              QuotationOutcome.QUOTE_FOUND, quote(model=model), source_worksheet=WS, source_row_position=position)


class Source:
    def __init__(self):
        self.clicks = 0
        self.after = ["采购已报价"]
        self.before = "发给采购"
        self.calls = []
        self.error = None
    def status(self, result):
        self.calls.append(result)
        if self.error:
            raise self.error
        if not self.clicks:
            return self.before
        value = self.after.pop(0) if len(self.after) > 1 else self.after[0]
        if isinstance(value, Exception):
            raise value
        return value


class Input:
    worksheet = SimpleNamespace(spreadsheet="fake-sheet")
    def __init__(self):
        self.writes, self.reads, self.schemas = [], 0, 0
        self.write_failures = []
        self.readbacks = []
        self.payload = ("old",)*14
        self.schema_error = None
    def validate_schema(self):
        self.schemas += 1
        if self.schema_error:
            raise self.schema_error
    def write_payload(self, payload):
        self.writes.append(payload)
        if self.write_failures:
            error = self.write_failures.pop(0)
            if error:
                raise error
        self.payload = payload
    def read_payload(self):
        self.reads += 1
        return self.readbacks.pop(0) if self.readbacks else self.payload


class Actions:
    def __init__(self, source_reader):
        self.source = source_reader
        self.popups = [POPUP]
        self.opened, self.closed, self.clicks, self.dismissed = 0, 0, 0, 0
        self.active = False
        self.dismiss_error = None
    def open_quote_input(self):
        assert not self.active
        self.opened += 1
        self.active = True
    def click_update_quote(self):
        assert self.active
        self.clicks += 1
        self.source.clicks += 1
    def read_update_result(self):
        value = self.popups.pop(0) if len(self.popups) > 1 else self.popups[0]
        if isinstance(value, Exception):
            raise value
        return value
    def dismiss_result(self):
        self.dismissed += 1
        if self.dismiss_error:
            raise self.dismiss_error
    def close(self):
        if self.active:
            self.closed += 1
            self.active = False


def service():
    src, io = Source(), Input()
    actions, waits = Actions(src), []
    updater = V13QuotationUpdater(source=src, quotation_input=io, actions=actions,
        wait=lambda seconds: waits.append(seconds) or False)
    return updater, src, io, actions, waits


@pytest.mark.parametrize("outcome", [QuotationOutcome.NO_RECENT_QUOTE, QuotationOutcome.ROW_FAILED])
def test_non_quote_input_passes_through_unchanged_without_any_side_effect(outcome):
    updater, src, io, actions, waits = service()
    upstream = replace(found(), outcome=outcome, row_error_reason=RowErrorReason.SOURCE_CHANGED)
    assert updater.update_one(upstream) is upstream
    assert not src.calls and not io.writes and actions.opened == actions.clicks == 0 and waits == []


@pytest.mark.parametrize("popup,outcome", [(POPUP, QuotationOutcome.UPDATED_INSERTED),
                                         (EXISTS, QuotationOutcome.UPDATED_ALREADY_EXISTS)])
def test_confirmed_popup_and_source_quoted_success_once(popup, outcome):
    updater, _, io, actions, waits = service()
    actions.popups = [popup]
    upstream = found()
    result = updater.update_one(upstream)
    assert result.outcome is outcome
    assert result.record_identity is upstream.record_identity and result.inquiry_id == upstream.inquiry_id
    assert io.writes == [upstream.quotation.payload] and io.reads == 2
    assert actions.opened == actions.closed == actions.clicks == 1 and waits == []


def test_raw_payload_business_mismatch_odd_empty_values_never_revalidated():
    updater, _, io, _, _ = service()
    upstream = found()
    raw = ("2026/10/07 00:00", "MPN", "unrelated", "", "奇币", "", "0001.2300", "",
           "0000", "批号", "", "  备注\n  ", "特殊\t", "")
    upstream = replace(upstream, quotation=replace(upstream.quotation, payload=raw))
    assert updater.update_one(upstream).outcome is QuotationOutcome.UPDATED_INSERTED
    assert io.writes == [raw]


@pytest.mark.parametrize("failure_kind", ["write", "readback", "stale"])
def test_full_write_readback_retries_recover_and_only_then_click(failure_kind):
    updater, _, io, actions, _ = service()
    if failure_kind == "write":
        io.write_failures = [QuotationInputAttemptFailed("QUOTE_INPUT_WRITE_FAILED"), None]
    elif failure_kind == "readback":
        io.readbacks = [("wrong",)*14]
    else:
        io.readbacks = [found().quotation.payload, ("overwritten",)*14]
    assert updater.update_one(found()).outcome is QuotationOutcome.UPDATED_INSERTED
    assert len(io.writes) == 2 and all(len(payload) == 14 for payload in io.writes)
    assert actions.clicks == 1


@pytest.mark.parametrize("failure_kind,reason", [("write", RowErrorReason.QUOTE_INPUT_WRITE_FAILED),
                                                 ("readback", RowErrorReason.QUOTE_INPUT_READBACK_MISMATCH)])
def test_four_input_failures_are_row_failed_without_click(failure_kind, reason):
    updater, _, io, actions, waits = service()
    if failure_kind == "write":
        io.write_failures = [QuotationInputAttemptFailed("private detail")]*4
    else:
        io.readbacks = [("wrong",)*14]*4
    result = updater.update_one(found())
    assert result.outcome is QuotationOutcome.ROW_FAILED and result.row_error_reason is reason
    assert len(io.writes) == 4 and actions.clicks == 0 and actions.closed == 1 and waits == []


@pytest.mark.parametrize("first_popup", [None, "unknown", UpdateAttemptUnconfirmed("hang"),
    "报价更新完成 成功填入：0行 已有报价：0行"])
def test_unconfirmed_update_retry_reestablishes_surface_and_entire_payload(first_popup):
    updater, src, io, actions, waits = service()
    src.after = ["发给采购"]*3 + ["采购已报价"]
    actions.popups = [first_popup, EXISTS]
    result = updater.update_one(found())
    assert result.outcome is QuotationOutcome.UPDATED_ALREADY_EXISTS
    assert actions.opened == actions.closed == actions.clicks == 2
    assert len(io.writes) == 2 and io.reads == 4 and waits == []


def test_popup_missing_but_prior_script_status_closed_prevents_second_click():
    updater, _, io, actions, waits = service()
    actions.popups = [None]
    result = updater.update_one(found())
    assert result.outcome is QuotationOutcome.UPDATED_ALREADY_EXISTS
    assert actions.clicks == actions.opened == actions.closed == 1 and len(io.writes) == 1 and waits == []


def test_four_update_attempts_exhaust_row_failure_and_rewrite_each_time():
    updater, src, io, actions, waits = service()
    src.after = ["发给采购"]
    actions.popups = [None]
    result = updater.update_one(found())
    assert result.row_error_reason is RowErrorReason.UPDATE_RESULT_UNCONFIRMED
    assert actions.opened == actions.closed == actions.clicks == 4
    assert len(io.writes) == 4 and io.reads == 8 and waits == []


def test_confirmed_popup_only_polls_source_and_never_resubmits():
    updater, src, _, actions, waits = service()
    src.after = ["发给采购", "发给采购", "采购已报价"]
    result = updater.update_one(found())
    assert result.outcome is QuotationOutcome.UPDATED_INSERTED
    assert actions.clicks == 1 and waits == [1.0, 1.0]


def test_confirmed_popup_status_still_sent_is_row_failure_not_an_update_retry():
    updater, src, _, actions, waits = service()
    src.after = ["发给采购"]
    result = updater.update_one(found())
    assert result.row_error_reason is RowErrorReason.SOURCE_STATUS_NOT_UPDATED
    assert actions.clicks == actions.opened == actions.closed == 1 and waits == [1.0, 1.0]


def test_dismiss_failure_after_success_does_not_retry_submission():
    updater, _, _, actions, _ = service()
    actions.dismiss_error = UpdateAttemptUnconfirmed("missing control")
    assert updater.update_one(found()).outcome is QuotationOutcome.UPDATED_INSERTED
    assert actions.clicks == 1


def test_short_status_wait_shutdown_interrupts_and_closes_owned_surface():
    updater, src, _, actions, _ = service()
    src.after = ["发给采购"]
    updater._wait = lambda seconds: True
    with pytest.raises(V13Stopped):
        updater.update_one(found())
    assert actions.clicks == 1 and actions.closed == 1


def test_already_quoted_on_entry_has_no_write_tab_or_click():
    updater, src, io, actions, waits = service()
    src.before = "采购已报价"
    assert updater.update_one(found()).outcome is QuotationOutcome.UPDATED_ALREADY_EXISTS
    assert io.writes == [] and actions.opened == actions.clicks == 0 and waits == []


def test_success_bad_success_batch_is_serial_without_180s_wait_or_quarantine():
    updater, _, io, actions, waits = service()
    original_update = updater.update_one
    def update(result):
        actions.source.clicks = 0
        io.write_failures = [QuotationInputAttemptFailed("write failed")]*4 if result.inquiry_id == "original-3" else []
        return original_update(result)
    updater.update_one = update
    results = updater.run([found(2), found(3), found(4)])
    assert [r.outcome for r in results] == [QuotationOutcome.UPDATED_INSERTED,
        QuotationOutcome.ROW_FAILED, QuotationOutcome.UPDATED_INSERTED]
    assert actions.clicks == 2 and actions.opened == actions.closed == 3 and waits == []
    assert all(r.record_identity.row_position in (2, 3, 4) for r in results)


@pytest.mark.parametrize("phase", ["schema", "write", "source"])
def test_shared_google_failure_is_global_not_row_error(phase):
    updater, src, io, actions, _ = service()
    if phase == "schema":
        io.schema_error = QuotationInputUnavailable("QUOTE_INPUT_SCHEMA_UNAVAILABLE")
    elif phase == "write":
        io.write_failures = [QuotationInputUnavailable()]
    else:
        src.error = V12Fault(FaultScope.GLOBAL_STOP, "SHEETS_READ_UNAVAILABLE")
    with pytest.raises(V12Fault) as raised:
        updater.update_one(found())
    assert raised.value.scope is FaultScope.GLOBAL_STOP and actions.clicks == 0


@pytest.mark.parametrize("moved", [False, True])
def test_actual_source_locator_accepts_script_quoted_state_preserves_original_identity(moved):
    original = item(2)
    reader = Sheets([source(20 if moved else 2, status="采购已报价")])
    verifier = WorkflowQuotationSource(reader=reader, store=Store([original]))
    upstream = found()
    assert verifier.status(upstream) == "采购已报价"
    assert upstream.record_identity.row_position == 2 and original.record_identity == upstream.record_identity


def test_actual_source_conflict_and_ambiguity_fail_only_the_row():
    verifier = WorkflowQuotationSource(reader=Sheets([source(20), source(21)]), store=Store([item(2)]))
    with pytest.raises(V13SourceRowError):
        verifier.status(found())
    verifier = WorkflowQuotationSource(reader=Sheets([source(2, status="未发")]), store=Store([item(2)]))
    with pytest.raises(V13SourceRowError):
        verifier.status(found())


@pytest.mark.parametrize("boundary", ["reader", "ledger"])
def test_actual_source_shared_reads_and_database_faults_still_global(boundary):
    reader, store = Sheets([source(2)]), Store([item(2)])
    def fail(*args):
        raise sqlite3.DatabaseError("private details")
    if boundary == "reader":
        reader.read_rows = fail
    else:
        store.get_by_inquiry_id = fail
    with pytest.raises(V12Fault) as raised:
        WorkflowQuotationSource(reader=reader, store=store).status(found())
    assert raised.value.scope is FaultScope.GLOBAL_STOP


def test_retry_source_conflict_is_row_only_with_no_second_input_or_click():
    updater, src, io, actions, waits = service()
    actions.popups = [None]
    src.after = [V13SourceRowError(RowErrorReason.SOURCE_CHANGED)]
    result = updater.update_one(found())
    assert result.row_error_reason is RowErrorReason.SOURCE_CHANGED
    assert actions.clicks == 1 and len(io.writes) == 1 and waits == []


def test_actual_source_status_reader_with_script_fake_closes_success_bad_success():
    reader = Sheets([source(2), source(3, model="BAD", brand="changed"), source(4, model="C")])
    store = Store([item(2), item(3, model="BAD"), item(4, model="C")])
    original_verifier = WorkflowQuotationSource(reader=reader, store=store)
    class Verifier:
        def status(self, result):
            self.last = result
            return original_verifier.status(result)
    verifier = Verifier()
    src, io = Source(), Input()
    class ScriptActions(Actions):
        def click_update_quote(self):
            super().click_update_quote()
            position = verifier.last.record_identity.row_position
            reader.rows = [replace(row, cells={**row.cells, "A": "采购已报价"})
                           if row.row_position == position else row for row in reader.rows]
    actions = ScriptActions(src)
    waits = []
    updater = V13QuotationUpdater(source=verifier, quotation_input=io, actions=actions,
                                  wait=lambda seconds: waits.append(seconds) or False)
    results = updater.run([found(2), found(3, model="BAD"), found(4, model="C")])
    assert [r.outcome for r in results] == [QuotationOutcome.UPDATED_INSERTED,
        QuotationOutcome.ROW_FAILED, QuotationOutcome.UPDATED_INSERTED]
    assert results[1].row_error_reason is RowErrorReason.SOURCE_CHANGED
    assert actions.clicks == actions.opened == actions.closed == 2 and waits == []
    assert len(io.writes) == 2


def test_confirmed_popup_with_source_status_conflict_is_row_failed_without_resubmit():
    updater, src, _, actions, _ = service()
    src.after = [V13SourceRowError(RowErrorReason.SOURCE_CHANGED)]
    result = updater.update_one(found())
    assert result.row_error_reason is RowErrorReason.SOURCE_CHANGED and actions.clicks == 1


def test_stop_before_update_does_not_open_or_write():
    updater, _, io, actions, _ = service()
    updater._stop = lambda: True
    with pytest.raises(V13Stopped):
        updater.update_one(found())
    assert actions.opened == actions.clicks == 0 and io.writes == []


def test_safely_retry_after_click_timeout_reestablishes_surface_and_input():
    updater, src, io, actions, _ = service()
    src.after = ["发给采购"]*3 + ["采购已报价"]
    click = actions.click_update_quote
    def first_timeout():
        click()
        if actions.clicks == 1:
            raise UpdateAttemptUnconfirmed("timeout after click")
    actions.click_update_quote = first_timeout
    actions.popups = [EXISTS]
    assert updater.update_one(found()).outcome is QuotationOutcome.UPDATED_ALREADY_EXISTS
    assert actions.clicks == actions.opened == actions.closed == 2 and len(io.writes) == 2


def test_schema_missing_is_global_while_source_ambiguity_is_not():
    updater, _, _, _, _ = service()
    updater._input.worksheet = SimpleNamespace(spreadsheet="other-book")
    with pytest.raises(V12Fault) as raised:
        updater.update_one(found())
    assert raised.value.reason == "QUOTE_INPUT_LOCATION_INVALID"


def test_other_source_status_is_never_submitted_by_the_update_service():
    updater, src, io, actions, waits = service()
    src.before = "人工处理"
    result = updater.update_one(found())
    assert result.row_error_reason is RowErrorReason.SOURCE_CHANGED
    assert actions.opened == actions.clicks == 0 and io.writes == [] and waits == []


# Exercise the actual Sheets adapter through Workflow, rather than a schema stub.
@pytest.mark.parametrize("metadata,gid", [
    ({"sheets": [{"properties": {"title": "报价输入", "sheetId": 27}}]}, "99"),
    ({"sheets": [{"properties": {"title": "报价输入", "sheetId": 27}},
                {"properties": {"title": "其他", "sheetId": 99}}]}, "99"),
    ({"sheets": [{"properties": {"title": "其他", "sheetId": 27}}]}, "27"),
    ({"sheets": []}, "27"),
    ({"sheets": [{"properties": {"title": "报价输入", "sheetId": 27}},
                {"properties": {"title": "报价输入", "sheetId": 28}}]}, "27"),
    (None, "27"), ({}, "27"), ({"sheets": {}}, "27"),
    ({"sheets": [None]}, "27"), ({"sheets": [{}]}, "27"),
    ({"sheets": [{"properties": None}]}, "27"),
    ({"sheets": [{"properties": {"title": "报价输入"}}]}, "27"),
    ({"sheets": [{"properties": {"title": 123, "sheetId": 27}}]}, "27"),
    *[({"sheets": [{"properties": {"title": "报价输入", "sheetId": bad}}]}, "27")
      for bad in (None, True, "27", 27.0, -1)],
])
def test_metadata_binding_fault_stops_before_any_header_write_ui_open_or_click(metadata, gid):
    from tests.sheets.test_quotation_input import adapter
    io, values = adapter(gid=gid)
    values.metadata = metadata
    source_reader = Source()
    actions = Actions(source_reader)
    updater = V13QuotationUpdater(source=source_reader, quotation_input=io, actions=actions, wait=lambda _: False)
    with pytest.raises(V12Fault) as raised:
        updater.update_one(found())
    assert raised.value.scope is FaultScope.GLOBAL_STOP
    assert [kind for kind, _ in values.calls] == ["metadata"]
    assert actions.opened == actions.closed == actions.clicks == 0


@pytest.mark.parametrize("failure", ["provider", "auth", 401, 403])
def test_metadata_request_failure_is_sanitized_global_stop_before_ui(failure):
    from src.sheets.google_oauth import GoogleSheetsAuthorizationError
    from tests.sheets.test_quotation_input import adapter
    io, values = adapter()
    error = (GoogleSheetsAuthorizationError("private provider contents") if failure == "auth"
             else RuntimeError("private provider contents"))
    if isinstance(failure, int):
        error.resp = SimpleNamespace(status=failure)
    values.metadata_error = error
    source_reader = Source()
    actions = Actions(source_reader)
    updater = V13QuotationUpdater(source=source_reader, quotation_input=io, actions=actions, wait=lambda _: False)
    with pytest.raises(V12Fault) as raised:
        updater.update_one(found())
    assert raised.value.scope is FaultScope.GLOBAL_STOP
    assert "private" not in str(raised.value)
    assert [kind for kind, _ in values.calls] == ["metadata"]
    assert actions.opened == actions.clicks == 0


@pytest.mark.parametrize("popup,outcome", [
    (POPUP, QuotationOutcome.UPDATED_INSERTED),
    (EXISTS, QuotationOutcome.UPDATED_ALREADY_EXISTS),
])
def test_actual_api_headerless_binding_raw_readback_and_popup_success(popup, outcome):
    from tests.sheets.test_quotation_input import adapter
    io, values = adapter()
    source_reader = Source()
    actions = Actions(source_reader)
    actions.popups = [popup]
    updater = V13QuotationUpdater(source=source_reader, quotation_input=io, actions=actions, wait=lambda _: False)
    upstream = found()
    result = updater.update_one(upstream)
    assert result.outcome is outcome
    assert result.inquiry_id == upstream.inquiry_id and result.record_identity == upstream.record_identity
    assert tuple(values.payload) == upstream.quotation.payload
    assert [kind for kind, _ in values.calls][:2] == ["metadata", "metadata"]
    assert sum(kind == "update" for kind, _ in values.calls) == actions.clicks == 1
    assert actions.opened == actions.closed == 1
