"""Fail if a generic Windows release contains local runtime/config artifacts."""

from __future__ import annotations

import re
import sys
from pathlib import Path


FORBIDDEN_SUFFIXES = {".sqlite", ".sqlite3", ".db", ".xlsx", ".xlsm"}
FORBIDDEN_NAMES = {
    "research.json",
    "production.json",
    "token.json",
    "credentials.json",
    "storage-state.json",
    "local state",
}
FORBIDDEN_DIRS = {
    ".browser-profile",
    "browser-profile",
    "chrome-profile",
    "playwright/.auth",
}
SENSITIVE_PATTERNS = (
    re.compile(rb"ya29\.[A-Za-z0-9_-]{20,}"),
    re.compile(rb"1//[A-Za-z0-9_-]{20,}"),
    re.compile(rb"AIza[0-9A-Za-z_-]{30,}"),
)
FORBIDDEN_BROWSER_BINARIES = {
    "chrome.exe",
    "chromium.exe",
    "chrome-headless-shell.exe",
    "headless_shell.exe",
}


def scan(root: Path) -> list[str]:
    problems = []
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if path.is_dir() and any(
            "/".join(relative.parts[index:]).casefold() == name
            for index in range(len(relative.parts))
            for name in FORBIDDEN_DIRS
        ):
            problems.append("browser profile directory")
        if path.name.casefold() in FORBIDDEN_BROWSER_BINARIES:
            problems.append("browser executable")
        if path.is_file():
            name = path.name.casefold()
            if (
                name in FORBIDDEN_NAMES
                or name.startswith(("client_secret", "oauth-token", "google-token"))
                or name.endswith(
                    (".sqlite", ".sqlite3", ".db", ".xlsx", ".xlsm", ".sqlite-wal", ".sqlite-shm", ".sqlite3-wal", ".sqlite3-shm", ".db-wal", ".db-shm")
                )
            ):
                problems.append("runtime data file")
            try:
                data = path.read_bytes()
            except OSError:
                problems.append("unreadable artifact file")
                continue
            if any(pattern.search(data) for pattern in SENSITIVE_PATTERNS):
                problems.append("credential token pattern")
    return sorted(set(problems))


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("dist/INSO_V1.1")
    findings = scan(target)
    if findings:
        print("RELEASE_SCAN_FAIL: " + ", ".join(findings))
        raise SystemExit(1)
    print("RELEASE_SCAN_OK")
