"""CDP Chrome launch/reuse and ownership lifecycle for the production launcher."""

from __future__ import annotations

import json
import os
import subprocess
import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import urlopen

from src.core.app_paths import resolve_app_path


class BrowserBootstrapError(RuntimeError):
    """CDP is unavailable and an approved browser could not be started."""


@dataclass
class BrowserHandle:
    owned: bool
    process: object | None = None
    close_fn: Callable[[], None] | None = None
    cleanup_fn: Callable[[], None] | None = None

    def close(self) -> None:
        if not self.owned:
            return
        try:
            if self.close_fn:
                self.close_fn()
        finally:
            if self.cleanup_fn:
                self.cleanup_fn()


def _hide_owned_windows(process_id: int) -> None:
    """Hide top-level windows owned by this app-launched Chrome process only."""

    if os.name != "nt":
        return
    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.WinDLL("user32", use_last_error=True)
        callback_type = ctypes.WINFUNCTYPE(
            wintypes.BOOL, wintypes.HWND, wintypes.LPARAM
        )

        @callback_type
        def hide_if_owned(hwnd, _lparam):
            owner_pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner_pid))
            if owner_pid.value == process_id:
                user32.ShowWindow(hwnd, 0)  # SW_HIDE
            return True

        user32.EnumWindows(hide_if_owned, 0)
    except (AttributeError, OSError):
        # This optional UI hygiene guard must never affect collection.
        return


def _start_owned_window_hider(process: object) -> Callable[[], None]:
    """Continuously hide only windows belonging to the owned Chrome process."""

    process_id = getattr(process, "pid", None)
    if os.name != "nt" or not isinstance(process_id, int) or process_id <= 0:
        return lambda: None
    stopped = threading.Event()

    def run() -> None:
        while not stopped.wait(0.02):
            _hide_owned_windows(process_id)

    _hide_owned_windows(process_id)
    threading.Thread(
        target=run,
        name="owned-chrome-window-hider",
        daemon=True,
    ).start()
    return stopped.set


def _launch(executable: Path, profile: Path, port: int):
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    startupinfo = None
    if os.name == "nt":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
    return subprocess.Popen(
        [
            str(executable),
            f"--user-data-dir={profile}",
            f"--remote-debugging-port={port}",
            "--remote-debugging-address=127.0.0.1",
            # Several authenticated supplier sites reject a headless Chrome
            # session even when the approved profile is valid.  A normal
            # Chrome session keeps those site checks intact. Do not create an
            # initial browser window: CDP creates research targets in the
            # background, so collection cannot steal desktop focus.
            "--no-startup-window",
            "--no-first-run",
            "--no-default-browser-check",
        ],
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        creationflags=flags,
        startupinfo=startupinfo,
    )


def _close_owned_process(process, cdp_url: str) -> None:
    if process.poll() is None:
        # Chrome's documented CDP Browser.close command shuts down the browser tree
        # cleanly. This is called only for a session launched by this backend.
        browser_close_sent = False
        try:
            import websocket
        except ImportError:
            websocket = None
        if websocket is not None:
            try:
                endpoint = cdp_url.rstrip("/") + "/json/version"
                with urlopen(endpoint, timeout=3) as response:
                    debugger_url = json.load(response).get("webSocketDebuggerUrl")
                if debugger_url:
                    connection = websocket.create_connection(
                        debugger_url, timeout=3, suppress_origin=True
                    )
                    try:
                        connection.send(json.dumps({"id": 1, "method": "Browser.close"}))
                        browser_close_sent = True
                        try:
                            connection.recv()
                        except websocket.WebSocketConnectionClosedException:
                            pass
                    finally:
                        connection.close()
            except (
                OSError,
                ValueError,
                KeyError,
                TypeError,
                websocket.WebSocketException,
            ):
                browser_close_sent = False
        if not browser_close_sent and process.poll() is None:
            # Fall back only to the process tree returned by our own Popen.
            if os.name == "nt" and getattr(process, "pid", None) is not None:
                subprocess.run(
                    ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                    stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL, check=False,
                )
            else:
                process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        if os.name == "nt" and getattr(process, "pid", None) is not None:
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL, check=False,
            )
            process.wait(timeout=5)
        else:
            process.kill()
            process.wait(timeout=5)


def acquire_cdp_browser(
    cdp_url: str,
    app_root: str | Path,
    config: Mapping[str, object],
    *,
    probe: Callable[[str], bool],
    launch: Callable[[Path, Path, int], object] = _launch,
    wait: Callable[[float], None] = time.sleep,
    monotonic: Callable[[], float] = time.monotonic,
) -> BrowserHandle:
    """Reuse reachable CDP, otherwise launch only from explicit approved config."""

    if probe(cdp_url):
        return BrowserHandle(owned=False)
    raw = config.get("browser_bootstrap")
    if not isinstance(raw, Mapping):
        raise BrowserBootstrapError("CDP unavailable and browser bootstrap is not configured")
    try:
        executable = resolve_app_path(str(raw["executable"]), root=app_root)
        profile = resolve_app_path(str(raw["profile_dir"]), root=app_root)
        port = int(raw["debug_port"])
        timeout = float(raw.get("ready_timeout_seconds", 30))
        parsed_port = urlsplit(cdp_url).port
    except (KeyError, TypeError, ValueError) as exc:
        raise BrowserBootstrapError("browser bootstrap config is invalid") from exc
    if not executable.is_file() or not profile.is_dir() or not 1 <= port <= 65535 or parsed_port != port or not 0 < timeout <= 180:
        raise BrowserBootstrapError("approved Chrome executable/profile/port is unavailable")
    try:
        process = launch(executable, profile, port)
    except Exception as exc:
        raise BrowserBootstrapError("approved Chrome failed to launch") from exc
    handle = BrowserHandle(
        owned=True, process=process,
        close_fn=lambda: _close_owned_process(process, cdp_url),
        cleanup_fn=_start_owned_window_hider(process),
    )
    deadline = monotonic() + timeout
    try:
        while monotonic() < deadline:
            if process.poll() is not None:
                break
            if probe(cdp_url):
                return handle
            wait(min(0.2, max(0, deadline - monotonic())))
    except Exception:
        handle.close()
        raise
    handle.close()
    raise BrowserBootstrapError("approved Chrome CDP readiness timed out")
