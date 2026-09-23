"""Pure five-source price-pool and status aggregation."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .contracts import ResearchReasonCode, ResearchStatus
from .source_contracts import (
    PRICE_SOURCES,
    EvidenceField,
    PriceCandidate,
    ResearchSource,
    SourceOutcome,
    SourceResult,
    money_text,
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
    used_out_of_stock_fallback: bool = False


_SOURCE_LABELS = {
    ResearchSource.FINDCHIPS: "Findchips",
    ResearchSource.HQEW: "华强",
    ResearchSource.LCSC: "立创",
    ResearchSource.BOM_AI: "正能量",
    ResearchSource.INSO: "INSO",
}


def _failure_code(result: SourceResult) -> str:
    return next(
        (
            str(field.value)
            for field in result.evidence.fields
            if isinstance(field, EvidenceField)
            and field.key == "failure_code"
            and field.value
        ),
        "SOURCE_UNAVAILABLE",
    )


def _failure_reason(code: str) -> str:
    upper = code.upper()
    if "CHALLENGE" in upper or "CAPTCHA" in upper or "OTP" in upper:
        return "需要人工验证"
    if "FX" in upper:
        return "汇率不可用"
    if any(word in upper for word in ("PARSE", "UNPARSEABLE", "MISSING")):
        return "结果解析失败"
    if "CREDENTIAL" in upper or "LOGIN" in upper:
        return "登录不可用"
    return "暂时不可用"


def _market_reference(
    candidates: tuple[PriceCandidate, ...],
) -> tuple[PriceCandidate, PriceCandidate | None, bool, str]:
    lowest = candidates[0]
    second = candidates[1] if len(candidates) > 1 else None
    show_second = bool(
        second
        and lowest.normalized_rmb_price
        <= second.normalized_rmb_price * Decimal("0.80")
    )
    rendered = money_text(lowest.normalized_rmb_price)
    if show_second and second is not None:
        rendered += (
            f"\n{money_text(second.normalized_rmb_price)}-"
            f"{_SOURCE_LABELS[second.source]}"
        )
    return lowest, second, show_second, rendered


def aggregate_price_results(
    results: tuple[SourceResult, ...], quantity: int
) -> PriceAggregation:
    by_source = {result.source: result for result in results}
    if set(by_source) != set(PRICE_SOURCES) or len(results) != len(PRICE_SOURCES):
        raise ValueError(
            "exactly one result for each canonical price source is required"
        )

    source_order = {source: index for index, source in enumerate(PRICE_SOURCES)}
    unavailable = tuple(
        sorted(
            (
                result
                for result in results
                if result.outcome is SourceOutcome.SOURCE_UNAVAILABLE
            ),
            key=lambda result: source_order[result.source],
        )
    )
    normal = tuple(
        sorted(
            (
                result.price_candidate
                for result in results
                if result.price_candidate is not None
            ),
            key=lambda candidate: (
                candidate.normalized_rmb_price,
                candidate.source.value,
            ),
        )
    )
    fallback = tuple(
        sorted(
            (
                result.out_of_stock_candidate
                for result in results
                if result.out_of_stock_candidate is not None
            ),
            key=lambda candidate: (
                candidate.normalized_rmb_price,
                candidate.source.value,
            ),
        )
    )
    technical_remarks = "；".join(
        f"{_SOURCE_LABELS[result.source]}：{_failure_reason(_failure_code(result))}"
        for result in unavailable
    )

    if normal:
        lowest, second, show_second, market = _market_reference(normal)
        status = (
            ResearchStatus.PARTIAL_SUCCESS
            if unavailable
            else ResearchStatus.SUCCESS
        )
        return PriceAggregation(
            normal,
            lowest,
            second,
            show_second,
            lowest.normalized_rmb_price * Decimal(quantity),
            market,
            status,
            ResearchReasonCode.SOURCE_UNAVAILABLE if unavailable else None,
            technical_remarks or None,
        )

    if unavailable:
        return PriceAggregation(
            (),
            None,
            None,
            False,
            None,
            None,
            ResearchStatus.RETRYABLE_FAILURE,
            ResearchReasonCode.SOURCE_UNAVAILABLE,
            technical_remarks,
        )

    if fallback:
        lowest, second, show_second, market = _market_reference(fallback)
        return PriceAggregation(
            fallback,
            lowest,
            second,
            show_second,
            lowest.normalized_rmb_price * Decimal(quantity),
            market,
            ResearchStatus.MANUAL_REVIEW_REQUIRED,
            None,
            "仅有无库存价格，需人工介入",
            True,
        )

    return PriceAggregation(
        (),
        None,
        None,
        False,
        None,
        None,
        ResearchStatus.MANUAL_REVIEW_REQUIRED,
        ResearchReasonCode.NO_MATCHING_PRODUCT,
        "疑似客户报错型号",
    )
