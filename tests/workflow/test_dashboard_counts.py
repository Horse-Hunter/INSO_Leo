"""Dashboard snapshot counts with synthetic Sheets and the real local ledger."""
from dataclasses import replace

import pytest

from src.sheets import WorksheetIdentity, WorksheetRow
from src.workflow.dashboard_counts import DashboardCounts, read_dashboard_counts
from src.workflow.v12_faults import V12Fault
from tests.workflow.test_purchase_follow_up import local, setup_follow_up
from tests.workflow.test_v13_quotation import WS, source


def test_source_counts_include_invalid_new_rows_history_and_holds_without_side_effects(tmp_path):
    db, store, sheets, holds, _, _, _, follow, now, _ = setup_follow_up(tmp_path)
    sheets.rows += [source(3, "未发", model="BAD"), source(4, "采购已报价"),
                    source(5, model="UNBOUND"), source(6, "成交")]
    before = db.read_bytes()
    counts = read_dashboard_counts(sheets, (WS,), store=store, episodes=follow.episodes, now=now[0])
    assert counts == DashboardCounts(1, 2, 1)
    assert db.read_bytes() == before
    assert holds.active() == ()
    # Repeated snapshots do not accumulate or depend on notification delivery.
    assert read_dashboard_counts(sheets, (WS,), store=store, episodes=follow.episodes, now=now[0]) == counts
    assert follow.run(WS) == 1
    assert read_dashboard_counts(sheets, (WS,), store=store, episodes=follow.episodes, now=now[0]) == counts
    sheets.rows = [source(2, "采购已报价")]
    assert read_dashboard_counts(sheets, (WS,), store=store, episodes=follow.episodes, now=now[0]) == DashboardCounts()


@pytest.mark.parametrize("stamp", [False, True])
def test_ambiguous_and_untimed_rows_are_counted_waiting_without_guessed_timeout(tmp_path, stamp):
    _, store, sheets, _, _, _, _, follow, now, _ = setup_follow_up(tmp_path, stamp=stamp)
    sheets.rows = [source(8), source(9)]
    assert read_dashboard_counts(sheets, (WS,), store=store, episodes=follow.episodes, now=now[0]) == DashboardCounts(0, 2, 0)
    if not stamp:
        sheets.rows = [source(2)]
        assert read_dashboard_counts(sheets, (WS,), store=store, episodes=follow.episodes, now=now[0]) == DashboardCounts(0, 1, 0)


@pytest.mark.parametrize("now,expected", [
    ("2026-10-09T18:00", 0), ("2026-10-11T18:00", 0),
    ("2026-10-12T11:00", 0), ("2026-10-12T11:00:01", 1),
])
def test_overdue_uses_strict_working_time_threshold(tmp_path, now, expected):
    _, store, sheets, _, _, _, _, follow, _, _ = setup_follow_up(tmp_path)
    assert read_dashboard_counts(sheets, (WS,), store=store, episodes=follow.episodes, now=local(now)).overdue_quotation == expected


def test_cross_worksheet_sum_reads_once_and_uses_shahab_columns():
    other = WorksheetIdentity("sheet", "SHAHAB")
    class Reader:
        def __init__(self):
            self.calls = []
        def read_rows(self, worksheet):
            self.calls.append(worksheet)
            if worksheet == other:
                return [WorksheetRow(2, {"A": "未发", "B": "发给采购", "D": "PART", "F": 1}),
                        WorksheetRow(3, {"B": "未发", "D": "OTHER", "F": "bad"})]
            return [source(2, "未发"), source(3)]
    reader = Reader()
    assert read_dashboard_counts(reader, (WS, other, WS), store=None, episodes=None,
                                 now=local("2026-10-12T11:00")) == DashboardCounts(2, 2, 0)
    assert reader.calls == [WS, other]


def test_late_sheet_read_failure_does_not_publish_partial_counts(tmp_path):
    from src.launcher.backend import ProductionBackend
    backend = ProductionBackend(root=tmp_path)
    backend._dashboard_counts = DashboardCounts(3, 4, 1)
    class Reader:
        def read_rows(self, worksheet):
            if worksheet == WS:
                return [source(2, "未发")]
            raise OSError("offline failure")
    with pytest.raises(V12Fault, match="SHEETS_READ_UNAVAILABLE"):
        backend._refresh_dashboard_counts(Reader(), (WS, replace(WS, worksheet="other")),
                                          episodes=None, now=local("2026-10-12T11:00"))
    session = backend.get_status()
    assert (session.new_orders, session.awaiting_quotation, session.overdue_quotation) == (3, 4, 1)
    backend.shutdown()


def test_backend_projection_is_not_changed_by_workflow_seen_or_manual_retry(tmp_path):
    from src.launcher.backend import ProductionBackend
    backend = ProductionBackend(root=tmp_path)
    assert backend.get_status().new_orders is None
    class Reader:
        def __init__(self):
            self.rows = [source(2, "未发"), source(3)]
        def read_rows(self, worksheet):
            return self.rows
    reader = Reader()
    backend._refresh_dashboard_counts(reader, (WS,), episodes=None, now=local("2026-10-12T11:00"))
    backend._seen("quotation-history")
    backend._begin_poll_projection()
    status = backend.get_status()
    assert (status.new_orders, status.awaiting_quotation, status.overdue_quotation) == (1, 1, 0)
    reader.rows = []
    backend._refresh_dashboard_counts(reader, (WS,), episodes=None, now=local("2026-10-12T11:15"))
    assert backend.get_status().new_orders == backend.get_status().awaiting_quotation == 0
    backend.shutdown()


def test_held_overdue_order_is_counted_and_new_sending_resets_timeout(tmp_path):
    from src.workflow.v13_quotation import (
        QuotationOutcome,
        RowErrorReason,
        V13QuotationResult,
    )

    db, store, sheets, holds, _, _, _, follow, now, iid = setup_follow_up(tmp_path)
    identity = store.get_by_inquiry_id(iid).record_identity
    holds.hold(V13QuotationResult(iid, identity, "MPN", QuotationOutcome.ROW_FAILED, None,
                                 RowErrorReason.UPDATE_RESULT_UNCONFIRMED, WS, 2), identity)
    before = db.read_bytes()
    assert read_dashboard_counts(sheets, (WS,), store=store, episodes=follow.episodes,
                                 now=now[0]) == DashboardCounts(0, 1, 1)
    assert db.read_bytes() == before and len(holds.active()) == 1
    follow.episodes.record_confirmed(iid, confirmed_at=now[0])
    assert read_dashboard_counts(sheets, (WS,), store=store, episodes=follow.episodes,
                                 now=now[0]) == DashboardCounts(0, 1, 0)
