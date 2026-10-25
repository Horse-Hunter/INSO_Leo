# Task: V1.5 RFQ_BRIEF discovery and inquiry identity alignment

status: DISCOVERY_REVIEW_REQUIRED
phase: DISCOVERY_ONLY
owner: Codex
created: 2026-10-25
updated: 2026-10-25

## problem / goal
Owner requests safe read-only Brief discovery and real source/order identity evidence for both 2026 and SHAHAB, using reviewed V1.4 infrastructure in an isolated V1.5 worktree. Preserve UNKNOWN and stop at discovery.

## current_facts / authority
- Owner request in this chat supplies the bounded task requirements.
- Baseline: 124e39ca17dcf4a59e7e72b97a40331609d955e8, with explicit CEO code-review PASS. Later remote tip 4f58926 contains REVIEW_REQUIRED INSO recovery; intentionally excluded.
- Owner separately approved once-only read-only extension of the exact Brief title in the existing configured Spreadsheet, preserving existing browser/auth/document/gid guards and TSV limits, complete column inspection, no production code/schema/write change.
- Exact title is RFQ_BRIEF; Owner explicitly confirmed correction of RPF_BRIEF and application of that authorization to RFQ_BRIEF.
- Initial business/browser conflict stopped interactive discovery. Owner subsequently stated the program was stopped and CDP available; preflight repeated before resuming. Existing manual pages preserved; own pages only.
- Owner requested evaluating model+quantity+reverse ordering, then model+quantity+rfq_date. Discovery verified those alternatives and retained the two-to-two current pointer/order alignment separately from unique business keys.

## scope / non_scope
Read existing relevant navigation/safety/module/source/config wiring; reuse canonical CDP 9222 and native TSV. Full schema, raw price format, direct IDs first, compound-key uniqueness, real samples for each source, existing local identity/Research linkage read-only. No Google edits, email, ERP/procurement, quotation calculation, polling, production SQLite writes, browser launch/login/close/profile cleanup, dependencies, builds or deployment. No raw TSV/table/customer/account/order values/screenshots in Git or report. No real business data in test DB.

## acceptance / evidence
- [x] Owner-approved isolated branch/worktree and reviewed baseline; unrelated dirty work preserved.
- [x] A-I sanitized report: V15_RPF_BRIEF_DISCOVERY.md (requested filename retained; actual target correction explicit).
- [x] 17-column schema/header/85-record/target-price discovery and limitations documented.
- [x] Real unique source and existing inquiry_id/Research samples for both 2026 and SHAHAB; no regenerated ID.
- [x] Ambiguous/unmatched/current two-to-two pointer-aligned cases distinguished; repeated keys and descending-date evidence recorded without arbitrary one-to-many selection.
- [x] Existing 185 synthetic tests pass; no new implementation/test files.
- [x] Discovery stops; CEO review required. No follow-on business task.

## completion
- Read and identity proof achieved for both sources, subject to the explicit snapshot and unresolved-contract limits in the report. This is not CEO PASS or production-processing approval.
- Changed: two sanitized Markdown files only. Product code and production state unchanged.
- Checks: 185 PASS; final diff/sensitivity review and publication receipt in Git/chat. Initial timezone collection failure resolved by reusing bundled tzdata, no dependency installation.
- Limitations: 2026 date provenance, stable external ID and pointer/sort lifecycle, field conflicts, and unmatched local ledger/Research remain documented UNKNOWN. Current two-to-two order/pointer alignment is not a permanent unique business key.
- Retain this single V1.5 managed worktree for CEO review. No handoff created. Retire owned ignored helpers and synthetic test artifacts only; preserve all other worktrees/runtime/CDP/browser/Profile.


## CEO independent discovery review — 2026-10-25

**DISCOVERY_REVIEW_PASS (scope-only) / TP_AUTOMATION_HOLD / LIVE_DELIVERY_NOT_AUTHORIZED.**

