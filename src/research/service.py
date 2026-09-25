"""Single-call Research V1 execution service."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .aggregation import (
    PriceAggregation,
    _failure_code,
    _failure_reason,
    aggregate_price_results,
)
from .contracts import ResearchInput, ResearchReasonCode, ResearchResult, ResearchStatus
from .excel_output import ExcelOutputError, ResearchExcelOutput
from .icnet import IcNetResult
from .source_contracts import (
    ResearchSource,
    SourceOutcome,
    SourceResult,
    format_source_result,
)


class IcNetSearcher(Protocol):
    def search(
        self, target_mpn: str, input_brand: str | None, customer_quantity: int
    ) -> IcNetResult: ...


class PriceSearcher(Protocol):
    def search(self, target_mpn: str, customer_quantity: int) -> SourceResult: ...


@dataclass(frozen=True, slots=True)
class ResearchExecution:
    result: ResearchResult
    icnet: IcNetResult
    price_sources: tuple[SourceResult, ...]
    aggregation: PriceAggregation


class ResearchService:
    def __init__(
        self,
        *,
        icnet: IcNetSearcher,
        findchips: PriceSearcher,
        hqew: PriceSearcher,
        lcsc: PriceSearcher,
        bom_ai: PriceSearcher,
        inso: PriceSearcher,
        output: ResearchExcelOutput,
    ) -> None:
        self._icnet = icnet
        self._price_sources = (findchips, hqew, lcsc, bom_ai, inso)
        self._output = output

    def execute(self, research_input: ResearchInput) -> ResearchResult:
        return self.execute_detailed(research_input).result

    def execute_detailed(self, research_input: ResearchInput) -> ResearchExecution:
        icnet = self._icnet.search(
            research_input.mpn, research_input.brand, research_input.quantity
        )
        price_results = tuple(
            source.search(research_input.mpn, research_input.quantity)
            for source in self._price_sources
        )
        aggregation = aggregate_price_results(price_results, research_input.quantity)
        resolved_brand = icnet.resolved_brand or research_input.brand
        status, reason_code, remarks = (
            aggregation.status,
            aggregation.reason_code,
            aggregation.remarks,
        )
        if icnet.source_result.outcome is SourceOutcome.SOURCE_UNAVAILABLE:
            icnet_remark = (
                f"IC.net：{_failure_reason(_failure_code(icnet.source_result))}"
            )
            remarks = "；".join(part for part in (remarks, icnet_remark) if part)
        source_values = {
            result.source: format_source_result(result) for result in price_results
        }
        if set(source_values) != {
            ResearchSource.FINDCHIPS,
            ResearchSource.HQEW,
            ResearchSource.LCSC,
            ResearchSource.BOM_AI,
            ResearchSource.INSO,
        }:
            raise ValueError("Research service requires all five price sources")
        try:
            self._output.upsert(
                research_input.inquiry_id,
                mpn=research_input.mpn,
                brand=resolved_brand,
                quantity=research_input.quantity,
                importance_raw=research_input.importance_raw,
                stock_label=icnet.stock_label,
                estimated_total=aggregation.estimated_total,
                market_reference=aggregation.market_reference,
                source_values=source_values,
                remarks=remarks,
                research_status=status.value,
            )
        except ExcelOutputError:
            result = ResearchResult(
                research_input.inquiry_id,
                ResearchStatus.RETRYABLE_FAILURE,
                resolved_brand,
                ResearchReasonCode.SOURCE_UNAVAILABLE,
                "调研结果暂时无法写入",
            )
            return ResearchExecution(result, icnet, price_results, aggregation)
        result = ResearchResult(
            research_input.inquiry_id, status, resolved_brand, reason_code, remarks
        )
        return ResearchExecution(result, icnet, price_results, aggregation)
