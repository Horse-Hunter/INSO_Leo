# Task: RESEARCH-005 — Market Completion

status: complete
owner: Research Codex
created: 2026-09-22
updated: 2026-09-22

## problem

Research has contracts, idempotent Excel, IC.net Brand/stock, and Findchips pricing, but no complete single-call V1 path. HQEW, LCSC, Bom.Ai, live FX, four-source aggregation, final Excel output, and the execution service remain.

## goal

Provide one Workflow-callable Research capability: `ResearchInput -> IC.net -> four price sources -> RMB normalization -> aggregation -> estimated total -> idempotent 调研价格.xlsx -> ResearchResult`.

## current_facts

- Baseline: `origin/main` `acc861c9d4ad92fc298a0c5684859f20cc28aec2`; RESEARCH-001 through 004 are complete.
- Runtime: Windows, Python 3.12.10, pytest, ruff, openpyxl, and installed browser tooling.
- IC.net has a verified ordinary-Chrome localhost-CDP read path and contributes Brand/market stock only.
- Findchips has bounded HTTP acquisition and injected `UsdRmbProvider`.
- Shared strict-MPN/source/evidence contracts must be reused.
- Owner selected the official ECB daily reference-rate API with an EUR bridge;
  no key and no fallback.
- Canonical `main` documents a Credential Provider, but its implementation is absent from `src/core/`; uncommitted provider files in another dirty worktree are not canonical and will not be copied.
- Bom.Ai prefers the lowest valid price in 7 days, else the lowest within one month; strict match without a valid recent price is `NO_VALID_PRICE`.
- Work Queue / coordination / lease: N/A in canonical Research runtime.
- Owner selected calendar-month Bom.Ai expiry with month-end clamping.
- Final display precision remains `UNKNOWN`; implementation preserves exact
  decimal text and performs no hidden rounding.

## scope

- HQEW and LCSC price adapters.
- Bom.Ai authenticated read adapter with injected credential/browser boundaries.
- Live USD/RMB diagnosis and implementation after Owner selection if no approved capability exists.
- Four-source aggregation, 20% rule, estimated total, status/no-match aggregation.
- Final Excel columns/idempotent update and a public Research execution service.
- Deterministic tests, bounded live read smokes, Research docs, and this packet.

## non_scope

- Sheets, Workflow scheduler/retry/SQLite, INSO, Quotation, messaging, payment, purchasing, RFQ, or website writes.
- Redis/Celery/Kafka/Docker, unrelated refactoring, CAPTCHA/OTP/QR/device bypass, stealth/fingerprint spoofing, hidden-endpoint reverse engineering, hardcoded secrets, committed sessions, fuzzy MPN, guessed price/currency, or invented rounding.

## requirements

### Acquisition and source rules

- Diagnose normal HQEW/LCSC/Bom.Ai result shapes before parsers. Keep bounded read-only acquisition separate from pure parsing and use finite timeouts.
- Reuse `is_strict_mpn_match`; fail closed on uncertain identity, price, currency, authentication, FX, or Excel consistency.
- HQEW: use only a reliably identified strict-MPN RMB market-reference/cloud-price field; ask Owner if materially different price meanings remain ambiguous.
- LCSC: select the displayed customer-quantity tier with `Decimal`; retain valid displayed preorder/out-of-stock prices; do not cross variants.
- Bom.Ai: obtain credentials only from an injected project capability; never log/persist them. Interactive verification is an Owner action. No match -> `NO_STRICT_MPN_MATCH`; strict match/no valid price -> `NO_VALID_PRICE`; technical/auth failure -> `SOURCE_UNAVAILABLE`. Do not silently choose month semantics.

### FX

- Check approved repository/OS capabilities first. If none exists, present 1–3 candidates with key/cost/stability/cadence and recommendation for Owner selection.
- Preserve `1 USD = rate RMB/CNY`, positive finite `Decimal`, provenance and capture time. No float, fabricated rate, fallback, rounding, or quantization.

### Aggregation and status

- Sort normalized RMB candidates. Choose lowest and optional second-lowest.
- Apply `lowest <= second_lowest * Decimal("0.80")`. If true, Excel shows lowest then newline plus `次低价格(RMB)-网站名称`; otherwise only lowest. One candidate is valid.
- `estimated_total = lowest * quantity` with exact `Decimal`.
- `SUCCESS`: required actions succeed, at least one price, Excel persists.
- `PARTIAL_SUCCESS`: source technical failure(s), at least one price, Excel persists.
- `MANUAL_REVIEW_REQUIRED/NO_MATCHING_PRODUCT`: all four price sources successfully report no strict match.
- Technical failure or strict match/no-valid-price cannot become no-match.
- `RETRYABLE_FAILURE`: technical/FX failure leaves no acceptable result, or Excel fails.
- Preserve collected evidence/candidates and resolved Brand across partial failures; remarks stay concise.

