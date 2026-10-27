"""Resolve the single application root used by Python and frozen builds."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def application_name() -> str:
    """Use the validated frozen product name; source dashboards keep their label."""
    name = Path(sys.executable).stem
    return name if getattr(sys, "frozen", False) and name in {
        "INSO_V1.1", "INSO_V1.2", "INSO_V1.3", "INSO_V1.4", "INSO_V1.5", "INSO_V1.6"
    } else "INSO_V1.6"


def app_root(*, module_file: str | Path | None = None, frozen: bool | None = None,
             executable: str | Path | None = None) -> Path:
    """Return repository root in Python mode and executable directory when frozen."""

    is_frozen = bool(getattr(sys, "frozen", False)) if frozen is None else frozen
    if is_frozen:
        exe = Path(executable) if executable is not None else Path(sys.executable)
        return exe.resolve().parent
    runtime_root = os.environ.get("INSO_RUNTIME_ROOT")
    if runtime_root:
        candidate = Path(runtime_root).expanduser()
        if candidate.is_dir():
            return candidate.resolve()
    source = Path(module_file) if module_file is not None else Path(__file__)
    return source.resolve().parents[2]


def runtime_config_path(name: str, *, root: str | Path | None = None) -> Path:
    if name not in {"research.json", "production.json"}:
        raise ValueError("unsupported runtime config name")
    base = Path(root) if root is not None else app_root()
    return base / "runtime" / name


def resolve_app_path(path: str | Path, *, root: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else Path(root) / candidate
