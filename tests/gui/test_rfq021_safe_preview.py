"""RFQ-021: a plain launch renders the dashboard and starts nothing."""

from __future__ import annotations

import sys

import pytest

from src.gui import main as launcher
from src.gui.app import _scope_button

ORDER = "inq_" + "a" * 24


class Harness:
    """Records the launch decisions without building a window."""

    def __init__(self):
        self.events: list = []
        self.backend_kwargs: dict = {}

    def install(self, monkeypatch, tmp_path):
        harness = self

        class Guard:
            def __init__(self, name=None):
                harness.events.append(("guard", name))

            def acquire(self):
                harness.events.append("acquire")
                return True

            def release(self):
                harness.events.append("release")

        class Backend:
            def __init__(self, **kwargs):
                harness.backend_kwargs = kwargs
                harness.events.append("backend")

            def start_process_services(self):
                harness.events.append("services")

            def start(self):
                harness.events.append("start")

            def shutdown(self):
                harness.events.append("shutdown")

            def local_view_loading(self):
                return False

        class App:
            def __init__(self, backend):
                harness.events.append("gui")

            def run(self):
                harness.events.append("run")

        monkeypatch.setattr(launcher, "app_root", lambda: tmp_path)
        monkeypatch.setattr(launcher, "_configure_startup_log", lambda _: None)
        monkeypatch.setattr(launcher, "InsoDashboardApp", App)
        monkeypatch.setattr(launcher, "SingleInstanceGuard", Guard)
        monkeypatch.setattr(launcher, "ProductionBackend", Backend)
        return harness


def argv(monkeypatch, *flags):
    monkeypatch.setattr(sys, "argv", ["INSO_V1.6.exe", *flags])


def test_a_plain_launch_is_a_safe_preview(tmp_path, monkeypatch):
    harness = Harness().install(monkeypatch, tmp_path)
    argv(monkeypatch)

    assert launcher.main() == 0

    assert harness.backend_kwargs["preview_mode"] is True
    assert harness.backend_kwargs["enforce_scope"] is True
    assert harness.backend_kwargs["run_scope"] is None
    assert "services" not in harness.events
    assert "start" not in harness.events
    guard_calls = [event for event in harness.events if isinstance(event, tuple)]
    assert guard_calls == [("guard", launcher.PREVIEW_MUTEX_NAME)]


def test_explicit_safe_preview_behaves_the_same(tmp_path, monkeypatch):
    harness = Harness().install(monkeypatch, tmp_path)
    argv(monkeypatch, "--safe-preview")
    assert launcher.main() == 0
    assert harness.backend_kwargs["preview_mode"] is True
    assert "services" not in harness.events


def test_start_without_a_scope_is_refused_not_downgraded(tmp_path, monkeypatch):
    harness = Harness().install(monkeypatch, tmp_path)
    shown = []
    monkeypatch.setattr(launcher, "_show_error", lambda message, title=None: shown.append(message))
    argv(monkeypatch, "--start-inquiry")

    assert launcher.main() == 2
    assert harness.events == []
    assert shown and "受控" in shown[0]


def test_an_invalid_scope_is_refused_before_any_backend(tmp_path, monkeypatch):
    harness = Harness().install(monkeypatch, tmp_path)
    shown = []
    monkeypatch.setattr(launcher, "_show_error", lambda message, title=None: shown.append(message))
    argv(monkeypatch, "--scoped-start", "--scope-inquiries", "not-an-order")

    assert launcher.main() == 2
    assert harness.events == []
    assert shown and "SCOPE_INVALID_INQUIRY_ID" in shown[0]


def test_a_scoped_start_starts_services_and_the_scoped_run(tmp_path, monkeypatch):
    harness = Harness().install(monkeypatch, tmp_path)
    argv(
        monkeypatch,
        "--scoped-start",
        "--scope-inquiries", ORDER,
        "--scope-modules", "inquiry,quotation",
        "--scope-writes", "google",
        "--scope-approval", "OWNER-APPROVED:RFQ-021-TRIAL-1",
        "--start-inquiry",
    )

    assert launcher.main() == 0

    scope = harness.backend_kwargs["run_scope"]
    assert harness.backend_kwargs["preview_mode"] is False
    assert harness.backend_kwargs["enforce_scope"] is True
    assert scope.inquiry_ids == frozenset({ORDER})
    assert scope.modules == frozenset({"inquiry", "quotation"})
    assert harness.events.index("services") < harness.events.index("gui")
    assert "start" in harness.events
    assert [event for event in harness.events if isinstance(event, tuple)] == [("guard", None)]


@pytest.mark.parametrize("blockers, expected", [
    ((), None),
    (("PREVIEW_ONLY",), "安全预览（不启动业务）"),
    (("SCOPE_MISSING",), "未配置受控试运行范围"),
])
def test_start_button_is_disabled_unless_a_scope_is_active(blockers, expected):
    button = _scope_button(blockers)
    if expected is None:
        assert button is None
        return
    assert button["text"] == expected
    assert button["state"] == "disabled"
