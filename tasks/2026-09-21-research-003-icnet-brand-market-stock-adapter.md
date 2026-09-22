# Task: RESEARCH-003 — IC.net Brand & Market Stock Adapter

status: blocked
owner: Research Codex
created: 2026-09-21
updated: 2026-09-22

## problem

Research now has a stable source/evidence foundation, but it has no real source adapter. IC.net is the lowest-risk first integration because V1 uses it only for Brand resolution and market-stock classification, not for final market-price candidates.

## goal

Implement a bounded, read-only IC.net adapter that searches one MPN, applies the confirmed strict-MPN rule, resolves Brand when needed, calculates the V1 market-stock label, and returns Research-owned structured evidence/results.

This task must not implement any other website or any final multi-source Research orchestration.

## current_facts

- Runtime: Python 3.12.
- IC.net is a confirmed Research V1 source and is not a V1 final market-price source.
- Current public IC.net site: `https://www.ic.net.cn/`; the site currently exposes model search and an exact-model option.
- Research V1 external access authorizes read-only IC.net market research.
- Web access baseline: ordinary HTTP first; Playwright only when JavaScript/browser behavior is actually required.
- Research Chat decision (2026-09-21): Playwright normal browser mode is authorized for read-only IC.net verification; CAPTCHA or anti-bot bypass remains prohibited.
- Shared `ResearchSource`, `SourceOutcome`, `SourceEvidence`, `SourceResult`, and `is_strict_mpn_match` already exist under `src/research/source_contracts.py`.
- IC.net must never produce a `PriceCandidate`.
- Strict MPN matching: trim leading/trailing whitespace and compare case-insensitively; otherwise characters must match completely. No suffix/variant/fuzzy substitution.
- If Research input Brand is present, use that Brand; do not replace it from IC.net.
- If Research input Brand is blank, inspect the first 20 IC.net model-search result rows and resolve manufacturer by frequency.
- Manufacturer display rule: pure English or pure Chinese is kept as displayed; when IC.net displays a bilingual manufacturer label with a separable English component, use the displayed English component. Do not translate or invent an English name.
- Brand tie rule:
  1. highest frequency wins;
  2. if tied, prefer an English candidate;
  3. if still tied among English candidates, prefer the shorter English name.
- If the confirmed tie rules still do not produce a unique Brand, leave Brand unresolved and preserve the ambiguity in structured evidence; do not invent an additional tie-break.
- IC.net market stock uses the first search-results page only.
- For market stock, sum the displayed product quantities of relevant rows carrying SSCP or ICCP certification.
- A row carrying both SSCP and ICCP is counted only once.
- Do not add a Brand filter to the stock sum unless a later confirmed rule explicitly requires it.
- `total <= quantity * 3` => `货少`.
- `total > quantity * 3` => `货多`.
- Equality at exactly `3 * quantity` is `货少`.
- IC.net stock is evidence/output context only and does not create a market-price candidate.
- Owner authorization: IC.net normal member login is allowed for this task only to perform read-only Research. Credentials must be obtained at runtime through the existing project Credential Provider; credentials must not be committed, logged, copied into Task Packets, or pasted into chat/code.
- Detailed selectors, XPath, hidden endpoints, and session mechanics are implementation details and must not be promoted into durable architecture docs.
- Research must not import `sheets`, `workflow`, `inso`, or `quotation`.

Sources: current `main` documentation, confirmed Research rules, and public IC.net read-only inspection.

## scope

- Add an IC.net adapter under `src/research/`.
- Add a small IC.net-specific immutable result contract if needed to carry:
  - the generic `SourceResult`;
  - optional resolved Brand;
  - optional V1 stock display value (`货少` / `货多`).
- Add pure helpers for:
  - Brand display extraction from IC.net manufacturer text;
  - Brand-frequency selection using the confirmed tie rules;
  - certified-stock summation;
  - stock-label classification.
