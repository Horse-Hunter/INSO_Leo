"""Private-data-free application lifetime receipts and Windows exit observation."""

from __future__ import annotations

import ctypes
import faulthandler
import json
import logging
import os
import re
import subprocess
import sys
import threading
import time
import uuid
from ctypes import wintypes
from datetime import UTC, datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

_RUN_ID = re.compile(r"[0-9a-f]{32}")
_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_<>.]{0,95}")
_EVENTS = {"start", "gui_ready", "exit_requested", "app_exception", "shutdown_exception",
           "main_exception", "thread_exception", "tk_exception", "app_finished",
           "observer_started", "observer_failed", "native_capture_failed",
           "previous_exit_unobserved", "previous_abnormal_exit"}


class _ReceiptHandler(RotatingFileHandler):
    def handleError(self, record):
        raise OSError("DIAGNOSTIC_WRITE_FAILED")


def _now():
    return datetime.now(UTC).isoformat()


def _atomic_json(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=True)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def _kernel():
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
    kernel.CloseHandle.restype = wintypes.BOOL
    kernel.WaitForSingleObject.argtypes = (wintypes.HANDLE, wintypes.DWORD)
    kernel.WaitForSingleObject.restype = wintypes.DWORD
    kernel.GetExitCodeProcess.argtypes = (wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD))
    kernel.GetExitCodeProcess.restype = wintypes.BOOL
    kernel.GetProcessId.argtypes = (wintypes.HANDLE,)
    kernel.GetProcessId.restype = wintypes.DWORD
    return kernel


def _alive(pid):
    if os.name != "nt":
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False
    kernel = _kernel()
    handle = kernel.OpenProcess(0x1000, False, pid)
    if not handle:
        # Access denied is not proof of exit, and PID reuse must not be guessed.
        return ctypes.get_last_error() != 87
    try:
        code = wintypes.DWORD()
        return not kernel.GetExitCodeProcess(handle, ctypes.byref(code)) or code.value == 259
    finally:
        kernel.CloseHandle(handle)


def watch_runtime(handle, run_id, root):
    """Wait only on an inherited process handle; never launch business or restart."""
    if os.name != "nt" or not _RUN_ID.fullmatch(run_id):
        return 2
    directory = Path(root) / "runtime" / "logs"
    state_path = directory / f"runtime-{run_id}.state.json"
    kernel = _kernel()
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
        if not isinstance(state, dict) or state.get("run_id") != run_id or kernel.GetProcessId(handle) != state.get("pid"):
            return 2
        pid = state["pid"]
        _atomic_json(directory / f"runtime-{run_id}.observer.json", {
            "run_id": run_id, "target_pid": state["pid"], "observer_pid": os.getpid(), "at": _now(),
        })
        if kernel.WaitForSingleObject(handle, 0xFFFFFFFF) != 0:
            return 2
        code = wintypes.DWORD()
        if not kernel.GetExitCodeProcess(handle, ctypes.byref(code)):
            return 2
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            state = {}
        if not isinstance(state, dict):
            state = {}
        normal = code.value == 0 and state.get("completed") is True and state.get("exit_reason") in {
            "owner_exit", "duplicate_instance", "command_exit",
        }
        _atomic_json(directory / f"runtime-{run_id}.exit.json", {
            "run_id": run_id, "pid": pid, "observed_at": _now(),
            "exit_code": code.value, "exit_code_hex": f"0x{code.value:08X}",
            "classification": "normal" if normal else "unexpected",
        })
        return 0
    except (OSError, ValueError, TypeError, KeyError):
        return 2
    finally:
        kernel.CloseHandle(handle)


