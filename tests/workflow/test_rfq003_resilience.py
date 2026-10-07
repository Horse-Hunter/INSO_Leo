"""Offline RFQ-003 policy regressions; no network, credentials or wall-clock sleeps."""
from dataclasses import replace
from decimal import Decimal
from types import SimpleNamespace

import pytest

from src.gui.app import _order_row_style, _v12_status_text
from src.gui.contracts import RunState
from src.inso.purchase_writer import InsoPurchaseWriter
from src.inso.write_safety import OwnerAuthorizedSaveAndSendGate
from src.launcher.backend import ProductionBackend, _Observer, _PreparedDuplicateChecker
from src.launcher.v12_gui import read_v12_order_state
from src.research import ResearchInput, ResearchResult, ResearchStatus
from src.sheets import WorksheetRow, query_pending_records
from src.workflow.v12_contracts import (
    CLOSED_BUSINESS_STATES,
    BusinessState,
    DuplicateCheckResult,
    DuplicateOutcome,
    EventType,
    PurchaseOutcome,
    ReconciliationOutcome,
    ReconciliationResult,
    business_label_for_state,
)
from src.workflow.v12_faults import FaultScope, V12Fault
from src.workflow.v12_flow import ResearchBusinessFacts
from src.workflow.v12_store import ReadOnlySaveReconciler, V12DatabaseError
from tests.launcher.test_purchase_completion import actions
from tests.launcher.test_purchase_completion import flow as completion_result
from tests.workflow.test_v12_flow import NOW, SHEET, FakeSheetsReader, _make_flow


def rows():
    first = query_pending_records(FakeSheetsReader(), SHEET)[0]
    second = replace(first, row_position=4, record_identity=replace(first.record_identity, row_position=4))
    return first, second


@pytest.mark.parametrize("status", [ResearchStatus.EXCEPTION, ResearchStatus.SUCCESS])
def test_row_terminal_continues_with_exact_cooldown_and_none_after_last(tmp_path, status):
    f, _ws, _vs, research, *_rest = _make_flow(tmp_path)
    events = []
    research.execute = lambda item: events.append("research") or ResearchResult(item.inquiry_id, status)
    f._row_wait = lambda seconds: events.append(seconds) or False
    results = f.process_pending(rows(), now=NOW)
    assert len(results) == 2 and events == ["research", 180, "research"]
    f.begin_poll_cycle()
    assert f.process_pending((), now=NOW) == ()
    assert events == ["research", 180, "research"]


def test_stop_interrupts_cooldown_without_starting_second_row(tmp_path):
    f, _ws, _vs, research, *_rest = _make_flow(tmp_path)
    f._row_wait = lambda seconds: seconds == 180
    assert len(f.process_pending(rows(), now=NOW)) == 1
    assert len(research.inputs) == 1


@pytest.mark.parametrize("bad", ["model", "brand", "quantity"])
def test_invalid_row_skips_research_but_next_row_runs(tmp_path, bad):
    f, _ws, _vs, research, *_rest = _make_flow(tmp_path)
    first, second = rows()
    first = replace(first, **{bad: ""})
    results = f.process_pending((first, second), now=NOW)
    assert results[0].business_state is BusinessState.INVALID_INPUT_SKIPPED
    assert len(research.inputs) == 1 and len(results) == 2


@pytest.mark.parametrize("site,scope", [("IC.net", FaultScope.V12_PAUSE), ("INSO", FaultScope.GLOBAL_STOP), ("立创", None)])
def test_site_challenge_scope_is_explicit(tmp_path, monkeypatch, site, scope):
    backend = ProductionBackend(root=tmp_path)
    monkeypatch.setattr(backend, "_alert_owner_of_login", lambda **_k: None)
    backend._state = RunState.RUNNING
    observer = _Observer(SimpleNamespace(execute=lambda item: ResearchResult(item.inquiry_id,
        ResearchStatus.PARTIAL_SUCCESS, remarks=f"{site}：需要人工验证")), lambda _i: None, backend._manual_review)
    item = ResearchInput("synthetic", "TEST", "Brand", 1, "A")
    if scope is None:
        observer.execute(item)
        assert backend.get_status().state is RunState.RUNNING
    else:
        with pytest.raises(V12Fault) as error:
            observer.execute(item)
        assert error.value.scope is scope
        assert backend.get_status().state is (RunState.GLOBAL_STOP if scope is FaultScope.GLOBAL_STOP else RunState.MODULE_PAUSED)
    backend.shutdown()


