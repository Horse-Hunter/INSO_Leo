from __future__ import annotations

import json
import sys
import threading

import pytest

from src.gui.contracts import RunState
from src.launcher.backend import ProductionBackend
from src.launcher.browser_bootstrap import (
    BrowserBootstrapError,
    BrowserHandle,
    acquire_cdp_browser,
    wait_for_cdp_ready,
)
from src.launcher.single_instance import ERROR_ALREADY_EXISTS, SingleInstanceGuard
from src.research import ResearchResult, ResearchStatus


class _MutexApi:
    def __init__(self, error=0):
        self.error = error
        self.calls = []

    def create_mutex(self, name):
        self.calls.append(("create", name))
        return 42

    def get_last_error(self):
        return self.error

    def release_mutex(self, handle):
        self.calls.append(("release", handle))

    def close_handle(self, handle):
        self.calls.append(("close", handle))


def test_named_mutex_acquire_duplicate_and_release_seam():
    api = _MutexApi()
    guard = SingleInstanceGuard(is_windows=True, api=api)
    assert guard.acquire()
    guard.release()
    assert api.calls == [
        ("create", "Local\\INSO_V1.2"), ("release", 42), ("close", 42)
    ]

    duplicate_api = _MutexApi(ERROR_ALREADY_EXISTS)
    duplicate = SingleInstanceGuard(is_windows=True, api=duplicate_api)
    assert not duplicate.acquire()
    assert duplicate.handle is None
    assert duplicate_api.calls[-1] == ("close", 42)


def test_frozen_vault_diagnostic_records_only_readiness(tmp_path, monkeypatch):
    from scripts import windows_release_entry
    from src.core import _vault_backend, app_paths, credential_provider
    from src.research import credentials

    module = tmp_path / "CredentialVault.psm1"
    module.touch()
    canonical_vault = tmp_path / "INSO_Leo" / "credential-vault.json"
    canonical_vault.parent.mkdir()
    canonical_vault.touch()
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setattr(app_paths, "app_root", lambda: tmp_path)
    monkeypatch.setattr(_vault_backend, "_default_module_path", lambda: str(module))
    monkeypatch.setattr(credential_provider, "_discover_pwsh", lambda: "powershell.exe")

    class SafeReadiness:
        def site_readiness(self):
            return (
                type("Site", (), {"site_id": "ic.net.cn", "available": True, "reason": None})(),
                type("Site", (), {"site_id": "bom.ai", "available": False, "reason": "CredentialProviderUnavailableError"})(),
                type("Site", (), {"site_id": "yingsuo.alperp.cn", "available": False, "reason": "unsafe detail"})(),
            )

    monkeypatch.setattr(credentials, "CoreResearchCredentials", SafeReadiness)
    assert windows_release_entry._diagnose_vault() == 1
    report_path = tmp_path / "runtime/logs/credential-readiness.json"
    report_text = report_path.read_text(encoding="utf-8")
    report = json.loads(report_text)
    assert report["canonical_vault_exists"]
    assert report["module_exists"]
    assert report["powershell_discovered"]
    assert report["sites"][0]["available"]
    assert report["sites"][1]["reason"] == "CredentialProviderUnavailableError"
    assert report["sites"][2]["reason"] == "CredentialError"
    assert "unsafe detail" not in report_text
    assert "username" not in report_text
    assert "password" not in report_text


def test_frozen_gui_self_check_rejects_unusable_tcl(monkeypatch):
    import tkinter

    from scripts import windows_release_entry

    def no_tcl():
        raise tkinter.TclError("synthetic unavailable Tcl")

    monkeypatch.setattr(tkinter, "Tcl", no_tcl)
    assert windows_release_entry._self_check() == 1


class _Process:
    def __init__(self):
        self.ended = False
        self.terminated = False

    def poll(self):
        return 0 if self.ended else None

    def terminate(self):
        self.terminated = True
        self.ended = True

    def wait(self, timeout=None):
        return 0


class _Clock:
    def __init__(self):
        self.now = 0.0

    def monotonic(self):
        return self.now

    def wait(self, seconds):
        self.now += seconds


class _FakeBrowser:
    def is_connected(self):
        return True


class _FakePlaywright:
    def __init__(self, connect):
        self.chromium = type("Chromium", (), {"connect_over_cdp": staticmethod(connect)})()
        self.stop_count = 0

    def start(self):
        return self

    def stop(self):
        self.stop_count += 1