class RuntimeDiagnostics:
    """One application's bounded receipts. No exception messages/locals are saved."""

    def __init__(self, root, *, observer=True, native=True):
        self.root = Path(root)
        self.directory = self.root / "runtime" / "logs"
        self.run_id = uuid.uuid4().hex
        self.state_path = self.directory / f"runtime-{self.run_id}.state.json"
        self.state = {"run_id": self.run_id, "pid": os.getpid(), "started_at": _now(),
                      "phase": "starting", "completed": False, "exit_reason": None}
        self.available = False
        self._observer_enabled, self._native_enabled = observer, native
        self._lock = threading.RLock()
        self._handler = self._fatal = self._observer = None
        self._old_hooks = None
        self._was_native_enabled = False
        self._native_installed = False
        self._observer_ready = False
        self._finished = False

    @property
    def healthy(self):
        return (self.available and (not self._native_enabled or self._native_installed)
                and (not self._observer_enabled or os.name != "nt" or self._observer_ready))

    def start(self):
        try:
            self.directory.mkdir(parents=True, exist_ok=True)
            self._handler = _ReceiptHandler(
                self.directory / f"runtime-{self.run_id}.events.jsonl",
                maxBytes=131072, backupCount=1, encoding="utf-8",
            )
            self._handler.setFormatter(logging.Formatter("%(message)s"))
            self.available = True
            self._previous_runs()
            self._record("start")
            if self._native_enabled:
                try:
                    self._fatal = (self.directory / f"runtime-{self.run_id}.fatal.log").open("ab", buffering=0)
                    self._was_native_enabled = faulthandler.is_enabled()
                    faulthandler.enable(file=self._fatal, all_threads=True)
                    self._native_installed = True
                except (OSError, RuntimeError, ValueError) as exc:
                    self.exception("native_capture_failed", type(exc), exc.__traceback__)
            if self._observer_enabled and os.name == "nt":
                try:
                    self._start_observer()
                    self._record("observer_started")
                except (OSError, RuntimeError, ValueError) as exc:
                    self.exception("observer_failed", type(exc), exc.__traceback__)
        except OSError:
            self.available = False
        self._old_hooks = (sys.excepthook, threading.excepthook)
        sys.excepthook = lambda kind, _value, trace: self.exception("main_exception", kind, trace)
        threading.excepthook = lambda args: self.exception("thread_exception", args.exc_type, args.exc_traceback)
        return self

    def _start_observer(self):
        kernel = _kernel()
        handle = kernel.OpenProcess(0x100000 | 0x1000, True, os.getpid())
        if not handle:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            if getattr(sys, "frozen", False):
                command = [sys.executable, "--watch-runtime"]
            else:
                command = [sys.executable, "-c",
                    ("import sys; from src.core import watch_runtime; "
                     "raise SystemExit(watch_runtime(int(sys.argv[1]),sys.argv[2],sys.argv[3]))")]
            command += [str(handle), self.run_id, str(self.root.resolve())]
            startup = subprocess.STARTUPINFO()
            startup.lpAttributeList = {"handle_list": [handle]}
            self._observer = subprocess.Popen(
                command, cwd=Path(__file__).resolve().parents[2],
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                close_fds=True, startupinfo=startup, creationflags=subprocess.CREATE_NO_WINDOW,
            )
            ready_path = self.directory / f"runtime-{self.run_id}.observer.json"
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline:
                if ready_path.is_file():
                    receipt = json.loads(ready_path.read_text(encoding="utf-8"))
                    if receipt.get("run_id") == self.run_id and receipt.get("target_pid") == os.getpid():
                        self._observer_ready = True
                        return
                if self._observer.poll() is not None:
                    break
                time.sleep(0.02)
            raise RuntimeError("EXIT_OBSERVER_NOT_READY")
        finally:
            kernel.CloseHandle(handle)

    def _record(self, event, **fields):
        if event not in _EVENTS:
            raise ValueError("unknown diagnostic event")
        with self._lock:
            if not self.available:
                return
            try:
                record = {"event": event, "at": _now(), "run_id": self.run_id,
                          "pid": os.getpid(), **fields}
                self._handler.handle(logging.LogRecord("runtime-diagnostics", logging.INFO,
                    "", 0, json.dumps(record, ensure_ascii=True), (), None))
                self.state["last_event"] = event
                _atomic_json(self.state_path, self.state)
            except OSError:
                self.available = False

    def gui_ready(self):
        self.state["phase"] = "gui"
        self._record("gui_ready")

    def request_exit(self, reason="owner_exit"):
        if reason not in {"owner_exit", "duplicate_instance", "command_exit"}:
            raise ValueError("unknown exit reason")
        self.state["exit_reason"] = reason
        self._record("exit_requested")

    def exception(self, event, kind, trace):
        frames = []
        source_root = Path(__file__).resolve().parents[2]
        while trace is not None:
            code = trace.tb_frame.f_code
            path = Path(code.co_filename)
            try:
                relative = path.resolve().relative_to(source_root).as_posix()
            except (OSError, ValueError):
                relative = "[external]"
            if not re.fullmatch(r"(?:src|scripts|tests)/[A-Za-z0-9_./-]+", relative):
                relative = "[external]"
            frames.append({"file": relative, "line": trace.tb_lineno,
                           "function": code.co_name if _NAME.fullmatch(code.co_name) else "[unknown]"})
            trace = trace.tb_next
        name = getattr(kind, "__name__", "Exception")
        self._record(event, error_type=name if _NAME.fullmatch(name) else "Exception", frames=frames[-16:])

    def tk_exception(self, kind, _value, trace):
        self.exception("tk_exception", kind, trace)

    def finish(self, code):
        if self._finished:
            return
        self._finished = True
        self.state.update(completed=True, application_exit_code=code, phase="finished")
        self._record("app_finished")
        if self._old_hooks is not None:
            sys.excepthook, threading.excepthook = self._old_hooks
            self._old_hooks = None
        if self._fatal is not None:
            if self._native_installed:
                faulthandler.disable()
            self._fatal.close()
            if self._native_installed and self._was_native_enabled and sys.__stderr__ is not None:
                faulthandler.enable(file=sys.__stderr__, all_threads=True)
        if self._handler is not None:
            self._handler.close()

    def _previous_runs(self):
        paths = sorted(self.directory.glob("runtime-*.state.json"), key=lambda path: path.stat().st_mtime, reverse=True)
        for index, path in enumerate(paths):
            old_id = path.name.removeprefix("runtime-").removesuffix(".state.json")
            if path.is_symlink() or not _RUN_ID.fullmatch(old_id):
                continue
            try:
                old = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(old, dict):
                    continue
                pid = old.get("pid")
                if not isinstance(pid, int) or not 0 < pid < 2**32:
                    continue
                exit_path = self.directory / f"runtime-{old_id}.exit.json"
                if not exit_path.exists():
                    if _alive(pid):
                        continue
                    self._record("previous_exit_unobserved", previous_run_id=old_id)
                else:
                    receipt = json.loads(exit_path.read_text(encoding="utf-8"))
                    if not isinstance(receipt, dict) or receipt.get("classification") != "normal":
                        self._record("previous_abnormal_exit", previous_run_id=old_id)
                if index >= 19:
                    for suffix in ("state.json", "events.jsonl", "events.jsonl.1", "fatal.log", "exit.json", "observer.json"):
                        owned = self.directory / f"runtime-{old_id}.{suffix}"
                        if not owned.is_symlink():
                            owned.unlink(missing_ok=True)
            except (OSError, ValueError, TypeError):
                continue


def run_monitored(load_main, root):
    """Protect the normal entry, including GUI imports, and preserve its exit code."""
    diagnostics = RuntimeDiagnostics(root).start()
    code = 1
    try:
        code = load_main()(diagnostics=diagnostics)
    except SystemExit as exc:
        code = 0 if exc.code is None else exc.code if isinstance(exc.code, int) else 1
        diagnostics.exception("main_exception", type(exc), exc.__traceback__)
    except BaseException as exc:  # noqa: BLE001 - last-resort entry receipt, no replay
        diagnostics.exception("main_exception", type(exc), exc.__traceback__)
    finally:
        diagnostics.finish(code)
    return code
