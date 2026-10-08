"""CDP Chrome launch/reuse and ownership lifecycle for the production launcher."""

from __future__ import annotations

import json
import logging
import os
import subprocess
import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar
from urllib.parse import urlsplit
from urllib.request import urlopen

from src.core.app_paths import resolve_app_path
from src.research.cdp_pages import new_background_page


class BrowserBootstrapError(RuntimeError):
    """CDP is unavailable and an approved browser could not be started."""

    def __init__(self, reason_code: str = "CDP_ATTACH_FAILED") -> None:
        super().__init__(reason_code)
        self.reason_code = reason_code


def park_shared_cdp(browser) -> None:
    """Owner's dedicated context: retain one blank tab without closing Chrome."""
    contexts = tuple(browser.contexts)
    if not browser.is_connected() or len(contexts) != 1:
        raise BrowserBootstrapError("CDP_CONTEXT_NOT_UNIQUE")
    context = contexts[0]
    pages = tuple(context.pages)
    blank = next((p for p in pages if not p.is_closed() and p.url == "about:blank"), None)
    if blank is None:
        blank = new_background_page(browser, context, timeout_ms=10000)  # Keep a live tab before cleanup.
    for page in pages:
        if page is not blank and not page.is_closed():
            page.close()
    remaining = tuple(p for p in context.pages if not p.is_closed())
    if remaining != (blank,) or blank.url != "about:blank":
        raise BrowserBootstrapError("CDP_TAB_CLEANUP_UNCONFIRMED")


@dataclass
class BrowserHandle:
    """A CDP attachment whose Playwright client is bound to one thread.

    Playwright's synchronous API binds its client to the greenlet of the thread
    that called ``sync_playwright().start()``. Stopping it from any other thread
    raises ``greenlet.error: Cannot switch to a different thread``. That matters
    here because the production runtime starts the client on the poller thread
    (the V1.2 duplicate check prepares the session first) and releases the idle
    session from the worker thread.

    A failed stop is unrecoverable -- ``disconnect`` has already dropped its
    reference -- and it orphans the Playwright driver process, which was measured
    at ~126 MB per idle-release cycle. The handle therefore records its owning
    thread and parks the client for that thread to stop, instead of stopping it
    from whatever thread happens to release the session.
    """

    owned: bool
    process: object | None = None
    close_fn: Callable[[], None] | None = None
    cleanup_fn: Callable[[], None] | None = None
    playwright: object | None = None
    browser: object | None = None
    _owner_thread: int = field(default=0, repr=False, compare=False)

    # Clients released by a thread that does not own them, keyed by the thread
    # that must stop them. Class-level so the parking survives the handle being
    # dropped, and so any runtime loop can drain its own entries.
    _deferred_stops: ClassVar[dict[int, list[object]]] = {}
    _deferred_stops_lock: ClassVar[threading.Lock] = threading.Lock()

    def __post_init__(self) -> None:
        self._owner_thread = threading.get_ident()

    def disconnect(self) -> None:
        playwright, self.playwright = self.playwright, None
        self.browser = None
        if playwright is None:
            return
        if threading.get_ident() == self._owner_thread:
            playwright.stop()
            return
        type(self)._defer_stop(self._owner_thread, playwright)

    @classmethod
    def drain_deferred_stops(cls) -> int:
        """Stop clients that were released by a thread that does not own them.

        Safe from any thread: only entries owned by the caller are stopped, so a
        runtime loop can call this freely. A foreign stop is exactly the
        ``greenlet.error`` this parking exists to avoid.
        """

        owner = threading.get_ident()
        with cls._deferred_stops_lock:
            pending = cls._deferred_stops.pop(owner, [])
        stopped = 0
        for playwright in pending:
            try:
                playwright.stop()
                stopped += 1
            except Exception as exc:  # noqa: BLE001 - classify only within deadline
                _LOG.debug("Deferred Playwright stop failed (%s)", type(exc).__name__)
        return stopped

    @classmethod
    def _defer_stop(cls, owner: int, playwright: object) -> None:
        with cls._deferred_stops_lock:
            cls._deferred_stops.setdefault(owner, []).append(playwright)

    def close(self) -> None:
        try:
            try:
                self.disconnect()
            finally:
                if self.owned and self.close_fn:
                    self.close_fn()
        finally:
            if self.owned and self.cleanup_fn:
                cleanup, self.cleanup_fn = self.cleanup_fn, None
                cleanup()


