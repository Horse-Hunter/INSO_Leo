# Task: RESEARCH-004 — Findchips Price Adapter & USD/RMB FX Boundary

status: complete
owner: Research Codex
created: 2026-09-22
updated: 2026-09-22

## problem

Research has a completed IC.net Brand/market-stock adapter and a generic source/evidence contract, but it does not yet have a real V1 price-source adapter. Findchips is the first price source to implement.

The Owner-provided Research workflow requires Findchips to contribute the lowest valid stocked market price for the queried MPN and to convert that USD reference into RMB. The repository already requires each selected price candidate to carry both raw price/currency and normalized RMB price, but no live FX source, cadence, or rounding rule has been selected yet.

## goal

Implement a bounded, read-only Findchips adapter that:

- searches one MPN;
- enforces the shared strict-MPN rule;
- accepts only offers with stock present and greater than zero;
- selects the price tier applicable to the customer quantity;
- selects the lowest valid USD unit price across eligible Findchips offers;
- produces Research-owned structured evidence;
- creates a valid Findchips `PriceCandidate` when supplied with a Research-internal USD/RMB rate provider;
- establishes the minimal Research-owned USD/RMB FX boundary without selecting or calling a live FX service.

This task must not implement another Research price site, final multi-source aggregation, or a live FX provider.

## current_facts

- Runtime: Python 3.12.
- Current main includes completed RESEARCH-001/001A/002/003 foundations.
- Shared source contracts exist in `src/research/source_contracts.py`.
- `ResearchSource.FINDCHIPS` is already a canonical price source.
- `PriceCandidate` requires:
  - source;
  - matched MPN;
  - Decimal raw price;
  - raw currency;
  - Decimal normalized RMB price;
  - capture timestamp;
  - optional source URL.
- Shared strict MPN rule: trim leading/trailing whitespace and compare case-insensitively; otherwise characters must match completely.
- Owner workflow rule: Findchips contributes the lowest price among records whose stock is not zero, and the USD price must be converted to RMB.
- Confirmed Research rule: Findchips stock only needs to exist/be nonzero; it does **not** need to be greater than or equal to customer Qty.
- Confirmed Research rule: concrete Findchips stock quantity is not persisted as business output/evidence.
- Confirmed Research rule: use the price tier applicable to the customer Qty.
- Confirmed Research rule: MOQ is not an exclusion criterion and does not need to be persisted.
- Operational interpretation for price tiers in this task:
  - ignore the separate MOQ field when deciding eligibility;
  - among displayed quantity-break tiers, the applicable tier is the greatest break quantity less than or equal to customer Qty;
  - if a row has no displayed tier at or below customer Qty, that row has no applicable price for this inquiry;
  - do not substitute a higher quantity tier merely because MOQ is ignored.
- Among eligible strict-MPN, positive-stock offers with an applicable USD tier, Findchips contributes the lowest applicable unit price.
- Findchips is currently publicly searchable without login at `https://www.findchips.com/search/<MPN>`.
- Public inspection on 2026-09-22 shows Findchips exposes:
  - part-number search;
  - stock;
  - quantity-break price tiers;
  - exact-match/in-stock filters;
  - a currency estimator including USD.
- Current public pages may contain different displayed currencies for different distributor/region rows. This task treats USD as the required Findchips raw currency. If a reliable site-level USD mode can be selected through the normal supported UI/request path, use it. Otherwise non-USD price tiers are not valid Findchips candidates in this task.
- No live USD/RMB FX source, refresh cadence, fallback policy, or final display rounding rule is confirmed in repository docs.
- Research may access only the confirmed V1 research sources. This task therefore must not call an arbitrary external FX website/service.
- `EvidenceValue` supports primitive values including `Decimal`, date, and datetime, but not nested lists/dicts.
- Research must not import `sheets`, `workflow`, `inso`, or `quotation`.

Sources: current `main` documentation/contracts, Owner-provided Research workflow, confirmed Research rules, and public Findchips inspection.

## scope

- Add a Findchips adapter under `src/research/`.
- Add pure immutable Findchips-specific row/tier contracts as needed.
- Add pure helpers for:
  - stock-presence parsing;
  - price-tier parsing;
  - applicable-tier selection for customer Qty;
  - lowest eligible Findchips USD price selection.
