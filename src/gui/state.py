"""Pure state constructors and transitions for the GUI."""

from __future__ import annotations

from datetime import datetime, timezone

from .contracts import RunSession, RunState


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
