"""Empty TP cycles still produce bounded, strictly sanitized run receipts."""
import logging
import sqlite3
from contextlib import nullcontext
from datetime import timedelta
from types import SimpleNamespace

import pytest

from src.gui.contracts import RunState
from src.gui.main import _SafeRuntimeLogFilter, _sanitized_line
from src.launcher import backend as launcher
from src.workflow.service import WorkflowRuntime
from tests.workflow.test_tp_research import NOW, build


def test_real_empty_tp_engine_has_three_independent_900s_cycles(tmp_path, monkeypatch, caplog):
    backend = launcher.ProductionBackend(root=tmp_path)
    tp, lines, _, transport, path = build(tmp_path / "tp")
    lines.clear()
    time = SimpleNamespace(tick=0.0)
    monkeypatch.setattr(launcher, "monotonic", lambda: time.tick)
    monkeypatch.setattr(launcher, "utc_now", lambda: NOW+timedelta(seconds=time.tick))
    runtime = WorkflowRuntime(None, None, ())
    runtime.configure_modules({"tp": 900}, timer=lambda: time.tick)
    backend._module_runtime, backend._tp, backend._state = runtime, tp, RunState.RUNNING
    backend._observation.enable(tp=True)
    for name in ("_check_site_recovery", "_notify", "_cache_workbench", "_close_inso_order_tab"):
        monkeypatch.setattr(backend, name, lambda *_a, **_k: None)
    waits = []
    def wait(seconds):
        waits.append(seconds)
        time.tick += seconds
        return len(waits) == 3
    monkeypatch.setattr(backend, "_wait_between_polls", wait)
    caplog.set_level(logging.INFO, logger="src.launcher.backend")
    backend._run_independent_poll(runtime, {"spreadsheet_id": "synthetic"}, None,
        SimpleNamespace(poll_scope=nullcontext), SimpleNamespace(discovery_scope=nullcontext), (), None)
    records = [r for r in caplog.records if getattr(r, "scheduled_module", None) == "tp"]
    assert waits == [900, 900, 900]
    assert [r.cycle_phase for r in records] == ["begin", "completed"]*3
    assert len({r.cycle_id for r in records}) == 3
    assert all(r.cycle_due_in == 900 for r in records if r.cycle_phase == "completed")
    assert all(_SafeRuntimeLogFilter().filter(r) and "scheduled_module=tp" in r.msg for r in records)
    assert not transport.calls and not tp.research.calls
    with sqlite3.connect(path) as db:
        assert db.execute('select count(*) from workflow_requirements').fetchone() == (0,)


@pytest.mark.parametrize("field,value", [("scheduled_module", "customer-secret"),
    ("scheduled_module", []), ("cycle_id", "raw customer id"), ("cycle_phase", "private-data"),
    ("cycle_phase", []), ("cycle_elapsed", float('nan')), ("cycle_elapsed", float('inf')),
    ("cycle_due_in", -1), ("cycle_due_in", True), ("cycle_elapsed", "credential")])
def test_cycle_receipt_drops_unvalidated_fields(field, value):
    record = logging.LogRecord("src.launcher.backend", logging.INFO, "", 0,
        "private body must never survive", (), None)
    for key, item in {"cycle_id": "cycle_"+"a"*32,"scheduled_module": "tp","cycle_phase": "completed",
                     "cycle_elapsed": 0.1,"cycle_due_in": 900}.items():
        setattr(record, key, item)
    setattr(record, field, value)
    assert _sanitized_line(record) == "launcher event (INFO)"
