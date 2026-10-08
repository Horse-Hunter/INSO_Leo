# Task: V1.3 dashboard source-status counts

status: in_progress
owner: Codex
created: 2026-10-08
updated: 2026-10-08

## problem / goal
Owner reports 14 discovered/completed orders although these include quotation/history work. Replace visible counters with new orders, purchases awaiting quotation, and overdue purchases awaiting quotation, refreshed each normal 15-minute cycle.

## requirements
- New orders: exact source status 未发, including invalid rows still in that state.
- Awaiting quotation: all exact 发给采购 source rows, including held/unbound/historical rows.
- Overdue: subset uniquely bound to a local confirmed sending episode and strictly over three working hours, using existing working-time rules. Historical rows lacking timestamps are not guessed.
- Each normal cycle publishes an atomic cross-worksheet snapshot before processing; retain snapshot between cycles. No cumulative processed/completed totals displayed.
- Keep internal in_progress for countdown and all workflow safety semantics. Reuse existing source parsing, identity binding and episode store; statistics are read-only and send no notifications.
- Offline fake-only verification; no production reads/writes, purchase, SMTP, browser operations, running EXE replacement. Candidate packaging permitted; deployment remains a separate reviewed decision.

## acceptance
Pending: source counts/repeated cycles, worksheet mappings, held/ambiguous/history handling, working-time boundaries, atomic failed reads, GUI labels and countdown regressions; focused/full/Ruff/diff checks.
