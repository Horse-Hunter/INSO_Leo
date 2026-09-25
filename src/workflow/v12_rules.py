"""Pure V1.2 workflow decisions over canonical Research/Sheet values."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import StrEnum

from .v12_contracts import (
    DuplicateCheckResult,
    DuplicateOutcome,
    PurchaseDraftResult,
    PurchaseOutcome,
    ReasonCode,
)
from .v12_safety import MpnPolicy, mpn_matches, normalize_mpn


class QuotationType(StrEnum):
    FULL_PRICE = "需要问全价格"
    ORDINARY = "普通询价"


class Purchaser(StrEnum):
    FULL_PRICE = "颜浩坚"
    ORDINARY = "陈熙"


class PurchaseRoutingOutcome(StrEnum):
    READY = "READY"
    INDETERMINATE = "INDETERMINATE"


class PostResearchRoute(StrEnum):
    DUPLICATE_STOP = "DUPLICATE_STOP"
    PURCHASE_ELIGIBLE = "PURCHASE_ELIGIBLE"
    DUPLICATE_CONFIRMATION_REQUIRED = "DUPLICATE_CONFIRMATION_REQUIRED"


@dataclass(frozen=True, slots=True)
class PurchaseRoutingDecision:
    outcome: PurchaseRoutingOutcome
    quotation_type: QuotationType | None
    purchaser: Purchaser | None


@dataclass(frozen=True, slots=True)
class HistoricalInquiryRecord:
    mpn: str
    quoted_at: datetime
    quantity: int
    creator: str | None
    inso_quote: Decimal | None
    currency: str | None = None


def route_after_research(result: DuplicateCheckResult) -> PostResearchRoute:
    """A failed/ambiguous duplicate read is never treated as nonduplicate."""

    if result.outcome is not DuplicateOutcome.CONFIRMED:
        return PostResearchRoute.DUPLICATE_CONFIRMATION_REQUIRED
    if result.repeated:
        return PostResearchRoute.DUPLICATE_STOP
    return PostResearchRoute.PURCHASE_ELIGIBLE


def duplicate_notification_required(result: DuplicateCheckResult) -> bool:
    return result.outcome is DuplicateOutcome.CONFIRMED and result.repeated is True


def should_send_important_order_notification(
    *, tier: str, estimated_total: Decimal | None, inventory_status: str
) -> bool:
    """Apply notification-only rules; stock is the canonical Research result."""

    if tier == "A":
        return True
    if inventory_status != "货少" or estimated_total is None:
        return False
    if tier == "B":
        return estimated_total > Decimal(50000)
    if tier == "C":
        return estimated_total > Decimal(300000)
    return False


def purchase_routing_decision(
    *, tier: str, estimated_total: Decimal | None
) -> PurchaseRoutingDecision:
    """Apply procurement quotation rules independently from email decisions."""

    if tier in {"B", "C"} and estimated_total is None:
        return PurchaseRoutingDecision(PurchaseRoutingOutcome.INDETERMINATE, None, None)

    full_price = tier == "A" or (
        tier == "B"
        and estimated_total is not None
        and estimated_total > Decimal(50000)
    ) or (
        tier == "C"
        and estimated_total is not None
        and estimated_total > Decimal(300000)
    )
    if full_price:
        return PurchaseRoutingDecision(
            PurchaseRoutingOutcome.READY, QuotationType.FULL_PRICE, Purchaser.FULL_PRICE
        )
    return PurchaseRoutingDecision(
        PurchaseRoutingOutcome.READY, QuotationType.ORDINARY, Purchaser.ORDINARY
    )


def evaluate_duplicate_history(
    *,
    inquiry_id: str,
    target_mpn: str,
    current_quantity: int,
    records: tuple[HistoricalInquiryRecord, ...],
    checked_at: datetime,
) -> DuplicateCheckResult:
    """Decide from exact canonical MPNs in the rolling inclusive 168h window.

    Same-timestamp latest rows remain AMBIGUOUS until a live, stable INSO
    identity and an approved tie policy are established.
    """

    if checked_at.tzinfo is None:
        raise ValueError("checked_at must be timezone-aware")
    if isinstance(current_quantity, bool) or not isinstance(current_quantity, int):
        return _duplicate_invalid(inquiry_id, target_mpn, checked_at)
    try:
        canonical = normalize_mpn(target_mpn, policy=MpnPolicy.DUP_MPN_V1)
    except (TypeError, ValueError):
        return _duplicate_invalid(inquiry_id, target_mpn, checked_at)
    if not canonical:
        return _duplicate_invalid(inquiry_id, canonical, checked_at)

    now_utc = checked_at.astimezone(UTC)
    cutoff = now_utc - timedelta(hours=168)
    exact_recent: list[HistoricalInquiryRecord] = []
    try:
        for record in records:
            if (
                record.quoted_at.tzinfo is None
                or isinstance(record.quantity, bool)
                or not isinstance(record.quantity, int)
                or not isinstance(record.mpn, str)
                or (
                    record.inso_quote is not None
                    and (
                        not isinstance(record.inso_quote, Decimal)
                        or not record.inso_quote.is_finite()
                        or record.inso_quote < 0
                    )
                )
            ):
                return _duplicate_invalid(inquiry_id, canonical, checked_at)
            observed = record.quoted_at.astimezone(UTC)
            historical_canonical = normalize_mpn(
                record.mpn, policy=MpnPolicy.DUP_MPN_V1
            )
            if not historical_canonical:
                return _duplicate_invalid(inquiry_id, canonical, checked_at)
            if cutoff <= observed <= now_utc and historical_canonical == canonical:
                exact_recent.append(record)
    except (TypeError, ValueError):
        return _duplicate_invalid(inquiry_id, canonical, checked_at)

    if not exact_recent:
        return DuplicateCheckResult(
            inquiry_id, DuplicateOutcome.CONFIRMED, canonical, checked_at, repeated=False
        )
    latest_at = max(record.quoted_at.astimezone(UTC) for record in exact_recent)
    latest = tuple(
        record
        for record in exact_recent
        if record.quoted_at.astimezone(UTC) == latest_at
    )
    if len(latest) != 1:
        return DuplicateCheckResult(
            inquiry_id,
            DuplicateOutcome.AMBIGUOUS,
            canonical,
            checked_at,
            reason_code=ReasonCode.DUPLICATE_LOOKUP_AMBIGUOUS,
        )
    record = latest[0]
    return DuplicateCheckResult(
        inquiry_id,
        DuplicateOutcome.CONFIRMED,
        canonical,
        checked_at,
        repeated=True,
        historical_date=record.quoted_at,
        historical_mpn=record.mpn,
        historical_quantity=record.quantity,
        quantity_equal=current_quantity == record.quantity,
        creator=record.creator,
        inso_quote=record.inso_quote,
        currency=record.currency,
    )


def _duplicate_invalid(
    inquiry_id: str, target_mpn: str, checked_at: datetime
) -> DuplicateCheckResult:
    canonical = (
        normalize_mpn(target_mpn, policy=MpnPolicy.DUP_MPN_V1)
        if isinstance(target_mpn, str)
        else ""
    )
    return DuplicateCheckResult(
        inquiry_id,
        DuplicateOutcome.INVALID_RESPONSE,
        canonical,
        checked_at,
        reason_code=ReasonCode.DUPLICATE_HISTORY_INVALID,
    )


def build_ai_input(mpn: str, brand: str, quantity: int) -> str:
    if not isinstance(mpn, str) or not isinstance(brand, str):
        raise TypeError("MPN and brand must be strings")
    if isinstance(quantity, bool) or not isinstance(quantity, int):
        raise TypeError("quantity must be an integer")
    return f"{mpn}{' ' * 6}{brand}{' ' * 6}{quantity}"


def validate_ai_recognition(
    *,
    command_id: str,
    completed_at: datetime,
    expected_mpn: str,
    expected_brand: str,
    expected_quantity: int,
    recognized_mpn: str | None,
    recognized_brand: str | None,
    recognized_quantity: int | None,
) -> PurchaseDraftResult:
    """Produce a typed result; any uncertain or mismatched field fails closed."""

    if completed_at.tzinfo is None:
        raise ValueError("completion timestamp must be timezone-aware")
    quantity_valid = (
        not isinstance(expected_quantity, bool)
        and isinstance(expected_quantity, int)
        and recognized_quantity is not None
        and not isinstance(recognized_quantity, bool)
        and isinstance(recognized_quantity, int)
        and recognized_quantity == expected_quantity
    )
    try:
        mpn_valid = (
            isinstance(expected_mpn, str)
            and isinstance(recognized_mpn, str)
            and mpn_matches(expected_mpn, recognized_mpn, policy=MpnPolicy.AI_MPN_V1)
        )
    except (TypeError, ValueError):
        mpn_valid = False
    brand_valid = (
        isinstance(expected_brand, str)
        and isinstance(recognized_brand, str)
        and recognized_brand.strip() == expected_brand.strip()
    )
    matches = mpn_valid and brand_valid and quantity_valid
    return PurchaseDraftResult(
        command_id=command_id,
        outcome=(PurchaseOutcome.AI_RECOGNIZED if matches else PurchaseOutcome.VALIDATION_FAILED),
        completed_at=completed_at,
        recognized_mpn=recognized_mpn if isinstance(recognized_mpn, str) else None,
        recognized_brand=recognized_brand if isinstance(recognized_brand, str) else None,
        recognized_quantity=(recognized_quantity if quantity_valid else None),
        reason_code=None if matches else ReasonCode.AI_RECOGNITION_MISMATCH,
    )
