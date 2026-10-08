# Task: Unified Owner-defined MPN matching and V1.3 deployment

status: complete
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
Complete; implementation and controlled asset-only deployment verified.

## pre-deployment verification
- Full safe/offline release environment: 1636 passed / 1 skipped (existing Windows symlink capability). Restricted preliminary run: 1626 passed / 11 environment skips, all ten extra skips verified in release environment.
- Core boundary cases, six Research adapters, prefix-query construction, lower-history full pagination/settlement, fuzzy duplicate latest/tie ambiguity, quotation suffix selection/raw14, exact AI validation all PASS in full suite. Existing RFQ-003/004/005/006, GUI, retry, status repair, purchase follow-up and background Chrome tests retained PASS.
- Ruff and git diff --check PASS; source/test diff manually reviewed, changes scoped. No credentials/live-business access during implementation.
- Packaging and controlled deployment completed (details below).

## final package / deployment
- Production source commit: 9bd601ebd6cb15cfbd511d031af69e4a8448523a on codex/v13-readiness-repair. Local commit only; no report/source push implied or performed.
- BuildOnly / candidate release scan / frozen self-check / isolated idle GUI: PASS. Final deployed self-check / idle GUI / existing fixed-CDP check / deployed-asset release scan: PASS.
- Formal path: `D:\Program_Leo\INSO_Leo\dist\INSO_V1.3`. EXE SHA256: `0BF58DF4CF0DF95999B6E3CC8F089FB4608B09ECE55D1D93A8761799C804B773`. All 2179 installed release asset hashes match the verified candidate.
- Fresh complete backup: `D:\Program_Leo\INSO_Leo\dist\release-backups\INSO_V1.3_20261008_184720_7f39e155`; all 2184 original files copied and hashes verified before replacement. Previous backups retained.
- All 3953 protected inventory file hashes unchanged. Production workflow DB and DB backups, OAuth/credentials/config/Research/SMTP, fixed Chrome profile and CDP settings retained. V1.2 before/after identical SHA256 `340D7F7E7E818FA74DE36B138B205F5905F320406FD8D391EF860BD052529E5F`.
- Only formal EXE and _internal replaced, no runtime replacement. GUI rendered STOPPED with no business thread; CDP connected to the existing unique context with one page, no second Chrome/profile. Idle validation exited normally.
- No live market/order replay, procurement/Save/Save-and-Send, Google quotation input/status write/update, Apps Script, SMTP delivery or business polling by this task. No production DB mutation or schema change.
- Native site result/first-page limits remain; new rule is verified offline against all adapters and packaged lifecycle, not a claim of exhaustive live-site recall. No new decision conflict beyond the explicitly authorized wider model matching; same-time latest duplicate ambiguity remains fail closed.
- Local evidence `D:\Program_Leo\INSO_Leo\.tmp\v13-deploy-20261008_184720_7f39e155/plan.json`, `verification.json`; `.tmp/fuzzy-mpn-full-final.log`, `.tmp/fuzzy-mpn-build.log`, `.tmp/v13-fuzzy-frozen-report.json`. Evidence remains untracked; no secrets/customer output added to Git.