- Implement one read-only model search against IC.net.
- If IC.net requires authentication, use the existing project Credential Provider to obtain runtime credentials through a stable IC.net site identity. Research must consume the credential capability only; it must not implement vault storage, DPAPI, credential CRUD, or secret lifecycle.
- Prefer ordinary HTTP and HTML parsing if sufficient.
- If ordinary HTTP cannot reliably obtain the required result data, stop and report the concrete blocker before adding Playwright or a new dependency.
- Reuse the shared strict-MPN helper.
- Parse enough of the first result page to obtain:
  - displayed MPN;
  - manufacturer;
  - displayed quantity;
  - SSCP / ICCP certification presence.
- Build structured `SourceEvidence` for the IC.net result.
- Add deterministic synthetic/fixture tests for parsing and all confirmed business rules.
- Add a separate, explicit read-only live smoke verification against IC.net when the environment permits.
- Update `docs/modules/RESEARCH.md` only with durable IC.net business rules established by this task; do not store selectors or volatile HTML details there.

## non_scope

- No Findchips implementation.
- No HQEW implementation.
- No LCSC implementation.
- No Bom.Ai implementation.
- No FX conversion.
- No market-price candidate from IC.net.
- No final lowest-price aggregation.
- No second-lowest / 20% rule.
- No estimated-order-total calculation.
- No Research orchestrator.
- No Excel business-column expansion.
- No Sheets, Workflow, INSO, or Quotation implementation.
- No credential storage/CRUD, DPAPI/vault implementation changes, secret logging, messaging, inquiry submission, or write action on IC.net.
- No reuse of arbitrary browser cookies or credentials outside the existing project Credential Provider.
- No pagination beyond the first IC.net search-results page.
- No screenshots as a mandatory requirement.
- No speculative Brand normalization, aliases, manufacturer dictionaries, transliteration, fuzzy matching, or extra tie-break rules.
- Do not add a new dependency unless ordinary standard-library/installed-library HTTP and parsing are demonstrably insufficient; if a new dependency appears necessary, stop and report before installing it.

## requirements

### Adapter input

The adapter must accept at least:

- target MPN;
- optional input Brand;
- customer quantity.

It must not require Workflow/SHEETS objects or import their modules.

### Search and strict identity

- Use IC.net model search in the most exact available read-only mode.
- Every parsed row used for Brand frequency or stock calculation must have a displayed MPN that passes the shared `is_strict_mpn_match` helper.
- Nonmatching rows must not contribute to Brand frequency or stock.
- If no strict-matching rows are found on a successfully parsed result page, return generic source outcome `NO_STRICT_MPN_MATCH`.
- A network error, block page, unexpected page shape, or inability to parse required fields reliably must return/raise through the source-unavailable path rather than being treated as no match.

### Brand resolution

If input Brand is nonblank:

- preserve/use the provided Brand;
- do not replace it using IC.net frequency.

If input Brand is blank:

- inspect at most the first 20 result rows in page order;
- only strict-MPN rows are eligible;
- derive one manufacturer display candidate per eligible row when possible;
- count candidate frequency;
- choose the highest-frequency candidate;
- on a top-frequency tie, prefer an English candidate;
- if multiple English candidates remain tied, choose the shorter English name;
- if the confirmed rules still leave more than one candidate tied, return no resolved Brand and record the ambiguity in Evidence.

Manufacturer display extraction:

- pure English -> keep displayed value;
- pure Chinese -> keep displayed value;
- clearly bilingual with a separable displayed English component -> use that English component;
- do not translate, transliterate, or invent an English manufacturer name.

### Market stock

On the first search-results page:

- consider only strict-MPN rows;
- include a row when it carries SSCP or ICCP;
- if it carries both, count the row once;
- sum each included row's displayed product quantity once;
- do not require stock quantity to meet customer Qty before inclusion;
- do not filter the stock sum by resolved/input Brand in V1;
- classify:
  - `total <= quantity * 3` -> `货少`
  - `total > quantity * 3` -> `货多`

