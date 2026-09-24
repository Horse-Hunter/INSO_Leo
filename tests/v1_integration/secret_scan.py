"""Quick secret scan for the V1 final integration commit."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

PATTERNS: tuple[tuple[str, str], ...] = (
    (r"AIza[0-9A-Za-z\-_]{35}", "Google API key"),
    (r"ya29\.[0-9A-Za-z\-_]{50,}", "Google OAuth token"),
    (r"1//[0-9A-Za-z\-_]{50,}", "Google OAuth refresh"),
    (r'sk-[A-Za-z0-9]{20,}', "OpenAI key"),
)

EXCLUDE = (".git", "__pycache__", ".pytest_cache", ".ruff_cache", "node_modules", ".browser-profile")

ok = True
for path in ROOT.rglob("*"):
    if not path.is_file():
        continue
    if any(part in path.parts for part in EXCLUDE):
        continue
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        continue
    for pattern, label in PATTERNS:
        for match in re.finditer(pattern, text):
            ok = False
            sys.stderr.write(
                f"POSSIBLE {label} in {path.relative_to(ROOT)}: "
                f"{match.group(0)[:40]}\n"
            )

print("SECRET_SCAN_OK" if ok else "SECRET_SCAN_FAIL")
sys.exit(0 if ok else 1)