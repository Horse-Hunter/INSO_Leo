from __future__ import annotations

import logging
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import ClassVar

import pytest

from src.inso import (
    AiRecognitionResult,
    ParentProductFields,
    PlaywrightParentProductFields,
)
from src.launcher.v12_composition import (
    CoordinatorPurchaseDraftWriter,
    PlaywrightReadOnlySaveReconciler,
    ResearchExcelFactsProvider,
    SaveReconciliationTarget,
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
from src.workflow.v12_store import ReadOnlySaveReconciler


class _DuplicateChecker:
    pass


class _ResearchFacts:
    pass


class _PrepareActions:
    def __init__(self, *, preview=None):
        self.preview = preview or ("", "LM358", "Texas Instruments", 123, True)
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

    def commit_ai_entry(self):
        self.calls.append(("commit_ai",))


class _ParentFields:
    """Read-only stand-in for the row the ERP renders into the 采购临时询价 grid.

    There is no setter by design: the automation must not type 编码/型号/品牌/数量
    into the operator's bill. ``rendered`` is what the ERP's own ``ai_appendRow``
    put there.
    """

    def __init__(self, *, readback=None, rendered=None):
        self.values = rendered or {
            "product_id": "P216328",
            "model": "LM358",
            "brand": "Texas Instruments",
            "quantity": 123,
        }
        self.readback = readback
        self.calls: list[tuple] = []

    def wait_for_model(self, expected_model, timeout_seconds):
        self.calls.append(("wait_for_model", expected_model))
        return self.values["model"] == expected_model

    def read_product_id(self):
        raise AssertionError("ProductID must not participate in production validation")

    def read_model(self):
        return self.readback[1] if self.readback else self.values["model"]

    def read_brand(self):
        return self.readback[2] if self.readback else self.values["brand"]

    def read_quantity(self):
        return self.readback[3] if self.readback else self.values["quantity"]


class _LateParentFields(_ParentFields):
    """``ai_appendRow`` never rendered our model inside the wait budget."""

    def wait_for_model(self, expected_model, timeout_seconds):
        self.calls.append(("wait_for_model", expected_model))
        return False


class _UnreadableParentFields(_ParentFields):
    """The model row rendered, but its business-field read-back failed."""

    def read_model(self):
        raise ValueError("synthetic unreadable parent model")


class _FailingCommitActions(_PrepareActions):
    """The 保存数据 commit itself never landed."""

    def commit_ai_entry(self):
        self.calls.append(("commit_ai",))
        raise TimeoutError("the 保存数据 control never became visible")


class _Transport:
    def send_one(self, *_args):
        return NotificationTransportResult(DeliveryOutcome.UNKNOWN)


class _Reconciler(ReadOnlySaveReconciler):
    def reconcile(self, _inquiry_id):
        raise AssertionError("not exercised by composition")


class _DetailLocator:
    def __init__(self, values, selector):
        self.values = values
        self.selector = selector

    def count(self):
        return 1 if self.selector in self.values else 0

    def is_visible(self):
        return True

    def input_value(self):
        value = self.values[self.selector]
        if self.selector.startswith("#_id_dg"):
            raise RuntimeError("detail cell")
        return value

    def inner_text(self):
        return self.values[self.selector]


class _DetailFrame:
    def __init__(self, values):
        self.values = values

    def locator(self, selector):
        return _DetailLocator(self.values, selector)


class _Access:
    def __init__(self, frame):
        self.frame = frame

    def operation_page(self):
        class _Operation:
            def __init__(self, frame):
                self.shell_frame = frame

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return None

        return _Operation(self.frame)


class _History:
    rows: ClassVar[list[dict[str, str]]] = []
    matched: ClassVar[bool] = True
    complete: ClassVar[bool] = True
    error: ClassVar[BaseException | None] = None

    def __init__(self, *_args, **_kwargs):
        pass

    @property
    def last_exact_request_matched(self):
        return self.matched

    @property
    def last_exact_result_set_complete(self):
        return self.complete

    def query_exact_response(self, _mpn):
        if self.error:
            raise self.error
        return {"rows": self.rows}

    def click(self, _selector):
        return None


def _live_reconciler(
    monkeypatch, *, rows, details, matched=True, complete=True, error=None
):
    import src.launcher.v12_composition as composition

    _History.rows = rows
    _History.matched = matched
    _History.complete = complete
    _History.error = error
    monkeypatch.setattr(composition, "PlaywrightDuplicateHistoryPage", _History)
    return PlaywrightReadOnlySaveReconciler(
        operation_access=_Access(_DetailFrame(details)),
        target_for_inquiry=lambda _inquiry: SaveReconciliationTarget("LM358", "Texas Instruments", 123),
        clock=lambda: datetime(2026, 9, 28, tzinfo=UTC),
    )


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
        _Reconciler(),
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
    assert isinstance(composition.save_reconciler, _Reconciler)


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
            _Reconciler(),
        )


