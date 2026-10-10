# RFQ-010 Execution Log

2026-10-10 executor: Codex. Status REVIEW_REQUIRED; CEO PASS not asserted.

## Base / boundaries

Read project entry and task/navigation, module/CDP/product rules. Continue reviewed
Phase1 b85d9c1a957938553da885ec3ed8b0feab45b283 on its development worktree.
Existing V1.3 reviewed fd7ce8665c65de3f0d1c18cf85369e8eff0a273c remains an ancestor.
Root checkout, release runtime/configs, credentials and production DB not edited.
Owner explicitly authorized two real mail samples and unsaved sales-header edits.
No deployment, dependencies installed, new login/profile or business state machine.

## Implementation

- order_mail adds bounded in-memory labelled PI extraction to existing read-only
  receiver, with final FLAGS audit even when extraction rejects structure.
- INSO owns header-only adapter/domain; only two text fields are fillable, enum
  fields use exact native choices. First matching customer, always-RMB and all
  eight early/final readbacks; no retry/save/submit/detail/upload operations.
- Launcher composes existing canonical CDP/InsoSessionGuard/Vault with a pinned
  V1.4 page; separate worker never changes inquiry execution state.
- Existing CDP tab helper adds reservation URL/window.name marker. Parking retains
  reservations, default authentication/research-shell discovery excludes them.
  INSO receives ownership predicate by injection, avoiding a Research dependency.
- GUI retains Phase1 split buttons, adds explicit sample choice/status and safe
  report. No periodic mail timer, production persistence or SMTP changes.
- Module/CDP docs record Owner-authorized exception for independently owned sales
  review tabs, submitted to CEO review as boundary extension.

## Authorized live evidence (sanitized only)

Both confirmed mail Excel PI fields uniquely parse; read-only FLAGS unchanged.
Native sales menu/list/Bill discovered in the existing authenticated shell.
Customer result dropdown contains fixed header plus a separate real tbody table;
initial strict selector stopped rather than guessing. Corrected scope to tbody.
Delivery text column is td.textField; initial wrong-column selector stopped,
then narrow adapter corrected after static DOM structure inspection.
No save/submit/details/upload action was used during discovery or verification.

Sample1: WAITING_OWNER, checked_controls=8, matching_customer_count=2,
RMB_SELECTED=True. Page retained. Owner inspected and replied 已返回 after
returning to sales list. Sample2: WAITING_OWNER, checked_controls=8,
TAB_REUSED=True, EXISTING_PROMPT_CANCELLED=False, RMB_SELECTED=True,
matching_customer_count=2. In-memory comparison confirmed same XS, value omitted.

Existing independent inquiry authentication: RESTORED, distinct tab=True;
sales URL and all header values unchanged. Existing shared parking cleaned the
inquiry authentication tab and preserved sales tab, wait marker and all values.
Disconnect stopped only the worker-owned Playwright client. No Chrome/tab closure
of V1.4. Concurrency production side effects intentionally not invoked.

## Offline checks

Initial focused run: 240 passed. Added reservation/login/parking isolation and
concurrent business-worker tests. First full: 1713 passed, 2 failed, 1 skipped;
failures were test doubles missing window.name/main_frame contracts, corrected
without weakening ownership fail-closed behavior. Final full: 1715 passed,
1 skipped in69.29s. Existing V1.3 suites included unchanged production behaviors.

Safe commands use existing Python and bundled dependency path for tzdata only:
`python -X utf8` with pytest.main(['tests','-q',
'--basetemp=.tmp/pytest-rfq010-full-final']). No dependency installation.
`python -m ruff check src tests --no-cache`: all checks passed.
`git diff --check`: passed. Raw live output/attachments not saved or staged.
Final focused: 248 passed in20.34s (PI/header/GUI/worker/auth/parking/keepalive
/release infrastructure). Commit/push verification is reported with final HEAD.

## Limitations / UNKNOWN

Only the two confirmed dates are eligible, fail closed if missing/ambiguous.
Other Excel formats are not generalized. Real existing-document prompt did not
appear in sample2; cancellation behavior tested offline. Full live inquiry
procurement/SMTP was outside authorized verification; concurrency tested with
real separate authentication/cleanup and offline workers. Frozen old V1.3 EXE
is unchanged and has not been validated concurrently with this undeployed build.
No claim of deployment, CEO approval or persistence of an unsaved order.
