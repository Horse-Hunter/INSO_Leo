# Task: RESEARCH-002 — Source Contract & Evidence Foundation

status: ready
owner: Research Codex
created: 2026-09-21
updated: 2026-09-21

## problem

Research V1 now has its public ResearchInput/ResearchResult contract and idempotent Excel foundation, but it does not yet have a shared internal contract for source adapters, normalized price candidates, evidence, strict MPN matching, or source-level outcome semantics. Implementing real websites before this foundation would force each adapter to invent its own result shape.

## goal

Create the Research-owned, website-agnostic source/evidence foundation that all later IC.net, Findchips, HQEW, LCSC, and Bom.Ai adapters will use.

This task must remain pure/local: no real website adapter, no HTTP, no Playwright, no login, no Credential Provider call, and no live external access.

## current_facts

- Runtime: Python 3.12.
- Public ResearchInput and ResearchResult already exist under `src/research/`.
- Confirmed Research sources are IC.net, Findchips, HQEW, LCSC, and Bom.Ai.
- Only Findchips, HQEW, LCSC, and Bom.Ai are V1 price sources. IC.net is not a final market-price source.
- Final comparable market prices must be normalized to RMB before aggregation.
- Strict MPN matching is confirmed: trim leading/trailing whitespace and compare case-insensitively; any other character difference is not a match.
- Research must not guess variants or substitute similar MPNs.
- Source-level business absence and technical unavailability are different conditions.
- `NO_MATCHING_PRODUCT` is valid only when all four price sources complete successfully and none has a strict MPN match.
- Technical failure must not count as “no match”.
- `SOURCE_UNAVAILABLE` is the confirmed technical-unavailability reason semantic.
- `PARTIAL_SUCCESS` requires at least one valid website price.
- Structured Evidence is required in V1; screenshot evidence is not mandatory.
- Evidence persistence technology remains undecided; this task defines in-memory contracts only.
- Findchips only requires that stock exists; `stock >= customer quantity` is not required and exact stock quantity does not need to be stored.
- MOQ is not a Research market-price exclusion condition and does not need to be stored.
- LCSC preorder/out-of-stock entries with an otherwise valid price may participate like normal price entries.
- Bom.Ai price validity is one month: prefer the lowest valid price in the most recent 7 days; if none exists, use the lowest valid price within one month.
- Research may depend on `core` but must not depend on `sheets`, `workflow`, `inso`, or `quotation`.

Sources: `docs/PRODUCT_BASELINE.md`, `docs/modules/RESEARCH.md`, `docs/MODULE_INDEX.md`.

## scope

- Add Research-owned internal source contract types under `src/research/`.
- Add a source identifier Enum covering exactly the five confirmed V1 Research sources.
- Add a source-level outcome Enum that can distinguish:
  - successful source processing;
  - no strict MPN match;
  - strict MPN match but no valid price for the source;
  - source unavailable / technical failure.
- Add a normalized `PriceCandidate` contract for price sources.
- Add a structured `SourceEvidence` contract plus an extensible structured evidence-field representation for source-specific observations.
- Add a `SourceResult` contract that can carry source outcome, evidence, and an optional normalized price candidate.
- Add the reusable strict-MPN-match helper according to the confirmed rule.
- Add a canonical `PRICE_SOURCES` set/tuple containing Findchips, HQEW, LCSC, and Bom.Ai only.
- Add the confirmed `SOURCE_UNAVAILABLE` Research reason code to the existing public reason-code Enum if not already present.
- Add pure unit tests for all new contracts and invariants.
- Update `docs/modules/RESEARCH.md` only where needed to document the durable source/evidence contract established by this task.

## non_scope

- No IC.net adapter implementation.
- No Findchips adapter implementation.
- No HQEW adapter implementation.
- No LCSC adapter implementation.
- No Bom.Ai adapter implementation.
- No HTTP client, HTML parser, browser, Playwright, selector, XPath, login, cookies, session handling, or Credential Provider calls.
- No live website access.
- No FX provider or USD/RMB conversion implementation.
- No source-specific price-selection algorithms beyond representing their results.
- No Bom.Ai date-window algorithm implementation.
- No IC.net brand-frequency or SSCP/ICCP quantity algorithm implementation.
- No final price aggregation, lowest/second-lowest selection, 20% rule, estimated-order-total calculation, or Research orchestrator.
- No Excel business-column expansion in this task.
- No Workflow, Sheets, INSO, Quotation, SQLite, scheduler, retry, or duplicate-prevention implementation.
- No screenshot capture or evidence persistence backend.
- Do not introduce a new shared/core abstraction merely because these Research types might hypothetically be reusable.

## requirements

### Source identity

Define one Research-owned Enum representing exactly:

- IC.net
- Findchips
- HQEW
- LCSC
- Bom.Ai

Names are implementation-level choices, but serialized/string values should be stable and unambiguous.

Define a canonical `PRICE_SOURCES` collection containing exactly the four price sources and excluding IC.net.

### Strict MPN match

Provide one reusable pure helper.

Confirmed behavior:

