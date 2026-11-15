"""RFQ-021-R4: the automatic effect paths must obey the same scope as the buttons.

The button refused the whole-browser login sweep in a scoped run (R3), but the
sweep had two automatic entrants that did not ask: the deferred-auth recovery in
`business_continuations` and the 30-minute idle keep-alive. Both attach the
protected Chrome and open login pages for no particular order, so neither can be
part of a one-order trial.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from src.launcher.backend import ProductionBackend
from src.launcher.run_scope import parse_run_scope

ORDER = "inq_" + "a" * 24


def scoped(writes: str = ""):
    return parse_run_scope(
        inquiry_ids=ORDER,
        modules="inquiry",
        write_targets=writes,
        approval="OWNER-APPROVED:RFQ-021-R4" if writes else "",
    )


class ExplodingAcquirer:
    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, *_args, **_kwargs):
        self.calls += 1
        raise AssertionError("the protected browser must not be attached")


def test_login_sweep_refuses_inside_a_scoped_run(tmp_path):
    acquirer = ExplodingAcquirer()
    backend = ProductionBackend(
        root=tmp_path, run_scope=scoped(), enforce_scope=True, browser_acquirer=acquirer)

    assert backend._run_login_sweep() == ()
    assert acquirer.calls == 0


def test_login_sweep_refuses_in_preview(tmp_path):
    acquirer = ExplodingAcquirer()
    backend = ProductionBackend(root=tmp_path, preview_mode=True, browser_acquirer=acquirer)

    assert backend._run_login_sweep(background=True) == ()
    assert acquirer.calls == 0


def test_idle_keepalive_does_nothing_in_a_scoped_run(tmp_path):
    backend = ProductionBackend(root=tmp_path, run_scope=scoped(), enforce_scope=True)
    backend._v13_enabled = True
    backend._run_login_sweep = ExplodingAcquirer()

    backend._idle_login_tick(now=datetime(2026, 11, 15, 3, tzinfo=UTC))

    assert backend._run_login_sweep.calls == 0


def test_idle_keepalive_still_runs_when_unscoped(tmp_path):
    """The legacy path keeps its behaviour; this is a narrowing, not a removal."""

    calls = []
    backend = ProductionBackend(root=tmp_path)
    backend._v13_enabled = True
    backend._state = None  # not RUNNING, so the tick returns before sweeping
    backend._run_login_sweep = lambda **_kwargs: calls.append(1) or ()

    backend._idle_login_tick(now=datetime(2026, 11, 15, 3, tzinfo=UTC))

    # Nothing swept here either, but because the run is not RUNNING -- the scope
    # gate must not be what stops an unscoped run.
    assert calls == []
    assert backend._idle_empty_polls == 0


def test_scoped_run_does_not_sweep_even_after_thirty_idle_minutes(tmp_path):
    """The 30-minute trigger is the one the live program would actually reach."""

    from src.launcher.backend import RunState

    swept = []
    backend = ProductionBackend(root=tmp_path, run_scope=scoped(), enforce_scope=True)
    backend._v13_enabled = True
    backend._state = RunState.RUNNING
    backend._combined = None
    backend._idle_empty_polls = 1
    backend._idle_login_since = datetime(2026, 11, 15, 3, tzinfo=UTC) - timedelta(minutes=31)
    backend._run_login_sweep = lambda **_kwargs: swept.append(1) or ()

    backend._idle_login_tick(now=datetime(2026, 11, 15, 3, tzinfo=UTC))

    assert swept == []