def test_production_requires_a_read_only_save_reconciler() -> None:
    with pytest.raises(TypeError, match="read-only save reconciler"):
        V12ProductionAdapters(
            _DuplicateChecker(), _ResearchFacts(), _purchase_writer(), _Transport(),
            (NotificationRecipient("owner", "owner@example.invalid"),), None,
        )


def _saved_detail(*, bill_id="42", mpn="LM358", brand="Texas Instruments", qty="123"):
    return {
        "#BillID": bill_id,
        "#PENO": "PENO-1",
        '#_id_dg td[data-field="PartNo"]': mpn,
        '#_id_dg td[data-field="Brand"]': brand,
        '#_id_dg td[data-field="Qty"]': qty,
    }


def test_save_reconciler_confirms_one_exact_saved_record(monkeypatch) -> None:
    result = _live_reconciler(
        monkeypatch, rows=[{"BillID": "42"}], details=_saved_detail()
    ).reconcile("inq-1")

    assert result.outcome is ReconciliationOutcome.CONFIRMED_SAVED
    assert result.saved_record_ref == "rec_7ae5535a91b87c3286427ddf141d5870"
    assert result.candidate_count == 1
    assert set(result.verified_fields) >= {"mpn", "brand", "quantity"}


def test_save_reconciler_confirms_authoritative_zero_candidates(monkeypatch) -> None:
    result = _live_reconciler(monkeypatch, rows=[], details={}).reconcile("inq-1")

    assert result.outcome is ReconciliationOutcome.CONFIRMED_NOT_SAVED
    assert result.authoritative is True
    assert result.candidate_count == 0


def test_save_reconciler_never_picks_one_of_multiple_candidates(monkeypatch) -> None:
    result = _live_reconciler(
        monkeypatch, rows=[{"BillID": "42"}, {"BillID": "43"}], details={}
    ).reconcile("inq-1")

    assert result.outcome is ReconciliationOutcome.AMBIGUOUS
    assert result.candidate_count == 2


@pytest.mark.parametrize(
    ("rows", "details"),
    (
        ([{"BillID": "42"}], _saved_detail(mpn="LM358X")),
        ([{"BillID": "42"}], _saved_detail(brand="Other")),
        ([{"BillID": "42"}], _saved_detail(qty="124")),
        ([{"BillID": "42"}], _saved_detail(bill_id="")),
    ),
)
def test_save_reconciler_mismatch_or_missing_stable_id_is_not_saved(monkeypatch, rows, details) -> None:
    result = _live_reconciler(monkeypatch, rows=rows, details=details).reconcile("inq-1")

    assert result.outcome is not ReconciliationOutcome.CONFIRMED_SAVED


