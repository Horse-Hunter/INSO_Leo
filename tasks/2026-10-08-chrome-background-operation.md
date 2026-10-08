# Task: Stop automatic Chrome focus and desktop activation

status: in_progress
owner: Codex
created: 2026-10-08
updated: 2026-10-08

## authority / goal
Owner requests a new version because Chrome steals focus and occupies the desktop. Keep automated production browser operations unobtrusive through the existing background target creation primitive.

## scope / requirements
- Reuse src/research/cdp_pages.py; remove foreground context.new_page calls in quote input, quote cleanup, INSO login/recovery and dedicated session parking.
- Background targets in an existing context do not activate/restore its window. If no page exists, explicitly create the first window minimized via supported CDP parameters; never switch profile, headless browser, cookies or CDP endpoint.
- Never fall back to foreground creation after protocol failure; retain existing failure handling and protected manual-auth pages.
- Explicit Owner one-click manual-login presentation remains available; automatic maintenance remains non-presenting.
- No persistent-window hider or focus-restoring timer; do not hide a window the Owner deliberately opened.
- Offline regression/full/Ruff and candidate BuildOnly/frozen/scan. Read-only local CDP version/protocol inspection permitted; no live login, purchase, mail, Sheets writes or production polling. Do not replace a running release or deploy a new unreviewed hash.

## acceptance
Pending: call-site regressions, blank keepalive cleanup, minimized-first target, no foreground fallback, manual protection, focused/full/candidate checks. Actual live desktop symptom must not be claimed resolved solely by mocked tests.