@pytest.mark.parametrize("successful_attempt", [1, 2, 3, 4, None])
def test_inso_queries_retry_fresh_only_after_180_seconds(successful_attempt):
    events = []
    attempts = []
    def check(iid, mpn, _quantity, *, at):
        attempts.append(1)
        events.append("query")
        return DuplicateCheckResult(iid,
            DuplicateOutcome.CONFIRMED if len(attempts) == successful_attempt else DuplicateOutcome.UNAVAILABLE,
            mpn, at, repeated=False if len(attempts) == successful_attempt else None)
    checker = _PreparedDuplicateChecker(SimpleNamespace(check=check),
        prepare=lambda: events.append("fresh"), reset=lambda: events.append("close"),
        wait=lambda seconds: events.append(seconds) or False)
    if successful_attempt is None:
        with pytest.raises(V12Fault) as error:
            checker.check("synthetic", "TEST", 1, at=NOW)
        assert error.value.scope is FaultScope.GLOBAL_STOP
    else:
        assert checker.check("synthetic", "TEST", 1, at=NOW).outcome is DuplicateOutcome.CONFIRMED
    count = successful_attempt or 4
    assert len(attempts) == count and events.count(180) == count - 1
    assert events[:2] == ["fresh", "query"]
    assert events.count("close") == count - (successful_attempt is not None)


def test_unique_click_receipt_is_required_for_unconfirmed_status(tmp_path):
    f, _ws, vs, *_rest = _make_flow(tmp_path, facts=ResearchBusinessFacts("货少", Decimal(10), Decimal(2)))
    iid = f.process_pending(rows()[:1], now=NOW)[0].inquiry_id
    assert vs.purchase_state(iid) is PurchaseOutcome.AI_RECOGNIZED
    writer = InsoPurchaseWriter.__new__(InsoPurchaseWriter)
    writer._gate = OwnerAuthorizedSaveAndSendGate()
    writer._registry = SimpleNamespace(resolve=lambda *_a: None)
    writer._port = SimpleNamespace(candidates=lambda: ())
    clicks = []
    writer._actions = SimpleNamespace(save_and_send=lambda: clicks.append(1))
    writer.save_and_send(vs, iid, at=NOW)
    assert vs.submit_click_proven(iid) and clicks == [1]
    with pytest.raises(V12DatabaseError):
        writer.save_and_send(vs, iid, at=NOW)
    reconciler = ReadOnlySaveReconciler
    class Unknown(reconciler):
        def reconcile(self, _iid):
            return ReconciliationResult(ReconciliationOutcome.UNKNOWN, NOW)
    assert vs.reconcile_unknown_save(iid, Unknown(), at=NOW) is PurchaseOutcome.SUBMIT_UNCONFIRMED
    assert clicks == [1]


def test_unconfirmed_submission_attempts_status_and_owner_command_only():
    handler, sheet, vs = actions(PurchaseOutcome.SUBMIT_UNCONFIRMED)
    assert handler.process(completion_result(PurchaseOutcome.SUBMIT_UNCONFIRMED), at=NOW)
    assert sheet.calls == 1 and len(vs.commands) == 1
    assert [r.address for r in next(iter(vs.commands.values())).recipients] == ["linan229@qq.com"]
    vs.submit_click_proven = lambda _i: False
    with pytest.raises(ValueError):
        handler.process(completion_result(PurchaseOutcome.SUBMIT_UNCONFIRMED), at=NOW)


