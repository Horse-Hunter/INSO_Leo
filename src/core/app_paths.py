"""Resolve the single application root used by Python and frozen builds."""

from __future__ import annotations

import sys
from pathlib import Path


def app_root(*, module_file: str | Path | None = None, frozen: bool | None = None,
             executable: str | Path | None = None) -> Path:
    """Return repository root in Python mode and executable directory when frozen."""

    is_frozen = bool(getattr(sys, "frozen", False)) if frozen is None else frozen
    if is_frozen:
        exe = Path(executable) if executable is not None else Path(sys.executable)
        return exe.resolve().parent
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
