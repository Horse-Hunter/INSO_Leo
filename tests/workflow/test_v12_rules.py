from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from src.workflow.v12_contracts import (
    DuplicateCheckResult,
    DuplicateOutcome,
    PurchaseOutcome,
    ReasonCode,
)
from src.workflow.v12_rules import (
    HistoricalInquiryRecord,
    PostResearchRoute,
    Purchaser,
    PurchaseRoutingOutcome,
    QuotationType,
    build_ai_input,
    duplicate_notification_required,
    evaluate_duplicate_history,
    purchase_routing_decision,
    route_after_research,
    should_send_important_order_notification,
    validate_ai_recognition,
)

NOW = datetime(2026, 9, 25, tzinfo=UTC)


def test_duplicate_rule_exact_match_rolling_window_latest_and_quantity_independent() -> None:
    records = (
        HistoricalInquiryRecord("ABC-123", NOW, 2, "older", Decimal(3), "CNY"),
        HistoricalInquiryRecord(
            " abc-123 ", NOW - timedelta(hours=2), 9, "latest", Decimal(4), "CNY"
        ),
        HistoricalInquiryRecord("ABC123", NOW, 7, "not-same", Decimal(6), "CNY"),
    )
    result = evaluate_duplicate_history(
        inquiry_id="inq_0123456789abcdef01234567",
        target_mpn="ＡＢＣ－１２３",
        current_quantity=9,
        records=records,
        checked_at=NOW,
    )
    assert result.outcome.value == "CONFIRMED"
    assert result.repeated is True
    assert result.historical_date == NOW
    assert result.historical_quantity == 2
    assert result.quantity_equal is False
    assert result.creator == "older"


def test_duplicate_rule_inclusive_168h_boundary_and_ambiguous_tie_fail_closed() -> None:
    lower = NOW - timedelta(hours=168)
    record = HistoricalInquiryRecord("ABC-1", lower, 1, None, None)
    found = evaluate_duplicate_history(
        inquiry_id="inq_0123456789abcdef01234567",
        target_mpn="ABC-1",
        current_quantity=1,
        records=(record,),
        checked_at=NOW,
    )
    assert found.repeated is True
    outside = HistoricalInquiryRecord("ABC-1", lower - timedelta(microseconds=1), 1, None, None)
    absent = evaluate_duplicate_history(
        inquiry_id="inq_0123456789abcdef01234567",
        target_mpn="ABC-1",
        current_quantity=1,
        records=(outside,),
        checked_at=NOW,
    )
    assert absent.repeated is False

    tie = evaluate_duplicate_history(
        inquiry_id="inq_0123456789abcdef01234567",
        target_mpn="ABC-1",
        current_quantity=1,
        records=(record, HistoricalInquiryRecord("ABC-1", lower, 2, None, None)),
        checked_at=NOW,
    )
    assert tie.outcome.value == "AMBIGUOUS"
    assert tie.repeated is None
    assert not hasattr(tie, "match_count")


def test_post_research_route_runs_after_research_and_blocks_unknown_duplicate() -> None:
    duplicate = evaluate_duplicate_history(
        inquiry_id="inq_0123456789abcdef01234567",
        target_mpn="ABC-1",
        current_quantity=1,
        records=(HistoricalInquiryRecord("ABC-1", NOW, 2, None, None),),
        checked_at=NOW,
    )
    assert route_after_research(duplicate) is PostResearchRoute.DUPLICATE_STOP
    assert duplicate_notification_required(duplicate) is True

    unavailable = DuplicateCheckResult(
        "inq_0123456789abcdef01234567",
        DuplicateOutcome.UNAVAILABLE,
        "ABC-1",
        NOW,
        reason_code=ReasonCode.DUPLICATE_LOOKUP_UNAVAILABLE,
    )
    assert route_after_research(unavailable) is PostResearchRoute.DUPLICATE_CONFIRMATION_REQUIRED
    assert duplicate_notification_required(unavailable) is False


@pytest.mark.parametrize(
    ("tier", "total", "stock", "expected"),
    [
        ("A", None, "货足", True),
        ("A", Decimal(0), "货少", True),
        ("B", Decimal(50000), "货少", False),
        ("B", Decimal("50000.01"), "货少", True),
        ("B", Decimal(90000), "货足", False),
        ("C", Decimal(300000), "货少", False),
        ("C", Decimal("300000.01"), "货少", True),
        ("C", Decimal(400000), "货足", False),
        ("D", Decimal(900000), "货少", False),
    ],
)
def test_important_notification_policy_is_separate_and_uses_canonical_stock(
    tier: str, total: Decimal | None, stock: str, expected: bool
) -> None:
    assert should_send_important_order_notification(
        tier=tier, estimated_total=total, inventory_status=stock
    ) is expected


def test_purchase_full_price_policy_ignores_stock_and_uses_confirmed_purchasers() -> None:
    decisions = (
        ("A", None, QuotationType.FULL_PRICE, Purchaser.FULL_PRICE),
        ("B", Decimal("50000.01"), QuotationType.FULL_PRICE, Purchaser.FULL_PRICE),
        ("C", Decimal("300000.01"), QuotationType.FULL_PRICE, Purchaser.FULL_PRICE),
        ("B", Decimal(50000), QuotationType.ORDINARY, Purchaser.ORDINARY),
        ("C", Decimal(900000), QuotationType.FULL_PRICE, Purchaser.FULL_PRICE),
    )
    for tier, total, quotation, purchaser in decisions:
        actual = purchase_routing_decision(tier=tier, estimated_total=total)
        assert actual.outcome is PurchaseRoutingOutcome.READY
        assert actual.quotation_type is quotation
        assert actual.purchaser is purchaser


@pytest.mark.parametrize("tier", ["B", "C"])
def test_missing_b_or_c_estimated_total_is_indeterminate(tier: str) -> None:
    decision = purchase_routing_decision(tier=tier, estimated_total=None)

    assert decision.outcome is PurchaseRoutingOutcome.INDETERMINATE
    assert decision.quotation_type is None
    assert decision.purchaser is None


def test_ai_input_uses_exact_six_space_delimiters() -> None:
    assert build_ai_input("M-1", "Brand", 7) == "M-1      Brand      7"
    with pytest.raises(TypeError):
        build_ai_input("M-1", "Brand", True)


def test_ai_recognition_uses_exact_ai_mpn_brand_and_integer_quantity() -> None:
    matches = validate_ai_recognition(
        command_id="draft-1",
        completed_at=NOW,
        expected_mpn=" abc-123 ",
        expected_brand=" Brand ",
        expected_quantity=7,
        recognized_mpn="ABC-123",
        recognized_brand="Brand",
        recognized_quantity=7,
    )
    assert matches.outcome is PurchaseOutcome.AI_RECOGNIZED
    for values in (
        {"recognized_mpn": "ABC123"},
        {"recognized_mpn": "ABC-124"},
        {"recognized_brand": "brand"},
        {"recognized_quantity": 7.0},
        {"recognized_quantity": 8},
    ):
        candidate = {
            "recognized_mpn": "ABC-123",
            "recognized_brand": "Brand",
            "recognized_quantity": 7,
        }
        candidate.update(values)
        result = validate_ai_recognition(
            command_id="draft-1",
            completed_at=NOW,
            expected_mpn="ABC-123",
            expected_brand="Brand",
            expected_quantity=7,
            **candidate,
        )
        assert result.outcome is PurchaseOutcome.VALIDATION_FAILED
        assert result.reason_code is ReasonCode.AI_RECOGNITION_MISMATCH
