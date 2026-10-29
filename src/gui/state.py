"""Pure state constructors and transitions for the GUI."""

from __future__ import annotations

from datetime import datetime, timezone

from .contracts import RunSession, RunState


def newest_orders(orders):
    """Immutable intake first; legacy processing fallback, undated rows last.

    Stable identity breaks ties independently of module merge or refresh order.
    This orders presentation only, never scheduling or action permissions.
    """
    def key(order):
        received = order.received_at
        value = received if received is not None else order.processed_at
        group = 0 if received is not None else 1 if value is not None else 2
        return group, -value.timestamp() if value is not None else 0, order.inquiry_id

    return tuple(sorted(orders, key=key))


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def make_empty_session() -> RunSession:
    return RunSession(
        run_id=None,
        state=RunState.STOPPED,
        started_at=None,
        stopped_at=None,
        orders_found=0,
        completed=0,
        in_progress=0,
        pending=0,
        next_poll_at=None,
    )