@pytest.mark.parametrize("armed", [False, True])
def test_restart_quarantines_and_sheet_manual_completion_releases_red_only(tmp_path, armed):
    f, ws, vs, research, *_rest = _make_flow(tmp_path)
    first = rows()[0]
    ws.enqueue(first, now=NOW)
    iid = ws.inquiry_id_for(first.record_identity)
    f._set_state(iid, BusinessState.DUPLICATE_CHECKING, EventType.DUPLICATE_CHECK_STARTED, NOW)
    if armed:
        vs.set_purchase_state(iid, "cmd", PurchaseOutcome.PRE_SAVE_READY, at=NOW)
        vs.set_purchase_state(iid, "cmd", PurchaseOutcome.AI_RECOGNIZED, at=NOW)
        vs.begin_save_dispatch(iid, at=NOW, save_and_send=True)
    f.initialize_run_state(now=NOW)
    state = vs.business_state(iid)
    assert state is (BusinessState.INTERRUPTED_POSSIBLY_SENT if armed else BusinessState.INTERRUPTED_UNSENT)
    reader = FakeSheetsReader()
    f.poll_and_process(reader, SHEET, now=NOW)
    assert not research.inputs
    dto = read_v12_order_state(vs, iid)
    assert "处理中断" in _v12_status_text(dto, "")
    assert _order_row_style(SimpleNamespace(status=SimpleNamespace(value=""), processed_at=None), NOW, dto) == "error"
    reader.row = WorksheetRow(99, {**reader.row.cells, "A": "发给采购"})
    f.poll_and_process(reader, SHEET, now=NOW)
    assert vs.business_state(iid) is BusinessState.HUMAN_COMPLETED and not research.inputs
    assert _order_row_style(SimpleNamespace(status=SimpleNamespace(value="error"), processed_at=None),
        NOW, read_v12_order_state(vs, iid)) == "legacy"
    assert f.poll_and_process(reader, SHEET, now=NOW) == () and not research.inputs


@pytest.mark.parametrize("state", [BusinessState.SUBMIT_UNCONFIRMED, BusinessState.STATUS_WRITE_PENDING])
def test_pending_rows_are_yellow_with_explicit_text(tmp_path, state):
    f, _ws, vs, *_rest = _make_flow(tmp_path)
    iid = f.process_pending(rows()[:1], now=NOW)[0].inquiry_id
    f._set_state(iid, state, EventType.HUMAN_RESOLUTION_RECORDED, NOW)
    dto = read_v12_order_state(vs, iid)
    assert dto.waiting_label in {"已发采购（待确认）", "采购已处理，表格状态待人工更新"}
    assert _order_row_style(SimpleNamespace(status=SimpleNamespace(value=""), processed_at=None), NOW, dto) == "warning"


@pytest.mark.parametrize("error,expected", [(V12DatabaseError("ledger"), RunState.GLOBAL_STOP),
    (RuntimeError("code"), RunState.MODULE_PAUSED)])
def test_ledger_fault_is_global_but_unknown_v12_code_is_module_only(tmp_path, monkeypatch, error, expected):
    backend = ProductionBackend(root=tmp_path)
    monkeypatch.setattr(backend, "_alert_owner_of_login", lambda **_k: None)
    backend._runtime_error(error)
    assert backend.get_status().state is expected and backend._immediate_stop_requested()
    backend.shutdown()


@pytest.mark.parametrize("success_after", [1, 2, 3, None])
def test_shared_cdp_has_at_most_three_recoveries(tmp_path, success_after):
    from src.research.source_contracts import ResearchSource, SourceOutcome
    from tests.research.test_aggregation_service import _result
    backend = ProductionBackend(root=tmp_path)
    calls = []
    recoveries = []
    def operation():
        calls.append(1)
        return _result(ResearchSource.LCSC,
            SourceOutcome.NO_VALID_PRICE if success_after is not None and len(calls) > success_after
            else SourceOutcome.SOURCE_UNAVAILABLE, failure_code="CDP_FAILURE")
    if success_after is None:
        with pytest.raises(V12Fault) as error:
            backend._run_source_query("synthetic", ResearchSource.LCSC, operation, lambda: recoveries.append(1))
        assert error.value.scope is FaultScope.GLOBAL_STOP
    else:
        assert backend._run_source_query("synthetic", ResearchSource.LCSC, operation,
            lambda: recoveries.append(1)).outcome is SourceOutcome.NO_VALID_PRICE
    assert len(recoveries) == (success_after or 3)
    assert len(calls) == len(recoveries) + 1
    backend.shutdown()


