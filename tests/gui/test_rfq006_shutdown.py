"""GUI safe shutdown and login exclusion during independent quotation polling."""

import pytest

from src.gui.contracts import RunState
from src.launcher.backend import ProductionBackend
from tests.gui.test_gui_contracts import (
    _close_test_app,
    _CloseBackend,
    _login_all_app,
    _LoginAllBackend,
)


@pytest.mark.parametrize(
    "state", [RunState.GLOBAL_STOP, RunState.MODULE_PAUSED, RunState.MANUAL_REVIEW]
)
def test_faulted_gui_closes_after_launcher_exits(state):
    events = []
    backend = _CloseBackend(events, state, worker_state="running")
    app = _close_test_app(backend, events)
    app._on_close()
    assert not app._close_finalized
    backend.worker_state = "stopped"
    app._root.run_next()
    assert events[-2:] == [("shutdown",), ("destroy",)]


def test_quotation_running_gui_requests_safe_stop_before_exit():
    events = []
    backend = _CloseBackend(events, RunState.QUOTATION_RUNNING)
    app = _close_test_app(backend, events)
    app._on_close()
    assert backend.stop_requests == 1 and not app._close_finalized
    backend.state = RunState.STOPPED
    app._root.run_next()
    assert app._close_finalized


def test_login_button_disabled_while_quotation_module_continues():
    backend = _LoginAllBackend(state=RunState.QUOTATION_RUNNING)
    app = _login_all_app(backend)
    app._sync_login_all()
    assert app._login_all_button.values["state"] == "disabled" and backend.sweeps == 0


def test_backend_refuses_second_browser_login_sweep_while_quotation_running(tmp_path):
    backend = ProductionBackend(root=tmp_path)
    backend._state = RunState.QUOTATION_RUNNING
    backend.start_login_all_sites()
    assert not backend.login_all_running() and backend._login_all_thread is None
    backend.shutdown()