def test_save_reconciler_query_or_settlement_failure_is_unknown(monkeypatch) -> None:
    result = _live_reconciler(
        monkeypatch, rows=[], details={}, error=RuntimeError("query failed")
    ).reconcile("inq-1")
    settlement = _live_reconciler(
        monkeypatch, rows=[], details={}, matched=False
    ).reconcile("inq-1")

    assert result.outcome is ReconciliationOutcome.UNKNOWN
    assert settlement.outcome is ReconciliationOutcome.UNKNOWN


@pytest.mark.parametrize("rows", ([], [{"BillID": "42"}]))
def test_save_reconciler_requires_a_complete_candidate_set(monkeypatch, rows) -> None:
    result = _live_reconciler(
        monkeypatch,
        rows=rows,
        details=_saved_detail(),
        complete=False,
    ).reconcile("inq-1")

    assert result.outcome is ReconciliationOutcome.UNKNOWN
    assert result.authoritative is False


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
        save_reconciler=_Reconciler(),
    )

    assert isinstance(adapters.notification_transport, QQSMTPTransport)
    assert adapters.notification_transport._config.sender_address == "sender@example.invalid"


def test_prepare_ai_mismatch_does_not_touch_parent_product_fields() -> None:
    actions = _PrepareActions(preview=("P216328", "LM358X", "Texas Instruments", 123, True))
    parent = _ParentFields()

    result = _purchase_writer(actions, parent).prepare(_command())

    assert result.outcome is PurchaseOutcome.VALIDATION_FAILED
    assert parent.calls == []


def test_prepare_lets_the_erp_fill_the_row_then_reads_it_back() -> None:
    actions = _PrepareActions()
    parent = _ParentFields()
    writer = _purchase_writer(actions, parent)

    result = writer.prepare(_command())

    assert result.outcome is PurchaseOutcome.AI_RECOGNIZED
    # The row is handed back by the ERP; the seam only waits for it and reads it.
    assert parent.calls == [("wait_for_model", "LM358")]
    assert actions.calls == [
        ("new_draft",),
        ("customer", "Win Source Elec. Tech. Ltd"),
        ("quotation_type", "需要问全价格"),
        ("purchaser", "颜浩坚"),
        ("open_ai",),
        ("ai_input", _command().ai_input),
        ("recognize",),
        ("read_preview",),
        ("commit_ai",),
    ]
    assert not hasattr(writer, "save_data")


def test_parent_product_fields_expose_no_way_to_type_into_the_bill() -> None:
    """The 采购临时询价 form is the operator's; we must not fill its product row.

    The ERP fills it itself when the AI录单 panel commits (``pasteImport`` ->
    ``ai_appendRow``). A seam that could write those cells is the process defect
    this guards against, so the capability must not exist at all.
    """

    for name in ("set_product_id", "set_model", "set_brand", "set_quantity"):
        assert not hasattr(PlaywrightParentProductFields, name)
        assert not hasattr(ParentProductFields, name)


def test_prepare_commits_the_ai_panel_before_reading_the_parent_grid() -> None:
    """The recognized row only reaches the grid through the panel's own commit."""

    order: list[str] = []

    class _OrderedActions(_PrepareActions):
        def read_ai_result(self):
            order.append("read_preview")
            return super().read_ai_result()

        def commit_ai_entry(self):
            order.append("commit_ai")
            super().commit_ai_entry()

    class _OrderedParentFields(_ParentFields):
        def wait_for_model(self, expected_model, timeout_seconds):
            order.append("wait_for_model")
            return super().wait_for_model(expected_model, timeout_seconds)

    result = _purchase_writer(
        _OrderedActions(), _OrderedParentFields()
    ).prepare(_command())

    assert result.outcome is PurchaseOutcome.AI_RECOGNIZED
    assert order == ["read_preview", "commit_ai", "wait_for_model"]


def test_prepare_never_commits_when_the_preview_mismatches() -> None:
    """A mismatched recognition must not be handed to the bill at all."""

    actions = _PrepareActions(preview=("P216328", "LM358X", "Texas Instruments", 123, True))

    result = _purchase_writer(actions).prepare(_command())

    assert result.outcome is PurchaseOutcome.VALIDATION_FAILED
    assert ("commit_ai",) not in actions.calls