def test_idle_projection_is_read_only_and_includes_orders_without_research_excel(tmp_path):
    from src.launcher.v12_gui import read_startup_interruptions
    f, ws, vs, *_rest = _make_flow(tmp_path)
    first = rows()[0]
    ws.enqueue(first, now=NOW)
    iid = ws.inquiry_id_for(first.record_identity)
    f._set_state(iid, BusinessState.DUPLICATE_CHECKING, EventType.DUPLICATE_CHECK_STARTED, NOW)
    before = vs.event_history(iid)
    preview = read_startup_interruptions(vs.database_path)
    assert preview[iid][0].business_label.value == "处理中断（未发送）"
    assert ws.get_by_inquiry_id(iid).status.value == "QUEUED"
    assert vs.event_history(iid) == before, "idle projection must never quarantine/write"
    assert f._records == {}


def test_other_research_sources_continue_after_timeout_and_challenge(tmp_path, monkeypatch):
    from src.research.icnet import IcNetResult
    from src.research.service import ResearchService
    from src.research.source_contracts import (
        PRICE_SOURCES,
        ResearchSource,
        SourceOutcome,
    )
    from tests.research.test_aggregation_service import _result
    backend = ProductionBackend(root=tmp_path)
    backend._state = RunState.RUNNING
    mails = []
    backend._v12_store = SimpleNamespace(notification_already_created=lambda *_: False, enqueue_notification=mails.append)
    calls = []
    def search(name):
        calls.append(name)
        if name is ResearchSource.HQEW:
            raise TimeoutError("synthetic")
        if name is ResearchSource.LCSC:
            return _result(name, SourceOutcome.SOURCE_UNAVAILABLE, failure_code="MANUAL_VERIFICATION_REQUIRED")
        return _result(name, SourceOutcome.SUCCESS, "2")
    sources = [SimpleNamespace(search=lambda *_a, name=name: search(name)) for name in PRICE_SOURCES]
    service = ResearchService(icnet=SimpleNamespace(search=lambda *_a: IcNetResult(
        _result(ResearchSource.IC_NET, SourceOutcome.NO_STRICT_MPN_MATCH))),
        findchips=sources[0], hqew=sources[1], lcsc=sources[2], bom_ai=sources[3], inso=sources[4],
        output=SimpleNamespace(upsert=lambda *_a, **_k: None), source_observer=backend._observe_source_failure)
    result = service.execute(ResearchInput("synthetic", "ABC", "Brand", 2, "A"))
    assert result.status is ResearchStatus.PARTIAL_SUCCESS
    assert calls == list(PRICE_SOURCES) and len(mails) == 2
    assert backend.get_status().state is RunState.RUNNING
    backend.shutdown()


def test_shared_fault_from_source_recovery_is_not_swallowed_as_optional_source_failure(tmp_path):
    from src.research.icnet import IcNetResult
    from src.research.service import ResearchService
    from src.research.source_contracts import (
        PRICE_SOURCES,
        ResearchSource,
        SourceOutcome,
    )
    from tests.research.test_aggregation_service import _result
    def source_query(_iid, name, operation):
        if name is ResearchSource.FINDCHIPS:
            raise V12Fault(FaultScope.GLOBAL_STOP, "CDP_RECONNECT_EXHAUSTED")
        return operation()
    source = SimpleNamespace(search=lambda *_a: _result(PRICE_SOURCES[0], SourceOutcome.NO_VALID_PRICE))
    service = ResearchService(icnet=SimpleNamespace(search=lambda *_a: IcNetResult(
        _result(ResearchSource.IC_NET, SourceOutcome.NO_STRICT_MPN_MATCH))),
        findchips=source, hqew=source, lcsc=source, bom_ai=source, inso=source,
        output=SimpleNamespace(upsert=lambda *_a, **_k: None), source_query=source_query)
    with pytest.raises(V12Fault) as error:
        service.execute(ResearchInput("synthetic", "ABC", "Brand", 2, "A"))
    assert error.value.scope is FaultScope.GLOBAL_STOP


