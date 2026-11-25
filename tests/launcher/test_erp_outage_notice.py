"""An ERP outage must be reported even when no purchase order is waiting.

Owner finding 2026-11-25: the program sat on a failing INSO session for a day and
nothing was sent. The browser channel got a program-level notice on 2026-11-23;
the ERP page is the same kind of news -- quotation stops too -- so it uses the same
mechanism, the same 45-minute duration rule and the same single Owner recipient.
"""
from types import SimpleNamespace

from tests.launcher.test_runtime_safety_notice import _block, _blocked_site


def test_an_erp_outage_reports_even_with_no_order_at_all(tmp_path, monkeypatch):
    backend, worker, smtp, clock = _blocked_site(tmp_path, monkeypatch, site="INSO")
    # No pending purchase order anywhere in the ledger.
    backend._store = SimpleNamespace(all_items=list, get_by_inquiry_id=lambda _id: None)

    _block(backend, worker, clock, 46, cycle="cycle-46", site="INSO")

    assert smtp.send_attempts == 1
    text = smtp.message.get_body(preferencelist=("plain",)).get_content()
    assert "INSO" in text
    assert smtp.message["To"] == "linan229@qq.com"


def test_a_short_erp_outage_stays_silent(tmp_path, monkeypatch):
    backend, worker, smtp, clock = _blocked_site(tmp_path, monkeypatch, site="INSO")
    backend._store = SimpleNamespace(all_items=list, get_by_inquiry_id=lambda _id: None)

    for minutes, cycle in ((0, "c0"), (15, "c15"), (30, "c30")):
        _block(backend, worker, clock, minutes, cycle=cycle, site="INSO")
        assert smtp.send_attempts == 0


def test_an_erp_outage_is_not_mailed_twice(tmp_path, monkeypatch):
    backend, worker, smtp, clock = _blocked_site(tmp_path, monkeypatch, site="INSO")
    backend._store = SimpleNamespace(all_items=list, get_by_inquiry_id=lambda _id: None)

    _block(backend, worker, clock, 46, cycle="cycle-46", site="INSO")
    _block(backend, worker, clock, 61, cycle="cycle-61", site="INSO")

    assert smtp.send_attempts == 1
