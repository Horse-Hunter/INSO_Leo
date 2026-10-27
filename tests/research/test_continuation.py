"""Same six-source implementation driven synchronously or by owner continuation."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from decimal import Decimal
from types import SimpleNamespace

import pytest

from src.research.contracts import ResearchInput
from src.research.market_contracts import MarketReadMode, MarketReadResult
from src.research.source_contracts import PRICE_SOURCES, SourceOutcome
from src.research.source_contracts import ResearchSource as S
from src.research.tp import TpOffer
from src.sheets.tp_brief import bind_tp_order
from tests.research.test_aggregation_service import NOW, _complete, _result, _service
from tests.research.test_tp import Fx
from tests.sheets.test_tp_brief import brief, source


def test_ordinary_same_aggregation_output_and_owner_observations(tmp_path):
    values = _complete({S.INSO: _result(S.INSO, SourceOutcome.SUCCESS, '9'),
                        S.HQEW: _result(S.HQEW, SourceOutcome.SUCCESS, '8')})
    direct = _service(tmp_path / 'direct.xlsx', values)
    stepped = _service(tmp_path / 'stepped.xlsx', values)
    writes, observations, contexts = [], [], []
    stepped._output = SimpleNamespace(upsert=lambda *args, **kwargs: writes.append((args, kwargs)))
    stepped._source_observer = lambda task, value: observations.append((task, value.source))
    def protected(task, operation):
        contexts.append(task)
        return operation()
    stepped._inso_query = protected
    item = ResearchInput('inq_synthetic', 'ABC', None, 10, 'A')
    expected = direct.execute_detailed(item)
    work = stepped.begin_detailed(item, now=NOW)
    actors = []
    while not work.ready:
        query = work.market_query
        if query is not None:
            actors.append(query.source)
            work.accept_actor(stepped.read_market_source(query))
        else:
            work.accept_owner(work.read_owner())
    actual = work.finish()
    assert actual == expected
    assert actors == [S.IC_NET, S.HQEW]
    assert observations == [(item.inquiry_id, site) for site in PRICE_SOURCES]
    assert contexts == [item.inquiry_id]
    assert len(writes) == 1 and writes[0][0] == (item.inquiry_id,)
    with pytest.raises(RuntimeError, match='NOT_READY_OR_FINISHED'):
        work.finish()


def test_tp_owner_single_fx_snapshot_and_no_ordinary_output(tmp_path, monkeypatch):
    from src.research import tp
    from tests.research.test_tp import NOW as TP_NOW
    calls = []
    class CountingFx(Fx):
        def get_quote(self):
            calls.append('fx')
            return super().get_quote()
    service = _service(tmp_path / 'unused.xlsx', _complete())
    service._fx_provider = CountingFx()
    service._output = SimpleNamespace(upsert=lambda *a, **kw: pytest.fail('TP ordinary output'))
    order = replace(bind_tp_order(brief(), 'synthetic', [source()]), currency='USD')
    monkeypatch.setattr(tp, 'collect_tp', lambda adapter, site, mpn, qty, now, fx:
        tp.select_tp_offers(site, (TpOffer(site, mpn, Decimal(3), 'USD', now, False),),
                            query=mpn, now=now, fx=fx))
    work = service.begin_tp('tp_synthetic', order, now=TP_NOW)
    while not work.ready:
        query = work.market_query
        if query is None or query.source is S.IC_NET:
            work.accept_owner(work.read_owner())
        else:
            work.accept_actor(MarketReadResult(query.source, MarketReadMode.TP_OFFERS,
                offers=(TpOffer(query.source, order.mpn, Decimal(2), 'USD', TP_NOW, False),)))
    result = work.finish()
    assert calls == ['fx']
    assert len(result.sources) == 6 and result.lowest.rmb == Decimal(14)
    assert result.second.rmb == Decimal(21)
    assert result.target_rmb == order.target_price * 7


def test_out_of_order_wrong_thread_and_incomplete_finish_are_rejected(tmp_path):
    service = _service(tmp_path / 'unused.xlsx', _complete())
    work = service.begin_detailed(ResearchInput('inq_synthetic', 'ABC', None, 10, 'A'), now=NOW)
    wrong = MarketReadResult(S.HQEW, MarketReadMode.ORDINARY,
                            ordinary=_result(S.HQEW, SourceOutcome.NO_VALID_PRICE))
    with pytest.raises(ValueError, match='RESULT_MISMATCH'):
        work.accept_actor(wrong)
    with pytest.raises(RuntimeError, match='NOT_READY'):
        work.finish()
    with ThreadPoolExecutor(max_workers=1) as pool, pytest.raises(RuntimeError, match='THREAD_MISMATCH'):
        pool.submit(work.read_owner).result()
    assert work.source is S.IC_NET
