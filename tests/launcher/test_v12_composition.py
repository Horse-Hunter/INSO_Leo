from __future__ import annotations

from datetime import UTC
from decimal import Decimal

import pytest

from src.launcher.v12_composition import (
    ResearchExcelFactsProvider,
    UnavailableReadOnlySaveReconciler,
    V12ProductionAdapters,
    compose_v12_production,
)
from src.research.excel_output import ResearchExcelOutput
from src.workflow.v12_contracts import (
    DeliveryOutcome,
    NotificationRecipient,
    NotificationTransportResult,
    ReconciliationOutcome,
)
from src.workflow.v12_smtp_transport import QQSMTPConfig, QQSMTPTransport


class _DuplicateChecker:
    pass


class _ResearchFacts:
    pass


class _PurchaseWriter:
    pass


class _Transport:
    def send_one(self, *_args):
        return NotificationTransportResult(DeliveryOutcome.UNKNOWN)


def test_v12_production_composition_uses_explicit_live_seams() -> None:
    workflow_store = object()
    v12_store = object()
    research = object()
    duplicate = _DuplicateChecker()
    facts = _ResearchFacts()
    purchase = _PurchaseWriter()
    transport = _Transport()
    adapters = V12ProductionAdapters(
        duplicate,
        facts,
        purchase,
        transport,
        (NotificationRecipient("owner", "owner@example.invalid"),),
    )

    composition = compose_v12_production(
        workflow_store=workflow_store,
        v12_store=v12_store,
        research=research,
        adapters=adapters,
    )

    assert composition.coordinator._workflow_store is workflow_store
    assert composition.coordinator._v12_store is v12_store
    assert composition.coordinator._research is research
    assert composition.coordinator._duplicate_checker is duplicate
    assert composition.coordinator._research_facts is facts
    assert composition.coordinator._purchase_writer is purchase
    assert composition.coordinator._notification_worker is composition.notification_worker
    assert composition.notification_worker._transport is transport
    assert isinstance(
        composition.save_reconciler, UnavailableReadOnlySaveReconciler
    )


def test_incomplete_v12_live_adapters_fail_closed() -> None:
    with pytest.raises(ValueError, match="adapters are incomplete"):
        V12ProductionAdapters(
            _DuplicateChecker(),
            _ResearchFacts(),
            None,
            _Transport(),
            (NotificationRecipient("owner", "owner@example.invalid"),),
        )


def test_unavailable_save_reader_only_returns_unknown() -> None:
    result = UnavailableReadOnlySaveReconciler().reconcile("synthetic-inquiry")

    assert result.outcome is ReconciliationOutcome.UNKNOWN
    assert result.reconciled_at.tzinfo is UTC
    assert result.authoritative is False
    assert result.candidate_count is None


def test_research_facts_provider_reads_only_persisted_canonical_snapshot(
    tmp_path,
) -> None:
    output = ResearchExcelOutput(tmp_path / "research.xlsx")
    output.upsert(
        "inquiry-1",
        mpn="LM358",
        brand="Texas Instruments",
        quantity=123,
        importance_raw="A",
        stock_label="货足",
        estimated_total=Decimal("1234.56"),
        market_reference="3.14\n4.00-HQEW",
        research_status="SUCCESS",
    )
    provider = ResearchExcelFactsProvider(output)

    facts = provider.get("inquiry-1")

    assert facts is not None
    assert facts.inventory_status == "货足"
    assert facts.estimated_total == Decimal("1234.56")
    assert facts.market_minimum_reference_price == Decimal("3.14")
    assert provider.get("missing") is None


def test_research_facts_provider_preserves_unknown_amounts(tmp_path) -> None:
    output = ResearchExcelOutput(tmp_path / "research.xlsx")
    output.upsert(
        "inquiry-1",
        importance_raw="B",
        stock_label="货少",
        estimated_total=None,
        market_reference=None,
        research_status="SUCCESS",
    )

    facts = ResearchExcelFactsProvider(output).get("inquiry-1")

    assert facts is not None
    assert facts.inventory_status == "货少"
    assert facts.estimated_total is None
    assert facts.market_minimum_reference_price is None


def test_qq_smtp_factory_uses_the_explicit_sender_config() -> None:
    adapters = V12ProductionAdapters.with_qq_smtp(
        duplicate_checker=_DuplicateChecker(),
        research_facts=_ResearchFacts(),
        purchase_writer=_PurchaseWriter(),
        smtp_config=QQSMTPConfig(sender_address="sender@example.invalid"),
        recipients=(NotificationRecipient("owner", "owner@example.invalid"),),
    )

    assert isinstance(adapters.notification_transport, QQSMTPTransport)
    assert adapters.notification_transport._config.sender_address == "sender@example.invalid"