@pytest.mark.parametrize("readback", [
    ("", "LM358X", "Texas Instruments", 123),
    ("", "LM358", "Wrong Brand", 123),
    ("", "LM358", "Texas Instruments", 124),
])
def test_prepare_parent_readback_mismatch_fails_validation(readback) -> None:
    parent = _ParentFields(readback=readback)

    result = _purchase_writer(parent=parent).prepare(_command())

    assert result.outcome is PurchaseOutcome.VALIDATION_FAILED


def test_prepare_row_that_never_arrives_fails_closed() -> None:
    """``ai_appendRow`` reloads the grid asynchronously, so the wait is a gate.

    A row whose model arrives only after the budget expired is not a rendered row:
    the leg must fail rather than treat the commit click as sufficient.
    """

    parent = _LateParentFields()

    result = _purchase_writer(parent=parent).prepare(_command())

    assert result.outcome is PurchaseOutcome.VALIDATION_FAILED
    assert parent.calls == [("wait_for_model", "LM358")]


@pytest.mark.parametrize("product_id", ["", "P999999"])
def test_prepare_ignores_parent_product_code_when_business_fields_match(product_id) -> None:
    parent = _ParentFields(
        rendered={
            "product_id": product_id,
            "model": "LM358",
            "brand": "Texas Instruments",
            "quantity": 123,
        }
    )

    result = _purchase_writer(parent=parent).prepare(_command())

    assert result.outcome is PurchaseOutcome.AI_RECOGNIZED
    assert parent.calls == [("wait_for_model", "LM358")]


def _purchase_steps(caplog) -> list[tuple[str, str | None]]:
    return [
        (record.inso_step, record.inso_cause)
        for record in caplog.records
        if record.name == "inso.diagnostics"
    ]


@pytest.mark.parametrize(
    ("actions", "parent", "expected_step", "expected_cause"),
    [
        (_FailingCommitActions, _ParentFields, "commit-ai-entry", "TimeoutError"),
        (_PrepareActions, _LateParentFields, "parent-row-missing", None),
        (_PrepareActions, _UnreadableParentFields, "parent-read", "ValueError"),
    ],
)
def test_prepare_failure_names_the_step_that_died(
    caplog, actions, parent, expected_step, expected_cause
) -> None:
    """``CONTROL_NOT_FOUND`` is one code for four different failure sites.

    The AI panel, the panel's own commit, the ERP's grid reload and the
    launcher's surface dismissal all surface the same reason code, so the step
    label is the only thing that says where a draft actually died -- and it is
    the one thing the operator-visible alert can never carry.
    """

    with caplog.at_level(logging.WARNING, logger="inso.diagnostics"):
        result = _purchase_writer(actions(), parent()).prepare(_command())

    assert result.outcome is PurchaseOutcome.VALIDATION_FAILED
    assert _purchase_steps(caplog) == [(expected_step, expected_cause)]


def test_prepare_ai_mismatch_reports_no_step_because_none_was_reached(caplog) -> None:
    """A recognition that never matched is its own reason code, not a lost control."""

    actions = _PrepareActions(preview=("P216328", "LM358X", "Texas Instruments", 123, True))

    with caplog.at_level(logging.WARNING, logger="inso.diagnostics"):
        result = _purchase_writer(actions).prepare(_command())

    assert result.outcome is PurchaseOutcome.VALIDATION_FAILED
    assert _purchase_steps(caplog) == []


def test_prepare_source_has_no_ai_import_footer_selector_or_save_send_path() -> None:
    source = Path("src/launcher/v12_composition.py").read_text(encoding="utf-8")

    assert "win_btn__dialog11" not in source
    assert "save_data(" not in source
    assert "SAVE_AND_SEND" not in source
