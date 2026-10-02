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


#: Verdicts the shared login implementation hands back verbatim. They are named
#: here rather than pattern-matched, because the words inside them ("CREDENTIAL",
#: "LOGIN") belong to the generic branch below and would be read as a dead
#: session rather than as the specific thing the site just said.
_LOGIN_VERDICT_REASONS = {
    "MANUAL_VERIFICATION_REQUIRED": "需要人工验证",
    "CREDENTIAL_REJECTED": "账号或密码被站点拒绝",
    "CREDENTIALS_UNAVAILABLE": "没有可用的登录凭据",
    "LOGIN_FORM_UNAVAILABLE": "站点登录表单已变化",
    "LOGIN_CONTROL_AMBIGUOUS": "站点登录表单已变化",
    # The credential is fine and the form was submitted; what could not be
    # confirmed is an option beside the form ("30天内免登录"). Saying "登录不可用"
    # here would send the repair at the password, which is not what broke.
    "LOGIN_OPTION_UNCONFIRMED": "登录前选项未能勾选",
}


def _failure_reason(code: str) -> str:
    upper = code.upper()
    verdict = _LOGIN_VERDICT_REASONS.get(upper)
    if verdict is not None:
        return verdict
    if "CHALLENGE" in upper or "CAPTCHA" in upper or "OTP" in upper:
        return "需要人工验证"
    if "REJECTED" in upper:
        # The site answered the credential itself. Waiting cannot fix it and
        # neither can a retry, so it must not read like a stalled session.
        return "账号或密码被站点拒绝"
    if "FX" in upper:
        return "汇率不可用"
    if "HTTP_STATUS_403" in upper:
        return "访问被站点拒绝"
    if any(word in upper for word in ("PARSE", "UNPARSEABLE", "MISSING")):
        return "结果解析失败"
    if (
        "CREDENTIAL" in upper
        or "LOGIN" in upper
        or "AUTHENTICATED_SESSION_REQUIRED" in upper
    ):
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
            ResearchStatus.PARTIAL_SUCCESS,
            None,
            "仅找到无库存报价",
            True,
        )

    return PriceAggregation(
        (),
        None,
        None,
        False,
        None,
        None,
        ResearchStatus.EXCEPTION,
        ResearchReasonCode.NO_MATCHING_PRODUCT,
        "五个价格来源均无报价，可能是客户填写的型号有误",
    )
