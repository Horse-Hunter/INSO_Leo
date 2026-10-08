# V1.3 readiness repair verification report

Date: 2026-10-08
Status: REVIEW_REQUIRED; repaired candidate verified, formal deployment pending Owner decision.
Base: feature/v1-3-integration, 03f4bf3328b0931b4bdc5dc05865b9f35322cf7e.
Repair branch: codex/v13-readiness-repair. Approved integration branch preserved.

## Findings and minimal repairs

1. The fixed Chrome endpoint responded, but one unresponsive Google Sheets target stalled Playwright CDP initialization. Closing that target restored attachment. A normally responsive Sheets page coexists successfully with the final frozen driver. Each attachment attempt now receives up to 10 seconds within the existing 20-second overall readiness window. Initialization timeout has a precise safe user message. No automatic closure of Owner tabs or profile reset.
2. Findchips explicitly returned a CAPTCHA login refusal. Its existing login path now classifies this as MANUAL_VERIFICATION_REQUIRED; other explicit refusals become LOGIN_REJECTED, without exposing server text. No CAPTCHA bypass.
3. Failed manual one-click login pages now use the existing protected-target mechanism, as background failures already did. They survive later research tab cleanup; protection is released when the Owner closes the page.

A narrow --cdp-self-check attaches/detaches the frozen driver to the existing session, records sanitized diagnostics and never starts business processing or launches/closes Chrome.

## Candidate and deployment boundary

Final candidate EXE SHA256:
F73A42E8F8ACBFED16DF622D5607A3C1F6E073C0884D0238C64AE1F69C50F5C5

Candidate path:
C:/Users/Leo/.codex/worktrees/rfq-006-integration/INSO_Leo/build/windows-release-stage-1.3/dist/INSO_V1.3

Formal production remains:
D:/Program_Leo/INSO_Leo/dist/INSO_V1.3
Original reviewed/formal EXE SHA256:
7ECE6917BF77E263E1E56BC528A63EE0798404DB1D03D494499B94A4A16B663F

The hash differs because this candidate contains the repairs and frozen diagnostic above. It has NOT replaced the approved formal release. The original deployment instruction requires reporting a different rebuilt hash and deciding before replacement. The approved candidate was separately preserved.

## Verification matrix

| Feature | Evidence / result |
|---|---|
| Fixed CDP / frozen driver | PASS; final frozen attachment also passed with an actual normal Sheets quote-input page open. Existing Chrome process/profile reused. |
| One-click/background login reuse | Five sites authenticated; Findchips requires manual CAPTCHA. Six-site sweep completes, failed pages preserved. |
| Research | Real read-only six-source query completed successfully; source-specific no-price results retained. Findchips public price search worked despite account CAPTCHA. |
| Google source reading | Real configured worksheets read successfully using existing OAuth grants. |
| INSO quotations | Live quotation rows have all 14 payload fields. All 12 currently eligible source rows returned NO_RECENT_QUOTE under real rolling72h; no date fabrication. |
| Google inline edits | Four editable fields passed actual same-value RAW write/readback through the canonical manual-action backend on a DB copy. Source values/status unchanged; projection refreshed and 15-minute timer reset. Double-click/context-menu bindings rendered; edit/rerun guards covered by regressions. |
| Quote update / already exists | Real RAW write/readback, one actual button click, ALREADY_EXISTS result, dismissal and script-owned automatic input cleanup passed. No repeat click. |
| Source status after update | Real 30-second status check detected unchanged source state and produced SOURCE_STATUS_NOT_UPDATED hold/yellow projection and queued notification in copied DB. Actual SMTP blocked. |
| New quote insertion | Offline insertion/readback/state regression PASS. No genuine eligible 72-hour quote was available among all 12 rows, so real new insertion was not fabricated or claimed. |
| Duplicate check / draft | Live canonical duplicate/history check passed. Separate guarded unsaved AI draft/readback passed; draft closed without Save/Save-and-Send. |
| Combined scheduler / stop | Actual backend start -> combined cycle -> 15-minute idle -> stop-after-cycle -> shutdown passed on copied DB, with hard purchase/SMTP/Google-write guards. Counters found=1/completed=1/in-progress=0; normal quotation row cooldown absent. |
| GUI / timers | Actual Tk dashboard rendered, counters projected, purchase cooldown 02:00, quotation state ordinary countdown, edit/context bindings present. Final frozen idle GUI passed; no business worker started. |
| Manual page protection | Both actual Findchips manual pages survived detach/reattach and later parking; offline Owner-close release regression passed. |
| Purchase/email safety | Save/Save-and-Send and SMTP blocked at concrete adapter boundaries. No actual purchase order or email sent. |

## Checks

- Focused RFQ-003/004/005/006/008, launcher, GUI and Findchips: 720 passed.
- Full safe/offline: 1519 passed, 1 skipped. Skip: Windows test environment cannot create the symlink required by one evidence/safety test.
- Ruff src tests scripts/windows_release_entry.py: PASS.
- git diff --check: PASS.
- V1.3 BuildOnly: PASS; frozen dependency self-check: PASS; release scan: PASS.
- Final frozen --self-check, --idle-self-check, --cdp-self-check: exit 0.
- All final tests refer to this final candidate; superseded intermediate builds are not deployment sources.

## Protected production assets and limits

V1.2 EXE before/after SHA256:
340D7F7E7E818FA74DE36B138B205F5905F320406FD8D391EF860BD052529E5F

Production workflow DB matched its deployment baseline hash after probes; live backend probes used isolated copies. Configuration, credential vault, fixed Chrome profile/session/CDP configuration were not replaced. Two OAuth token cache files refreshed naturally and Chrome Local State/Preferences changed through normal browser activity; these files are not claimed bitwise identical. Cookies were not cleared, Chrome was not restarted, and no second Chrome was established.

No unguarded production business loop, real purchase, Save/Save-and-Send, real SMTP or historical purchase replay was executed. The Owner-authorized quote duplicate update was executed once; historical quote dates were preserved. No fake recent quotation was introduced.

Remaining external prerequisite: Findchips manual CAPTCHA/account login. New-insert live evidence remains unavailable because current real data has no eligible recent quote. No claim that every site is authenticated or that real insertion was exercised. The repaired EXE requires an Owner deployment decision and subsequent formal deployed checks; the current formal EXE is still the original reviewed version.

Sanitized local evidence is under ignored .tmp. Raw production rows, OAuth contents, credentials, DB copies and generated release assets are excluded from Git.