def _factory_for(connect, started):
    def factory():
        instance = _FakePlaywright(connect)
        started.append(instance)
        return instance
    return factory


def test_tcp_open_but_cdp_version_not_ready_does_not_return_handle(tmp_path):
    launches = []
    with pytest.raises(BrowserBootstrapError, match="CDP_ATTACH_FAILED"):
        acquire_cdp_browser(
            "http://127.0.0.1:9222", tmp_path, {}, probe=lambda _url: True,
            version_reader=lambda _url: None,
            launch=lambda *_args: launches.append(True),
        )
    assert launches == []


def test_version_without_websocket_is_not_ready():
    clock = _Clock()
    with pytest.raises(BrowserBootstrapError, match="CDP_ATTACH_FAILED"):
        wait_for_cdp_ready(
            "http://127.0.0.1:9222", process=None,
            version_reader=lambda _url: None,
            monotonic=clock.monotonic, wait=clock.wait, timeout_seconds=1,
        )


def test_cdp_attach_retries_reset_then_returns_ready():
    clock = _Clock()
    started = []
    attempts = []

    def connect(_url, **_kwargs):
        attempts.append(True)
        if len(attempts) < 3:
            raise ConnectionResetError("synthetic reset")
        return _FakeBrowser()

    playwright, browser = wait_for_cdp_ready(
        "http://127.0.0.1:9222", process=None,
        playwright_factory=_factory_for(connect, started),
        version_reader=lambda _url: "ws://127.0.0.1/devtools/browser/test",
        monotonic=clock.monotonic, wait=clock.wait, timeout_seconds=5,
    )
    assert browser.is_connected()
    assert len(attempts) == 3
    assert len(started) == 3
    assert [item.stop_count for item in started] == [1, 1, 0]
    assert playwright is started[-1]


def test_cdp_attach_timeout_has_stable_reason_code():
    clock = _Clock()
    with pytest.raises(BrowserBootstrapError) as error:
        wait_for_cdp_ready(
            "http://127.0.0.1:9222", process=None,
            version_reader=lambda _url: "ws://127.0.0.1/devtools/browser/test",
            playwright_factory=_factory_for(
                lambda *_args, **_kwargs: (_ for _ in ()).throw(ConnectionResetError()), []
            ),
            monotonic=clock.monotonic, wait=clock.wait, timeout_seconds=1,
        )
    assert error.value.reason_code == "CDP_ATTACH_FAILED"


def test_browser_process_exit_fails_immediately():
    process = _Process()
    process.ended = True
    with pytest.raises(BrowserBootstrapError) as error:
        wait_for_cdp_ready("http://127.0.0.1:9222", process=process)
    assert error.value.reason_code == "CDP_ATTACH_FAILED"


def test_reused_browser_disconnect_does_not_close_remote_browser():
    started = []
    remote_browser = _FakeBrowser()
    handle = acquire_cdp_browser(
        "http://127.0.0.1:9222", ".", {},
        version_reader=lambda _url: "ws://127.0.0.1/devtools/browser/test",
        playwright_factory=_factory_for(lambda *_args, **_kwargs: remote_browser, started),
    )
    handle.close()
    assert handle.owned is False
    assert remote_browser.is_connected()
    assert started[0].stop_count == 1


