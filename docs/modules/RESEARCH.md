# Research Module

## Public contract

The cross-module entry is `ResearchService.execute(ResearchInput) -> ResearchResult`.

`ResearchInput`:

- `inquiry_id`
- `mpn`
- optional `brand`
- `quantity`
- `importance_raw`

`ResearchResult`:

- `inquiry_id`
- `status`: `SUCCESS | PARTIAL_SUCCESS | MANUAL_REVIEW_REQUIRED | RETRYABLE_FAILURE`
- optional `resolved_brand`
- optional `reason_code`
- optional `remarks`

V1 has no `output_ref`. Research returns `resolved_brand` to Workflow. `importance_raw` is used only for Excel display: exact `A` or `B` → `重要`; otherwise → `普通`. It must not affect sources, order, price logic, evidence, status, retry, or matching.

## Sources and evidence

Confirmed read-only sources are IC.net, Findchips, HQEW, LCSC, and Bom.Ai. Findchips, HQEW, LCSC, and Bom.Ai are the four price sources; IC.net supplies Brand resolution and market-stock display only.

Strict MPN match trims outer whitespace and compares case-insensitively. It never changes internal whitespace, punctuation, prefix/suffix, package code, or guesses a variant.

Each price source reports `SUCCESS`, `NO_STRICT_MPN_MATCH`, `NO_VALID_PRICE`, or `SOURCE_UNAVAILABLE` before aggregation. Technical failure remains distinct from business absence. Evidence records source, query, optional matched MPN/URL, outcome, capture time, and immutable typed observations; it never contains secrets, cookies, or tokens. A price candidate carries matched MPN, decimal-safe raw price/currency, normalized RMB price, source, URL, and capture time.

## Durable source rules

### IC.net

- Every row used for Brand or stock must strictly match MPN.
- Preserve a nonblank input Brand. Otherwise inspect at most the first 20 first-page rows and choose displayed manufacturer by frequency, then English preference, then shorter English name; an unresolved tie stays unresolved. Do not translate, transliterate, alias, or invent a Brand.
- Sum first-page strict-match stock carrying SSCP or ICCP; count a row carrying both once. Brand does not filter stock. Total `<= 3 × customer quantity` displays `货少`; greater displays `货多`. A required but unparseable quantity is `SOURCE_UNAVAILABLE`, not zero.
- Authentication uses an authorized Credential Provider login for a bounded read-only session.

### Price sources

- **Findchips:** require strict MPN and positive stock. Select the greatest displayed quantity tier not above customer quantity; never substitute a higher tier or range summary. MOQ is not exclusionary or persisted. Only USD tiers qualify; select the lowest eligible USD unit price.
- **HQEW:** use the first cloud-price page in an Owner-authenticated ordinary Chrome context over loopback CDP; do not export/persist cookies or use anonymous HTTP as the production path. Never bypass a challenge. Under the current temporary policy, a challenge is non-blocking when another source provides a valid candidate, producing persisted `PARTIAL_SUCCESS`.
- **LCSC:** use only the primary product on the official product page and the greatest displayed tier not above quantity. A displayed preorder or zero-stock price remains eligible. Explicit RMB/CNY needs no FX; USD uses the approved FX boundary.
- **Bom.Ai:** use injected Credential Provider/login capabilities. A price is valid for one calendar month using the same prior-month wall-clock time clamped to month end. Prefer the lowest valid price from the most recent seven days; otherwise the lowest valid one-month price. Older prices are not candidates.

USD/RMB uses the ECB daily reference API: same-date USD/EUR and CNY/EUR observations derive `CNY per USD = CNY per EUR / USD per EUR`. Values and arithmetic use positive `Decimal`; missing, duplicate, mismatched, non-positive, or non-finite observations fail closed. There is no fallback rate or hidden rounding.

## Aggregation and status

- Sort candidates by normalized RMB unit price; the lowest is the market reference.
- If a second candidate exists and `lowest <= second × 0.80`, display the lowest plus a newline containing second-lowest price and source; otherwise display only the lowest.
- Estimated total is exact lowest unit price × customer quantity.
- At least one candidate plus any unavailable price source yields `PARTIAL_SUCCESS`; candidates with no unavailable price source yield `SUCCESS`.
- `NO_MATCHING_PRODUCT` is `MANUAL_REVIEW_REQUIRED` only when all four price-source queries succeed and all report no strict MPN match. A technical failure is not “no match”; a strict Bom.Ai match is not “no match” even when price is expired, absent, or unusable.
- No usable candidate outside the all-no-match case is `RETRYABLE_FAILURE`.

## Excel output

Project-local `调研价格.xlsx` is the official Research V1 persistence. Visible columns are `型号`, `品牌`, `数量`, `重要等级`, `货量标识`, `预计订单总价`, `市场最低参考价`, `备注`; hidden `_inquiry_id` is the idempotency key.

Retry/crash recovery must not duplicate a normal inquiry row. `SUCCESS` and `PARTIAL_SUCCESS` may return only after required output succeeds; `PARTIAL_SUCCESS` requires a valid price. Excel load/schema/save failure fails closed as `RETRYABLE_FAILURE`. An ambiguous or unrecognized schema is not guessed.

## Boundary and UNKNOWN

Research does not access Google Sheets, schedule global work, perform INSO actions, or calculate quotations. External access is read-only and limited to confirmed sources; local Excel is its only V1 write. Dependency direction is owned by `MODULE_INDEX.md`; safety by `BOUNDARIES.md`.

Still `UNKNOWN`: broader reason-code catalog, additional input validation/status-field rules, Excel display precision/retention/concurrent-locking policy, and future INSO importance behavior. Selectors, XPath, session mechanics, temporary workarounds, and Task history are not durable contract text.
