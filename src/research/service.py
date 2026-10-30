"""Single-call Research V1 execution service."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

from .aggregation import (
    PriceAggregation,
    aggregate_price_results,
)
from .contracts import ResearchInput, ResearchReasonCode, ResearchResult, ResearchStatus
from .excel_output import ExcelOutputError, ResearchExcelOutput
from .icnet import IcNetResult
from .source_contracts import (
    ResearchSource,
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
        source_observer: Callable | None = None,
        inso_query: Callable | None = None,
        source_query: Callable | None = None,
        fx_provider=None,
    ) -> None:
        self._icnet = icnet
        self._price_sources = (findchips, hqew, lcsc, bom_ai, inso)
        self._output = output
        self._source_observer = source_observer
        self._inso_query = inso_query
        self._source_query = source_query
        self._fx_provider = fx_provider

    def read_market_source(self, query):
        """One canonical read without Excel, business state, callbacks or INSO.

        A caller supplies an actor-local service; Backend-bound service instances
        must never be handed to another thread. TP returns raw native offers so
        the task owner retains its single FX snapshot and existing selection.
        """
        from .market_contracts import MarketReadMode, MarketReadQuery, MarketReadResult
        from .tp import TpOffer, TpSourceResult, collect_tp_offers
        if type(query) is not MarketReadQuery:
            raise ValueError("MARKET_QUERY_PARAMETERS_INVALID")
        if query.source is ResearchSource.IC_NET:
            result = self._icnet.search(query.mpn, query.brand, query.quantity)
            if query.mode is MarketReadMode.ORDINARY:
                return MarketReadResult(query.source, query.mode, ordinary=result)
            candidate = result.source_result.price_candidate
            offers = () if candidate is None else (TpOffer(query.source, candidate.matched_mpn,
                candidate.raw_price, candidate.raw_currency, None, True),)
            return MarketReadResult(query.source, query.mode, offers=offers, icnet_context=result)
        sources = (ResearchSource.FINDCHIPS, ResearchSource.HQEW, ResearchSource.LCSC,
                   ResearchSource.BOM_AI, ResearchSource.INSO)
        adapter = self._price_sources[sources.index(query.source)]
        if query.mode is MarketReadMode.ORDINARY:
            return MarketReadResult(query.source, query.mode,
                                    ordinary=adapter.search(query.mpn, query.quantity))
        offers = collect_tp_offers(adapter, query.source, query.mpn, query.quantity, query.reference_at)
        if isinstance(offers, TpSourceResult):
            raise ValueError("MARKET_OWNER_REQUIRED")  # noqa: TRY004 - typed acquisition outcome
        return MarketReadResult(query.source, query.mode, offers=offers)

    def execute_tp(self, task_id, order, *, now):
        from .tp import execute_tp
        return execute_tp(self, task_id, order, now)

    def read_detailed_source(self, source, order, *, now, fx):
        """Canonical public read-only source projection; no TP or business writes."""
        from dataclasses import replace

        from src.core.mpn import normalize_lookup_mpn

        from .detailed import collect_tp, icnet_detailed_result
        from .source_contracts import EvidenceField, SourceOutcome
        if source is ResearchSource.IC_NET:
            result = self._icnet.search(order.mpn, order.brand, order.quantity or 1)
            selected = icnet_detailed_result(result, fx)
            brand = result.resolved_brand
            if (isinstance(brand, str) and brand.strip() and len(brand) <= 256
                    and selected.outcome is not SourceOutcome.SOURCE_UNAVAILABLE
                    and normalize_lookup_mpn(selected.evidence.matched_mpn) == normalize_lookup_mpn(order.mpn)):
                selected = replace(selected, evidence=replace(selected.evidence,
                    fields=(*selected.evidence.fields, EvidenceField("trusted_report_brand", brand))))
            return selected, result.stock_label
        sources = (ResearchSource.FINDCHIPS, ResearchSource.HQEW, ResearchSource.LCSC,
                   ResearchSource.BOM_AI, ResearchSource.INSO)
        return collect_tp(self._price_sources[sources.index(source)], source, order.mpn,
                          order.quantity or 1, now, fx), None

    def execute_market_report(self, task_id, order, *, now):
        """Read-only detailed report; no output workbook, business write or target."""
        from .detailed import execute_tp
        if getattr(order, "target_price", None) is not None:
            raise ValueError("ORDINARY_REPORT_TARGET_FORBIDDEN")
        return execute_tp(self, task_id, order, now)

    def execute(self, research_input: ResearchInput) -> ResearchResult:
        return self.execute_detailed(research_input).result

    def begin_detailed(self, research_input: ResearchInput, *, now=None):
        from .continuation import ResearchContinuation
        return ResearchContinuation(self, research_input=research_input, now=now or datetime.now(UTC))

    def begin_tp(self, task_id, order, *, now):
        from .continuation import ResearchContinuation
        return ResearchContinuation(self, task_id=task_id, order=order, now=now)

    def execute_detailed(self, research_input: ResearchInput) -> ResearchExecution:
        continuation = self.begin_detailed(research_input)
        while not continuation.ready:
            continuation.accept_owner(continuation.read_owner())
        return continuation.finish()

    def complete_detailed(self, research_input, icnet, price_results):
        """Canonical owner-side aggregation/output after all six source results."""
        if (type(price_results) is not tuple or len(price_results) != 6
                or tuple(result.source for result in price_results) != (
                    ResearchSource.IC_NET, ResearchSource.FINDCHIPS, ResearchSource.HQEW,
                    ResearchSource.LCSC, ResearchSource.BOM_AI, ResearchSource.INSO)
                or price_results[0] != icnet.source_result):
            raise ValueError("Research service requires all six price sources")
        aggregation = aggregate_price_results(price_results, research_input.quantity)
        resolved_brand = icnet.resolved_brand or research_input.brand
        status, reason_code, remarks = (
            aggregation.status,
            aggregation.reason_code,
            aggregation.remarks,
        )
        source_values = {
            result.source: format_source_result(result) for result in price_results
        }
        if set(source_values) != {
            ResearchSource.IC_NET,
            ResearchSource.FINDCHIPS,
            ResearchSource.HQEW,
            ResearchSource.LCSC,
            ResearchSource.BOM_AI,
            ResearchSource.INSO,
        }:
            raise ValueError("Research service requires all six price sources")
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