### Excel and service

- Visible columns in order: `型号`, `品牌`, `数量`, `重要等级`, `货量标识`, `预计订单总价`, `市场最低参考价`, `备注`; hidden `_inquiry_id`.
- Exact-`inquiry_id` retry/recovery updates one row and never duplicates it. Market reference supports newline.
- Excel failure is `RETRYABLE_FAILURE`, never false success.
- Public Research service owns IC.net, four price sources, FX, aggregation, Excel, and `ResearchResult`, but not Sheets, scheduler, Workflow state, or retry timing.
- Research may depend on `core` public capabilities and approved web/Excel libraries, never `sheets`, `workflow`, `inso`, or `quotation`.

## acceptance

- [x] Deterministic integration covers IC.net + four price sources + FX + aggregation + Excel and returns a complete result/row.
- [x] HQEW strict-MPN fixture produces a valid RMB candidate; the bounded live
  read reached an interactive safety challenge and failed closed without bypass.
- [x] LCSC quantity-tier and preorder/out-of-stock behavior pass.
- [x] Bom.Ai auth boundary, secret safety, calendar-month selection, and no-valid-price semantics pass.
- [x] Lowest/second-lowest, 20%, single-price, partial failure, and exact no-match semantics pass.
- [x] Final Excel schema, hidden key, newline display, and idempotent retry pass.
- [x] Source/FX/Excel failures fail closed without silent fallback.
- [x] No secrets, website writes, fuzzy matching, or forbidden imports.
- [x] All Research tests and ruff pass; bounded ECB, LCSC, HQEW, and Bom.Ai live
  reads were run. Volatile observations were not copied into fixtures.
- [x] Final diff is scoped; packet is complete; one unmerged PR is created.

## verification

- Focused adapter/FX/aggregation/Excel/service tests.
- `py -3.12 -m pytest tests/research`.
- `py -3.12 -m ruff check` on changed Research Python/tests.
- `git diff --check origin/main...HEAD`; inspect full diff, boundaries, secrets, float math, and external writes.
- Bounded live read smokes; volatile observations never become fixture constants.

## decisions and live evidence

- ECB API query: daily USD/EUR and CNY/EUR, last observation only, CSV. On
  2026-09-22 it returned a same-date 2026-09-21 quote and the provider derived a
  positive Decimal USD/CNY rate. The numeric observation is volatile and is not
  a fixture.
- LCSC official product page smoke for `MMBT2222ALT1G`, quantity 50, selected
  the displayed 50-unit USD tier and normalized it with the live ECB quote.
- HQEW normal public cloud-price URL returned
  `INTERACTIVE_CHALLENGE_REQUIRED`; no CAPTCHA/safety mechanism was bypassed.
- Owner selected the temporary non-blocking policy on 2026-09-22: an HQEW
  challenge does not pause the workflow when another valid price exists; the
  available result is persisted as `PARTIAL_SUCCESS`.
- Local uncommitted CredentialVault code was used only at runtime, as explicitly
  approved by the Owner. No provider file or secret was copied. The configured
  `bom.ai` entry authenticated a disposable browser context; the repository
  parser read three strict-page quote records and selected the lowest record in
  the 7-day window. The volatile price and credential material are not fixtures.
- The desktop Computer Use helper failed initialization twice. Per its recovery
  rule, testing continued through a pre-installed Playwright browser in a
  disposable context; no session was persisted.

## completion

- status: complete
- pull request: https://github.com/Horse-Hunter/INSO_Leo/pull/6 (open,
  unmerged)
- changed: HQEW, LCSC, Bom.Ai, ECB FX, aggregation, Research service, final Excel
  schema/idempotency, tests, and durable Research documentation.
- verified: 126 tests passed; Research ruff passed; compileall and diff checks
  passed before final documentation update; live reads recorded above.
- limitations: HQEW currently requires interactive human completion of its
  safety challenge for live data. Bom.Ai production login remains an injected
  browser boundary because the canonical branch does not yet contain the
  Credential Provider implementation. Display precision and concurrent workbook
  locking remain `UNKNOWN`; exact decimal values are preserved.
