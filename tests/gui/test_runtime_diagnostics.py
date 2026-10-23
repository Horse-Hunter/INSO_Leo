"""Diagnostic integration uses existing GUI shutdown/startup, no business I/O."""

import json
import sys

import pytest

from src.core import RuntimeDiagnostics
from src.gui import main as launcher
from src.gui.contracts import RunState
from tests.gui.test_gui_contracts import _close_test_app, _CloseBackend
from tests.gui.test_tray import app as tray_app


@pytest.mark.parametrize("acquired, broken, healthy", [
    (True, False, True), (False, False, True), (True, True, True), (True, False, False),
])
def test_startup_exit_and_failed_monitor(monkeypatch, tmp_path, acquired, broken, healthy):
    item = RuntimeDiagnostics(tmp_path, native=False, observer=False).start()
    notices = []
    ran = []

    class Guard:
        def acquire(self):
            return acquired

        def release(self):
            ran.append("release")

    class Backend:
        def shutdown(self):
            ran.append("shutdown")

    class App:
        def __init__(self, backend, *, diagnostics):
            assert diagnostics is item
            if broken:
                raise ValueError("PRIVATE_VALUE")

        def run(self):
            ran.append("run")

    monkeypatch.setattr(sys, "argv", ["INSO_V1.4.exe"])
    monkeypatch.setattr(launcher, "app_root", lambda: tmp_path)
    monkeypatch.setattr(launcher, "_configure_startup_log", lambda _: None)
    monkeypatch.setattr(launcher, "_show_error", lambda message: notices.append(message))
    monkeypatch.setattr(launcher, "InsoDashboardApp", App)
    if not healthy:
        item.available = False
    try:
        code = launcher.main(guard_factory=Guard, backend_factory=Backend, diagnostics=item)
        assert code == int(broken)
        assert ("run" in ran) == (acquired and not broken)
        assert bool(notices) == (broken or not acquired or not healthy)
        if not acquired:
            assert item.state["exit_reason"] == "duplicate_instance"
            assert "shutdown" not in ran
        if broken:
            path = next(item.directory.glob("*.events.jsonl"))
            assert "app_exception" in path.read_text() and "PRIVATE_VALUE" not in path.read_text()
        assert "release" in ran
    finally:
        item.finish(code)


def test_only_actual_exit_sets_owner_intent(tmp_path):
    item = RuntimeDiagnostics(tmp_path, native=False, observer=False).start()
    try:
        hidden, calls = tray_app()
        hidden._runtime_diagnostics = item
        hidden._on_window_close()
        assert calls == ["hide"] and item.state["exit_reason"] is None
        calls = []
        backend = _CloseBackend(calls, RunState.STOPPED)
        closing = _close_test_app(backend, calls)
        closing._runtime_diagnostics = item
        closing._on_close()
        assert item.state["exit_reason"] == "owner_exit"
        assert calls[-1] == ("destroy",)
        rows = [json.loads(line) for line in next(item.directory.glob("*.events.jsonl")).read_text().splitlines()]
        assert sum(row["event"] == "exit_requested" for row in rows) == 1
    finally:
        item.finish(0)
