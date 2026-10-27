"""Original owner recovery and untruncated large result, no actual browsers."""
import threading
from decimal import Decimal

import pytest

from src.gui.contracts import SiteLoginOutcome, SiteLoginResult
from src.launcher.market_actors import MarketReadActors
from src.launcher.market_continuation import OwnerMarketResearch
from src.research.cdp_pages import PageResourceAdmission
from src.research.market_contracts import MarketReadResult
from src.research.site_login import SiteLoginError
from src.research.source_contracts import ResearchSource as S
from src.research.tp import TpOffer, select_tp_offers
from src.workflow.service import WorkflowRuntime
from tests.launcher.test_market_actors import Session, drain_until, request
from tests.launcher.test_tp_continuation import fixture, run_research
from tests.research.test_tp import NOW


def test_only_exact_successful_original_sweep_reopens_auth_site():
    class AuthSession(Session):
        def __init__(self, config, admission):
            self.owner = threading.get_ident()
        def read(self, query):
            raise SiteLoginError('OTP_REQUIRED')
    runtime = WorkflowRuntime(None, None, ())
    runtime.configure_modules({'quotation': 900, 'tp': 900})
    actors = MarketReadActors(runtime, None, PageResourceAdmission(), session_type=AuthSession)
    actors.start()
    try:
        actors.admit(request('blocked'))
        actors.dispatch_ready()
        drain_until(actors, 1)
        assert actors.site_deferred(S.HQEW)
        assert not actors.recover_sites_on_owner(lambda: (
            SiteLoginResult('华强电子网', SiteLoginOutcome.NEEDS_HUMAN),))
        assert actors.site_deferred(S.HQEW)
        assert not actors.recover_sites_on_owner(lambda: (
            SiteLoginResult('Findchips', SiteLoginOutcome.SIGNED_IN),))
        recovered = actors.recover_sites_on_owner(lambda: (
            SiteLoginResult('华强电子网', SiteLoginOutcome.ALREADY_SIGNED_IN),))
        assert recovered == (S.HQEW,) and not actors.site_deferred(S.HQEW)
        assert not runtime.module_resource_failed
        actors.request_stop()
        with pytest.raises(RuntimeError, match='STOPPED'):
            actors.recover_sites_on_owner(lambda: pytest.fail('Stop cannot invoke recovery'))
    finally:
        assert actors.close()


def test_oversized_legitimate_offers_go_to_owner_without_low_price_truncation(tmp_path, monkeypatch):
    from src.research import tp
    cycle, order, identity, runtime, actors, _, _, _, transport, _ = fixture(tmp_path, monkeypatch)
    original_read = actors._session_type.read
    offers = tuple(TpOffer(S.HQEW, order.mpn, Decimal(10), 'USD', NOW, False)
                   for _ in range(128)) + (TpOffer(S.HQEW, order.mpn, Decimal('0.01'), 'USD', NOW, False),)
    def read(session, query):
        if query.source is S.HQEW:
            return MarketReadResult(query.source, query.mode, offers=offers)
        return original_read(session, query)
    monkeypatch.setattr(actors._session_type, 'read', read)
    original_collect = tp.collect_tp
    def collect(adapter, site, mpn, qty, now, fx):
        if site is S.HQEW:
            return select_tp_offers(site, offers, query=mpn, now=now, fx=fx)
        return original_collect(adapter, site, mpn, qty, now, fx)
    monkeypatch.setattr(tp, 'collect_tp', collect)
    try:
        work = cycle.begin_continuation(order, identity, runtime, now=NOW)
        result = run_research(OwnerMarketResearch(runtime, actors, work.lease, work.research, due_at=0), actors)
        assert result.result.lowest.rmb == Decimal('0.07')  # last of129, never sliced away
        assert result.result.lowest.offer.source is S.HQEW
        assert actors.requires_owner(S.HQEW) and not runtime.module_resource_failed
        work.complete(result)
        assert not transport.calls and runtime.business_resource_counts()['active'] == 0
    finally:
        assert actors.close()