- trim leading/trailing whitespace on both target and observed MPN;
- compare case-insensitively;
- otherwise require complete character equality;
- do not remove internal whitespace;
- do not remove hyphens, slashes, dots, suffixes, prefixes, package codes, or any other characters;
- do not use fuzzy matching.

Examples:
- `"ABC123"` vs `"abc123"` -> match
- `" ABC123 "` vs `"ABC123"` -> match
- `"ABC123"` vs `"ABC123TR"` -> no match
- `"ABC123-7"` vs `"ABC123-13"` -> no match

### Source outcome

Create a Research-internal source outcome contract that distinguishes at least these semantics:

- source processed successfully;
- no strict MPN match;
- strict MPN match but no valid source price;
- source unavailable / technical failure.

Do not map these source outcomes to final ResearchStatus in this task. Final multi-source aggregation belongs to a later Research orchestrator task.

### PriceCandidate

Create an immutable/dataclass-style contract for one selected price candidate from one V1 price source.

It must include enough normalized information for later aggregation:

- source;
- matched MPN;
- raw numeric price;
- raw currency code;
- normalized RMB numeric price;
- source/capture timestamp;
- source URL when available.

Use a decimal-safe monetary representation; do not use binary float for monetary values.

A `PriceCandidate` represents a source-specific price that has already passed that adapter's source-specific validity rules. This task does not decide those rules.

IC.net must not produce a final market-price candidate under the V1 contract.

### Structured Evidence

Create an immutable/dataclass-style `SourceEvidence` contract containing at least:

- source;
- query MPN;
- matched MPN when one exists;
- source outcome;
- source URL when available;
- captured timestamp;
- structured source-specific evidence fields.

Evidence fields must be structured rather than a single opaque prose blob. Use a simple immutable key/value evidence-field representation or an equivalent typed structure that later adapters can extend without changing the base contract.

Do not include:
- secrets;
- credentials;
- cookies;
- raw password/token data;
- mandatory screenshots;
- mandatory raw HTML.

Evidence may later contain source-specific facts such as quote date, displayed quantity band, stock-presence flag, or IC.net observed quantities, but this task must not implement website extraction.

### SourceResult

Create an immutable/dataclass-style source result contract that includes:

- source;
- source outcome;
- structured evidence;
- optional `PriceCandidate`.

Enforce or test these invariants:

- only confirmed price sources may carry a `PriceCandidate`;
- a source-unavailable result cannot carry a valid price candidate;
- a no-match result cannot carry a valid price candidate;
- a no-valid-price result cannot carry a valid price candidate;
- a successful price-source result may carry a price candidate;
- IC.net source results may be successful without a price candidate.

Avoid inventing IC.net-specific brand/stock output fields in this task; those belong to the IC.net adapter task.

### Reason code

Add `SOURCE_UNAVAILABLE` to the existing `ResearchReasonCode` public Enum.

Do not invent a broad reason-code catalog.

### Safety and dependencies

- Keep implementation under `src/research/` and tests under `tests/research/`.
- No imports from `sheets`, `workflow`, `inso`, or `quotation`.
- No external side effects.
- No real URLs are required in tests; use synthetic examples.
- No credentials or secret-bearing examples.

## acceptance

- [ ] A stable Research source Enum covers exactly the five confirmed sources.
- [ ] `PRICE_SOURCES` contains exactly Findchips, HQEW, LCSC, and Bom.Ai.
- [ ] Source outcome semantics distinguish success, no strict match, no valid price, and technical unavailability.
- [ ] Strict MPN helper passes confirmed equality/non-equality examples and does no fuzzy/variant normalization.
- [ ] `PriceCandidate` uses a decimal-safe monetary type and always carries normalized RMB price.
- [ ] Structured `SourceEvidence` exists and is not just one prose string.
- [ ] `SourceResult` can represent IC.net without a price candidate and each price source with an optional candidate.
- [ ] Invalid outcome/candidate combinations fail closed or are rejected by construction/validation.
- [ ] IC.net cannot carry a final market-price candidate.
- [ ] Existing public `ResearchReasonCode` includes `SOURCE_UNAVAILABLE` and does not grow unrelated reason codes.
- [ ] Existing ResearchInput/ResearchResult/Excel behavior from RESEARCH-001/001A remains compatible.
- [ ] Tests use only local/synthetic data and perform no live website/network/browser/credential access.
- [ ] Research code has no forbidden cross-module imports.
- [ ] No source-specific adapter or final price aggregation/orchestrator is implemented.

## verification

- Run the scoped Research test suite with Python 3.12 / pytest.
- Run ruff on changed Python files if available.
- Inspect the complete diff against the Task Packet.
- Confirm no HTTP/Playwright/browser/credential/network code.
- Confirm no imports from `sheets`, `workflow`, `inso`, or `quotation`.
- Confirm no secret-bearing values or real credentials.
- Record unavailable verification tools honestly.

## completion

- status: pending
- changed: pending
- verified: pending
- limitations: all real source adapters, FX, source-specific selection logic, final multi-source aggregation, Excel business output completion, and orchestration remain future tasks.
