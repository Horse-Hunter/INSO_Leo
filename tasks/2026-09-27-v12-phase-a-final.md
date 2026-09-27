# Task: V1.2 Phase A final contract discovery

status: blocked
owner: Main Programmer
created: 2026-09-27
updated: 2026-09-27

## problem

Production duplicate query settlement is implemented. Creator, INSO quote
semantics, AI recognition/read-back, and blank-draft product writer still need
Owner-authenticated Chrome evidence. The Codex execution context cannot safely
inspect the Owner's authenticated browser.

## goal

Finish statically provable work and provide one bounded, read-only Owner-session
runner for remaining browser observations. Keep Production Write Gate CLOSED.

## implementation

- Reuse current Chrome bootstrap and `InsoSessionLease`; validate configured
  executable/profile/endpoint before attach and require one verified context.
  The lease uses the unique authenticated shell page directly; it creates no
  child page.
- Use a same-document POST through the authenticated shell with the exact
  `List_Detail` contract; record schema and approved labels only. Do not touch
  the hidden `#nolike` control.
- Inspect at most one unambiguous detail and a blank temporary form/AI panel.
- Do not run AI recognition, import a row, fill product fields, or click Save or
  Send controls.
- Write a sanitized JSON report only under ignored runtime evidence.
- Provide `runtime/run_v12_phase_a_readonly.cmd` as a local ignored double-click
  entry point; do not add a browser profile or change configuration.

## acceptance

- [x] Existing query settlement implementation is reused.
- [x] Creator/quote are confirmed only from matching schema/grid/detail facts.
- [x] The report stores no row values or raw exceptions.
- [x] The runner never clicks `#btnSave`, `#btnSave2`, or `#bcSend`.
- [x] AI recognition/import are not executed by the runner.
- [x] The local one-click command is Git-ignored.
- [x] Owner-session runner executed; report records current read-only result.
- [x] Lease reuses the unique verified authenticated shell; no child page.
- [x] Same-document exact request path avoids the hidden `#nolike` control.
- [ ] Exact query response is a verifiable structured result.
- [ ] Creator and quote/currency semantics are confirmed from response/detail.
- [ ] AI frame/read-back and blank-form product-field selectors are confirmed.

## verification

- Run Ruff and deterministic Launcher, INSO, Workflow, and notification tests.
- Run `git diff --check` and inspect the scoped diff.
- Do not execute the Owner-session runner from the Codex sandbox.

## Original packet completion (superseded)

- status: partial_live_acceptance
- changed: bounded read-only runner, deterministic report/classifier tests,
  direct exact-query adapter, shell-page lease, current task and INSO module docs
- remaining: structured exact-query response, creator/quote semantics, and
  AI/parent-field read-back. No Save or other business write is involved or
  authorized.

## Owner-session closeout — 2026-09-27

This closeout supersedes the earlier restrictions on reusing the authenticated
shell and on one synthetic AI recognition.

- The current authenticated shell's `1.业务询价` frame was verified by host,
  path, and unique `#DetailFieldValue`, `#select_btns`, and `#_id_dg` controls;
  it contained live rows. The accepted `query_exact_response(part_no)` adapter
  was called three times using existing row values held only in memory. Each
  attempt ended `QUERY_SETTLEMENT_UNCONFIRMED`; the final attempt matched the
  native request shape. The three-attempt limit is exhausted.
- The response schema could not yield a non-empty exact response. Therefore
  creator remains UNKNOWN, and quote/currency cannot be live-confirmed against
  an exact response/cache row. The user-confirmed schema/grid mapping is
  `OfferPrice` → `报价` and `OfferCurrencyID` → `报价币种`.
- The code classifier now applies that mapping without requiring same-named
  detail fields. For one unique response row with the selected BillID, it
  checks that `OfferPrice` Decimal-parses and `OfferCurrencyID` is nonempty.
  Live `CONFIRMED` still requires the requested non-empty exact response and
  same-BillID grid/cache comparison.
- On a new blank temporary inquiry, the AI panel and `textarea#paste-area` /
  `button#ai-recognize` were confirmed. One request containing only the
  authorized synthetic text returned “未能识别出有效数据”; no preview row was
  produced, so import and parent read-back did not run. Save/Send controls were
  not activated. The AI dialog is still open because the UI bridge timed out
  after dismissing the recognition alert; the parent form remained blank.
- Save, Save-and-Send, Send, SMTP, Sheets write, and edits to existing business
  records: NO. Production Write Gate: CLOSED.

## completion

- status: blocked
- changed: quote/currency schema/grid classifier and focused launcher tests
- verified: authenticated list/frame identity; three bounded query attempts;
  one synthetic AI recognition failure; `pytest tests/launcher/test_v12_phase_a_readonly.py -q`;
  `ruff check` for touched Python files; `git diff --check`
- limitations: non-empty exact response, live quote/cache comparison, creator
  schema conclusion, AI preview success, and parent writer/read-back remain
  unresolved. No further query or AI recognition attempt is authorized by this
  task's attempt limits.
