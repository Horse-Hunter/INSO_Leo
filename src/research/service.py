"""Single-call Research V1 execution service."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .aggregation import PriceAggregation, aggregate_price_results
from .contracts import ResearchInput, ResearchReasonCode, ResearchResult, ResearchStatus
from .excel_output import ExcelOutputError, ResearchExcelOutput
from .icnet import IcNetResult
from .source_contracts import SourceOutcome, SourceResult


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
        output: ResearchExcelOutput,
    ) -> None:
        self._icnet = icnet
        self._price_sources = (findchips, hqew, lcsc, bom_ai)
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
        if status in {ResearchStatus.SUCCESS, ResearchStatus.PARTIAL_SUCCESS} and (
            icnet.source_result.outcome is SourceOutcome.SOURCE_UNAVAILABLE
        ):
            status = ResearchStatus.PARTIAL_SUCCESS
            reason_code = ResearchReasonCode.SOURCE_UNAVAILABLE
            remarks = "部分调研来源暂时不可用"
        if status is ResearchStatus.RETRYABLE_FAILURE:
            result = ResearchResult(
                research_input.inquiry_id, status, resolved_brand, reason_code, remarks
            )
            return ResearchExecution(result, icnet, price_results, aggregation)
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
                remarks=remarks,
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