_LOG = logging.getLogger(__name__)
_CDP_READY_TIMEOUT_SECONDS = 20.0
_CDP_RETRY_INTERVAL_SECONDS = 0.4
_CDP_ATTACH_ATTEMPT_TIMEOUT_SECONDS = 10.0


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
    args = [
        str(executable),
        f"--user-data-dir={profile}",
        f"--remote-debugging-port={port}",
        "--remote-debugging-address=127.0.0.1",
        "--no-first-run",
        "--no-default-browser-check",
    ]
    # Keep the stable V1.1 Chrome runtime windowless.
    args.append("--no-startup-window")
    return subprocess.Popen(
        args,
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


def _reap_failed_launch(process: object) -> None:
    """Terminate only a just-launched, never-ready Chrome process tree.

    This never addresses the CDP endpoint, so it can never touch an unrelated
    (for example, already authenticated) browser that may serve the same port.
    """

    try:
        if process.poll() is None:
            if os.name == "nt" and getattr(process, "pid", None) is not None:
                subprocess.run(
                    ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )
            else:
                process.terminate()
        process.wait(timeout=10)
    except Exception:  # noqa: BLE001 - expose only the stable reason code
        return


def _snapshot_session_cookies(browser: object, profile: Path) -> None:
    """Best-effort refresh of the protected session backup next to the profile.

    The profile is the only irreplaceable asset in this system (the Owner will
    not supply another INSO SMS code), so every successful attach refreshes a
    plaintext cookie snapshot beside it. Failures here must never be fatal.
    """

    try:
        contexts = tuple(getattr(browser, "contexts", ()) or ())
        if not contexts:
            return
        cookies = [
            cookie
            for cookie in contexts[0].cookies()
            if "alperp" in (cookie.get("domain") or "")
        ]
        if not cookies:
            return
        backup_dir = Path(profile).parent / "session-backup"
        backup_dir.mkdir(parents=True, exist_ok=True)
        target = backup_dir / "inso-cookies-latest.json"
        target.write_text(
            json.dumps(cookies, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        _LOG.info("Session cookie backup refreshed at %s", target)
    except Exception:  # noqa: BLE001 - expose only the stable reason code
        return


def _read_cdp_version(cdp_url: str) -> str | None:
    """Return the advertised websocket endpoint, or None until CDP is ready."""

    try:
        parsed = urlsplit(cdp_url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            return None
        with urlopen(cdp_url.rstrip("/") + "/json/version", timeout=1) as response:
            payload = json.load(response)
    except (OSError, UnicodeError, ValueError, TypeError):
        return None
    if not isinstance(payload, Mapping):
        return None
    websocket_url = payload.get("webSocketDebuggerUrl")
    if not isinstance(websocket_url, str) or not websocket_url.strip():
        return None
    return websocket_url.strip()


def _start_playwright(playwright_factory: Callable[[], object] | None):
    if playwright_factory is None:
        from playwright.sync_api import sync_playwright

        playwright_factory = sync_playwright
    return playwright_factory().start()


def wait_for_cdp_ready(
    cdp_url: str,
    *,
    process: object | None,
    playwright_factory: Callable[[], object] | None = None,
    version_reader: Callable[[str], str | None] = _read_cdp_version,
    wait: Callable[[float], None] = time.sleep,
    monotonic: Callable[[], float] = time.monotonic,
    timeout_seconds: float = _CDP_READY_TIMEOUT_SECONDS,
) -> tuple[object, object]:
    """Wait for stable DevTools JSON and prove Playwright can attach.

    TCP reachability is not a readiness signal. The browser must remain alive,
    advertise its websocket endpoint twice consecutively, and accept a real
    Playwright CDP connection before this returns.
    """

    deadline = monotonic() + min(timeout_seconds, _CDP_READY_TIMEOUT_SECONDS)
    consecutive_versions = 0
    last_attach_timed_out = False
    while monotonic() < deadline:
        if process is not None and process.poll() is not None:
            raise BrowserBootstrapError("CDP_ATTACH_FAILED")
        websocket_url = version_reader(cdp_url)
        if websocket_url:
            consecutive_versions += 1
        else:
            consecutive_versions = 0
            last_attach_timed_out = False
        if consecutive_versions >= 2:
            playwright = None
            try:
                playwright = _start_playwright(playwright_factory)
                browser = playwright.chromium.connect_over_cdp(
                    cdp_url,
                    timeout=max(1, int(min(
                        _CDP_ATTACH_ATTEMPT_TIMEOUT_SECONDS, deadline - monotonic()
                    ) * 1000)),
                )
                if (
                    browser.is_connected()
                    and (process is None or process.poll() is None)
                ):
                    return playwright, browser
            except Exception as exc:  # noqa: BLE001 - classify only within deadline
                last_attach_timed_out = type(exc).__name__ == "TimeoutError"
                _LOG.debug("CDP attach attempt failed (%s)", type(exc).__name__)
            if playwright is not None:
                try:
                    playwright.stop()
                except Exception as exc:  # noqa: BLE001 - teardown is best effort
                    _LOG.debug("Playwright disconnect failed (%s)", type(exc).__name__)
            consecutive_versions = 0
        remaining = deadline - monotonic()
        if remaining > 0:
            wait(min(_CDP_RETRY_INTERVAL_SECONDS, remaining))
    raise BrowserBootstrapError(
        "CDP_SESSION_INITIALIZATION_TIMEOUT"
        if last_attach_timed_out else "CDP_ATTACH_FAILED"
    )


def _devtools_active_port_status(
    profile: Path, expected_port: int
) -> tuple[bool, bool | None]:
    """Read only the first DevToolsActivePort line for safe diagnostics."""

    path = profile / "DevToolsActivePort"
    try:
        first_line = path.read_text(encoding="ascii").splitlines()[0].strip()
    except FileNotFoundError:
        return False, None
    except (OSError, UnicodeError, IndexError):
        return True, None
    return True, first_line.isdecimal() and int(first_line) == expected_port


def acquire_cdp_browser(
    cdp_url: str,
    app_root: str | Path,
    config: Mapping[str, object],
    *,
    probe: Callable[[str], bool] | None = None,
    version_reader: Callable[[str], str | None] = _read_cdp_version,
    playwright_factory: Callable[[], object] | None = None,
    launch: Callable[[Path, Path, int], object] = _launch,
    wait: Callable[[float], None] = time.sleep,
    monotonic: Callable[[], float] = time.monotonic,
) -> BrowserHandle:
    """Attach to verified CDP or launch only the explicitly configured browser."""

    websocket_url = version_reader(cdp_url)
    if websocket_url:
        playwright, browser = wait_for_cdp_ready(
            cdp_url,
            process=None,
            playwright_factory=playwright_factory,
            version_reader=version_reader,
            wait=wait,
            monotonic=monotonic,
        )
        raw_attach = config.get("browser_bootstrap")
        if isinstance(raw_attach, Mapping) and raw_attach.get("persistent_session") is True:
            profile_attach = resolve_app_path(str(raw_attach["profile_dir"]), root=app_root)
            _snapshot_session_cookies(browser, profile_attach)
        return BrowserHandle(owned=False, playwright=playwright, browser=browser)
    if probe is not None and probe(cdp_url):
        # A listener without a valid DevTools endpoint may belong to another
        # process; never launch over it or treat it as ready.
        raise BrowserBootstrapError("CDP_ATTACH_FAILED")
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
    if (
        not executable.is_file()
        or not profile.is_dir()
        or not 1 <= port <= 65535
        or parsed_port != port
        or not 0 < timeout <= 180
    ):
        raise BrowserBootstrapError("approved Chrome executable/profile/port is unavailable")
    # The shared INSO session profile is irreplaceable: it holds the Owner's
    # authenticated cookies (including the multi-day SMS-verification memory).
    # Starting a blank profile would silently demand a new SMS code, so refuse.
    persistent = raw.get("persistent_session") is True
    if persistent and not (profile / "Default").is_dir():
        _LOG.error(
            "Refusing to start a blank CDP profile; the protected session profile "
            "at %s has no Default/ directory",
            profile,
        )
        raise BrowserBootstrapError("protected CDP session profile is missing")
    try:
        process = launch(executable, profile, port)
    except Exception as exc:
        raise BrowserBootstrapError("approved Chrome failed to launch") from exc
    handle = BrowserHandle(
        # A persistent session must outlive this process: never take ownership,
        # and never install the window hider, so no shutdown path can stop the
        # browser or drop the in-use session.
        owned=not persistent,
        process=process,
        close_fn=(
            None if persistent else (lambda: _close_owned_process(process, cdp_url))
        ),
        cleanup_fn=None if persistent else _start_owned_window_hider(process),
    )
    try:
        handle.playwright, handle.browser = wait_for_cdp_ready(
            cdp_url,
            process=process,
            playwright_factory=playwright_factory,
            version_reader=version_reader,
            wait=wait,
            monotonic=monotonic,
            timeout_seconds=timeout,
        )
        exists, port_matches = _devtools_active_port_status(profile, port)
        _LOG.info(
            "CDP ready; DevToolsActivePort exists=%s port_matches=%s persistent=%s",
            exists,
            port_matches,
            persistent,
        )
        if persistent:
            _snapshot_session_cookies(handle.browser, profile)
        return handle
    except BrowserBootstrapError:
        exists, port_matches = _devtools_active_port_status(profile, port)
        _LOG.warning(
            "CDP attach failed; DevToolsActivePort exists=%s port_matches=%s",
            exists,
            port_matches,
        )
        handle.close()
        if persistent:
            # The process we just launched never served CDP, so it cannot be the
            # authenticated session holder. Reap only that fresh, unused process.
            _reap_failed_launch(process)
        raise
    except Exception:  # noqa: BLE001 - expose only the stable reason code
        handle.close()
        raise BrowserBootstrapError("CDP_ATTACH_FAILED") from None
