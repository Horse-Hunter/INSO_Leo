"""Offline combined GUI projection; no UI windows or business I/O."""
from datetime import datetime, timedelta, timezone

import pytest

from src.gui.app import _countdown_text
from src.gui.contracts import RunSession, RunState

NOW = datetime(2026, 10, 7, tzinfo=timezone.utc)


@pytest.mark.parametrize("state,cooldown,in_progress,next_poll,expected", [
    (RunState.RUNNING, 120, 0, 900, "冷却 02:00"),
    (RunState.RUNNING, 119, 0, 900, "冷却 01:59"),
    (RunState.RUNNING, None, 1, 900, "订单处理中"),
    (RunState.RUNNING, None, 0, 900, "15:00"),
    (RunState.RUNNING, None, 0, None, "即将轮询"),
    (RunState.QUOTATION_RUNNING, None, 0, 900, "15:00"),
    (RunState.QUOTATION_RUNNING, None, 1, None, "订单处理中"),
    (RunState.QUOTATION_RUNNING, 120, 0, 900, "15:00"),
    (RunState.STOPPED, 120, 1, 900, "00:00"),
    (RunState.MODULE_PAUSED, 120, 1, 900, "00:00"),
    (RunState.GLOBAL_STOP, 120, 1, 900, "00:00"),
])
def test_combined_countdown_preserves_quotation_and_purchase_isolation(
    state, cooldown, in_progress, next_poll, expected
):
    session = RunSession(None, state, None, None, in_progress=in_progress,
        next_poll_at=NOW + timedelta(seconds=next_poll) if next_poll is not None else None,
        row_cooldown_until=NOW + timedelta(seconds=cooldown) if cooldown is not None else None)
    assert _countdown_text(session, NOW) == expected