- Reuse the shared `is_strict_mpn_match` helper.
- Implement one bounded read-only Findchips search acquisition path.
- Prefer ordinary HTTP/server-rendered HTML first.
- Keep acquisition separate from pure parsing/business-rule functions.
- Add a minimal Research-owned FX boundary, preferably under `src/research/`, representing:
  - one USD -> RMB rate;
  - Decimal rate where `1 USD = rate RMB`;
  - capture timestamp;
  - non-secret source label/provenance string;
  - a provider/protocol that supplies the quote.
- The Findchips adapter may use the injected FX quote to calculate `normalized_rmb_price = raw_usd_price * usd_rmb_rate`.
- Do not quantize or round the normalized Decimal in this task; rounding/display precision remains UNKNOWN.
- Add deterministic local fixture/synthetic tests.
- Add a separate bounded live Findchips smoke check for source acquisition/parsing when environment access permits.
- Update `docs/modules/RESEARCH.md` only with durable Findchips and FX-boundary rules established by this task.
- Export the intended stable Research public API from `src/research/__init__.py` only when it is actually intended for later orchestration.

## non_scope

- No live FX web/API provider.
- No arbitrary FX-site access.
- No HQEW implementation.
- No LCSC implementation.
- No Bom.Ai implementation.
- No IC.net changes except compatibility imports if strictly necessary.
- No final multi-source lowest-price aggregation.
- No second-lowest / 20% rule.
- No estimated-order-total calculation.
- No Research orchestrator.
- No Excel business-column expansion.
- No Sheets, Workflow, INSO, or Quotation implementation.
- No Google Sheet access.
- No login/account creation on Findchips.
- No purchasing, RFQ, alert creation, messaging, or other Findchips write action.
- No distributor crawling outside the normal search-results document.
- No pagination/crawl unless later explicitly approved.
- No MOQ persistence.
- No concrete Findchips stock quantity persistence in Evidence or public result objects.
- No inferred currency conversion for non-USD currencies.
- No price rounding rule invented in this task.

## requirements

### Adapter input

The adapter must accept at least:

- target MPN;
- customer quantity;
- an injected USD/RMB FX provider/quote capability.

It must not require Workflow or Sheets objects.

### Search and strict identity

- Query the normal Findchips part-search path for one MPN.
- Trim only leading/trailing whitespace before constructing the search path.
- Every offer used for pricing must pass shared strict-MPN matching.
- Do not accept suffixes, alternate parts, fuzzy matches, distributor part numbers, or similar-looking variants as a match.
- Findchips exact-match UI/filter may be used as an acquisition aid, but Research must still enforce its own strict-MPN helper.
- If a successfully parsed result has no strict-MPN offers, return `NO_STRICT_MPN_MATCH`.
- Network errors, block pages, unexpected result shapes, or unreliable parsing must use `SOURCE_UNAVAILABLE`, not no-match.

### Stock validity

- A strict-MPN offer is price-eligible only if Findchips reports stock present and greater than zero.
- Stock does **not** need to meet customer Qty.
- Zero stock is invalid for pricing.
- If stock state cannot be determined reliably for a candidate row, do not assume in-stock.
- Do not persist the concrete stock number in `SourceEvidence`, `PriceCandidate`, or Findchips public result objects.
- Evidence may record aggregate non-sensitive facts such as counts of strict rows and counts of positive-stock rows.

### Price-tier selection

For each strict-MPN, positive-stock offer:

- parse displayed quantity-break unit-price tiers using `Decimal`;
- only USD tiers are valid for this task;
- choose the greatest tier quantity that is less than or equal to customer Qty;
- if no displayed tier quantity is less than or equal to customer Qty, that offer has no applicable price;
- ignore the separate MOQ field for exclusion; do not save it;
- do not use a summary “price range” minimum as a substitute for the applicable Qty tier;
- do not use hidden/alternate/fallback prices that are not displayed as a normal quantity tier.

Across all offers with an applicable USD tier, select the lowest applicable USD unit price.

If strict-MPN offers exist but none yields a valid price after stock/currency/tier checks, return `NO_VALID_PRICE`.

### USD/RMB FX boundary

Add a minimal Research-owned FX contract, for example an immutable quote plus provider protocol.

Required semantics:

