"""PyInstaller entry shim and non-secret frozen credential readiness probe."""

import json
import os
import re
import sys
from pathlib import Path


def _diagnose_vault() -> int:
    """Write only readiness booleans and safe error class names to local logs."""
    from src.core._vault_backend import _default_module_path
    from src.core.app_paths import app_root
    from src.core.credential_provider import _discover_pwsh
    from src.research.credentials import CoreResearchCredentials

    local_app_data = os.environ.get("LOCALAPPDATA")
    canonical_vault = (
        Path(local_app_data) / "INSO_Leo" / "credential-vault.json"
        if local_app_data
        else None
    )
    sites = CoreResearchCredentials().site_readiness()

    def safe_reason(reason: str | None) -> str | None:
        if reason is None:
            return None
        return (
            reason
            if re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*Error", reason)
            else "CredentialError"
        )

    report = {
        "canonical_vault_exists": bool(canonical_vault and canonical_vault.is_file()),
        "module_exists": Path(_default_module_path()).is_file(),
        "powershell_discovered": bool(_discover_pwsh()),
        "vault_override_set": bool(os.environ.get("INSO_CREDENTIAL_VAULT_PATH")),
        "powershell_override_set": bool(os.environ.get("INSO_CREDENTIAL_PWSH")),
        "sites": [
            {
                "site_id": item.site_id,
                "available": item.available,
                "reason": safe_reason(item.reason),
            }
            for item in sites
        ],
    }
    log_dir = app_root() / "runtime" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / "credential-readiness.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return (
        0
        if (
            report["canonical_vault_exists"]
            and report["module_exists"]
            and report["powershell_discovered"]
            and not report["vault_override_set"]
            and not report["powershell_override_set"]
            and all(item.available for item in sites)
        )
        else 1
    )


def _self_check() -> int:
    """Check bundled GUI dependencies without opening a window or runtime."""
    try:
        import tkinter

        interpreter = tkinter.Tcl()
        interpreter.eval("info patchlevel")
        import customtkinter  # noqa: F401 - import is the packaging check

        from src.gui import main  # noqa: F401 - import is the packaging check
    except Exception:  # noqa: BLE001 - frozen dependency probe must return a safe exit code
        return 1
    return 0


def _idle_self_check() -> int:
    """Construct and render the real idle dashboard; never press Start or acquire CDP."""
    from src.core.app_paths import app_root
    from src.gui.app import InsoDashboardApp
    from src.gui.contracts import RunState
    from src.launcher.backend import ProductionBackend

    backend = ProductionBackend()
    app = None
    try:
        app = InsoDashboardApp(backend)
        app._root.withdraw()
        app._action_button.configure(state="disabled")
        app._root.update_idletasks()
        app._root.update()
        report = {
            "title": app._root.title(),
            "state": backend.get_status().state.value,
            "business_thread_started": backend._thread is not None,
            "gui_rendered": True,
            "start_action": app._action_button.cget("text"),
        }
        directory = app_root() / "runtime" / "logs"
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "v13-idle-self-check.json").write_text(
            json.dumps(report, ensure_ascii=False), encoding="utf-8"
        )
        return (
            0
            if report["title"] == "INSO_V1.3"
            and backend.get_status().state is RunState.STOPPED
            and not report["business_thread_started"]
            else 1
        )
    finally:
        if app is not None:
            app._finish_close()
        backend.shutdown()


def _cdp_self_check() -> int:
    """Prove the frozen driver attaches; never launch/close Chrome or run business."""
    from src.core.app_paths import app_root, runtime_config_path
    from src.launcher.browser_bootstrap import (
        BrowserBootstrapError,
        _read_cdp_version,
        acquire_cdp_browser,
    )
    from src.research.runtime import load_runtime_config

    root = app_root()
    handle = None
    report = {"connected": False, "business_started": False}
    try:
        config = json.loads(runtime_config_path("production.json", root=root).read_text(encoding="utf-8"))
        research = load_runtime_config(runtime_config_path("research.json", root=root))
        if _read_cdp_version(research.cdp.cdp_url) is None:
            raise BrowserBootstrapError("CDP_ATTACH_FAILED")
        # A diagnostic only attaches to the already-running fixed session.
        handle = acquire_cdp_browser(research.cdp.cdp_url, root, config, probe=lambda _: True)
        report.update(connected=handle.browser.is_connected(),
                      unique_context=len(handle.browser.contexts) == 1,
                      page_count=sum(len(context.pages) for context in handle.browser.contexts))
    except Exception as exc:  # noqa: BLE001 - never persist raw browser/provider exceptions
        reason = getattr(exc, "reason_code", None)
        report["reason"] = reason if isinstance(reason, str) and re.fullmatch(r"[A-Z_]+", reason) else "CDP_CHECK_FAILED"
        report["error_class"] = type(exc).__name__
    finally:
        if handle is not None:
            handle.disconnect()  # No Browser.close, tab cleanup, workflow or SMTP.
    directory = root / "runtime" / "logs"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "v13-cdp-self-check.json").write_text(json.dumps(report), encoding="utf-8")
    return 0 if report["connected"] and report.get("unique_context") else 1


if __name__ == "__main__":
    if sys.argv[1:] == ["--cdp-self-check"]:
        raise SystemExit(_cdp_self_check())
    if sys.argv[1:] == ["--idle-self-check"]:
        raise SystemExit(_idle_self_check())
    if sys.argv[1:] == ["--self-check"]:
        raise SystemExit(_self_check())
    if sys.argv[1:] == ["--diagnose-vault"]:
        raise SystemExit(_diagnose_vault())
    from src.gui.main import main

    raise SystemExit(main())
