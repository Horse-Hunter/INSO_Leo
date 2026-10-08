# Task: INSO searches original full source model; normalize only comparisons

status: in_progress
owner: Codex
created: 2026-10-08

## authority / scope
Owner clarification supersedes cleaned-prefix/first-token INSO retrieval. Use original full Google source model for all three INSO procurement-history consumers (Research, duplicate check, quotation); normalization and dropping two tail characters only apply to comparison of returned models. Continue existing authorized packaging/asset-only overwrite after validation. No real procurement, quote update, Apps Script, SMTP or historical replay. Preserve B/L model fix, currency/window/zero rules, durable holds, identity, CDP and runtime protection.

## implementation / acceptance
Preserve raw model case, separators and whitespace through retrieval. Duplicate history bridge must not send its canonical comparison key to the lower-history reader. HTTP form and URL encode raw model so separators/plus/ampersand survive as data. Native CDP reads raw text exactly and verifies corresponding request. Legacy upper-history exact rule unchanged. Comparison remains existing shared lookup_mpn_matches. Existing source validation still rejects invalid/empty model.

## verification
Offline raw-query transport/model-comparison regressions, prior B/L/notification/RFQ regression, full safe tests/Ruff/diff, BuildOnly/frozen/scan/idle and deployed protected manifest checks.

## completion
pending
