from __future__ import annotations

from datetime import UTC

import pytest

from src.launcher.v12_composition import (
    UnavailableReadOnlySaveReconciler,
    V12ProductionAdapters,
    compose_v12_production,
)
from src.workflow.v12_contracts import (
    DeliveryOutcome,
    NotificationRecipient,
    NotificationTransportResult,
    ReconciliationOutcome,
)


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