If a row that must be included has a quantity that cannot be parsed reliably, fail closed through source unavailability rather than guessing or silently treating it as zero.

### IC.net-specific result

A successful IC.net adapter result must:

- use `ResearchSource.IC_NET`;
- carry no `PriceCandidate`;
- carry structured evidence;
- expose the effective/resolved Brand when the confirmed rules resolve one;
- expose the stock display value when stock calculation succeeds.

For `NO_STRICT_MPN_MATCH` or `SOURCE_UNAVAILABLE`, do not fabricate Brand or stock values that were not reliably established.

The generic `SourceOutcome.NO_VALID_PRICE` is not an IC.net business outcome and should not be produced by this adapter.

### Evidence

IC.net Evidence must remain structured and include enough observations to audit the result without persisting raw HTML. Include, when applicable:

- number of first-page rows inspected;
- number of strict-MPN rows;
- number of Brand-frequency rows used;
- Brand candidate counts or equivalent structured observations;
- whether Brand came from input or IC.net resolution;
- qualified SSCP/ICCP row count;
- certified-stock total;
- customer quantity;
- stock threshold (`quantity * 3`);
- final stock display value;
- source/capture timestamp;
- source/result URL when available.

Do not persist credentials, cookies, tokens, full raw HTML, or unnecessary personal/business contact data from supplier rows.

### Authentication boundary

- Normal IC.net member login is explicitly authorized for this task when required to reach read-only model-search results.
- Obtain credentials only at runtime through the existing project Credential Provider capability.
- Do not hardcode usernames/passwords, persist live secrets, print secrets, or add secret-bearing fixtures.
- Do not modify the Credential Provider, vault format, DPAPI logic, GUI, or credential lifecycle in this task.
- If the local Credential Provider has no IC.net credential entry, stop and request that the Owner add one locally; never request the password in chat.
- If login requires CAPTCHA, SMS/OTP, QR confirmation, device approval, or another interactive challenge, do not bypass or automate the challenge. Stop and report the exact user action required.
- Authenticated cookies/session state may be held only in-memory for the bounded read-only session unless an existing approved browser/session facility already defines otherwise.
- Successful login does not authorize any write-side action.

### HTTP / parsing boundary

- Keep network acquisition separate from pure parsing/business-rule functions so fixture tests do not require live internet.
- Use a finite timeout.
- Use a clear, non-secret User-Agent.
- Do not implement aggressive retry, crawling, pagination, or concurrency in the adapter.
- Do not bypass anti-bot controls.
- If IC.net blocks the approved read-only request path, report the blocker rather than adding evasion logic.

## acceptance

- [ ] IC.net adapter exists under `src/research/` and has no forbidden cross-module imports.
- [ ] IC.net uses the shared strict-MPN helper.
- [ ] IC.net cannot produce a `PriceCandidate`.
- [ ] Provided input Brand is preserved and not replaced by IC.net.
- [ ] Blank Brand is resolved from at most the first 20 result rows using the confirmed frequency/tie rules.
- [ ] Pure English / pure Chinese / bilingual-English display handling has deterministic tests.
- [ ] Remaining unresolved Brand tie is preserved as unresolved rather than guessed.
- [ ] Stock uses first-page strict-MPN rows carrying SSCP or ICCP.
- [ ] A row carrying both SSCP and ICCP is counted once.
- [ ] No Brand filter is applied to stock calculation.
- [ ] `total == quantity * 3` yields `货少`.
- [ ] `total > quantity * 3` yields `货多`.
- [ ] Required but unparseable qualified quantity fails closed rather than becoming zero.
- [ ] Successful generic source outcome carries structured IC.net Evidence and no price candidate.
- [ ] No-match and technical-unavailability paths remain distinct.
- [ ] Default tests use deterministic local fixtures/synthetic HTML and make no live call.
- [ ] A separate read-only authenticated IC.net live smoke verification is attempted when IC.net requires login and local authorized credentials are available; its result is recorded honestly.
- [ ] No other website adapter, FX, aggregation, orchestrator, Excel expansion, credentials, login, or write side effect is introduced.
- [ ] Python 3.12 Research tests pass.
- [ ] Ruff passes for changed Python files.