def test_single_row_source_conflict_cannot_purchase_and_next_order_continues(tmp_path):
    f, _ws, _vs, _research, _checker, _facts, writer, _worker = _make_flow(tmp_path,
        facts=ResearchBusinessFacts("货少", Decimal(10), Decimal(2)))
    first, second = rows()
    second = replace(second, model="OTHER", record_identity=replace(second.record_identity,
        identifying_snapshot=replace(second.record_identity.identifying_snapshot, model="OTHER")))
    reader = FakeSheetsReader()
    f._current_reader = SimpleNamespace(read_rows=lambda _s: [WorksheetRow(3, {**reader.row.cells, "G": 99}),
        WorksheetRow(4, {**reader.row.cells, "E": "OTHER"})])
    result = f.process_pending((first, second), now=NOW)
    assert result[0].business_state is BusinessState.SOURCE_CHANGED
    assert len(writer.commands) == 1 and writer.commands[0].mpn == "OTHER"


@pytest.mark.parametrize("writer_fails", [False, True])
def test_unconfirmed_click_and_status_failure_do_not_block_next_order(tmp_path, writer_fails):
    from src.launcher.purchase_completion import PurchaseCompletionActions
    from src.workflow.v12_contracts import PurchaseDraftResult
    f, ws, vs, _research, _checker, _facts, _writer, _worker = _make_flow(tmp_path,
        facts=ResearchBusinessFacts("货少", Decimal(10), Decimal(2)))
    first, second = rows()
    second = replace(second, model="OTHER", record_identity=replace(second.record_identity,
        identifying_snapshot=replace(second.record_identity.identifying_snapshot, model="OTHER")))
    reader = FakeSheetsReader()
    sheet_rows = [reader.row, WorksheetRow(4, {**reader.row.cells, "E": "OTHER"})]
    writes = []
    def write(_sheet, position):
        writes.append(position)
        if writer_fails:
            raise RuntimeError("synthetic status failure")
        index = next(i for i, r in enumerate(sheet_rows) if r.row_position == position)
        sheet_rows[index] = WorksheetRow(position, {**sheet_rows[index].cells, "A": "发给采购"})
    sheet = SimpleNamespace(read_rows=lambda _s: tuple(sheet_rows), write_purchase_status=write)
    handler = PurchaseCompletionActions(workflow_store=ws, v12_store=vs, reader=sheet, writer_factory=lambda: sheet)
    f._on_result = lambda result: handler.process(result, at=NOW)
    clicks = []
    def prepare(command):
        vs.set_purchase_state(command.inquiry_id, command.command_id, PurchaseOutcome.AI_RECOGNIZED, at=NOW)
        vs.begin_save_dispatch(command.inquiry_id, at=NOW, save_and_send=True)
        clicks.append(command.inquiry_id)  # Synthetic native successful-click receipt.
        vs.record_submit_click(command.inquiry_id, at=NOW)
        vs.mark_submit_unconfirmed(command.inquiry_id, at=NOW)
        return PurchaseDraftResult(command.command_id, PurchaseOutcome.SUBMIT_UNCONFIRMED, NOW)
    f._purchase_writer = SimpleNamespace(prepare=prepare)
    result = f.process_pending((first, second), now=NOW)
    assert len(result) == 2 and len(clicks) == 2 and writes == [3, 4]
    assert len(set(clicks)) == 2
    assert all(vs.purchase_state(r.inquiry_id) is PurchaseOutcome.SUBMIT_UNCONFIRMED for r in result)
    assert all(vs.business_state(r.inquiry_id) is
        (BusinessState.STATUS_WRITE_PENDING if writer_fails else BusinessState.SUBMIT_UNCONFIRMED) for r in result)
    f.process_pending((first, second), now=NOW)
    assert len(clicks) == 2 and writes == [3, 4]


