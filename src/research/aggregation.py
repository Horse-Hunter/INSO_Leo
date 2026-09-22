"""Pure four-source price and status aggregation."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .contracts import ResearchReasonCode, ResearchStatus
from .source_contracts import (
    PRICE_SOURCES,
    PriceCandidate,
    ResearchSource,
    SourceOutcome,
    SourceResult,
)


@dataclass(frozen=True, slots=True)
class PriceAggregation:
    candidates: tuple[PriceCandidate, ...]
    lowest: PriceCandidate | None
    second_lowest: PriceCandidate | None
    show_second_lowest: bool
    estimated_total: Decimal | None
    market_reference: str | None
    status: ResearchStatus
    reason_code: ResearchReasonCode | None
    remarks: str | None


_SOURCE_LABELS = {
    ResearchSource.FINDCHIPS: "Findchips",
    ResearchSource.HQEW: "华强电子网",
    ResearchSource.LCSC: "LCSC",
    ResearchSource.BOM_AI: "Bom.Ai",
}


def _money(value: Decimal) -> str:
    return format(value, "f")


def aggregate_price_results(
    results: tuple[SourceResult, ...], quantity: int
) -> PriceAggregation:
    by_source = {result.source: result for result in results}
    if set(by_source) != set(PRICE_SOURCES) or len(results) != len(PRICE_SOURCES):
        raise ValueError(
            "exactly one result for each canonical price source is required"
        )
    candidates = tuple(
        sorted(
            (r.price_candidate for r in results if r.price_candidate is not None),
            key=lambda candidate: (
                candidate.normalized_rmb_price,
                candidate.source.value,
            ),
        )
    )
    unavailable = [
        r.source for r in results if r.outcome is SourceOutcome.SOURCE_UNAVAILABLE
    ]
    if not candidates:
        all_no_match = all(
            r.outcome is SourceOutcome.NO_STRICT_MPN_MATCH for r in results
        )
        if all_no_match:
            return PriceAggregation(
                (),
                None,
                None,
                False,
                None,
                None,
                ResearchStatus.MANUAL_REVIEW_REQUIRED,
                ResearchReasonCode.NO_MATCHING_PRODUCT,
                "四个价格源均未找到严格匹配型号",
            )
        return PriceAggregation(
            (),
            None,
            None,
            False,
            None,
            None,
            ResearchStatus.RETRYABLE_FAILURE,
            ResearchReasonCode.SOURCE_UNAVAILABLE if unavailable else None,
            "价格源暂时无法形成有效市场价格",
        )
    lowest = candidates[0]
    second = candidates[1] if len(candidates) > 1 else None
    show_second = bool(
        second
        and lowest.normalized_rmb_price <= second.normalized_rmb_price * Decimal("0.80")
    )
    market = _money(lowest.normalized_rmb_price)
    if show_second and second is not None:
        market += (
            f"\n{_money(second.normalized_rmb_price)}-{_SOURCE_LABELS[second.source]}"
        )
    status = ResearchStatus.PARTIAL_SUCCESS if unavailable else ResearchStatus.SUCCESS
    remarks = None if not unavailable else "部分价格源暂时不可用"
    return PriceAggregation(
        candidates,
        lowest,
        second,
        show_second,
        lowest.normalized_rmb_price * Decimal(quantity),
        market,
        status,
        ResearchReasonCode.SOURCE_UNAVAILABLE if unavailable else None,
        remarks,
    )
