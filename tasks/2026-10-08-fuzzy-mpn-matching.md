# Task: Unified Owner-defined MPN matching and V1.3 deployment

status: in_progress
owner: Codex
created: 2026-10-08
updated: 2026-10-08

## authority / goal
Owner explicitly authorizes all Research sources and lower INSO temporary-procurement-history duplicate and quotation recognition to use one fuzzy model rule; after validation package and overwrite formal V1.3. This supersedes exact duplicate and previous six-character Research suffix rules only in these read/decision paths.

## requirements
- NFKC/case normalization; remove whitespace, underscore, Unicode dash punctuation/minus and invisible whitespace. Strip two final characters from the cleaned Google target, require result to start with that prefix, with at most ten further cleaned characters. Nonempty targets of at most two characters retain exact matching. Empty inputs never match.
- Share one pure public Core policy across Research, INSO and Workflow; no duplicate implementations/dependencies. Prefix query acquisition preserves original target for result filtering (no double truncation).
- Research price/stock scope includes IC.net, Findchips, HQEW, LCSC, Bom.Ai and INSO; retain source-specific prices/stock windows and tie behavior.
- Lower INSO duplicate: retain rolling168h/latest/tie ambiguity/quantity/creator/zero-price rules and all pagination/settlement proofs.
- Quotation: retain rolling72h, lowest RMB-equivalent supplier net price, positive-before-zero, newest ties and raw14 original text. Display/API attribution remains exact and distinct from target matching.
- Preserve Google row identity, procurement AI/parent/submission outcome exact validation and durable second-send guards. No historical replay or production business tests.

## scope / verification
Offline matcher boundaries, each Research adapter, native query keywords, duplicate read/decision, quotation reader/selection, unchanged submit safety; focused/full safe tests/Ruff/diff; BuildOnly/frozen/release scan; fresh backup and asset-only deployment with protected DB/config/V1.2/profile inventory and idle GUI only. No source write, purchase, quote execution, SMTP or polling in tests.

## UNKNOWN
Live sites may limit native prefix-search results/pagination; offline tests prove filtering/query construction, not exhaustive remote recall. This task does not bypass native limits or authentication.

## completion
pending

## pre-deployment verification
- Full safe/offline release environment: 1636 passed / 1 skipped (existing Windows symlink capability). Restricted preliminary run: 1626 passed / 11 environment skips, all ten extra skips verified in release environment.
- Core boundary cases, six Research adapters, prefix-query construction, lower-history full pagination/settlement, fuzzy duplicate latest/tie ambiguity, quotation suffix selection/raw14, exact AI validation all PASS in full suite. Existing RFQ-003/004/005/006, GUI, retry, status repair, purchase follow-up and background Chrome tests retained PASS.
- Ruff and git diff --check PASS; source/test diff manually reviewed, changes scoped. No credentials/live-business access during implementation.
- Packaging and controlled deployment pending.
