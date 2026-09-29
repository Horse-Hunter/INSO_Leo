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
