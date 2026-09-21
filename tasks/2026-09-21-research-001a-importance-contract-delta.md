# Task: RESEARCH-001A — Importance Contract Delta Sync

status: complete
owner: Research Codex
created: 2026-09-21
updated: 2026-09-21

## problem

RESEARCH-001 was merged before the Architecture Gate approved `importance_raw` in `ResearchInput`. The current code and durable docs therefore still say Research does not receive this value. Bom.Ai's confirmed price-window rule also changed after the previous baseline.

## goal

Synchronize the approved `importance_raw` contract and Excel display behavior, plus the confirmed Bom.Ai price-window rule, without implementing any real website adapter or changing Research behavior beyond Excel presentation.

## current_facts

- `importance_raw` comes from Google Sheet column C.
- Sheets reads the raw value; Workflow only passes it through.
- Research must not use `importance_raw` to change website selection, pricing, status, retry, evidence, MPN handling, or any research decision.
- Research uses `importance_raw` only when writing `调研价格.xlsx`: exact raw `A` or `B` -> `重要`; all other values -> `普通`.
- This display rule is Research V1 Excel presentation only and is not an INSO importance rule.
- Bom.Ai strict MPN matching remains required.
- Bom.Ai price validity is one month.
- If valid Bom.Ai prices exist within the most recent 7 days, use the lowest of those prices.
- If no valid price exists within the most recent 7 days but valid prices exist within one month, use the lowest valid one-month price.
- Prices older than one month are not valid Bom.Ai candidates.
- RESEARCH-001 already owns Excel persistence and hidden `_inquiry_id` idempotency.

## scope

- Add `importance_raw` to the canonical ResearchInput contract.
- Add the confirmed Excel display transformation `A/B -> 重要; other -> 普通`.
- Ensure persisted Research rows can write/update the visible `重要等级` column.
- Thread `importance_raw` through the existing Research result-finalization persistence path only.
- Add/update scoped tests for the contract and Excel display rule.
- Update durable Research, Workflow, and Product Baseline documentation to reflect the approved pass-through contract.
- Document the confirmed Bom.Ai one-month / seven-day price-window rule.

## non_scope

- No IC.net, Findchips, HQEW, LCSC, or Bom.Ai adapter implementation.
- No HTTP, Playwright, login, Credential Provider call, or live network access.
- No change to Sheets code or Sheet write behavior.
- No Workflow implementation.
- No INSO or Quotation implementation.
- Do not use `importance_raw` for any research decision.
- Do not define or reuse this V1 display classification as an INSO/V2 business rule.
- No price aggregation, FX, evidence, MPN, stock, MOQ, or 20% rule implementation.
- No redesign of the Excel idempotency contract.

## requirements

- `ResearchInput` adds `importance_raw`.
- The implementation must preserve raw input semantics; no hidden business normalization may affect Research decisions.
- Excel output must expose a visible `重要等级` column.
- Display mapping is exactly:
  - raw `A` -> `重要`
  - raw `B` -> `重要`
  - every other value, including blank/None -> `普通`
- Existing hidden `_inquiry_id` idempotency remains unchanged.
- Existing `备注` behavior remains unchanged.
- Retry/upsert for the same inquiry updates the same row rather than appending a duplicate.
- Durable docs must state that Workflow passes `importance_raw` through without interpreting it.
- Durable docs must state that this classification is Excel presentation only.
- Durable Research docs must record the confirmed Bom.Ai price-window rule without adding adapter implementation detail.

## acceptance

- [x] Canonical ResearchInput contains `importance_raw`.
- [x] Existing ResearchResult contract is unchanged.
- [x] Excel contains visible `重要等级`.
- [x] `A` and `B` persist as `重要`; all other tested raw values persist as `普通`.
- [x] Re-upsert of the same `inquiry_id` updates the same row and does not duplicate it.
- [x] `importance_raw` does not alter Research status/result semantics.
- [x] Research, Workflow, and Product Baseline docs no longer state that `importance_raw` is excluded.
- [x] Bom.Ai one-month validity and seven-day-priority lowest-price rule are documented.
- [x] No real website adapter, credential use, network/browser access, or forbidden Research dependency is introduced.

## verification

- Run scoped Research tests with Python 3.12 / pytest when available.
- Run ruff on changed Python files when available.
- Review the complete task diff.
- Confirm no website/network/credential implementation was added.
- Confirm no imports from `sheets`, `workflow`, `inso`, or `quotation`.
- Record unavailable verification tools honestly.

## completion

- status: complete
- changed: added `importance_raw` to ResearchInput, persisted the V1 Excel-only `重要等级` display value, threaded it through result finalization, synchronized Research/Workflow/Product Baseline docs, and recorded the confirmed Bom.Ai one-month / seven-day price-window rule
- verified: scoped Research pytest reproduction passed 16 tests; reviewed the scoped branch diff and confirmed no real website adapter, credential use, network/browser access, or forbidden Research dependency was introduced
- limitations: ruff was not available in the validation environment; real Bom.Ai behavior and all source adapters remain for later tasks.
