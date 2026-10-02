# RFQ-002 — V1.2 runnable Windows release closeout

**Status source:** `control-room/COORDINATION.md`  
**Review:** REQUIRED  
**Branch:** `feature/v1-2`

## Owner decision — packaging timing (2026-09-30)

SUPERSEDED 2026-10-02: Owner completed personal discussion/Review of final
submission changes and explicitly authorized packaging V1.2 now. Reuse the
existing release pipeline; build and dependency/launch smoke only. Do not run
orders or test final Save-and-Send. First submission remains Owner's next true
order. This lifts EXE deferral, not authorization for executor production sends.

Do **not** build or hand over the Windows release artifact yet. The packaging
closeout is deferred until the whole chain **including the purchase-draft leg**
has run through end to end on real production inputs. Scope items 4–6 and the
artifact-related acceptance lines below are therefore *gated*, not cancelled:
they stay open and unstarted, and the RFQ remains `IN_PROGRESS`.

Rationale: packaging first would freeze an artifact whose most valuable path
(the purchase-draft leg) has not yet been proven end to end, so a successful
build would not mean a working product.

## Business goal

### Owner update — final submission, pending implementation (2026-10-02)

Owner accepted the real draft results and requested removal of automatic
purchase screenshots, then a maximum of ten new implementation lines for a
single 客临时询价 保存并发送 click, five-second wait, upper business-inquiry
verification of the matching model and newly added time, and operation-tab
closure. No tests or live execution of this final step are authorized now;
Owner will perform its first real run on the next genuine order. An uncertain
result must never trigger a second click. This is a narrowly scoped future
submission authorization, not authorization for arbitrary INSO sends, Sheets
writes, new CDP sessions or EXE packaging. Existing closed-gate statements
remain the execution boundary until that implementation is safely connected.

Owner subsequently approved relaxing the ten-line ceiling and explicitly
requested a detailed implementation report for personal Review. The submission
connection is now implemented in the existing production chain; it is NOT run
or live-tested by the executor. Prior closed-gate/NO-SEND acceptance statements
below are historical baseline restrictions, superseded only for this narrowly
authorized future Save-and-Send and the earlier real SMTP exception. Ordinary
Save Data, generic INSO Send and Sheets writes remain forbidden. No EXE work.
See FINAL_SUBMISSION_REVIEW.md for exact scope, safeguards and unverified items.

Owner further clarified: the upper inquiry list is newest-first by time.
Final submission confirmation reads ONLY the first row of the settled first
page, checking exact model, current submission time and a changed stable ID.
Total history exceeding one page must NOT block submission. This does not
relax complete lower-history reads for the seven-day duplicate check or the
default complete-set legacy reconciliation. No submission testing/restart.

### Owner clarification — duplicate-history source (2026-10-02)

The seven-day duplicate check must read the LOWER 采临时询价 region of the
business-inquiry page, including its true creator column, not the upper
business-inquiry list. Reuse the existing Stock_VenQuote source and native
controls, existing parser and Workflow rules; preserve the shared CDP and
closed save/send/Sheets-write gate. Prove pagination completeness and do not
filter out unquoted history using Research price eligibility. This clarification
supersedes upper-list duplicate-history assumptions, not save reconciliation.

Turn the already-built V1.2 capability into a Windows release candidate that the Owner can actually package, launch and observe through the real production entry point, while keeping every real external write/send gate closed.

This RFQ is release/integration closeout, not a new feature project.

## Current gap

RFQ-001 closed the pre-save live acceptance, but the current Windows release path is still the V1.1 release path:

- packaging, executable naming and release docs still identify V1.1;
- the default production launcher does not automatically activate the V1.2 production flow;
- V1.2 persistence/runtime readiness is not yet proven from a clean packaged-start path;
- there is no V1.2 packaged smoke evidence proving that the real release entry point reaches the safe V1.2 workflow.

Therefore V1.2 is not yet ready to hand to Owner as a packaged runnable release.

