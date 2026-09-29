# RFQ-001 Execution Log

Append concise technical facts here during execution. Git remains the source of truth for full diffs.

For each meaningful execution step record:
- implementation decision;
- changed files and diff/commit range;
- exact test command and result;
- runtime evidence path/reference;
- implementation-only decision;
- true blocker, if any.

Do not record passwords, tokens, cookies, raw secrets, or unnecessary terminal noise.

## Entries

### 2026-09-29 — review repair closeout

- Changed exact-history settlement so a result set is complete only when the
  native response, cache and DOM agree and the pagination contract proves a
  first-page, single-page result: positive page size, `total_count <= page_size`
  and `total_count == response_row_count`. Missing, invalid or non-complete
  pagination now fails closed before a caller can treat zero or one rows as
  authoritative.
- `PlaywrightReadOnlySaveReconciler` now requires both an exact matched request
  and the explicit complete-result-set proof before it can return
  `CONFIRMED_NOT_SAVED` or `CONFIRMED_SAVED`; otherwise it returns `UNKNOWN`.
  Deterministic coverage includes total count greater than the current rows,
  non-first page, too-small page size, and both zero/one-row reconciliation
  candidates lacking completeness proof.
- Updated `docs/modules/INSO.md` to the live-verified parent-field contract:
  unique `td[data-field]` cell, double-click, exactly one visible enabled
  transient editor, immediate read-back. Updated the V1.2 baseline to retain a
  repository-visible, sanitized review summary alongside ignored detailed
  runtime evidence.
- Added `control-room/RFQ-001/LIVE_EVIDENCE_SANITIZED.json`, a reviewable
  evidence summary containing only side-effect booleans, selector/result counts,
  and identity/read-back checks. It contains no credentials, cookies, business
  values, record identifiers, or raw page data.
- Focused verification:
  `python -m pytest -q tests/inso/test_v12_duplicate_history.py tests/launcher/test_v12_composition.py -p no:cacheprovider --basetemp D:\\Program_Leo\\INSO_Leo\\.worktrees\\v1-2-design\\runtime\\pytest-rfq001-focused`
  — 80 passed.
- Full verification (split for the command-window time bound):
  `tests/core tests/gui` — 83 passed, 10 skipped;
  `tests/inso tests/launcher` — 179 passed;
  `tests/workflow tests/sheets` — 172 passed, 1 skipped;
  `tests/research` — 230 passed. Total: 664 passed, 11 skipped.
  `python -m ruff check src tests` and `git diff --check` — PASS.
- No real Save, Save-and-Send, Send, SMTP, or Sheets write was performed.
  Production Write Gate remains CLOSED.
- Committed repair and Control Room records under
  `fix(v1.2): require complete save reconciliation results`; the final commit
  is the branch HEAD after this execution log update.

### 2026-09-29 — parent-field and runtime recovery acceptance work

- Updated `PlaywrightParentProductFields` to use the verified business-inquiry
  grid contract: uniquely identify each `PartNo` / `Brand` / `Qty` cell,
  double-click it, require one visible enabled editor, write, and read back
  from the editor or committed cell. No positional selectors are used.
- Added the matching static-cell/editor regression coverage in
  `tests/inso/test_v12_purchase_writer.py`.
- Updated `attach_inso_research_session` so an app-owned Chrome is closed if
  authentication stops at a manual verification challenge; added the
  regression in `tests/launcher/test_inso_session.py`.
- Live unsaved business-inquiry parent-field read-back was performed without
  Save, Save-and-Send, or Send. Runtime evidence is sanitized and ignored at
  `runtime/evidence/v12-phase-a-final/report.json`.
- Focused verification:
  `python -m pytest -q tests/launcher/test_inso_session.py tests/inso/test_v12_purchase_writer.py tests/launcher/test_v12_phase_a_readonly.py tests/launcher/test_v12_composition.py -p no:cacheprovider --basetemp D:\\Program_Leo\\INSO_Leo\\runtime\\pytest-focused-0929c`
  — 67 passed.
- Full verification (split only to use project-local temporary directories):
  `tests/core tests/gui` — 83 passed, 10 skipped;
  `tests/inso tests/launcher` — 174 passed;
  `tests/workflow tests/sheets` — 172 passed, 1 skipped;
  `tests/research` — 230 passed.
  `python -m ruff check src tests` and `git diff --check` — PASS.
- Live read-only reconciliation-detail acceptance was completed through the
  existing authenticated INSO session: one existing record was opened without
  mutation; `BillID` and `PENO` were unique and nonempty; `PartNo`, `Brand`,
  and `Qty` each had one field and exactly matched the selected list record.
  No record values were persisted in this log.
- The live form had one visible `#btnSave` with save semantics. `#btnSave2`
  and `#bcSend` were inspected only; neither was dispatched. Production Write
  Gate remains CLOSED.
- The isolated Chrome profile's phone-verification-code control remains a
  correctly fail-closed `MANUAL_VERIFICATION_REQUIRED` path, but did not block
  read-only acceptance because an already-authenticated INSO session was
  available for the scoped verification.