@pytest.mark.parametrize("successful_attempt", [1, 2, 3, 4, None])
def test_research_inso_history_retry_is_bounded_and_does_not_treat_failure_as_empty(tmp_path, monkeypatch, successful_attempt):
    from src.research.source_contracts import ResearchSource, SourceOutcome
    from tests.research.test_aggregation_service import _result
    backend = ProductionBackend(root=tmp_path)
    events = []
    attempts = []
    backend._stop = SimpleNamespace(wait=lambda seconds: events.append(seconds) or False)
    monkeypatch.setattr(backend, "_close_inso_order_tab", lambda: events.append("close"))
    monkeypatch.setattr(backend, "_begin_inso_inquiry", lambda _iid: events.append("fresh"))
    def operation():
        attempts.append(1)
        return _result(ResearchSource.INSO,
            SourceOutcome.NO_VALID_PRICE if len(attempts) == successful_attempt else SourceOutcome.SOURCE_UNAVAILABLE)
    if successful_attempt is None:
        with pytest.raises(V12Fault) as error:
            backend._run_inso_query("synthetic", operation, lambda: events.append("prepare"))
        assert error.value.scope is FaultScope.GLOBAL_STOP
    else:
        result = backend._run_inso_query("synthetic", operation, lambda: events.append("prepare"))
        assert result.outcome is SourceOutcome.NO_VALID_PRICE
    assert len(attempts) == (successful_attempt or 4)
    assert events.count(180) == (successful_attempt or 4) - 1
    assert events.count("fresh") == events.count("prepare") == events.count(180)


def test_owned_tab_cleanup_error_cannot_lose_post_dispatch_result(monkeypatch):
    from src.launcher.backend import _LivePurchaseDraftWriter
    from src.workflow.v12_contracts import PurchaseDraftResult
    from tests.launcher.test_backend import _purchase_command
    def close():
        raise TimeoutError("synthetic cleanup")
    writer = _LivePurchaseDraftWriter(lambda: SimpleNamespace(close_owned_operation_tab=close),
        store=SimpleNamespace(event_history=lambda _iid: [SimpleNamespace(event_type=EventType.SAVE_DISPATCH_ARMED)]))
    expected = PurchaseDraftResult("synthetic", PurchaseOutcome.SUBMIT_UNCONFIRMED, NOW)
    monkeypatch.setattr(writer, "_prepare_on_page", lambda *_a: expected)
    assert writer._prepare_once(_purchase_command()) is expected


def test_surface_cleanup_error_cannot_lose_completed_draft(monkeypatch):
    from src.launcher import backend as launcher
    from src.workflow.v12_contracts import PurchaseDraftResult
    from tests.launcher.test_backend import (
        _live_writer,
        _purchase_command,
        _StubOperationPage,
    )
    calls = []
    def dismiss(_self):
        calls.append(1)
        if len(calls) == 2:
            raise TimeoutError("synthetic cleanup")
        return True
    expected = PurchaseDraftResult("synthetic", PurchaseOutcome.AI_RECOGNIZED, NOW)
    monkeypatch.setattr(launcher.InsoPurchaseWriter, "dismiss_order_surface", dismiss)
    monkeypatch.setattr(launcher, "CoordinatorPurchaseDraftWriter",
        lambda **_k: SimpleNamespace(prepare=lambda _cmd: expected))
    monkeypatch.setattr(launcher, "PlaywrightParentProductFields", lambda _form: object())
    assert _live_writer(_StubOperationPage()).prepare(_purchase_command()) is expected


