# Task: INSO monthly tolerance preference and nonzero price display

status: REVIEW_REQUIRED
owner: Codex
created: 2026-10-23

## authorization / baseline / scope
Owner requests two small Research adjustments based on9e48db95b516fce010138006d548210ec34689c4.
Latest remote5594feb78d1f955412c15519779856b0254994a9 adds CEO's independent
review of that commit: one precision-display defect, otherwise scoped behavior
accepted at code level only. Preserve that review in the parent history.
Reuse current six-source aggregation, first-valid1–6 month candidates, Decimal
FX/raw prices, same Excel fields/migration. Only Research, relevant offline tests
and canonical documents/task record. No procurement/Google/order-state/adapter
filtering change, dependency/new module/schema/column, production/customer/CDP/
credential/network business operations, package or running-install replacement.
Push original codex/v1-4-order-mail-inspection, REVIEW_REQUIRED for CEO review.

## policy / implementation limits
Compute actual minimum positive RMB price from the unchanged eligible source
pool. INSO's first-valid-window month1,2,3,4,5,6 maps to exact Decimal tolerance
12%,10%,8%,6%,4%,2%. Prefer valid INSO if its unrounded price <= actual minimum
times(1+tolerance), inclusive; otherwise actual minimum. No average, no candidate
mutation/reordering, no extra source query. Existing normal/out-of-stock fallback
and technical-failure status policy remain unchanged.
Existing market-reference column contains the final selected single unit price;
estimated-total column uses that exact Decimal price times original quantity.
The old20% second-price multiline display is superseded in this field by Owner's
explicit single-final-price instruction; no explanation/decision columns added.
Keep actual minimum/second minimum/candidates observable in the existing result
contract, with second-price display disabled. Six raw source cells unchanged
except the separately authorized precision correction shared by all prices.
Preserve two-decimal formatting when nonzero; if a strictly positive value would
round to0, render its nonzero Decimal digits. Literal zero remains zero and cannot
become a valid price candidate. No rounding before selection or multiplication.

## verification / acceptance
Offline synthetic records: all six months just below/equal/just above tolerance;
no valid INSO, INSO already lowest/only price, unchanged original candidates and
actual minimum, partial technical failure and out-of-stock fallback; minuscule
prices and exact total, real IC.net capture→six-source service→synthetic Excel,
true-zero exclusion, old Excel migration and unchanged headers. Relevant Research
and caller regressions; Ruff/diff, preserve real Git HEAD/index/unrelated work.
Retire task-owned synthetic test roots; retain only compact ignored evidence.
Live site/history availability and production acceptance remain UNKNOWN.

## completion
Production changes are limited to src/research/aggregation.py and
src/research/source_contracts.py. Existing Excel formatting calls reuse the shared
precision repair; no Excel schema or migration code change. Actual minimum,
second minimum and raw sorted pool remain unchanged while chosen reference/total
use the inclusive INSO tolerance. Market reference now a single scalar string;
old extra second-price display disabled, as required by Owner's final-unit-price
output rule. No weighted average or mutation/rounding of candidates/calculations.

Before correction the new targeted suite reproduced31 failures/10 passes in0.93s
(tolerance choice and positive-sub-cent display paths). After correction the
Research suite423 passed in2.99s. Final combined offline suite1684 passed,1 skipped
in67.45s, including Research/INSO/Sheets/workflow/GUI and relevant backend/manual/
site-recovery/countdown/hold callers. Existing two old second-price-display tests
were updated to require the new single reference while retaining actual second
candidate and stock/status assertions. Ruff and git diff --check PASS.

Coverage: all six tolerances below/equal/above limit without rounding before
comparison; INSO lowest/only candidate and no valid INSO; partial failures and
unchanged out-of-stock fallback;0.001/0.00001/1E-30 and true-zero distinction;
exact selected-price multiplication (including0.00112×3=0.00336), actual IC.net
parser→six-source service→synthetic Excel with unchanged explicit17 headers,
single query, six raw source cells and existing old-workbook migration tests.

Source ready for CEO independent review. Preserve CEO review5594feb parent and
all existing history; publish only the two implementation files, two Research
test files, two canonical documents and this Task Packet. No production/customer
data/browser/credentials/business operations, dependency install, packaging,
deployment or production process start/stop performed. Existing installed V1.4
and unknown dirty work remain untouched; real local Git HEAD/index preserved.
Live website/date coverage/production acceptance remain UNKNOWN. Synthetic test
roots are retired in this task; compact ignored logs/manifests only are retained
at .tmp/research-inso-preference-20261023. Keep REVIEW_REQUIRED, not self-approved.
Retired all four owned test roots (77266009 bytes); no reparse point followed.