## Required outcome

The Owner must be able to build a clearly identified V1.2 Windows artifact, place the normal local runtime configuration beside it, launch it, and have the production path use V1.2 rather than silently falling back to V1.1-only behavior.

A safe release-candidate run must be able to reach the V1.2 workflow through the current allowed boundary:

Sheets/read → Research → duplicate/business-rule evaluation → V1.2 state/GUI → safe purchase-draft preparation/read-back where applicable.

Notification decisions/state may be produced, but no real SMTP may be sent while the gate is closed.

No real INSO Save, Save-and-Send, Send, SMTP send, or Sheets write is authorized in this RFQ.

## Scope

1. Make the normal packaged production entry point activate the existing V1.2 production workflow without test-only/manual dependency injection.
2. Complete the minimum production composition needed for the existing V1.2 modules to run from the packaged application.
3. Ensure V1.2 persistence is initialized/migrated through the approved additive/backup-safe path and does not require a pre-handcrafted database.
4. Create a V1.2 Windows release artifact/path that is clearly separate from the V1.1 release artifact and does not overwrite the V1.1 baseline.
5. Update Windows release documentation and user-facing version identity to V1.2 where the V1.2 artifact is concerned.
6. Prove a packaged V1.2 safe smoke path using the real release entry point and repository-reviewable sanitized evidence.
7. Run focused integration/release tests, full regression, Ruff and diff check.
8. Record execution facts in `EXECUTION_LOG.md`, produce `FINAL_REPORT.md`, and set status to `REVIEW_REQUIRED`.

## Acceptance

- V1.1 release anchor remains unchanged and recoverable.
- A V1.2 Windows artifact can be built successfully and passes frozen self-check/artifact safety scan.
- The produced executable/release directory is identified as V1.2, not V1.1.
- Launching the V1.2 production artifact uses the V1.2 workflow path by default; it must not silently run V1.1-only processing because V1.2 production adapters were omitted.
- A clean/approved runtime can initialize or migrate V1.2 persistence through the canonical safe migration path; no destructive schema rewrite.
- Packaged smoke evidence proves the real V1.2 entry reaches V1.2 state/flow and does not merely import V1.2 code.
- Existing business rules from `docs/PRODUCT_BASELINE.md` and `docs/V1_2_ARCHITECTURE.md` are preserved; no new business rules are invented.
- GUI can surface V1.2 business state from the same packaged production run.
- Missing/invalid V1.2 production dependencies fail closed and visibly; no silent downgrade to V1.1-only behavior.
- Repository-visible sanitized evidence is sufficient for independent CEO Review and contains no credentials, cookies, business values, raw page dumps or sensitive record identifiers.
- Full regression: PASS.
- Ruff: PASS.
- `git diff --check`: PASS.
- Build/release smoke: PASS.
- REAL SAVE: NO.
- REAL SAVE-AND-SEND: NO.
- REAL SEND: NO.
- REAL SMTP: NO.
- SHEETS WRITE: NO.
- Production Write Gate: CLOSED.
- Implementation + Control Room records committed and pushed.
- RFQ status: `REVIEW_REQUIRED`.

## Non-goals

- Do not open Production Write Gate.
- Do not perform real INSO Save / Save-and-Send / Send.
- Do not send real email.
- Do not write Google Sheets.
- Do not redesign V1.2 business rules.
- Do not add unrelated frameworks or refactor V1.1.
- Do not merge/release to main in this RFQ.

## Canonical sources

- `AI_START_HERE.md`
- `docs/PROJECT_BASELINE.md`
- `docs/PRODUCT_BASELINE.md`
- `docs/V1_2_ARCHITECTURE.md`
- `docs/WINDOWS_RELEASE.md`
- `docs/SAFETY.md`
- `docs/MODULE_INDEX.md`
- `control-room/RFQ-001/REVIEW.md`

## Safety

Production Write Gate remains **CLOSED** for all execution and packaged smoke verification in this RFQ.