- base currency = USD;
- quote currency = RMB/CNY;
- rate is a positive `Decimal`;
- orientation is `1 USD = rate RMB`;
- quote has a capture timestamp;
- quote has a non-secret provenance/source label;
- adapter uses exact Decimal multiplication;
- no float math;
- no hidden rounding/quantization.

The live rate source itself is intentionally **UNKNOWN** and out of scope.

Tests must use deterministic fixed FX quotes, e.g. a synthetic rate, and must never present that synthetic rate as a real/current market rate.

If the FX provider fails or returns an invalid quote during a full adapter call, fail closed through the source-unavailable/technical path rather than inventing a rate.

### PriceCandidate

On successful adapter processing with at least one eligible Findchips offer and a valid injected FX quote:

- `source = ResearchSource.FINDCHIPS`;
- `matched_mpn` must be the strict matched MPN;
- `raw_price` is the selected applicable Findchips USD unit price;
- `raw_currency = "USD"`;
- `normalized_rmb_price = raw_price * rate`;
- `captured_at` is the source-page capture time;
- `source_url` is the Findchips result URL when available.

The adapter must not select a different MPN merely because it is cheaper.

### Evidence

Evidence should be structured and auditable without persisting raw HTML or concrete stock quantities.

Include, when applicable:

- number of offers/rows inspected;
- strict-MPN row count;
- positive-stock strict-MPN row count;
- strict rows with an applicable USD tier;
- customer quantity;
- selected tier break quantity;
- selected raw USD price;
- FX base/quote currency;
- FX rate used;
- FX capture timestamp;
- FX source label;
- final normalized RMB Decimal;
- source/result URL;
- capture timestamp;
- technical failure code when unavailable.

Do not include:

- concrete stock quantity;
- MOQ;
- cookies/tokens;
- account data;
- full raw HTML;
- distributor contact details;
- arbitrary nested JSON structures when primitive Evidence fields suffice.

### Acquisition boundary

- Prefer ordinary HTTP because current public Findchips search content is server-readable.
- Use a finite timeout and a clear non-secret User-Agent.
- No login is required or authorized for this task.
- Do not implement aggressive retries, concurrency, crawling, pagination, alerts, RFQs, or buy actions.
- If ordinary HTTP cannot reliably obtain the required rows, a bounded standard-browser fallback may be investigated only through normal supported browser behavior.
- Do not add stealth, fingerprint changes, CAPTCHA/challenge bypass, hidden endpoint reverse engineering, or a new dependency without reporting the concrete need first.
- If the live site blocks the approved read-only path, record the blocker honestly.

### Live smoke boundary

The live smoke should validate Findchips acquisition/parsing with a public representative MPN such as a current Findchips example (for example `MMBT2222ALT1G`) and a bounded customer quantity.

Because no live FX source is authorized in this task:

- live smoke must validate the raw Findchips path through strict match, positive stock, applicable USD tier, and selected raw USD price;
- record the observed raw price as volatile evidence, not a permanent assertion;
- do **not** claim a real normalized RMB live result using a fabricated/static FX rate;
- full `PriceCandidate` normalization is verified deterministically with an injected test FX quote.

If a separately approved live FX capability is discovered in current `main`, stop and report it before using it; do not silently adopt it.

## acceptance

- [x] Findchips adapter exists under `src/research/` and has no forbidden cross-module imports.
- [x] Shared strict-MPN helper is reused.
- [x] Only strict-MPN offers may contribute pricing.
- [x] Positive stock is required, but stock does not need to meet customer Qty.
- [x] Concrete stock quantity is not persisted in Evidence/public results.
- [x] MOQ is not used as an exclusion rule and is not persisted.
- [x] Applicable tier uses the greatest displayed tier break <= customer Qty.
- [x] A row with no tier break <= customer Qty does not fabricate an applicable price.
- [x] Summary price-range minimum is not substituted for the Qty-applicable tier.
- [x] Non-USD tiers are not silently converted in this task.
- [x] Lowest applicable USD unit price across eligible offers is selected.
- [x] Strict matches with no eligible price map to `NO_VALID_PRICE`.
- [x] No strict match maps to `NO_STRICT_MPN_MATCH`.
- [x] Technical acquisition/parsing/FX failure maps to `SOURCE_UNAVAILABLE`.
- [x] Successful adapter call produces a Findchips `PriceCandidate`.
- [x] Price math uses `Decimal` only.
- [x] Research-owned USD/RMB FX quote/provider boundary exists with positive-rate validation and provenance.
- [x] No live FX source is added.
- [x] No rounding/quantization rule is invented.
- [x] Default tests are deterministic and make no live calls.
- [x] One bounded read-only Findchips live smoke is attempted and honestly recorded.
- [x] No Findchips write action, login, alert, RFQ, purchase action, or crawl is introduced.
- [x] No HQEW/LCSC/Bom.Ai/final aggregation/Excel expansion is introduced.
- [x] Python 3.12 Research tests pass.
- [x] Ruff passes for changed Research Python/test files.
- [x] Final diff contains no unrelated changes.

