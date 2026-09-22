# Research Module

## Purpose and contract

Research accepts a `ResearchInput`, performs read-only web market research, produces the required project-local Excel output, and returns a `ResearchResult`. It owns market-source interaction, price-evidence collection, source metadata, evidence provenance, and its Excel output behavior.

### ResearchInput V1

- `inquiry_id`
- `mpn`
- optional `brand`
- `quantity`
- `importance_raw`

`importance_raw` originates from Google Sheet column C. Sheets reads the raw value, Workflow forwards it unchanged, and Research uses it only for display in `调研价格.xlsx`: exact `A` or `B` displays as `重要`; every other value displays as `普通`.

`importance_raw` must not affect website selection, research order, pricing algorithms, prices, MPN handling, evidence, Research status, retry, `NO_MATCHING_PRODUCT`, or any other Research behavior. Future INSO order-importance behavior belongs to a future version and must not implicitly reuse this display rule.

### ResearchResult V1

- `inquiry_id`
- `status`
- optional `resolved_brand`
- optional `reason_code`
- optional `remarks`

V1 `ResearchResult` does not contain `output_ref`. Allowed `status` values are:

- `SUCCESS`
- `PARTIAL_SUCCESS`
- `MANUAL_REVIEW_REQUIRED`
- `RETRYABLE_FAILURE`

Research returns `resolved_brand` to Workflow when it resolves a Brand value. Detailed price-item schema, validation rules, and reason-code catalog beyond confirmed cases remain `UNKNOWN`.

## Confirmed sources

- IC.net
- Findchips
- 华强电子网 (HQEW)
- LCSC / 立创商城
- Bom.Ai

Bom.Ai requires login. Research may request an authorized login using a stable `site_id` through the project Credential Provider. Research must not know or reproduce DPAPI, vault-file, or PowerShell storage details, and it must never log or persist a live secret.

Bom.Ai price records are valid for one calendar month. The cutoff is the same
wall-clock time in the previous month, clamped to that month's final day (for
example, March 31 maps to February 28 or 29). If one or more valid prices exist
within the most recent 7 days, Bom.Ai contributes the lowest valid 7-day price.
If no valid 7-day price exists but one or more valid prices exist within the
calendar-month window, it contributes the lowest valid one-month price. Older
prices are not valid Bom.Ai price candidates.

### Source and evidence foundation

Research owns one website-agnostic source contract for the five confirmed sources. The canonical price-source collection contains Findchips, HQEW, LCSC, and Bom.Ai only; IC.net does not produce a final V1 market-price candidate.

Each source reports one of four pre-aggregation outcomes: successful processing, no strict MPN match, strict MPN match with no valid source price, or source unavailability/technical failure. These outcomes are not themselves final `ResearchStatus` values. A technical failure must remain distinguishable from business absence.

Strict MPN matching trims leading and trailing whitespace and compares case-insensitively. It does not remove or alter internal whitespace, punctuation, prefixes, suffixes, package codes, or any other characters, and it does not guess variants.

A selected price candidate records the source, matched MPN, decimal-safe raw price and currency, decimal-safe normalized RMB price, capture timestamp, and optional source URL. It represents a result that has already passed a future adapter's source-specific validity rules; it does not define those rules or perform FX conversion.

Source evidence records the source, query and optional matched MPN, outcome, capture timestamp, optional source URL, and immutable structured key/value observations. Evidence must not contain secrets, credentials, cookies, or token data. Screenshot, raw-HTML, and persistence requirements remain outside this contract.

## Excel output and result consistency

The project-local `调研价格.xlsx` is the official persisted output of Research V1. It uses a hidden `_inquiry_id` field as the technical idempotency key.

- Retry or crash recovery must not create duplicate normal records for the same `inquiry_id`.
- Research may return `SUCCESS` only after the required Excel output succeeds.
- Research may return `PARTIAL_SUCCESS` only when at least one valid price exists and the required Excel output succeeds.
- An Excel write failure returns `RETRYABLE_FAILURE`; it must not be reported as a successful result.
- The visible `重要等级` and `备注` columns are confirmed. Other business-column schema, workbook update/locking mechanics, and detailed idempotency implementation remain `UNKNOWN`.

Local Excel output remains part of Research V1. A separate Excel or storage module should be considered only after multiple modules demonstrate a stable shared requirement.

## NO_MATCHING_PRODUCT

Return `MANUAL_REVIEW_REQUIRED` with `reason_code = NO_MATCHING_PRODUCT` only when all four price sources—Findchips, HQEW, LCSC, and Bom.Ai—were queried successfully and none returned a strict MPN match.

- A technical failure must not be counted as “no match.”
- If Bom.Ai finds a strict MPN match, the result must not be classified as `NO_MATCHING_PRODUCT`, even when the price is outside the one-calendar-month validity window, unavailable, or absent.
- Product existence and price validity are separate decisions.
- User-facing remarks wording and the broader reason-code catalog remain `UNKNOWN`.

## IC.net Brand and market stock

IC.net contributes Brand resolution and the V1 market-stock display only; it never produces a `PriceCandidate`.

