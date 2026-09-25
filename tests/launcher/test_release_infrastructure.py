from __future__ import annotations

import json
import sys

import pytest

from src.gui.contracts import RunState
from src.launcher.backend import ProductionBackend
from src.launcher.browser_bootstrap import (
    BrowserBootstrapError,
    BrowserHandle,
    acquire_cdp_browser,
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
        ("create", "Local\\INSO_V1.1"), ("release", 42), ("close", 42)
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


def test_cdp_reachable_reuses_without_launch_or_close(tmp_path):
    launches = []
    handle = acquire_cdp_browser(
        "http://127.0.0.1:9222", tmp_path, {}, probe=lambda _url: True,
        launch=lambda *_args: launches.append(True),
    )
    handle.close()
    assert handle.owned is False
    assert launches == []


def test_owned_chrome_bootstrap_is_headless_and_never_shows_foreground(monkeypatch, tmp_path):
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

    assert "--headless=new" in captured["args"]
    assert "--disable-gpu" in captured["args"]
    assert "--remote-debugging-address=127.0.0.1" in captured["args"]
    kwargs = captured["kwargs"]
    assert kwargs["stdin"] is browser_module.subprocess.DEVNULL
    assert kwargs["stdout"] is browser_module.subprocess.DEVNULL
    assert kwargs["stderr"] is browser_module.subprocess.DEVNULL
    assert not kwargs["creationflags"] & getattr(
        browser_module.subprocess, "DETACHED_PROCESS", 0
    )


def test_cdp_launches_only_explicit_existing_profile_and_closes_owned(tmp_path):
    executable = tmp_path / "chrome.exe"
    executable.touch()
    profile = tmp_path / "approved-profile"
    profile.mkdir()
    calls = []
    process = _Process()
    probes = iter((False, True))
    handle = acquire_cdp_browser(
        "http://127.0.0.1:9222", tmp_path,
        {"browser_bootstrap": {
            "executable": str(executable), "profile_dir": str(profile),
            "debug_port": 9222, "ready_timeout_seconds": 2,
        }},
        probe=lambda _url: next(probes),
        launch=lambda exe, prof, port: calls.append((exe, prof, port)) or process,
        wait=lambda _seconds: None,
    )
    assert handle.owned is True
    assert calls == [(executable, profile, 9222)]
    handle.close()
    assert process.terminated


def test_cdp_missing_or_invalid_bootstrap_fails_closed(tmp_path):
    with pytest.raises(BrowserBootstrapError):
        acquire_cdp_browser("http://127.0.0.1:9222", tmp_path, {}, probe=lambda _: False)

    with pytest.raises(BrowserBootstrapError):
        acquire_cdp_browser(
            "http://127.0.0.1:9222", tmp_path,
            {"browser_bootstrap": {"executable": "absent.exe", "profile_dir": "unknown", "debug_port": 9222}},
            probe=lambda _: False,
        )


def test_cdp_timeout_closes_only_just_launched_process(tmp_path):
    executable = tmp_path / "chrome.exe"
    executable.touch()
    profile = tmp_path / "profile"
    profile.mkdir()
    process = _Process()
    ticker = iter((0.0, 0.2, 0.4, 0.6))
    with pytest.raises(BrowserBootstrapError, match="timed out"):
        acquire_cdp_browser(
            "http://127.0.0.1:9222", tmp_path,
            {"browser_bootstrap": {
                "executable": str(executable), "profile_dir": str(profile),
                "debug_port": 9222, "ready_timeout_seconds": 0.5,
            }},
            probe=lambda _: False,
            launch=lambda *_: process,
            wait=lambda _: None,
            monotonic=lambda: next(ticker),
        )
    assert process.terminated


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
    monkeypatch.setattr(sys, "argv", ["INSO_V1.1.exe"])
    assert main_module.main(guard_factory=lambda: guard, backend_factory=lambda: constructed.append(True)) == 0
    assert constructed == []
    assert messages == ["INSO_V1.1 已在运行。"]
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
    monkeypatch.setattr(sys, "argv", ["INSO_V1.1.exe"])
    monkeypatch.setattr(main_module, "ProductionBackend", lambda: (_ for _ in ()).throw(ValueError("private-token-value")))
    assert main_module.main(guard_factory=Guard) == 1
    log_text = (tmp_path / "runtime/logs/INSO_V1.1.log").read_text(encoding="utf-8")
    assert "ValueError" in log_text
    assert "private-token-value" not in log_text
    assert "INSO_V1.1.log" in messages[0]
    assert "private-token-value" not in messages[0]


@pytest.mark.parametrize("owned", [False, True])
def test_backend_closes_only_owned_browser_after_runtime_thread_exits(tmp_path, monkeypatch, owned):
    import threading

    import src.launcher.backend as backend_module
    import src.research.runtime as research_runtime

    # Reuse the deterministic test config seam from the launcher suite.
    from tests.launcher.test_backend import _SheetsService, _write_runtime_configs

    production, research, rows = _write_runtime_configs(tmp_path)
    poll_called = threading.Event()
    closed = []
    browser = BrowserHandle(owned=owned, close_fn=lambda: closed.append(threading.current_thread().name))
    monkeypatch.setattr(backend_module, "build_read_only_google_sheets_service", lambda _path: _SheetsService(rows, poll_called))
    monkeypatch.setattr(backend_module, "assess_readiness", lambda *_a, **_k: type("Ready", (), {"ready": True})())
    monkeypatch.setattr(research_runtime, "assess_readiness", lambda *_a, **_k: type("Ready", (), {"ready": True})())
    monkeypatch.setattr(backend_module, "build_production_research_service", lambda *_a, **_k: type("Research", (), {"execute": lambda self, item: ResearchResult(item.inquiry_id, ResearchStatus.SUCCESS)})())
    backend = ProductionBackend(
        config_path=research, production_config_path=production,
        cdp_probe=lambda _url: True,
        browser_acquirer=lambda *_args, **_kwargs: browser,
    )
    backend.start()
    assert poll_called.wait(5)
    backend.request_stop_after_cycle()
    backend._thread.join(5)
    assert not backend._thread.is_alive()
    assert backend.get_status().state is RunState.STOPPED
    assert closed == (["production-launcher"] if owned else [])
