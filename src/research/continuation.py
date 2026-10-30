"""Owner-thread continuation of the canonical six-source Research, no scheduler.

Existing synchronous entrypoints drive this same object to completion. Optional
Workflow integration advances one source at a time without a batch wait. Only
immutable market payloads may leave this owner object.
"""
import threading
from datetime import UTC, datetime

from .contracts import ResearchInput
from .icnet import IcNetResult
from .market_contracts import MarketReadMode, MarketReadQuery, MarketReadResult
from .source_contracts import (
    PRICE_SOURCES,
    EvidenceField,
    ResearchSource,
    SourceEvidence,
    SourceOutcome,
    SourceResult,
)
from .tp import (
    TpFx,
    TpSourceResult,
    finish_tp,
    select_tp_offers,
)


class ResearchContinuation:
    def __init__(self, service, *, now, research_input=None, task_id=None, order=None):
        if not isinstance(now, datetime) or now.utcoffset() is None:
            raise ValueError("RESEARCH_REFERENCE_TIME_INVALID")
        if (research_input is None) == (order is None):
            raise ValueError("RESEARCH_CONTINUATION_INPUT_INVALID")
        if research_input is not None and type(research_input) is not ResearchInput:
            raise TypeError("RESEARCH_CONTINUATION_INPUT_INVALID")
        self._service, self._input, self._order = service, research_input, order
        self._task = research_input.inquiry_id if research_input is not None else task_id
        self._now, self._owner = now, threading.get_ident()
        self._results, self._icnet, self._finished = [], None, False
        self._fx = TpFx(service._fx_provider, now) if order is not None else None
        self._target_rmb = self._fx.convert(order.target_price, order.currency) if order is not None and getattr(order, "target_price", None) is not None else None

    def _check_owner(self):
        if self._owner != threading.get_ident():
            raise RuntimeError("RESEARCH_CONTINUATION_THREAD_MISMATCH")

    @property
    def ready(self):
        return len(self._results) == len(PRICE_SOURCES)

    @property
    def source(self):
        return None if self.ready else PRICE_SOURCES[len(self._results)]

    @property
    def task_id(self):
        return self._task

    @property
    def mode(self):
        return MarketReadMode.TP_OFFERS if self._order is not None else MarketReadMode.ORDINARY

    @property
    def market_query(self):
        self._check_owner()
        source = self.source
        # Foreign-currency ordinary adapters currently convert as part of their
        # canonical search; keep those on owner rather than fork their FX/parser.
        actor_sources = ({ResearchSource.IC_NET, ResearchSource.FINDCHIPS, ResearchSource.HQEW,
                          ResearchSource.LCSC} if self._order is not None else
                         {ResearchSource.IC_NET, ResearchSource.HQEW})
        if source not in actor_sources:
            return None
        item = self._order or self._input
        return MarketReadQuery(source, self.mode, item.mpn, item.quantity or 1, self._now, item.brand)

    def read_owner(self):
        self._check_owner()
        if self.ready or self._finished:
            raise RuntimeError("RESEARCH_CONTINUATION_COMPLETE")
        service, source, item = self._service, self.source, self._order or self._input
        if source is ResearchSource.IC_NET:
            operation = lambda: service._icnet.search(item.mpn, item.brand, item.quantity or 1)
        else:
            adapter = service._price_sources[PRICE_SOURCES.index(source) - 1]
            def operation():
                if self._order is None:
                    try:
                        return adapter.search(item.mpn, item.quantity)
                    except Exception:
                        if source is ResearchSource.INSO:
                            raise
                        return SourceResult(source, SourceOutcome.SOURCE_UNAVAILABLE,
                            SourceEvidence(source, item.mpn, None, SourceOutcome.SOURCE_UNAVAILABLE,
                                datetime.now(UTC), fields=(EvidenceField("failure_code", "SOURCE_UNAVAILABLE"),)))
                try:
                    from .tp import collect_tp
                    return collect_tp(adapter, source, item.mpn, item.quantity or 1, self._now, self._fx)
                except Exception as exc:
                    from .lcsc import LcscNoMatchingProduct
                    if source is ResearchSource.LCSC and isinstance(exc, LcscNoMatchingProduct):
                        return TpSourceResult(source, SourceOutcome.NO_STRICT_MPN_MATCH,
                            SourceEvidence(source, item.mpn, None, SourceOutcome.NO_STRICT_MPN_MATCH, self._now))
                    code = getattr(exc, 'code', None)
                    if not isinstance(code, str):
                        if isinstance(exc, ValueError) and str(exc) == 'FX_QUOTE_UNAVAILABLE':
                            code = 'FX_QUOTE_UNAVAILABLE'
                        else:
                            raise
                    return TpSourceResult(source, SourceOutcome.SOURCE_UNAVAILABLE,
                        SourceEvidence(source, item.mpn, None, SourceOutcome.SOURCE_UNAVAILABLE,
                            self._now, fields=(EvidenceField('failure_code', code),)))
        def read():
            return service._source_query(self._task, source, operation) if service._source_query else operation()
        return service._inso_query(self._task, read) if source is ResearchSource.INSO and service._inso_query else read()

    def accept_actor(self, result):
        self._check_owner()
        if (type(result) is not MarketReadResult or result.source is not self.source or result.mode is not self.mode
                or self.market_query is None):
            raise ValueError("RESEARCH_CONTINUATION_RESULT_MISMATCH")
        if self._order is None:
            return self.accept_owner(result.ordinary)
        if self.source is ResearchSource.IC_NET:
            if result.icnet_context is None:
                raise ValueError("RESEARCH_ICNET_CONTEXT_MISSING")
            return self.accept_owner(result.icnet_context)
        selected = select_tp_offers(self.source, result.offers, query=self._order.mpn,
                                    now=self._now, fx=self._fx)
        self.accept_owner(selected)

    def accept_owner(self, result):
        self._check_owner()
        if self.ready or self._finished:
            raise RuntimeError("RESEARCH_CONTINUATION_COMPLETE")
        source = self.source
        if source is ResearchSource.IC_NET:
            if type(result) is not IcNetResult or result.source_result.source is not source:
                raise ValueError("RESEARCH_CONTINUATION_RESULT_MISMATCH")
            self._icnet = result
            native = result.source_result
            selected = native
            if self._order is not None:
                from .detailed import icnet_detailed_result
                selected = icnet_detailed_result(result, self._fx)
            observation = native
        else:
            expected = TpSourceResult if self._order is not None else SourceResult
            if type(result) is not expected or result.source is not source:
                raise ValueError("RESEARCH_CONTINUATION_RESULT_MISMATCH")
            selected = observation = result
        self._results.append(selected)
        if self._service._source_observer:
            self._service._source_observer(self._task, observation)

    def finish(self):
        self._check_owner()
        if not self.ready or self._finished:
            raise RuntimeError("RESEARCH_CONTINUATION_NOT_READY_OR_FINISHED")
        self._finished = True
        if self._order is not None:
            return finish_tp(self._order, self._icnet, tuple(self._results), target_rmb=self._target_rmb, fx=self._fx)
        return self._service.complete_detailed(self._input, self._icnet, tuple(self._results))
