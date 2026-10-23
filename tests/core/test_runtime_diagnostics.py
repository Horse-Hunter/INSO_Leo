"""Offline lifetime evidence: synthetic processes, never the installed app."""

import faulthandler
import json
import os
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path

import pytest

from src.core import RuntimeDiagnostics, run_monitored
from src.core import runtime_diagnostics as module

ROOT = Path(__file__).resolve().parents[2]
SECRET = "CUSTOMER_PASSWORD_DO_NOT_RECORD"


def events(diagnostics):
    path = diagnostics.directory / f"runtime-{diagnostics.run_id}.events.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines()]


@pytest.fixture
def diagnostic(tmp_path):
    item = RuntimeDiagnostics(tmp_path, observer=False, native=False).start()
    try:
        yield item
    finally:
        item.finish(0)


def test_real_thread_and_tk_hooks_omit_exception_values(diagnostic):
    def fail():
        private_local = SECRET
        raise ValueError(private_local)

    worker = threading.Thread(target=fail, name=SECRET)
    worker.start()
    worker.join(timeout=5)
    assert not worker.is_alive()
    try:
        fail()
    except ValueError:
        diagnostic.tk_exception(*sys.exc_info())
        sys.excepthook(*sys.exc_info())
    rows = events(diagnostic)
    assert {"thread_exception", "tk_exception", "main_exception"} <= {row["event"] for row in rows}
    assert SECRET not in json.dumps(rows)
    assert all(row["frames"][-1]["function"] == "fail" for row in rows if "frames" in row)
    assert all(row["error_type"] == "ValueError" for row in rows if "error_type" in row)


def test_hook_restore_and_distinct_duplicate_run(tmp_path):
    before = sys.excepthook, threading.excepthook
    first = RuntimeDiagnostics(tmp_path, observer=False, native=False).start()
    try:
        second = RuntimeDiagnostics(tmp_path, observer=False, native=False).start()
        second.request_exit("duplicate_instance")
        second.finish(0)
        assert first.run_id != second.run_id
        assert not any(row["event"].startswith("previous_") for row in events(second))
        assert first.state_path.exists() and second.state_path.exists()
    finally:
        first.finish(0)
    assert (sys.excepthook, threading.excepthook) == before


@pytest.mark.parametrize("payload", ["[]", "null", "bad-json", '{"pid": "bad"}'])
def test_corrupted_old_state_cannot_prevent_start(tmp_path, payload):
    directory = tmp_path / "runtime/logs"
    directory.mkdir(parents=True)
    (directory / f"runtime-{uuid.uuid4().hex}.state.json").write_text(payload)
    item = RuntimeDiagnostics(tmp_path, observer=False, native=False).start()
    try:
        assert item.healthy
    finally:
        item.finish(0)


def test_dead_previous_run_and_bounded_retention(tmp_path, monkeypatch):
    directory = tmp_path / "runtime/logs"
    directory.mkdir(parents=True)
    for _ in range(24):
        run_id = uuid.uuid4().hex
        (directory / f"runtime-{run_id}.state.json").write_text(json.dumps({"pid": 123}))
    unrelated = directory / "INSO_V1.3.log"
    unrelated.write_text("existing")
    monkeypatch.setattr(module, "_alive", lambda _: False)
    item = RuntimeDiagnostics(tmp_path, observer=False, native=False).start()
    try:
        assert len(list(directory.glob("runtime-*.state.json"))) == 20
        assert any(row["event"] == "previous_exit_unobserved" for row in events(item))
        assert unrelated.read_text() == "existing"
    finally:
        item.finish(0)


def test_write_failure_reports_unhealthy_without_raising(tmp_path, monkeypatch):
    def deny(*_args):
        raise PermissionError(SECRET)

    monkeypatch.setattr(module, "_atomic_json", deny)
    item = RuntimeDiagnostics(tmp_path, observer=False, native=False).start()
    try:
        assert not item.healthy
        item.gui_ready()
        item.request_exit()
    finally:
        item.finish(0)


def test_entry_captures_import_error_without_message(tmp_path, monkeypatch):
    factory = lambda root: RuntimeDiagnostics(root, observer=False, native=False)
    monkeypatch.setattr(module, "RuntimeDiagnostics", factory)

    def broken_loader():
        raise ImportError(SECRET)

    assert run_monitored(broken_loader, tmp_path) == 1
    files = list((tmp_path / "runtime/logs").glob("*.events.jsonl"))
    assert "main_exception" in files[0].read_text()
    assert SECRET not in files[0].read_text()


@pytest.mark.skipif(os.name != "nt", reason="Windows process handle observer")
@pytest.mark.parametrize("action, expected, classification", [
    ("d.request_exit(); d.finish(0)", 0, "normal"),
    ("d.request_exit('duplicate_instance'); d.finish(0)", 0, "normal"),
    ("d.finish(0)", 0, "unexpected"),
    ("os._exit(0)", 0, "unexpected"),
    ("os._exit(7)", 7, "unexpected"),
    ("os._exit(-1073741819)", 0xC0000005, "unexpected"),
    ("d.state_path.write_text('[]'); os._exit(8)", 8, "unexpected"),
])
def test_actual_observer_exit_codes(tmp_path, action, expected, classification):
    code = (
        "import os,sys,faulthandler; from pathlib import Path; "
        "from src.core import RuntimeDiagnostics; "
        "d=RuntimeDiagnostics(Path(sys.argv[1])).start(); "
        "assert d.healthy; assert faulthandler.is_enabled(); "
        "faulthandler.dump_traceback(file=d._fatal); " + action
    )
    result = subprocess.run([sys.executable, "-c", code, str(tmp_path)], cwd=ROOT,
                            capture_output=True, timeout=15, check=False)
    assert result.returncode == expected, result.stderr.decode(errors="replace")
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        receipts = list((tmp_path / "runtime/logs").glob("*.exit.json"))
        if receipts:
            break
        time.sleep(0.03)
    assert receipts, "Independent observer did not write an exit receipt"
    receipt = json.loads(receipts[0].read_text())
    assert receipt["exit_code"] == expected
    assert receipt["classification"] == classification
    assert receipt["exit_code_hex"] == f"0x{expected:08X}"
    assert "<module>" in next((tmp_path / "runtime/logs").glob("*.fatal.log")).read_text()
    assert not any(tmp_path.rglob("*.sqlite*"))