Reviewed exact commit `4c349ba02fad986c6ff905b7e3f6f8bdcd1f220e`,
the entire sanitized `V15_RPF_BRIEF_DISCOVERY.md` and this Task Packet,
against existing V1.4 GitHub source
(`src/launcher/google_web.py`, `src/sheets/google_reader.py`,
`src/sheets/pending.py`, `src/workflow/store.py`,
`src/research/excel_output.py`). Commit touches exactly two new
Markdown files, **no production source, test, Google Sheet, or DB files**.
The report's observed production data and live safety assertions are
executor-reported evidence, not independently reproduced by this
reviewer, who did not access Chrome/CDP, business Sheets, local DB
or source worktrees. Executor's 185 offline PASS was likewise not
independently executed.

**Accepted discovery facts/evidence:** true tab title is `RFQ_BRIEF`
(the report records Owner confirmation of title correction); complete
17-column A:Q header and 85 nonempty rows (41 `2026`, 44 `SHAHAB`).
Four nonempty `target_price` texts are 3 USD + 1 RMB with no inferred
sheet numeric/FX contract. The report demonstrates at least one
unique real source, ledger inquiry-id and Research cross-reference
for each original worksheet. `rfq_line_id` is currently present and
distinct across 85 rows but has **no demonstrated shared stable ID
contract** with the original sheets. The source code corroborates
the independent-risk constraint that a persisted `inquiry_id` is
derived from a source worksheet's initial physical position; a current
brief row number or reordered source row must not synthesize it.

**Crucial implementation gate:** A unique source-row correspondence
is not equivalent to a unique *existing local inquiry/Research*:
of the report's 76 uniquely matched source rows, only 18 have
ledger+Research; 4 have ledger but no Research; 54 lack a matching
existing local ledger under the inspected method. There are additionally
duplicate/ambiguous/conflicting source matches. V1.5 must not silently
skip all such rows and claim support for all brief inquiries, nor
create a fake `inquiry_id` or dispatch an email for an ambiguous order.
The report does **not** provide a per-TP-row matrix proving whether
each of the four currently populated H cells individually has
unique, stable 2026/SHAHAB linkage and a usable inquiry/Research.
This is required before any actual TP processing or email.

**Required next nonproduction design/verification gate, not
rejection of the completed discovery task:**
1. Produce a fully sanitized **four-target-row** mapping matrix:
   brief row alias, original `sheet`, exact target price currency/
   parseability, source match cardinality, whether `sheet_row` points
   to the same corroborated source, field/date conflicts, existing
   `inquiry_id` availability, Research availability, and an
   explicit READY / AMBIGUOUS / UNMATCHED / LOCAL_UNRESOLVED verdict.
   No actual prices, MPNs, customer values, raw TSV, spreadsheet IDs
   or sensitive identifying text in Git.
2. Establish how 2026 `rfq_date` was derived; whether `rfq_line_id`
   and `sheet_row` survive sorting/insertion/deletion/rebuilding;
   treat current reversed two-to-two correspondence only as
   `CURRENT_ORDER_POINTER_ALIGNED`, **not** an automatic durable key.
   If unavailable, use fail-closed uniqueness + current source
   revalidation (and explicit unresolved handling), not guessed pairing.
3. Specify the safe workflow for TP rows **without** a V1.4
   ledger/Research entry: independently authorized fresh TP research
   and durable TP-specific idempotency, or a clear per-row hold with
   operator visibility. Do not automatically create or reuse a
   worksheet-position-derived V1.4 `inquiry_id`.
4. Any later transport support for `RFQ_BRIEF` requires a scoped,
   exact-sheet, header/gid/range-only **read** extension, reusing
   protected native TSV and existing CDP; never broaden source
   schema/write allowlists indiscriminately.
5. Future owner-specific decisions (target-price trigger, 1–12
   month TP-only windows, lowest/second-lowest/date fidelity, exchange
   rate, notifications/idempotent retries, UI **重跑 TP 价格**) belong
   to a separate V1.5 product/design approval, **not** this discovery
   authorization.

The executor reports preserving user pages/TSV hygiene and readonly DB/
Excel state; no independent claim of live proof is made here. All
unresolved `UNKNOWN` items remain explicit. **Disposition:** the
bounded `DISCOVERY_ONLY` objective is complete and accepted. Leave
TP polling, email, UI action, production writes, packaging and
deployment **on hold** until Owner approves a separately reviewed
implementation design. No work beyond review document was performed.
