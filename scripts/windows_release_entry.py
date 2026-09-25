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
        return reason if re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*Error", reason) else "CredentialError"

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
    return 0 if (
        report["canonical_vault_exists"]
        and report["module_exists"]
        and report["powershell_discovered"]
        and not report["vault_override_set"]
        and not report["powershell_override_set"]
        and all(item.available for item in sites)
    ) else 1


def _self_check() -> int:
    """Check bundled GUI dependencies without opening a window or runtime."""
    try:
        import tkinter

        interpreter = tkinter.Tcl()
        interpreter.eval("info patchlevel")
        import customtkinter  # noqa: F401 - import is the packaging check
        from src.gui import main  # noqa: F401 - import is the packaging check
    except Exception:
        return 1
    return 0


if __name__ == "__main__":
    if sys.argv[1:] == ["--self-check"]:
        raise SystemExit(_self_check())
    if sys.argv[1:] == ["--diagnose-vault"]:
        raise SystemExit(_diagnose_vault())
    from src.gui.main import main

    raise SystemExit(main())