def test_real_tk_callback_keeps_loop_alive(diagnostic):
    import tkinter

    root = tkinter.Tk()
    root.withdraw()
    root.report_callback_exception = diagnostic.tk_exception
    reached = []

    def fail():
        raise RuntimeError(SECRET)

    try:
        root.after(0, fail)
        root.after(1, lambda: reached.append(True))
        root.after(30, root.quit)
        root.mainloop()
        assert reached
        assert any(row["event"] == "tk_exception" for row in events(diagnostic))
        assert SECRET not in json.dumps(events(diagnostic))
    finally:
        root.destroy()


def test_native_flag_unchanged_when_disabled(diagnostic):
    before = faulthandler.is_enabled()
    diagnostic.finish(0)
    assert faulthandler.is_enabled() == before


@pytest.mark.parametrize("failed_part", ["observer", "native"])
def test_partial_monitor_failure_is_visible(tmp_path, monkeypatch, failed_part):
    def fail(*_args, **_kwargs):
        raise OSError(SECRET)

    if failed_part == "observer":
        if os.name != "nt":
            pytest.skip("Windows observer")
        monkeypatch.setattr(RuntimeDiagnostics, "_start_observer", fail)
    else:
        monkeypatch.setattr(faulthandler, "enable", fail)
    item = RuntimeDiagnostics(tmp_path, observer=failed_part == "observer",
                              native=failed_part == "native").start()
    try:
        assert item.available and not item.healthy
        rows = events(item)
        assert any(row["event"] == ("observer_failed" if failed_part == "observer"
                                   else "native_capture_failed") for row in rows)
        assert SECRET not in json.dumps(rows)
    finally:
        item.finish(0)


@pytest.mark.parametrize("exit_code", [None, 0, 3])
def test_explicit_system_exit_keeps_exit_code(tmp_path, monkeypatch, exit_code):
    factory = lambda root: RuntimeDiagnostics(root, observer=False, native=False)
    monkeypatch.setattr(module, "RuntimeDiagnostics", factory)

    def main(**_kwargs):
        raise SystemExit(exit_code)

    assert run_monitored(lambda: main, tmp_path) == (exit_code or 0)


@pytest.mark.skipif(os.name != "nt", reason="Windows process handle observer")
@pytest.mark.parametrize("intent, error, expected, classification", [
    (None, "SystemExit(0)", 0, "unexpected"),
    (None, "SystemExit(None)", 0, "unexpected"),
    ("owner_exit", "SystemExit(0)", 0, "normal"),
    ("duplicate_instance", "SystemExit(0)", 0, "normal"),
    ("command_exit", "SystemExit(0)", 0, "normal"),
    (None, "SystemExit(7)", 7, "unexpected"),
    ("owner_exit", "SystemExit(7)", 7, "unexpected"),
    (None, "SystemExit('CUSTOMER_PASSWORD_DO_NOT_RECORD')", 1, "unexpected"),
    (None, "RuntimeError('CUSTOMER_PASSWORD_DO_NOT_RECORD')", 1, "unexpected"),
])
def test_monitored_main_actual_exit_classification(tmp_path, intent, error, expected, classification):
    code = (
        "import sys\nfrom src.core import run_monitored\n"
        "def main(*, diagnostics):\n"
        "    assert diagnostics.healthy\n"
        f"    intent = {intent!r}\n"
        "    if intent is not None: diagnostics.request_exit(intent)\n"
        "    private_local = 'CUSTOMER_PASSWORD_DO_NOT_RECORD'\n"
        f"    raise {error}\n"
        "raise SystemExit(run_monitored(lambda: main, sys.argv[1]))\n"
    )
    result = subprocess.run([sys.executable, "-c", code, str(tmp_path)], cwd=ROOT,
                            capture_output=True, timeout=15, check=False)
    assert result.returncode == expected, result.stderr.decode(errors="replace")
    directory = tmp_path / "runtime/logs"
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        receipts = list(directory.glob("*.exit.json"))
        if receipts:
            break
        time.sleep(0.03)
    assert receipts, "Observer did not record the monitored main exit"
    receipt = json.loads(receipts[0].read_text())
    assert receipt["exit_code"] == expected
    assert receipt["exit_code_hex"] == f"0x{expected:08X}"
    assert receipt["classification"] == classification
    state = json.loads(next(directory.glob("*.state.json")).read_text())
    assert state["exit_reason"] == intent
    rows = [json.loads(line) for line in next(directory.glob("*.events.jsonl")).read_text().splitlines()]
    errors = [row for row in rows if row["event"] == "main_exception"]
    assert len(errors) == 1
    assert errors[0]["error_type"] == error.split("(", 1)[0]
    assert errors[0]["frames"][-1]["function"] == "main"
    assert errors[0]["frames"][-1]["line"] > 0
    assert SECRET not in "".join(path.read_text() for path in directory.iterdir() if path.is_file())
