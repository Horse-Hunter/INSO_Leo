"""Original-owner source continuation over existing actors/runtime, no scheduler.

One instance per admitted domain continuation. Caller drains actors ONCE and
passes that immutable batch to its active continuations before the next owner
step. This object never releases the parent business lease or sends mail.
"""
from src.research.continuation import ResearchContinuation
from src.research.site_login import SITE_AUTH_RECOVERY_REASONS
from src.workflow.market_messages import (
    BusinessResearchCompletion,
    MarketFaultScope,
    MarketTerminal,
)
from src.workflow.service import BusinessContinuationLease, OrderResourceOwnershipError

from .market_actors import _fault


class MarketContinuationFault(RuntimeError):
    def __init__(self, fault):
        self.fault = fault
        super().__init__(fault.reason)


class MarketContinuationCancelled(RuntimeError):
    pass


class OwnerMarketResearch:
    def __init__(self, runtime, actors, lease, research, *, due_at):
        if (type(lease) is not BusinessContinuationLease or type(research) is not ResearchContinuation
                or lease.identity.domain_task_id != research.task_id):
            raise ValueError('OWNER_RESEARCH_IDENTITY_INVALID')
        actors.require_owner_resources(runtime)
        runtime.require_business_continuation(lease)
        self._runtime, self._actors, self._lease = runtime, actors, lease
        self._research, self._due_at = research, due_at
        self._request, self._finished = None, False

    def _require_open(self):
        self._actors.require_owner_resources(self._runtime)
        self._runtime.require_business_continuation(self._lease)

    def advance(self, completions=()):
        """One owner source at most, never wait for a future or Research batch.

        Completion receipt/lease accounting already happened in actors.drain.
        Batch global faults always take priority over any successful payload.
        Parent source resource remains held for caller's domain finalization.
        """
        if self._finished:
            raise RuntimeError('OWNER_RESEARCH_ALREADY_FINISHED')
        global_fault = next((message.fault for message in completions
                             if message.fault is not None
                             and message.fault.scope is MarketFaultScope.GLOBAL_STOP), None)
        global_fault = global_fault or next(iter(self._actors.faults), None)
        if global_fault is not None:
            self._runtime.fail_market_reads(global_fault)
            self._actors.request_stop()
            self._finished = True
            raise MarketContinuationFault(global_fault)
        if self._actors.stopped:
            raise MarketContinuationCancelled('MARKET_CONTINUATION_STOPPED')
        self._require_open()
        own = [message for message in completions
               if message.identity.domain_task_id == self._lease.identity.domain_task_id
               and message.identity.module is self._lease.identity.module
               and message.identity.cycle_id == self._lease.identity.cycle_id]
        if own:
            if (len(own) != 1 or self._request is None or own[0].identity != self._request.identity):
                self._actors.invalidate_owner_result()
                raise OrderResourceOwnershipError()
            message, self._request = own[0], None
            if message.terminal is MarketTerminal.CANCELLED:
                raise MarketContinuationCancelled('MARKET_CONTINUATION_CANCELLED')
            if message.fault is not None:
                self._finished = True
                raise MarketContinuationFault(message.fault)
            self._require_open()
            try:
                self._research.accept_actor(message.result)
            except Exception as error:
                self._finished = True
                fault = _fault(error, self._actors.admission)
                if fault.scope is MarketFaultScope.GLOBAL_STOP:
                    self._runtime.fail_market_reads(fault)
                    self._actors.request_stop()
                raise MarketContinuationFault(fault) from error
        if self._request is not None:
            return None
        if self._research.ready:
            self._require_open()
            result = self._research.finish()
            self._require_open()
            self._finished = True
            return BusinessResearchCompletion(self._lease.identity, result)
        query = self._research.market_query
        if query is not None:
            if self._actors.site_deferred(query.source):
                from src.workflow.market_messages import MarketFault
                raise MarketContinuationFault(MarketFault(MarketFaultScope.SITE_DEFER, 'MARKET_AUTH_REQUIRED'))
            request = self._runtime.prepare_business_market_read(self._lease, query, due_at=self._due_at)
            if request is None:
                raise RuntimeError('OWNER_RESEARCH_REQUEST_ALREADY_PENDING')
            if not self._actors.admit(request):
                raise MarketContinuationCancelled('MARKET_CONTINUATION_STOPPED')
            self._request = request
            self._actors.dispatch_ready()
            return None
        if not self._actors.owner_source_available(self._research.source):
            return None
        try:
            value = self._research.read_owner()
            self._require_open()  # Includes failures softened by old adapters.
            native = getattr(value, 'source_result', value)
            if any(field.key == 'failure_code' and field.value in SITE_AUTH_RECOVERY_REASONS
                   for field in native.evidence.fields if isinstance(field.value, str)):
                from src.workflow.market_messages import MarketFault
                raise MarketContinuationFault(MarketFault(MarketFaultScope.SITE_DEFER, 'MARKET_AUTH_REQUIRED'))
            self._research.accept_owner(value)
        except MarketContinuationFault:
            self._finished = True
            raise
        except Exception as error:
            self._finished = True
            fault = _fault(error, self._actors.admission)
            if fault.scope is MarketFaultScope.GLOBAL_STOP:
                self._runtime.fail_market_reads(fault)
                self._actors.request_stop()
            raise MarketContinuationFault(fault) from error
        return None
