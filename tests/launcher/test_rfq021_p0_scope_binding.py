"""RFQ-021 follow-up: the three P0 defects found by the CEO review.

P0-A  the launcher's RunScope never reached `_inquiry_scope`, so a "scoped"
      run composed the V1.2 coordinator with ``inquiry_ids=None`` (all orders).
P0-B  the launcher started the mail-research service unconditionally, opening
      IMAP/SMTP outside any notification/smtp scope.
P0-C  only the Start button was disabled in preview; order-mail, one-click
      login and per-order actions were still reachable.

Each test is a negative: it fails on the code as reviewed.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.gui import app as app_module
from src.launcher import backend as launcher
from src.launcher.backend import ProductionBackend
from src.launcher.run_scope import ScopeError, parse_run_scope

ORDER = "inq_" + "a" * 24
OTHER = "inq_" + "b" * 24


def scoped(writes: str = ""):
    return parse_run_scope(
        inquiry_ids=ORDER,
        modules="inquiry",
        write_targets=writes,
        approval="OWNER-APPROVED:RFQ-021-FOLLOWUP" if writes else "",
    )


# --- P0-A: the scope must actually restrict composition ---------------------

def test_run_scope_binds_the_order_scope_it_was_given(tmp_path):
    backend = ProductionBackend(root=tmp_path, run_scope=scoped(), enforce_scope=True)
    assert backend._inquiry_scope == frozenset({ORDER})


def test_explicit_inquiry_ids_conflicting_with_the_scope_are_refused(tmp_path):
    # RFQ-021-R3: two different order sets cannot both be "the scope"; the
    # earlier "explicit wins" behaviour silently widened or narrowed the run.
    from src.launcher.run_scope import ScopeError
    with pytest.raises(ScopeError) as info:
        ProductionBackend(
            root=tmp_path, inquiry_ids=frozenset({OTHER}),
            run_scope=scoped(), enforce_scope=True)
    assert info.value.reason == "SCOPE_INQUIRY_IDS_CONFLICT"


def test_composition_receives_the_scoped_orders(tmp_path, monkeypatch):
    """The real `_run` path, stopped at the composition boundary."""
    from tests.launcher.test_backend import _write_runtime_configs

    production, research, _rows = _write_runtime_configs(tmp_path, pending_count=1)
    captured = {}

    def fake_compose(**kwargs):
        captured.update(kwargs)
        raise RuntimeError("stop-after-composition")

    monkeypatch.setattr(launcher, "compose_v12_production", fake_compose, raising=True)
    monkeypatch.setattr(launcher, "assess_readiness", lambda *_a, **_k: SimpleNamespace(
        missing_site_ids=(), ready=True))

    backend = ProductionBackend(
        config_path=research, production_config_path=production,
        cdp_probe=lambda _url: True, run_scope=scoped(), enforce_scope=True)
    backend.start()
    thread = backend._thread
    if thread is not None:
        thread.join(timeout=10)

    assert captured.get("inquiry_ids") == frozenset({ORDER})


def test_a_module_without_order_isolation_is_refused():
    with pytest.raises(ScopeError) as info:
        parse_run_scope(inquiry_ids=ORDER, modules="inquiry,quotation")
    assert info.value.reason == "SCOPE_MODULE_NOT_ISOLATABLE"
    with pytest.raises(ScopeError) as info:
        parse_run_scope(inquiry_ids=ORDER, modules="inquiry,tp")
    assert info.value.reason == "SCOPE_MODULE_NOT_ISOLATABLE"
    with pytest.raises(ScopeError) as info:
        parse_run_scope(inquiry_ids=ORDER, modules="inquiry,notification")
    assert info.value.reason == "SCOPE_MODULE_NOT_ISOLATABLE"


def test_mail_cannot_be_named_as_a_write_target():
    with pytest.raises(ScopeError) as info:
        parse_run_scope(inquiry_ids=ORDER, modules="inquiry", write_targets="smtp",
                        approval="OWNER-APPROVED:RFQ-021-FOLLOWUP")
    assert info.value.reason == "SCOPE_SMTP_NOT_ISOLATABLE"


# --- P0-B: no IMAP/SMTP without an explicit mail scope ---------------------

def test_preview_never_may_start_process_services(tmp_path):
    backend = ProductionBackend(root=tmp_path, preview_mode=True)
    assert backend.may_start_process_services() is False
    backend.start_process_services()
    assert backend._mail_research_service is None
    assert backend._mail_initial_start_consumed is False


def test_scoped_run_without_mail_scope_never_starts_process_services(tmp_path):
    backend = ProductionBackend(root=tmp_path, run_scope=scoped(), enforce_scope=True)
    assert backend.may_start_process_services() is False
    backend.start_process_services()
    assert backend._mail_research_service is None


def test_legacy_composition_is_unchanged(tmp_path):
    backend = ProductionBackend(root=tmp_path)
    assert backend.may_start_process_services() is True


def test_launcher_does_not_start_mail_when_the_backend_refuses(tmp_path, monkeypatch):
    events = []

    class Guard:
        def acquire(self):
            return True

        def release(self):
            return None

    class Backend:
        def __init__(self, **kwargs):
            events.append("backend")

        def may_start_process_services(self):
            return False

        def start_process_services(self):
            events.append("services")

        def start(self):
            events.append("start")

        def shutdown(self):
            events.append("shutdown")

        def local_view_loading(self):
            return False

    class App:
        def __init__(self, backend):
            events.append("gui")

        def run(self):
            events.append("run")

    import sys

    from src.gui import main as launcher_main
    monkeypatch.setattr(sys, "argv", [
        "INSO_V1.6.exe", "--scoped-start", "--scope-inquiries", ORDER])
    monkeypatch.setattr(launcher_main, "app_root", lambda: tmp_path)
    monkeypatch.setattr(launcher_main, "_configure_startup_log", lambda _: None)
    monkeypatch.setattr(launcher_main, "InsoDashboardApp", App)
    monkeypatch.setattr(launcher_main, "ProductionBackend", Backend)

    assert launcher_main.main(guard_factory=Guard) == 0
    assert "services" not in events


# --- P0-C: every other effect entry is gated too ---------------------------

def test_preview_refuses_order_mail_and_login_sweep(tmp_path):
    backend = ProductionBackend(root=tmp_path, preview_mode=True)
    assert backend.effect_actions_blocked() is True
    assert backend.start_order_mail_check() is False
    assert backend._order_mail_thread is None
    backend.start_login_all_sites()
    assert backend._login_all_thread is None
    assert backend.can_order_action(ORDER, "edit") is False
    assert backend.order_action_hint(ORDER, "edit") is False
    assert backend.request_order_action(ORDER, "edit", field="model", value="X") == (
        "安全预览模式不执行任何订单操作。")


def test_scoped_run_refuses_order_actions_outside_the_named_orders(tmp_path):
    backend = ProductionBackend(root=tmp_path, run_scope=scoped(), enforce_scope=True)
    assert backend.effect_actions_blocked() is True
    assert backend.can_order_action(OTHER, "edit") is False
    assert backend.request_order_action(OTHER, "edit", field="model", value="X") == (
        "该订单不在本次受控试运行范围内。")


def test_order_mail_handler_explains_the_refusal(monkeypatch):
    shown = []
    monkeypatch.setattr(app_module.messagebox, "showinfo",
                        lambda title, message: shown.append((title, message)))
    fake_self = SimpleNamespace(
        _closing=False,
        _backend=SimpleNamespace(
            effect_actions_blocked=lambda: True,
            start_order_mail_check=lambda: pytest.fail("must not start mail check"),
        ),
    )
    app_module.InsoDashboardApp._on_order_mail(fake_self)
    assert shown and "订单录单" in shown[0][1]


def test_login_all_handler_explains_the_refusal(monkeypatch):
    shown = []
    monkeypatch.setattr(app_module.messagebox, "showinfo",
                        lambda title, message: shown.append((title, message)))
    fake_self = SimpleNamespace(
        _login_all_running=False,
        _backend=SimpleNamespace(
            effect_actions_blocked=lambda: True,
            start_login_all_sites=lambda: pytest.fail("must not start a sweep"),
        ),
    )
    app_module.InsoDashboardApp._on_login_all(fake_self)
    assert shown and "一键登录" in shown[0][1]
