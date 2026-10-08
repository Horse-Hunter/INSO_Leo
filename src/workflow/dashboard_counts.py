"""Read-only, per-poll source counts; no processing totals or notification effects."""
from dataclasses import dataclass

from src.sheets import query_pending_records, query_quotation_candidates

from .purchase_follow_up import purchase_episode_overdue
from .v13_quotation import V13Candidate, _read_source_rows, read_v13_candidates


@dataclass(frozen=True, slots=True)
class DashboardCounts:
    new_orders: int = 0
    awaiting_quotation: int = 0
    overdue_quotation: int = 0


def read_dashboard_counts(reader, worksheets, *, store, episodes, now):
    """Count all source rows; infer timeout only through canonical unique binding."""
    new_orders = awaiting = overdue = 0
    for worksheet in dict.fromkeys(worksheets):
        rows = _read_source_rows(reader, worksheet)

        class SnapshotReader:
            def __init__(self, source_rows):
                self.rows = source_rows

            def read_rows(self, requested):
                return self.rows

        snapshot = SnapshotReader(rows)
        new_orders += len(query_pending_records(snapshot, worksheet))
        awaiting += len(query_quotation_candidates(snapshot, worksheet))
        if store is not None and episodes is not None:
            for candidate in read_v13_candidates(snapshot, worksheet, store):
                if isinstance(candidate, V13Candidate) and purchase_episode_overdue(
                    episodes.latest(candidate.inquiry_id), now,
                ):
                    overdue += 1
    return DashboardCounts(new_orders, awaiting, overdue)
