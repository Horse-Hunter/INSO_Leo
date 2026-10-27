"""Canonical parsers and scope fault tests; no production/browser access."""
from dataclasses import replace
from decimal import Decimal
from types import SimpleNamespace

import pytest

from src.research.cdp_pages import (
    PageResourceAdmission,
    PageTargetOwnershipError,
    close_research_page,
    market_read_pages,
    native_page_owner,
    new_background_page,
)
from src.research.hqew import HqewAdapter
from src.research.market_contracts import MarketReadMode, MarketReadQuery
from src.research.service import ResearchService
from src.research.source_contracts import ResearchSource
from src.research.tp import TpFx, collect_tp, select_tp_offers
from tests.research.test_cdp_pages import RacingTargets
from tests.research.test_hqew import NOW, Client, _row

OWNER = 'market-' + 'a' * 32


def attach_scope_target(protocol, page):
    page.context = protocol
    page.closed = False
    page.is_closed = lambda: page.closed
    page.close = lambda: setattr(page, 'closed', True)
    for candidate in protocol.pages:
        if not hasattr(candidate, 'is_closed'):
            candidate.is_closed = lambda: False
    return page


def test_market_scope_proves_native_target_after_marker_clears_and_closes_only_it():
    protocol = RacingTargets()
    admission = PageResourceAdmission()
    protocol._inso_page_admission = admission
    with market_read_pages(OWNER, admission):
        page = attach_scope_target(protocol, new_background_page(protocol, protocol, timeout_ms=1234))
        assert native_page_owner(page) == OWNER
        page.owner_name = ''  # Legitimate cross-origin window.name clearing.
        close_research_page(page)
        assert page.closed
        assert not protocol.pages[0].is_closed()
    admission.require_open()


@pytest.mark.parametrize('mode', ['missing_native', 'reassigned_review', 'foreign_page'])
def test_market_scope_uncertainty_is_shared_hard_fault_and_preserves_review(mode):
    protocol = RacingTargets()
    admission = PageResourceAdmission()
    protocol._inso_page_admission = admission
    with pytest.raises(PageTargetOwnershipError), market_read_pages(OWNER, admission):
        page = attach_scope_target(protocol, new_background_page(protocol, protocol, timeout_ms=1234))
        if mode == 'missing_native':
            del page._inso_native_page_owner
        elif mode == 'reassigned_review':
            page.owner_name = 'INSO_OWNER_TAB:human-review'
        else:
            page = SimpleNamespace(is_closed=lambda: False, close=lambda: pytest.fail('foreign close'))
        close_research_page(page)
    with pytest.raises(PageTargetOwnershipError):
        admission.require_open()


def test_read_market_reuses_normal_adapter_and_raw_tp_parser_without_output_or_callbacks():
    adapter = HqewAdapter(Client(_row('SYNTHETIC', '2', NOW.isoformat()) +
                                  _row('SYNTHETIC', '3', NOW.isoformat())), clock=lambda: NOW)
    def forbidden(*_args):
        pytest.fail('no owner callback or output in acquisition')
    service = ResearchService(icnet=None, findchips=None, hqew=adapter, lcsc=None,
                              bom_ai=None, inso=None, output=SimpleNamespace(upsert=forbidden),
                              source_observer=forbidden, source_query=forbidden, inso_query=forbidden)
    query = MarketReadQuery(ResearchSource.HQEW, MarketReadMode.TP_OFFERS, 'SYNTHETIC', 10, NOW)
    raw = service.read_market_source(query)
    assert [offer.price for offer in raw.offers] == [Decimal(2), Decimal(3)]
    assert all(offer.quoted_at == NOW for offer in raw.offers)
    fx = TpFx(None, NOW)  # RMB does not call any FX provider.
    owner_selected = select_tp_offers(query.source, raw.offers, query=query.mpn, now=NOW, fx=fx)
    assert owner_selected == collect_tp(adapter, query.source, query.mpn, 10, NOW, TpFx(None, NOW))
    ordinary = service.read_market_source(replace(query, mode=MarketReadMode.ORDINARY))
    assert ordinary.ordinary.price_candidate.raw_price == Decimal(2)