## verification

- Run focused Findchips/FX unit and fixture tests.
- Run `py -3.12 -m pytest tests/research`.
- Run `py -3.12 -m ruff check` for changed Research Python/test files.
- Run `git diff --check origin/main...HEAD`.
- Inspect the complete diff against this Task Packet.
- Confirm no imports from `sheets`, `workflow`, `inso`, or `quotation`.
- Confirm no concrete Findchips stock quantity is persisted in Evidence/public contracts.
- Confirm no live FX source or arbitrary extra network source was added.
- Confirm no float price/rate math.
- Perform one bounded live Findchips smoke when network access permits.
- Do not assert a volatile live price as a permanent test constant.

## completion

- status: complete
- changed:
  - Added `src/research/findchips.py` with ordinary-HTTP acquisition, server-rendered offer parsing, strict-MPN enforcement, positive-stock filtering, Qty-applicable USD tier selection, lowest-price selection, structured Evidence, and Findchips `PriceCandidate` creation.
  - Added `src/research/fx.py` with immutable positive-Decimal `UsdRmbQuote` and an injected `UsdRmbProvider` protocol oriented as `1 USD = rate RMB/CNY`; no live FX provider was added.
  - Exported the intended Findchips adapter/client and USD/RMB boundary from `src/research/__init__.py`.
  - Added a sanitized Findchips fixture and deterministic tests for strict MPN, stock state, Qty tiers, MOQ/price-range exclusion, currency filtering, outcomes, Decimal normalization, FX validation, and technical failures.
  - Added durable Findchips and FX-boundary rules to `docs/modules/RESEARCH.md`.
- verified:
  - Focused `py -3.12 -m pytest tests/research/test_fx.py tests/research/test_findchips.py`: 25 passed.
  - `py -3.12 -m pytest tests/research`: 94 passed.
  - `py -3.12 -m ruff check src/research/fx.py src/research/findchips.py src/research/__init__.py tests/research/test_fx.py tests/research/test_findchips.py`: passed.
  - `git diff --check origin/main...HEAD`: passed.
  - Public ordinary-HTTP live smoke for `MMBT2222ALT1G` with customer Qty 100 parsed 87 offers, found 65 strict-MPN offers, 65 positive-stock strict offers, and 27 offers with an applicable USD tier. It selected displayed break 100 at raw USD unit price `0.0086`. This price is a volatile observation from this smoke only, not a permanent constant.
  - The live smoke used no FX provider and made no claim of a live normalized RMB price. Deterministic tests verified exact `Decimal` USD multiplication using a synthetic injected quote labeled test-only.
  - No concrete Findchips stock quantity, MOQ, raw HTML, cookie, token, account data, or contact data is persisted in Evidence, `PriceCandidate`, or public Findchips result objects.
  - No imports from `sheets`, `workflow`, `inso`, or `quotation`; no HQEW/LCSC/Bom.Ai/IC.net change, orchestration, aggregation, Excel expansion, login, write action, crawler, browser automation, stealth, or anti-bot bypass was introduced.
- limitations:
  - Live USD/RMB FX source, refresh cadence, fallback policy, and final RMB display rounding/precision remain `UNKNOWN` and intentionally out of scope.
  - Findchips live prices and result counts are volatile and must not become fixture assertions or business constants.
  - HQEW, LCSC, Bom.Ai, final aggregation, 20% comparison, second-lowest logic, estimated total, Excel business-column completion, and Research orchestration remain future tasks.