## verification

- Run `py -3.12 -m pytest tests/research`.
- Run `py -3.12 -m ruff check` for changed Research Python/test files.
- Run focused IC.net unit/fixture tests separately if useful.
- Perform one bounded read-only IC.net live smoke check using a public test MPN; do not assert volatile quantities/Brand counts as fixed long-term values.
- Inspect the complete diff against this Task Packet.
- Confirm no imports from `sheets`, `workflow`, `inso`, or `quotation`.
- Confirm IC.net authentication, when used, goes only through the existing Credential Provider and introduces no secret-bearing values; confirm no IC.net write actions, CAPTCHA/anti-bot bypass, pagination crawler, or credential-storage changes.
- If the live site still cannot be accessed or parsed after the authorized normal-login path, keep the Task blocked and report the concrete reason; do not pretend the real adapter has been verified.

## completion

- status: blocked
- changed:
  - Added `src/research/icnet.py` with an immutable IC.net result contract, pure Brand/stock helpers, a minimal visibility-aware HTML parser, an injectable page boundary, and a bounded authenticated Playwright client.
  - Exported the IC.net public API from `src/research/__init__.py`.
  - Added a minimal synthetic fixture and deterministic IC.net tests without supplier/contact data or live network calls.
  - Added durable IC.net Brand, certified-stock, authentication, and failure rules to `docs/modules/RESEARCH.md`.
  - The Owner-provided full HTML samples remain local and were not committed.
- verified:
  - Dedicated standard-Chrome headed login verification found and filled both credential fields, clicked login, reached `https://www.ic.net.cn/`, and found the logged-in marker. Credentials came only from the existing Credential Provider and were neither printed nor persisted.
  - The real result sample `icnet_result_sample.html` (SHA-256 `b2925e0483d8b2f4d6b76c47c54c794ee94634ddd963ca8a82631908e4089055`) parsed in memory as 21 first-page rows; all 21 strictly matched `BE890D3S152T0I1000`; 2 SSCP/ICCP-qualified rows summed to displayed stock 244. The parser ignored CSS-hidden decoy MPN and quantity nodes.
  - `py -3.12 -m pytest tests/research`: 60 passed.
  - `py -3.12 -m ruff check src/research/icnet.py src/research/__init__.py tests/research/test_icnet.py`: passed.
  - Authenticated headed live smoke through the implemented Adapter used the configured `ic.net.cn` Credential Provider entry and returned `SOURCE_UNAVAILABLE` with `failure_code = RESULT_PAGE_BLOCKED`; Evidence retained the non-secret result URL.
  - A separate headed standard-Chrome check logged in successfully and navigated directly to the Owner-specified HTTPS URL `https://www.ic.net.cn/search/BE890D3S152T0I1000.html`. The HTTPS response was HTTP 200 and the final URL remained HTTPS, but the complete document still had no `<body>`, result rows, or target-MPN nodes.
  - No CAPTCHA, OTP, device verification, stealth setting, browser-fingerprint change, challenge-script analysis, cookie persistence/reuse, or IC.net write action was used.
- limitations:
  - The authenticated live result response still completes as a 108-character script-only document containing `q.js`, without a `<body>` or product rows, in unmodified headed Chrome. The local real sample proves parser behavior but is not a successful live retrieval.
  - The Task Packet explicitly requires a successful authenticated live smoke; therefore RESEARCH-003 remains blocked and a PR must not be created yet.
  - Completion requires an Owner-provided site-supported read-only path that returns the result document to an unmodified normal browser. Anti-bot or challenge bypass remains prohibited.
  - Findchips, HQEW, LCSC, Bom.Ai, FX, final aggregation, Excel business-row completion, and Research orchestration remain future tasks.
