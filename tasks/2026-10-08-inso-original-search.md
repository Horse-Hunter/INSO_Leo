# Task: INSO searches original full source model; normalize only comparisons

status: completed
owner: Codex
created: 2026-10-08

## authority / scope
Owner clarification supersedes cleaned-prefix/first-token INSO retrieval. Use original full Google source model for all three INSO procurement-history consumers (Research, duplicate check, quotation); normalization and dropping two tail characters only apply to comparison of returned models. Continue existing authorized packaging/asset-only overwrite after validation. No real procurement, quote update, Apps Script, SMTP or historical replay. Preserve B/L model fix, currency/window/zero rules, durable holds, identity, CDP and runtime protection.

## implementation / acceptance
Preserve raw model case, separators and whitespace through retrieval. Duplicate history bridge must not send its canonical comparison key to the lower-history reader. HTTP form and URL encode raw model so separators/plus/ampersand survive as data. Native CDP reads raw text exactly and verifies corresponding request. Legacy upper-history exact rule unchanged. Comparison remains existing shared lookup_mpn_matches. Existing source validation still rejects invalid/empty model.

## verification
Offline raw-query transport/model-comparison regressions, prior B/L/notification/RFQ regression, full safe tests/Ruff/diff, BuildOnly/frozen/scan/idle and deployed protected manifest checks.

## completion
- Production commit: 20fad4938a8312da00b1bd48e10af4f3c1bdbc8f. Search preserves complete raw source string through native CDP and HTTP decoded form/query; normalization occurs only in result comparison. Research INSO / procurement-history duplicate / quotation all reuse the same corrected helper. Legacy upper-history rule and all other websites unchanged.
- Focused 406 passed; full safe/offline 1669 passed / 1 skipped (Windows symlink unavailable); Ruff and diff check PASS.
- Raw original query tests cover separators, whitespace, case, plus/ampersand transport escaping, normalized duplicate-result matching and zero-price quotation. Prior B/L/source race/notification/RFQ tests PASS.
- Targeted read-only canonical INSO verification selects the already-existing separated-model no-stock zero quote. No actual quote update/replay/SMTP test or procurement executed.
- BuildOnly, release scan, frozen self-check and idle GUI PASS. Deployed self-check/idle/CDP/scan PASS; no business thread started by validation.
- Formal deployment: D:\Program_Leo\INSO_Leo\dist\INSO_V1.3
- EXE SHA256: BFFEFA407375211E758EC793AF5388D4FBCEF6A7BB01E456251DFE8213EDD98C
- New complete backup: D:\Program_Leo\INSO_Leo\dist\release-backups\INSO_V1.3_20261008_201354_8f602a52
- All 2179 release assets match candidate; 3953 protected files unchanged. Runtime DB/backups, V1.2, OAuth, credentials, production config, fixed Chrome profile/CDP preserved. V1.2 hash before=after 340D7F7E7E818FA74DE36B138B205F5905F320406FD8D391EF860BD052529E5F.
- Local evidence: D:\Program_Leo\INSO_Leo\.tmp\v13-deploy-20261008_201354_8f602a52; source workspace clean after report commit. No push or production raw-data commit. Business loop remains stopped.
- This Owner clarification supersedes first-token retrieval recorded in the previous task. No new architecture, browser or notification system.
