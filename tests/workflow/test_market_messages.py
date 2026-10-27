"""Immutable port validation only; never a browser/business parallel proof."""
from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime

import pytest

from src.research.market_contracts import (
    MarketReadMode,
    MarketReadQuery,
    MarketReadResult,
)
from src.research.source_contracts import (
    EvidenceField,
    ResearchSource,
    SourceEvidence,
    SourceOutcome,
    SourceResult,
)
from src.sheets.pending import (
    IdentifyingSnapshot,
    SheetRecordIdentity,
    WorksheetIdentity,
)
from src.workflow.market_messages import (
    MarketCompletion,
    MarketFault,
    MarketFaultScope,
    MarketModule,
    MarketProgress,
    MarketReadRequest,
    MarketStage,
    MarketTaskIdentity,
    MarketTerminal,
)


def request():
    source = SheetRecordIdentity(WorksheetIdentity('synthetic', '2026'), 43,
                                IdentifyingSnapshot('pending', None, 'SYNTHETIC-MPN', None, 10))
    identity = MarketTaskIdentity(MarketModule.TP, 'synthetic-cycle', 'request-1', 'tp-real-domain-id', source)
    query = MarketReadQuery(ResearchSource.HQEW, MarketReadMode.TP_OFFERS, 'SYNTHETIC-MPN', 10,
                            datetime(2026, 10, 27, tzinfo=UTC))
    return MarketReadRequest(identity, query, 0, 10)


def test_original_identity_reused_and_sensitive_fields_not_in_repr():
    item = request()
    assert item.identity.source_record.worksheet.worksheet == '2026'
    assert 'SYNTHETIC-MPN' not in repr(item)
    assert 'tp-real-domain-id' not in repr(item)
    with pytest.raises(FrozenInstanceError):
        item.identity.module = MarketModule.QUOTATION
    with pytest.raises(FrozenInstanceError):
        item.query.quantity = 20
    assert replace(item.identity, module=MarketModule.INQUIRY).source_record is item.identity.source_record


@pytest.mark.parametrize('changes', [{'version': 2}, {'version': True}, {'request_id': 'bad / path'},
                                    {'source_record': object()}, {'domain_task_id': ''}])
def test_invalid_identity_rejected(changes):
    with pytest.raises(ValueError):
        replace(request().identity, **changes)


@pytest.mark.parametrize('changes', [{'quantity': True}, {'quantity': 0}, {'mpn': ''},
                                    {'source': ResearchSource.INSO}, {'source': 'hqew'},
                                    {'reference_at': datetime(2026, 10, 27)},  # noqa: DTZ001 - rejection fixture
                                     {'mode': 'ordinary'}])
def test_invalid_or_protected_query_rejected(changes):
    with pytest.raises(ValueError):
        replace(request().query, **changes)


def test_terminal_outcomes_cannot_hide_resource_fault_or_include_mutable_payload():
    item = request()
    fault = MarketFault(MarketFaultScope.GLOBAL_STOP, 'CDP_PAGE_OWNERSHIP_UNCONFIRMED', ('ValueError',))
    message = MarketCompletion(item.identity, MarketTerminal.FAILED, 1, 2, fault=fault)
    assert message.fault.reason == 'CDP_PAGE_OWNERSHIP_UNCONFIRMED'
    with pytest.raises(ValueError):
        replace(fault, scope=MarketFaultScope.FAILED)
    with pytest.raises(ValueError):
        replace(message, terminal=MarketTerminal.SUCCEEDED)
    with pytest.raises(ValueError):
        replace(message, finished_at=0)
    with pytest.raises(ValueError):
        MarketFault(MarketFaultScope.FAILED, 'PAGE_TEXT_FROM_WEBSITE')
    with pytest.raises(ValueError):
        replace(fault, exception_classes=['ValueError'])
    assert MarketCompletion(item.identity, MarketTerminal.CANCELLED, 1, 1).result is None


def test_only_canonical_deeply_immutable_source_results_cross_port():
    item = request()
    evidence = SourceEvidence(ResearchSource.HQEW, item.query.mpn, None,
                              SourceOutcome.NO_VALID_PRICE, item.query.reference_at)
    source = SourceResult(ResearchSource.HQEW, SourceOutcome.NO_VALID_PRICE, evidence)
    result = MarketReadResult(ResearchSource.HQEW, MarketReadMode.ORDINARY, ordinary=source)
    assert result.ordinary is source
    with pytest.raises(ValueError):
        replace(result, source=ResearchSource.LCSC)
    contaminated = replace(source, evidence=replace(evidence, fields=(EvidenceField('unsafe', {}),)))
    with pytest.raises(ValueError):
        replace(result, ordinary=contaminated)
    with pytest.raises(ValueError):
        MarketReadResult(ResearchSource.HQEW, MarketReadMode.TP_OFFERS, offers=[])
    with pytest.raises(ValueError):
        MarketProgress(item.identity, 'unbounded free-text stage', 1)
    assert MarketProgress(item.identity, MarketStage.READING, 1).stage is MarketStage.READING



def test_ordinary_module_cannot_silently_use_tp_month_selection_profile():
    item = request()
    with pytest.raises(ValueError, match='MARKET_MODULE_QUERY_MODE_MISMATCH'):
        replace(item, identity=replace(item.identity, module=MarketModule.QUOTATION))