@pytest.mark.parametrize("state", [RunState.GLOBAL_STOP, RunState.MODULE_PAUSED, RunState.MANUAL_REVIEW])
def test_final_release_after_manual_pause_detaches_only_and_preserves_active_human_page(tmp_path, state):
    from src.launcher.browser_bootstrap import BrowserHandle
    backend = ProductionBackend(root=tmp_path)
    calls = []
    backend._state = state
    backend._research_ready = True
    backend._browser_handle = BrowserHandle(owned=False,
        playwright=SimpleNamespace(stop=lambda: calls.append("disconnect")),
        browser=SimpleNamespace(close=lambda: calls.append("chrome-close")))
    backend._inso_session = SimpleNamespace(close_after_drain=lambda: calls.append("page-close"))
    backend._release_idle_browser(force=True)
    assert calls == ["disconnect"]
    backend.shutdown()


def test_human_completion_clears_red_even_without_an_active_alert(tmp_path):
    from src.gui.contracts import Order, OrderStatus, V12BusinessLabel, V12OrderStateDTO
    row = Order("synthetic", "MODEL", "Brand", 1, "待验证", None, None, OrderStatus.ERROR)
    dto = V12OrderStateDTO("synthetic", V12BusinessLabel.HUMAN_COMPLETED, None)
    assert _order_row_style(row, v12_state=dto) == "legacy"


@pytest.mark.parametrize("outcome", [PurchaseOutcome.UNKNOWN_WRITE_OUTCOME,
    PurchaseOutcome.MANUAL_REVIEW, PurchaseOutcome.READ_ONLY_RECONCILIATION_REQUIRED])
def test_legacy_unproven_submit_exception_is_unfinished_and_quarantined(tmp_path, outcome):
    from src.workflow.v12_contracts import interrupted_business_state
    assert interrupted_business_state(BusinessState.PURCHASE_EXCEPTION, outcome, True) is BusinessState.INTERRUPTED_POSSIBLY_SENT
    assert interrupted_business_state(BusinessState.PURCHASE_EXCEPTION, PurchaseOutcome.VALIDATION_FAILED, False) is None
    backend = ProductionBackend(root=tmp_path)
    backend._v12_store = SimpleNamespace(business_state=lambda _iid: BusinessState.PURCHASE_EXCEPTION,
        purchase_state=lambda _iid: outcome)
    assert not backend._business_completed("synthetic")
    backend._v12_store = None
    backend.shutdown()


def _b1_batch():
    first = rows()[0]
    return tuple(replace(first, model=f"B1-{offset}", row_position=3 + offset,
        record_identity=replace(first.record_identity, row_position=3 + offset,
            identifying_snapshot=replace(first.record_identity.identifying_snapshot, model=f"B1-{offset}")))
        for offset in range(3))


@pytest.mark.parametrize("during_cooldown", [False, True])
def test_b1_three_row_restart_preserves_untouched_rows_and_source_order(tmp_path, during_cooldown):
    from src.launcher.v12_gui import read_startup_interruptions
    batch = _b1_batch()
    flow, ws, vs, research, checker, *_rest = _make_flow(tmp_path)
    if during_cooldown:
        research.execute = lambda item: ResearchResult(item.inquiry_id, ResearchStatus.EXCEPTION)
        flow._row_wait = lambda seconds: seconds == 180  # Exit while waiting; no real sleep.
        assert len(flow.process_pending(batch, now=NOW)) == 1
    else:
        def interrupted(*_a, **_k):
            raise V12Fault(FaultScope.V12_PAUSE, "synthetic active query interruption")
        checker.check = interrupted
        with pytest.raises(V12Fault):
            flow.process_pending(batch, now=NOW)
    ids = [ws.inquiry_id_for(record.record_identity) for record in batch]
    assert len(ws.all_items()) == 3
    assert all(ws.get_by_inquiry_id(iid).attempt_count == 0 for iid in ids[1:])
    assert all(vs.business_state(iid) is BusinessState.DUPLICATE_CHECK_PENDING for iid in ids[1:])
    assert all([e.event_type for e in vs.event_history(iid)] == [EventType.DUPLICATE_CHECK_STARTED] for iid in ids[1:])
    preview = read_startup_interruptions(vs.database_path)
    assert not any(iid in preview for iid in ids[1:]), "idle GUI must not mark untouched rows red"
    restarted, ws, vs, _research, *_rest = _make_flow(tmp_path)
    restarted.initialize_run_state(now=NOW)
    expected = BusinessState.RESEARCH_FAILED if during_cooldown else BusinessState.INTERRUPTED_UNSENT
    assert vs.business_state(ids[0]) is expected
    assert all(ws.get_by_inquiry_id(iid).status.value == "QUEUED" for iid in ids[1:])
    if not during_cooldown:
        assert ws.get_by_inquiry_id(ids[0]).status.value == "MANUAL_REVIEW"
        assert _order_row_style(SimpleNamespace(status=SimpleNamespace(value=""), processed_at=None),
            NOW, read_v12_order_state(vs, ids[0])) == "error"
    execution = []
    restarted._research.execute = lambda item: execution.append(item.mpn) or ResearchResult(item.inquiry_id, ResearchStatus.EXCEPTION)
    restarted._row_wait = lambda seconds: execution.append(seconds) or False
    result = restarted.process_pending(batch, now=NOW)
    assert [row.inquiry_id for row in result] == ids[1:]
    assert execution == ["B1-1", 180, "B1-2"]
    assert vs.business_state(ids[0]) is expected