def test_owned_chrome_bootstrap_uses_windowless_normal_chrome(monkeypatch, tmp_path):
    import src.launcher.browser_bootstrap as browser_module

    executable = tmp_path / "chrome.exe"
    profile = tmp_path / "profile"
    captured = {}

    def fake_popen(args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return object()

    monkeypatch.setattr(browser_module.subprocess, "Popen", fake_popen)
    browser_module._launch(executable, profile, 9222)

    assert "--no-startup-window" in captured["args"]
    assert "--start-minimized" not in captured["args"]
    assert "--headless=new" not in captured["args"]
    assert "--remote-debugging-address=127.0.0.1" in captured["args"]
    kwargs = captured["kwargs"]
    assert kwargs["stdin"] is browser_module.subprocess.DEVNULL
    assert kwargs["stdout"] is browser_module.subprocess.DEVNULL
    assert kwargs["stderr"] is browser_module.subprocess.DEVNULL
    assert kwargs["startupinfo"] is not None
    assert (
        kwargs["startupinfo"].dwFlags
        & browser_module.subprocess.STARTF_USESHOWWINDOW
    )
    assert kwargs["startupinfo"].wShowWindow == browser_module.subprocess.SW_HIDE
    assert not kwargs["creationflags"] & getattr(
        browser_module.subprocess, "DETACHED_PROCESS", 0
    )


def test_cdp_launches_only_explicit_existing_profile_and_closes_owned(
    tmp_path, monkeypatch
):
    import src.launcher.browser_bootstrap as browser_module

    executable = tmp_path / "chrome.exe"
    executable.touch()
    profile = tmp_path / "approved-profile"
    profile.mkdir()
    calls = []
    hider_stopped = []
    process = _Process()
    monkeypatch.setattr(
        browser_module,
        "_start_owned_window_hider",
        lambda candidate: (lambda: hider_stopped.append(candidate)),
    )
    started = []
    launched = []

    def launch(exe, prof, port):
        launched.append(True)
        return process

    def version(_url):
        return "ws://127.0.0.1/devtools/browser/test" if launched else None

    handle = acquire_cdp_browser(
        "http://127.0.0.1:9222", tmp_path,
        {"browser_bootstrap": {
            "executable": str(executable), "profile_dir": str(profile),
            "debug_port": 9222, "ready_timeout_seconds": 2,
        }},
        probe=lambda _url: False,
        launch=lambda exe, prof, port: calls.append((exe, prof, port)) or launch(exe, prof, port),
        wait=lambda _seconds: None,
        version_reader=version,
        playwright_factory=_factory_for(lambda *_args, **_kwargs: _FakeBrowser(), started),
    )
    assert handle.owned is True
    assert calls == [(executable, profile, 9222)]
    handle.close()
    assert process.terminated
    assert hider_stopped == [process]


def test_persistent_session_is_never_owned_and_never_closes_the_browser(
    tmp_path, monkeypatch
):
    """The shared INSO session browser must survive every shutdown path."""

    import src.launcher.browser_bootstrap as browser_module

    executable = tmp_path / "chrome.exe"
    executable.touch()
    profile = tmp_path / "shared-profile"
    (profile / "Default").mkdir(parents=True)
    process = _Process()
    hider_calls = []
    monkeypatch.setattr(
        browser_module,
        "_start_owned_window_hider",
        lambda candidate: (hider_calls.append(candidate), lambda: None)[1],
    )
    started = []
    launched = []

    def version(_url):
        return "ws://127.0.0.1/devtools/browser/test" if launched else None

    handle = acquire_cdp_browser(
        "http://127.0.0.1:9222", tmp_path,
        {"browser_bootstrap": {
            "executable": str(executable), "profile_dir": str(profile),
            "debug_port": 9222, "ready_timeout_seconds": 2,
            "persistent_session": True,
        }},
        probe=lambda _url: False,
        launch=lambda exe, prof, port: launched.append((exe, prof, port)) or process,
        wait=lambda _seconds: None,
        version_reader=version,
        playwright_factory=_factory_for(lambda *_args, **_kwargs: _FakeBrowser(), started),
    )

    assert handle.owned is False
    assert launched == [(executable, profile, 9222)]
    handle.close()
    assert process.terminated is False
    assert hider_calls == []
    assert started[0].stop_count == 1


def test_persistent_session_refuses_to_start_a_blank_profile(tmp_path):
    executable = tmp_path / "chrome.exe"
    executable.touch()
    profile = tmp_path / "blank-profile"
    profile.mkdir()
    launches = []

    with pytest.raises(BrowserBootstrapError) as error:
        acquire_cdp_browser(
            "http://127.0.0.1:9222", tmp_path,
            {"browser_bootstrap": {
                "executable": str(executable), "profile_dir": str(profile),
                "debug_port": 9222, "ready_timeout_seconds": 2,
                "persistent_session": True,
            }},
            probe=lambda _url: False,
            version_reader=lambda _url: None,
            launch=lambda *_args: launches.append(True),
        )

    assert error.value.reason_code == "protected CDP session profile is missing"
    assert launches == []


def test_persistent_session_reaps_only_the_never_ready_launch(tmp_path, monkeypatch):
    import src.launcher.browser_bootstrap as browser_module

    executable = tmp_path / "chrome.exe"
    executable.touch()
    profile = tmp_path / "shared-profile"
    (profile / "Default").mkdir(parents=True)
    process = _Process()
    reaped = []
    monkeypatch.setattr(browser_module, "_reap_failed_launch", lambda p: reaped.append(p))
    clock = _Clock()
    launched = []

    def version(_url):
        return "ws://127.0.0.1/devtools/browser/test" if launched else None

    with pytest.raises(BrowserBootstrapError, match="CDP_ATTACH_FAILED"):
        acquire_cdp_browser(
            "http://127.0.0.1:9222", tmp_path,
            {"browser_bootstrap": {
                "executable": str(executable), "profile_dir": str(profile),
                "debug_port": 9222, "ready_timeout_seconds": 0.5,
                "persistent_session": True,
            }},
            probe=lambda _url: False,
            launch=lambda *_args: (launched.append(True) or process),
            version_reader=version,
            playwright_factory=_factory_for(
                lambda *_args, **_kwargs: (_ for _ in ()).throw(ConnectionResetError()), []
            ),
            wait=clock.wait,
            monotonic=clock.monotonic,
        )

    assert reaped == [process]


def test_persistent_attach_refreshes_the_session_cookie_backup(tmp_path):
    """Every persistent attach must refresh a recoverable session snapshot."""

    profile = tmp_path / "shared-profile"
    (profile / "Default").mkdir(parents=True)
    inso_cookie = {
        "name": "erp_token", "domain": ".yingsuo.alperp.cn", "value": "synthetic"
    }
    unrelated = {"name": "junk", "domain": "example.com", "value": "x"}

    class _Context:
        def cookies(self):
            return [inso_cookie, unrelated]

    class _Browser:
        contexts = (_Context(),)

        def is_connected(self):
            return True

    handle = acquire_cdp_browser(
        "http://127.0.0.1:9222", tmp_path,
        {"browser_bootstrap": {
            "executable": "chrome.exe", "profile_dir": str(profile),
            "debug_port": 9222, "persistent_session": True,
        }},
        version_reader=lambda _url: "ws://127.0.0.1/devtools/browser/test",
        playwright_factory=_factory_for(lambda *_args, **_kwargs: _Browser(), []),
    )

    assert handle.owned is False
    backup = profile.parent / "session-backup" / "inso-cookies-latest.json"
    assert backup.is_file()
    assert json.loads(backup.read_text(encoding="utf-8")) == [inso_cookie]


def test_cdp_missing_or_invalid_bootstrap_fails_closed(tmp_path):
    with pytest.raises(BrowserBootstrapError):
        acquire_cdp_browser(
            "http://127.0.0.1:9222", tmp_path, {},
            probe=lambda _: False, version_reader=lambda _url: None,
        )

    with pytest.raises(BrowserBootstrapError):
        acquire_cdp_browser(
            "http://127.0.0.1:9222", tmp_path,
            {"browser_bootstrap": {"executable": "absent.exe", "profile_dir": "unknown", "debug_port": 9222}},
            probe=lambda _: False,
            version_reader=lambda _url: None,
        )


def test_cdp_timeout_closes_only_just_launched_process(tmp_path):
    executable = tmp_path / "chrome.exe"
    executable.touch()
    profile = tmp_path / "profile"
    profile.mkdir()
    process = _Process()
    unrelated_process = _Process()
    clock = _Clock()
    import src.launcher.browser_bootstrap as browser_module
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(
        browser_module,
        "_close_owned_process",
        lambda owned_process, _url: owned_process.terminate(),
    )
    launched = []

    def version(_url):
        return "ws://127.0.0.1/devtools/browser/test" if launched else None

    with pytest.raises(BrowserBootstrapError, match="CDP_ATTACH_FAILED"):
        acquire_cdp_browser(
            "http://127.0.0.1:9222", tmp_path,
            {"browser_bootstrap": {
                "executable": str(executable), "profile_dir": str(profile),
                "debug_port": 9222, "ready_timeout_seconds": 0.5,
            }},
            probe=lambda _: False,
            launch=lambda *_: (launched.append(True) or process),
            version_reader=version,
            playwright_factory=_factory_for(
                lambda *_args, **_kwargs: (_ for _ in ()).throw(ConnectionResetError()), []
            ),
            wait=clock.wait,
            monotonic=clock.monotonic,
        )
    assert process.terminated
    assert unrelated_process.terminated is False
    monkeypatch.undo()


def test_windowed_startup_duplicate_does_not_construct_backend(tmp_path, monkeypatch):
    import src.gui.main as main_module

    class Guard:
        def __init__(self):
            self.released = False

        def acquire(self):
            return False

        def release(self):
            self.released = True

    guard = Guard()
    constructed = []
    messages = []
    monkeypatch.setattr(main_module, "app_root", lambda: tmp_path)
    monkeypatch.setattr(main_module, "_show_error", lambda message, *_: messages.append(message))
    monkeypatch.setattr(sys, "argv", ["INSO_V1.2.exe"])
    assert main_module.main(guard_factory=lambda: guard, backend_factory=lambda: constructed.append(True)) == 0
    assert constructed == []
    assert messages == ["INSO_V1.2 已在运行。"]
    assert guard.released


def test_windowed_startup_error_is_sanitized_and_points_to_log(tmp_path, monkeypatch):
    import src.gui.main as main_module

    class Guard:
        def acquire(self):
            return True

        def release(self):
            pass

    messages = []
    monkeypatch.setattr(main_module, "app_root", lambda: tmp_path)
    monkeypatch.setattr(main_module, "_show_error", lambda message, *_: messages.append(message))
    monkeypatch.setattr(sys, "argv", ["INSO_V1.2.exe"])
    monkeypatch.setattr(main_module, "ProductionBackend", lambda: (_ for _ in ()).throw(ValueError("private-token-value")))
    assert main_module.main(guard_factory=Guard) == 1
    log_text = (tmp_path / "runtime/logs/INSO_V1.2.log").read_text(encoding="utf-8")
    assert "ValueError" in log_text
    assert "private-token-value" not in log_text
    assert "INSO_V1.2.log" in messages[0]
    assert "private-token-value" not in messages[0]


def test_runtime_log_keeps_the_failed_step_and_no_page_text(tmp_path):
    """The step is the only ERP-free diagnosis a failed run can be read from.

    A plain ``log.warning`` from a leg was dropped by the runtime filter, so a
    draft that never reached the AI录单 panel and one that died after the ERP
    handed its row back were the same one-line failure. The step label and the
    exception class name are our own vocabulary and must survive; the
    exception's *message* is where customer names and field values hide and
    must not.
    """

    import src.gui.main as main_module
    from src.launcher.diagnostics import log_step

    path = main_module._configure_startup_log(tmp_path)
    try:
        raise TimeoutError("客户 张三 的报价 private-token-value")
    except TimeoutError as cause:
        log_step("parent-row-missing", cause=cause)
    log_step("surface-left-open")

    log_text = path.read_text(encoding="utf-8")
    assert (
        "workflow step failed at parent-row-missing (TimeoutError)" in log_text
    )
    assert "workflow step failed at surface-left-open" in log_text
    for leaked in ("private-token-value", "张三", "TimeoutError:"):
        assert leaked not in log_text


def test_runtime_log_rebuilds_from_extras_never_from_the_message(tmp_path):
    """A caller cannot smuggle text in by formatting it into the record."""

    import logging

    import src.gui.main as main_module
    from src.launcher.diagnostics import LOG_NAME

    path = main_module._configure_startup_log(tmp_path)
    logger = logging.getLogger(LOG_NAME)
    step_shaped = logging.LogRecord(
        LOG_NAME, logging.WARNING, __file__, 1, "客户 张三 private-token-value", (), None
    )
    step_shaped.inso_step = "../../etc/passwd"
    step_shaped.inso_cause = "客户 张三 said hello"
    logger.handle(step_shaped)
    plain = logging.LogRecord(
        LOG_NAME, logging.WARNING, __file__, 1, "private-token-value", (), None
    )
    logger.handle(plain)

    log_text = path.read_text(encoding="utf-8")
    assert log_text.count("launcher event (WARNING)") == 2
    for leaked in ("private-token-value", "张三", "etc/passwd"):
        assert leaked not in log_text


@pytest.mark.parametrize("owned", [False, True])
def test_backend_closes_only_owned_browser_after_runtime_thread_exits(tmp_path, monkeypatch, owned):
    import threading

    import src.launcher.backend as backend_module
    import src.research.runtime as research_runtime
    from src.workflow.v12_contracts import DeliveryOutcome, ReasonCode
    from src.workflow.v12_notifications import NotificationTransportResult

    monkeypatch.setattr(backend_module.QQSMTPTransport, "send_one", lambda *_a, **_k:
                        NotificationTransportResult(DeliveryOutcome.SENT, ReasonCode.NOTIFICATION_SENT))

    # Reuse the deterministic test config seam from the launcher suite.
    from tests.launcher.test_backend import (
        _FakeInsoSession,
        _SheetsService,
        _write_runtime_configs,
    )

    production, research, rows = _write_runtime_configs(tmp_path, pending_count=1)
    poll_called = threading.Event()
    browser_acquired = threading.Event()
    closed = []
    browser = BrowserHandle(owned=owned, close_fn=lambda: closed.append(threading.current_thread().name))
    monkeypatch.setattr(backend_module, "build_read_only_google_sheets_service", lambda _path: _SheetsService(rows, poll_called))
    monkeypatch.setattr(backend_module, "assess_readiness", lambda *_a, **_k: type("Ready", (), {"ready": True, "missing_site_ids": ()})())
    monkeypatch.setattr(backend_module, "attach_inso_research_session", lambda _endpoint, handle, **_kw: _FakeInsoSession(handle))
    monkeypatch.setattr(research_runtime, "assess_readiness", lambda *_a, **_k: type("Ready", (), {"ready": True})())
    monkeypatch.setattr(backend_module, "build_research_service", lambda *_a, **_k: type("Research", (), {"execute": lambda self, item: ResearchResult(item.inquiry_id, ResearchStatus.SUCCESS)})())
    backend = ProductionBackend(
        config_path=research, production_config_path=production,
        cdp_probe=lambda _url: True,
        browser_acquirer=lambda *_args, **_kwargs: (browser_acquired.set() or browser),
    )
    backend.start()
    assert poll_called.wait(5)
    assert browser_acquired.wait(5)
    backend.request_stop_after_cycle()
    backend._thread.join(5)
    assert not backend._thread.is_alive()
    assert backend.get_status().state is RunState.STOPPED
    # The V1.2 coordinator owns Research synchronously; the production
    # launcher performs the final owned-browser cleanup after both loops end.
    assert closed == (["production-launcher"] if owned else [])


class _FakePlaywrightClient:
    """Mirrors Playwright's sync client: only its owning thread may stop it."""

    def __init__(self) -> None:
        self.owner = threading.get_ident()
        self.stops = 0
        self.foreign_stop_attempts = 0

    def stop(self) -> None:
        if threading.get_ident() != self.owner:
            self.foreign_stop_attempts += 1
            raise RuntimeError("greenlet.error: Cannot switch to a different thread")
        self.stops += 1


def test_owner_thread_release_still_stops_the_client_immediately() -> None:
    client = _FakePlaywrightClient()
    handle = BrowserHandle(owned=False, playwright=client)

    handle.disconnect()

    assert client.stops == 1
    assert client.foreign_stop_attempts == 0
    assert handle.playwright is None
    assert BrowserHandle.drain_deferred_stops() == 0


def test_foreign_thread_release_parks_the_client_for_the_owning_thread() -> None:
    """The production runtime starts Playwright on the poller thread and releases
    the idle session from the worker thread. Stopping it there raises
    greenlet.error and orphans the driver process (~126 MB, measured), so the
    release must park the client instead of stopping it from the wrong thread."""

    client = _FakePlaywrightClient()
    handle = BrowserHandle(owned=False, playwright=client, browser=object())
    released = threading.Event()

    def release_from_worker() -> None:
        handle.disconnect()
        released.set()

    worker = threading.Thread(target=release_from_worker, name="worker")
    worker.start()
    worker.join(10)

    # A raise inside the worker would leave the event unset.
    assert released.is_set()
    assert client.foreign_stop_attempts == 0  # never even attempted cross-thread
    assert client.stops == 0
    assert handle.playwright is None and handle.browser is None

    # The owning thread stops it at its next drain, exactly once.
    assert BrowserHandle.drain_deferred_stops() == 1
    assert client.stops == 1
    assert BrowserHandle.drain_deferred_stops() == 0


def test_drain_from_another_thread_leaves_a_foreign_client_parked() -> None:
    client = _FakePlaywrightClient()
    handle = BrowserHandle(owned=False, playwright=client)

    worker = threading.Thread(target=handle.disconnect, name="worker")
    worker.start()
    worker.join(10)

    drained: list[int] = []
    stranger = threading.Thread(
        target=lambda: drained.append(BrowserHandle.drain_deferred_stops()),
        name="stranger",
    )
    stranger.start()
    stranger.join(10)

    assert drained == [0]
    assert client.stops == 0

    assert BrowserHandle.drain_deferred_stops() == 1
    assert client.stops == 1
