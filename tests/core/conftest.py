"""Pytest bootstrap for Core tests.

Adds ``src/`` to ``sys.path`` so business modules and tests can
``from core.credential_provider import ...`` without an installed package.

The canonical Python Provider must remain importable without third-party
dependencies; this conftest is therefore dependency-free and contains no
test fixtures of its own.
"""

import pathlib
import sys


def _add_src_to_path() -> None:
    root = pathlib.Path(__file__).resolve().parents[2]
    src = root / "src"
    src_str = str(src)
    if src_str not in sys.path:
        sys.path.insert(0, src_str)


_add_src_to_path()