@pytest.mark.parametrize("evidence", ["claim", "research-event", "armed", "clicked", "unknown", "reconciliation", "manual"])
def test_b1_real_execution_evidence_is_still_quarantined_without_active_business_state(tmp_path, evidence):
    from src.launcher.v12_gui import read_startup_interruptions
    from src.workflow.v12_contracts import WorkflowEvent
    flow, ws, vs, research, *_rest = _make_flow(tmp_path)
    row = rows()[0]
    ws.enqueue(row, now=NOW)
    iid = ws.inquiry_id_for(row.record_identity)
    if evidence == "claim":
        ws.claim_due(now=NOW)
    elif evidence in {"research-event", "armed", "clicked"}:
        event = {"research-event": EventType.RESEARCH_STARTED,
            "armed": EventType.SAVE_DISPATCH_ARMED, "clicked": EventType.SAVE_CLICK_COMPLETED}[evidence]
        vs.append_event(WorkflowEvent("synthetic-event", iid, event, NOW, "workflow"))
    else:
        vs.set_purchase_state(iid, "synthetic-cmd", PurchaseOutcome.PRE_SAVE_READY, at=NOW)
        vs.set_purchase_state(iid, "synthetic-cmd", PurchaseOutcome.AI_RECOGNIZED, at=NOW)
        vs.begin_save_dispatch(iid, at=NOW)  # Ledger only; no action/transport.
        if evidence == "reconciliation":
            def crash(_iid):
                raise SystemExit("synthetic reconciliation interruption")
            with pytest.raises(SystemExit):
                vs.reconcile_unknown_save(iid, SimpleNamespace(reconcile=crash), at=NOW)
        elif evidence == "manual":
            vs.reconcile_unknown_save(iid, SimpleNamespace(reconcile=lambda _iid:
                ReconciliationResult(ReconciliationOutcome.UNKNOWN, NOW)), at=NOW)
    expected = (BusinessState.INTERRUPTED_UNSENT if evidence in {"claim", "research-event"}
        else BusinessState.INTERRUPTED_POSSIBLY_SENT)
    assert read_startup_interruptions(vs.database_path)[iid][0].business_label.value == business_label_for_state(expected).value
    flow.initialize_run_state(now=NOW)
    assert vs.business_state(iid) is expected
    assert flow.process_pending((row,), now=NOW) == () and research.inputs == []


@pytest.mark.parametrize("state", list(CLOSED_BUSINESS_STATES))
def test_b1_closed_business_states_are_not_quarantined(state):
    from src.workflow.v12_contracts import interrupted_business_state
    assert interrupted_business_state(state, None, False, execution_started=True) is None
