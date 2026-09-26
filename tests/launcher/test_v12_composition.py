from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from src.inso import AiRecognitionResult
from src.launcher.v12_composition import (
    CoordinatorPurchaseDraftWriter,
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
    PurchaseDraftCommand,
    PurchaseOutcome,
    ReconciliationOutcome,
)
from src.workflow.v12_rules import build_ai_input
from src.workflow.v12_smtp_transport import QQSMTPConfig, QQSMTPTransport


class _DuplicateChecker:
    pass


class _ResearchFacts:
    pass


class _PrepareActions:
    def __init__(self, *, preview=None):
        self.preview = preview or ("LM358", "Texas Instruments", 123, True)
        self.calls: list[tuple] = []

    def new_draft(self):
        self.calls.append(("new_draft",))

    def set_customer(self, value):
        self.calls.append(("customer", value))

    def set_quotation_type(self, value):
        self.calls.append(("quotation_type", value))

    def set_purchaser(self, value):
        self.calls.append(("purchaser", value))

    def open_ai_entry(self):
        self.calls.append(("open_ai",))

    def set_ai_input(self, value):
        self.calls.append(("ai_input", value))

    def run_ai_recognition(self):
        self.calls.append(("recognize",))

    def read_ai_result(self):
        self.calls.append(("read_preview",))
        return AiRecognitionResult(*self.preview)


class _ParentFields:
    def __init__(self, *, readback=None):
        self.values = {"model": None, "brand": None, "quantity": None}
        self.readback = readback
        self.calls: list[tuple] = []

    def set_model(self, value):
        self.calls.append(("set_model", value))
        self.values["model"] = value

    def set_brand(self, value):
        self.calls.append(("set_brand", value))
        self.values["brand"] = value

    def set_quantity(self, value):
        self.calls.append(("set_quantity", value))
        self.values["quantity"] = value

    def read_model(self):
        return self.readback[0] if self.readback else self.values["model"]

    def read_brand(self):
        return self.readback[1] if self.readback else self.values["brand"]

    def read_quantity(self):
        return self.readback[2] if self.readback else self.values["quantity"]


class _Transport:
    def send_one(self, *_args):
        return NotificationTransportResult(DeliveryOutcome.UNKNOWN)


def _command():
    return PurchaseDraftCommand(
        command_id="cmd-1",
        inquiry_id="inquiry-1",
        customer_name="Example Customer",
        customer_tier="A",
        mpn="LM358",
        brand="Texas Instruments",
        quantity=123,
        inventory_status="货足",
        estimated_total=Decimal(1234),
        market_minimum_reference_price=Decimal(1),
        quotation_type="需要问全价格",
        purchaser="颜浩坚",
        ai_input=build_ai_input("LM358", "Texas Instruments", 123),
    )


def _purchase_writer(actions=None, parent=None):
    return CoordinatorPurchaseDraftWriter(
        actions=actions or _PrepareActions(),
        parent_fields=parent or _ParentFields(),
        clock=lambda: datetime(2026, 9, 26, tzinfo=UTC),
    )


def test_v12_production_composition_uses_explicit_live_seams() -> None:
    workflow_store = object()
    v12_store = object()
    research = object()
    duplicate = _DuplicateChecker()
    facts = _ResearchFacts()
    purchase = _purchase_writer()
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
    assert isinstance(composition.save_reconciler, UnavailableReadOnlySaveReconciler)


def test_incomplete_v12_live_adapters_fail_closed() -> None:
    with pytest.raises(ValueError, match="parent product fields"):
        CoordinatorPurchaseDraftWriter(actions=_PrepareActions(), parent_fields=None)

    with pytest.raises(TypeError, match="parent product fields"):
        V12ProductionAdapters(
            _DuplicateChecker(),
            _ResearchFacts(),
            object(),
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
        purchase_writer=_purchase_writer(),
        smtp_config=QQSMTPConfig(sender_address="sender@example.invalid"),
        recipients=(NotificationRecipient("owner", "owner@example.invalid"),),
    )

    assert isinstance(adapters.notification_transport, QQSMTPTransport)
    assert adapters.notification_transport._config.sender_address == "sender@example.invalid"


def test_prepare_ai_mismatch_does_not_touch_parent_product_fields() -> None:
    actions = _PrepareActions(preview=("LM358X", "Texas Instruments", 123, True))
    parent = _ParentFields()

    result = _purchase_writer(actions, parent).prepare(_command())

    assert result.outcome is PurchaseOutcome.VALIDATION_FAILED
    assert parent.calls == []


def test_prepare_ai_match_writes_preview_fields_then_reads_back() -> None:
    actions = _PrepareActions()
    parent = _ParentFields()
    writer = _purchase_writer(actions, parent)

    result = writer.prepare(_command())

    assert result.outcome is PurchaseOutcome.AI_RECOGNIZED
    assert parent.calls == [
        ("set_model", "LM358"),
        ("set_brand", "Texas Instruments"),
        ("set_quantity", 123),
    ]
    assert actions.calls == [
        ("new_draft",),
        ("customer", "Win Source Elec. Tech. Ltd"),
        ("quotation_type", "需要问全价格"),
        ("purchaser", "颜浩坚"),
        ("open_ai",),
        ("ai_input", _command().ai_input),
        ("recognize",),
        ("read_preview",),
    ]
    assert not hasattr(writer, "save_data")


def test_prepare_parent_readback_mismatch_fails_validation() -> None:
    parent = _ParentFields(readback=("LM358", "Wrong Brand", 123))

    result = _purchase_writer(parent=parent).prepare(_command())

    assert result.outcome is PurchaseOutcome.VALIDATION_FAILED


def test_prepare_source_has_no_ai_import_footer_selector_or_save_send_path() -> None:
    source = Path("src/launcher/v12_composition.py").read_text(encoding="utf-8")

    assert "win_btn__dialog11" not in source
    assert "save_data(" not in source
    assert "SAVE_AND_SEND" not in source
