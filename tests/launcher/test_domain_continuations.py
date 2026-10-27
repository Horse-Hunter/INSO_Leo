"""Canonical domain ports with synthetic source clients and isolated real stores."""
from dataclasses import replace
from decimal import Decimal

import pytest

from src.launcher.market_actors import MarketReadActors
from src.launcher.market_continuation import OwnerMarketResearch
from src.research.cdp_pages import PageResourceAdmission
from src.research.source_contracts import ResearchSource as S
from src.research.source_contracts import SourceOutcome
from src.sheets.brand_write import SheetRecordConflict
from src.sheets.pending import identify_worksheet_row, query_pending_records
from src.workflow.market_messages import (
    BusinessResearchCompletion,
    MarketModule,
    MarketTaskIdentity,
)
from src.workflow.service import WorkflowRuntime
from src.workflow.v12_contracts import BusinessState
from src.workflow.v12_flow import ResearchBusinessFacts
from src.workflow.v13_quotation import QuotationOutcome, V13SourceRowError
from tests.inso.test_v13_quotation_read import quote
from tests.launcher.test_tp_continuation import run_research
from tests.research.test_aggregation_service import _complete, _result, _service
from tests.workflow.test_business_continuation import runtime as isolated_runtime
from tests.workflow.test_rfq006_integration import fixture as quote_fixture
from tests.workflow.test_v12_flow import NOW, SHEET, FakeSheetsReader, _make_flow
from tests.workflow.test_v13_quotation import WS


def inquiry_fixture(tmp_path):
    flow, store, ledger, _, checker, _, writer, _ = _make_flow(tmp_path,
        facts=ResearchBusinessFacts('货少', Decimal(14), Decimal(2)))
    values = _complete({S.HQEW: _result(S.HQEW, SourceOutcome.SUCCESS, '2')})
    def service():
        return _service(tmp_path / 'synthetic.xlsx', values)
    flow._research = service()
    class Session:
        def __init__(self, config, admission):
            self.service = service()  # actor creates its own service, no shared object
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def read(self, query):
            return self.service.read_market_source(query)
    runtime = WorkflowRuntime(None, None, ())
    runtime.configure_modules({'inquiry': 900, 'quotation': 900, 'tp': 900})
    actors = MarketReadActors(runtime, None, PageResourceAdmission(), session_type=Session)
    actors.start()
    reader = FakeSheetsReader()
    record, = query_pending_records(reader, SHEET)
    identity = MarketTaskIdentity(MarketModule.INQUIRY, 'inquiry-cycle', 'inquiry-transaction',
        store.inquiry_id_for(record.record_identity), record.record_identity)
    return flow, store, ledger, checker, writer, reader, record, identity, runtime, actors


def test_inquiry_actor_to_original_duplicate_and_purchase_route(tmp_path):
    flow, store, _, checker, writer, reader, record, identity, runtime, actors = inquiry_fixture(tmp_path)
    try:
        work = flow.begin_continuation(record, identity, runtime, reader, now=NOW)
        assert checker.calls and store.get_by_inquiry_id(identity.domain_task_id).status.value == 'RESEARCHING'
        driver = OwnerMarketResearch(runtime, actors, work.lease, work.research, due_at=0)
        completion = run_research(driver, actors)
        other = replace(identity, module=MarketModule.TP, request_id='tp-transaction', domain_task_id='tp_existing')
        assert runtime.claim_business_continuation(other) is None
        result = work.complete(completion)
        assert result.inquiry_id == identity.domain_task_id
        assert writer.commands and len(writer.commands) == 1
        assert runtime.business_resource_counts()['active'] == 0
        assert store.get_by_inquiry_id(identity.domain_task_id).status.value == 'COMPLETED'
        assert runtime.claim_business_continuation(other) is not None
    finally:
        assert actors.close()


def test_inquiry_changed_source_and_stale_cycle_never_purchase(tmp_path):
    flow, _, ledger, _, writer, reader, record, identity, runtime, actors = inquiry_fixture(tmp_path)
    try:
        work = flow.begin_continuation(record, identity, runtime, reader, now=NOW)
        completion = run_research(OwnerMarketResearch(runtime, actors, work.lease, work.research, due_at=0), actors)
        with pytest.raises(ValueError, match='RESULT_MISMATCH'):
            work.complete(BusinessResearchCompletion(replace(identity, cycle_id='old-cycle'), completion.result))
        reader.row = replace(reader.row, cells={**reader.row.cells, 'G': 999})
        with pytest.raises(SheetRecordConflict):
            work.complete(completion)
        assert ledger.business_state(identity.domain_task_id) is BusinessState.SOURCE_CHANGED
        assert not writer.commands and runtime.business_resource_counts()['active'] == 0
    finally:
        assert actors.close()


def test_inquiry_preserves_original_120_second_closed_row_wait(tmp_path):
    flow, _, _, _, _, reader, record, identity, runtime, actors = inquiry_fixture(tmp_path)
    try:
        waits = []
        flow._row_closed = True
        flow._row_wait = lambda seconds: waits.append(seconds) or False
        work = flow.begin_continuation(record, identity, runtime, reader, now=NOW)
        assert waits == [120]
        work.cancel()
    finally:
        assert actors.close()


def test_quotation_original_owner_query_closes_then_guarded_settlement(tmp_path):
    _, _, sheets, _, _, _, make, observed = quote_fixture(tmp_path, [(quote(),)])
    cycle = make()
    records, _, _ = cycle.prepare_run(WS)
    candidate, = cycle.cycle.read_candidates(WS)
    identity = MarketTaskIdentity(MarketModule.QUOTATION, 'quote-cycle', 'quote-transaction',
        candidate.inquiry_id, identify_worksheet_row(WS, sheets.rows[0]))
    runtime = isolated_runtime()
    work = cycle.begin_continuation(candidate, identity, runtime, records)
    completion = work.read_owner()
    assert cycle.cycle._operations.active is None
    assert runtime.business_resource_counts()['active'] == 1
    result = work.complete(completion)
    assert result.outcome is QuotationOutcome.QUOTE_FOUND and observed
    assert runtime.business_resource_counts()['active'] == 0


def test_quotation_identity_change_after_protected_read_blocks_update(tmp_path):
    _, _, sheets, _, _, _, make, _ = quote_fixture(tmp_path, [(quote(),)])
    updates = []
    cycle = make(lambda result: updates.append(result) or result)
    records, _, _ = cycle.prepare_run(WS)
    candidate, = cycle.cycle.read_candidates(WS)
    identity = MarketTaskIdentity(MarketModule.QUOTATION, 'quote-cycle', 'quote-transaction',
        candidate.inquiry_id, identify_worksheet_row(WS, sheets.rows[0]))
    runtime = isolated_runtime()
    work = cycle.begin_continuation(candidate, identity, runtime, records)
    completion = work.read_owner()
    sheets.rows[0] = replace(sheets.rows[0], cells={**sheets.rows[0].cells, 'G': 999})
    with pytest.raises(V13SourceRowError):
        work.complete(completion)
    assert not updates
    work.cancel()