- Every row used for Brand or stock must satisfy the shared strict-MPN rule.
- A nonblank input Brand is preserved. When input Brand is blank, Research inspects at most the first 20 first-page result rows, counts displayed manufacturer candidates from strict-MPN rows, and selects by highest frequency, then English preference, then shorter English name. A tie that remains after those rules stays unresolved.
- Pure English and pure Chinese manufacturer labels are kept as displayed. A clearly separable English component of a bilingual displayed label is used without translation, transliteration, aliasing, or invention.
- Market stock uses all first-page strict-MPN rows carrying SSCP or ICCP. A row carrying both certifications is counted once, and Brand does not filter the stock sum.
- Certified stock at or below three times customer quantity displays `货少`; a greater total displays `货多`.
- An unparseable quantity on a row that must contribute to certified stock is a source-unavailable technical failure, not zero stock or no match.
- When authentication is required, IC.net credentials are obtained at runtime through the project Credential Provider and remain in memory for the bounded read-only session. Login does not authorize any write action or challenge bypass.

## Price acquisition and USD/RMB boundary

Findchips is a V1 price source and may produce one `PriceCandidate`.

- Every price-eligible offer must pass the shared strict-MPN rule and report positive stock. Stock does not need to meet customer quantity, and concrete stock quantities are not persisted in Evidence or public results.
- MOQ is not an exclusion criterion and is not persisted.
- For each eligible offer, Research selects the greatest displayed quantity break at or below customer quantity. A higher break is never substituted when no applicable break exists, and a summary price-range minimum is not a quantity tier.
- Only USD tiers are eligible in this adapter. Non-USD tiers are not converted or inferred.
- Findchips contributes the lowest applicable USD unit price across eligible offers.
- Research owns an injected USD/RMB quote boundary oriented as `1 USD = rate RMB/CNY`. The rate and all price math use positive `Decimal` values without hidden rounding or quantization.
- HQEW reads the first cloud-price result page through an Owner-authenticated
  ordinary Chrome context connected only over loopback CDP. The client reuses
  the browser context without reading, exporting, or persisting its cookies;
  anonymous direct HTTP is not the production acquisition path. A safety
  challenge encountered on this authenticated path remains a technical source
  failure and is not bypassed. Under the temporary policy, that failure is
  non-blocking when another source returns a valid candidate: Research persists
  the available result and returns `PARTIAL_SUCCESS`.
- LCSC reads only the primary product represented by the official product page.
  It selects the greatest displayed quantity break at or below the customer
  quantity. A valid displayed preorder or zero-stock price remains eligible.
  USD prices use the approved FX boundary; explicit RMB/CNY prices do not.
- Bom.Ai obtains credentials and an authenticated page through separate injected
  capabilities. Server-rendered quote records carry absolute quote times and
  RMB prices. Secrets, cookies, and raw authenticated pages are not evidence and
  are never persisted by Research.
- The live FX provider is the ECB daily reference-rate API. It requests USD/EUR
  and CNY/EUR observations for the same date and derives
  `CNY per USD = CNY per EUR / USD per EUR` with `Decimal`. Missing,
  non-positive, non-finite, duplicate, or date-mismatched observations fail
  closed. There is no fallback rate and no hidden rounding or quantization.
- Public Findchips acquisition is bounded, read-only ordinary HTTP without login, crawling, RFQ, alert, or purchase actions.

## Aggregation and final output

Research sorts the four price-source candidates by normalized RMB unit price.
The lowest candidate is the market reference. When a second candidate exists
and `lowest <= second * Decimal("0.80")`, the Excel market-reference cell
contains the lowest value followed by a newline and
`second-lowest RMB price-source name`. Otherwise it contains only the lowest
value. Estimated total is the exact lowest normalized unit price multiplied by
customer quantity.

The visible columns of `调研价格.xlsx`, in order, are `型号`, `品牌`,
`数量`, `重要等级`, `货量标识`, `预计订单总价`,
`市场最低参考价`, and `备注`. The hidden `_inquiry_id` column is the
idempotency key. Decimal values are persisted as exact decimal text; display
precision remains a presentation concern and is not rounded by Research.

The known legacy schema `_inquiry_id | 重要等级 | 备注` is migrated
deterministically to the canonical column order without duplicating rows or
discarding those values. A workbook with an unrecognized or ambiguous schema
fails closed. A complete `ResearchService` execution replaces the full business
snapshot for its inquiry, including clearing stale values when the new value is
explicitly empty. Ordinary workbook load, parse, migration, and save exceptions
are converted to Research Excel errors and therefore to
`RETRYABLE_FAILURE`; `KeyboardInterrupt` and `SystemExit` are not swallowed.

`ResearchService` is the public single-call owner of IC.net, the canonical
four price sources, aggregation, Excel persistence, and the final
`ResearchResult`. It preserves per-source evidence in its detailed execution
result and does not own Workflow scheduling or retry timing.
The earlier `finalize_research_result` helper remains internal for compatibility
but is not part of the package-level public API.

## Boundaries

- Allowed dependency: `core`, including the Credential Provider capability, plus explicitly approved web and local Excel adapters.
- Forbidden dependencies: `sheets`, `workflow`, `inso`, and `quotation`.
- Research does not access Google Sheets, orchestrate the global workflow, perform INSO actions, or calculate quotations.
- Access is read-only and limited to the confirmed sources. It does not authorize arbitrary sites, customer messaging, external writes other than the required local Excel output, or production-data modification.
- Selectors, XPath, session mechanics, and other volatile website details belong in future implementation tasks, not this durable document.
