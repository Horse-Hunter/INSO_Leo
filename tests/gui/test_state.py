"""Tests for pure GUI state helpers."""

from src.gui.contracts import RunState
from src.gui.state import make_empty_session, utc_now


def test_utc_now_returns_aware_datetime():
    now = utc_now()
    assert now.tzinfo is not None
    assert now.utcoffset() is not None


def test_make_empty_session_is_stopped():
    session = make_empty_session()
    assert session.state == RunState.STOPPED
    assert session.run_id is None
    assert session.orders_found == 0
    assert session.completed == 0
    assert session.in_progress == 0
    assert session.pending == 0
