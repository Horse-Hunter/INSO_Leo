"""Production entry point: ``python -m src.gui.main``.

Use ``--mock`` only for GUI development and demonstrations.
"""

from __future__ import annotations

import argparse
import ctypes
import logging
import re
import sys
import tkinter.messagebox
from logging.handlers import RotatingFileHandler
from pathlib import Path

from src.core.app_paths import app_root
from src.launcher import ProductionBackend
from src.launcher.single_instance import SingleInstanceGuard

from .app import InsoDashboardApp
from .mock_backend import MockBackend

#: A control-flow step label: lower case, hyphenated, ours. Nothing else fits,
#: so a caller cannot pass a path or a sentence through as a "step".
_STEP_LABEL = re.compile(r"[a-z][a-z0-9-]{0,31}")

#: A Python class name, which is all a cause is ever allowed to contribute.
_CAUSE_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,63}")


class _SafeRuntimeLogFilter(logging.Filter):
    """Permit sanitized startup and launcher diagnostics only.

    The log is a support artifact the operator can open, so a record survives
    only when every word in it belongs to our own vocabulary. ``inso.startup``
    already speaks that way and passes through. Every other accepted logger is
    *rebuilt* from the structured extras the caller attached and never from the
    formatted message: the message is where page text, customer names and field
    values live, and it must not be able to smuggle itself into the file.
    """

    #: Loggers whose lines are rebuilt from validated extras, never from ``msg``.
    #: ``inso.diagnostics`` is what ``src/launcher/diagnostics.py`` emits on.
    _REBUILT = frozenset({"inso.diagnostics", "src.launcher.backend"})

    def filter(self, record: logging.LogRecord) -> bool:
        if record.name == "inso.startup":
            return True
        if record.name not in self._REBUILT:
            return False
        record.msg = _sanitized_line(record)
        record.args = ()
        record.exc_info = None
        record.exc_text = None
        return True


def _sanitized_line(record: logging.LogRecord) -> str:
    """Rebuild one record from our own vocabulary, or the generic launcher line.

    ``inso_step`` is a control-flow label such as ``parent-row-missing`` and
    ``inso_cause`` is an exception class name. Both are validated rather than
    truncated, so a caller that tries to put a path, a sentence or a field value
    in either one degrades to the generic line instead of leaking it.
    """

    step = getattr(record, "inso_step", None)
    if not isinstance(step, str) or _STEP_LABEL.fullmatch(step) is None:
        return f"launcher event ({record.levelname})"
    cause = getattr(record, "inso_cause", None)
    suffix = (
        f" ({cause})"
        if isinstance(cause, str) and _CAUSE_NAME.fullmatch(cause) is not None
        else ""
    )
    return f"workflow step failed at {step}{suffix}"


def _configure_startup_log(root: Path) -> Path:
    log_dir = root / "runtime" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    path = log_dir / "INSO_V1.2.log"
    handler = RotatingFileHandler(path, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    handler.addFilter(_SafeRuntimeLogFilter())
    logger = logging.getLogger("inso.startup")
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.WARNING)
    return path


def _show_error(message: str, title: str = "INSO_V1.2") -> None:
    try:
        tkinter.messagebox.showerror(title, message)
    except (tkinter.TclError, RuntimeError):
        if sys.platform == "win32":
            message_box = ctypes.windll.user32.MessageBoxW
            message_box.argtypes = (
                ctypes.c_void_p,
                ctypes.c_wchar_p,
                ctypes.c_wchar_p,
                ctypes.c_uint,
            )
            message_box.restype = ctypes.c_int
            message_box(None, message, title, 0x10)


def main(*, guard_factory=None, backend_factory=None) -> int:
    log_path = None
    guard = None
    backend = None
    try:
        root = app_root()
        log_path = _configure_startup_log(root)
        parser = argparse.ArgumentParser(description="INSO V1 production launcher")
        parser.add_argument(
            "--mock", action="store_true", help="run GUI demo backend instead of production"
        )
        args = parser.parse_args()
        guard = (guard_factory or SingleInstanceGuard)()
        if not guard.acquire():
            _show_error("INSO_V1.2 已在运行。")
            return 0
        backend = (
            MockBackend(cycle_seconds=12.0)
            if args.mock
            else (backend_factory or ProductionBackend)()
        )
        InsoDashboardApp(backend).run()
        return 0
    except Exception as exc:  # noqa: BLE001 - windowed startup safety boundary
        logging.getLogger("inso.startup").error(
            "Application startup failed (%s)", type(exc).__name__
        )
        message = "INSO_V1.2 启动失败。"
        if log_path is not None:
            message += f"\n请查看本地日志：{log_path}"
        else:
            message += "\n应用目录不可写，请检查发布目录权限后重试。"
        _show_error(message)
        return 1
    finally:
        if backend is not None:
            try:
                backend.shutdown()
            except Exception as exc:  # noqa: BLE001 - cleanup boundary
                logging.getLogger("inso.startup").error(
                    "Backend shutdown failed (%s)", type(exc).__name__
                )
        if guard is not None:
            guard.release()


if __name__ == "__main__":
    sys.exit(main())
