# Task: V1.3 dashboard source-status counts

status: complete
review_status: REVIEWED_DONE
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
- [x] Counts come from source rows rather than processed/discovered history.
- [x] Repeat polls replace counts; manual processing and old internal counters do not alter the snapshot.
- [x] Cross-worksheet sum uses canonical status mapping, including SHAHAB.
- [x] Held/unbound/history rows remain in awaiting count; timeout requires unique canonical identity and local episode.
- [x] Exact three-hour boundary is not overdue; nights/weekends/lunch excluded by existing working-time policy; new sending episode resets timer.
- [x] Read-only count collection leaves DB and notification ledger unchanged; partial failed reads do not publish incomplete totals.
- [x] New GUI labels display supplied source totals; internal in_progress/countdown semantics retained.
- [x] Focused/full/Ruff/diff checks and frozen packaging/idle GUI verification passed.

## completion / CEO report
- Production code commit: `91299e1dafaa14d8f449beae8191b4901e098bd3`.
- Changed: src/workflow/dashboard_counts.py (source snapshot projection), src/workflow/purchase_follow_up.py (shared overdue predicate), src/launcher/backend.py (per-normal-poll refresh), src/gui/contracts.py (additive DTO fields), src/gui/app.py (three replacement labels), associated workflow/GUI tests.
- Root cause: old `_poll_inquiries` combined purchase and quotation work, so quotation/history inquiries were displayed as newly discovered orders.
- Counts are published atomically before normal cycle processing and retained until the next normal cycle. New orders are all exact 未发 rows, even invalid pending inputs; awaiting includes all exact 发给采购 rows; overdue is a subset of awaiting, not a separate disjoint category.
- Missing local timestamp / ambiguous binding: excluded only from overdue count, never fabricated. Future timestamps cannot produce a timeout.
- Before the first successful snapshot, labels show `--`, rather than pretending a query returned zero.
- Focused: **262 passed**.
- Full safe/offline: **1571 passed / 1 skipped** (existing Windows symlink capability skip).
- Ruff / git diff --check: PASS.
- V1.3 BuildOnly / release scan / frozen self-check / isolated frozen idle GUI: PASS.
- Candidate EXE SHA256: `DB11A02BCB4929EA9B45A973AD086A163D4FE1ED09AF72ED9AB0C222A8819E5E`.
- Approved deployed EXE remains `4777E6000A861EC4E1C881CD9692E18B8B21FB8A1F6672DD82DF2115E5D6E6CC`, unchanged. No deployment or running process replacement performed.
- No production Sheets reads/writes, browser sessions, purchases, quotation updates, SMTP deliveries or historical replay. All feature validation used synthetic source rows and isolated local ledgers.
- No new dependencies, workflow scheduler, CDP path, cooldown, alert system or identity mechanism. Existing email recipient/once-per-sending policies remain unchanged.
- Evidence: main repository `.tmp/v13-dashboard-build.log` and `.tmp/v13-dashboard-frozen-report.json`, not tracked.
- Review status: REVIEW_REQUIRED; no new CEO approval claimed. Deployment awaits independent review of this increment.


---

# CEO Independent Review — 2026-10-08

**Status:** COMPLETE  
**Verdict:** PASS / REVIEWED_DONE  
**Reviewed branch HEAD:** `e4f877b77c674652ea53debe41ee22634119a99f`  
**Reviewed production-code commit:** `91299e1dafaa14d8f449beae8191b4901e098bd3`  
**Reviewed base:** `4c53c2c1159c7abca36cebf061223b5bbe07e3fb`

## Decision

PASS. No production blocker was found in this GUI/source-count increment.

The change fixes the reported dashboard semantic error without changing purchase, quotation, scheduler, browser/CDP, notification, identity, hold, cooldown or submission behavior.

## Source-count semantics

PASS.

The three visible counters now mean:

- **新订单**: every source row whose canonical worksheet status is exactly `未发`, including rows whose business fields are invalid;
- **采购未报价**: every source row whose canonical status is exactly `发给采购`, including held, unresolved and historical rows;
- **采购超时未报价**: only the uniquely canonical-bound subset of `发给采购` rows that has a local confirmed sending episode and is strictly beyond the existing three-working-hour rule.

The count path reuses the canonical worksheet schemas, pending/quotation status parsers, V1.3 identity relocation and the already-reviewed purchase-follow-up episode store. It does not infer an overdue timestamp for historical, ambiguous or source-changed rows.

The exact three-hour boundary remains non-overdue; lunch, night and weekend exclusions use the same shared predicate as the reminder workflow. A newer confirmed sending episode resets the visible overdue timer in the same way it resets reminder timing.

## Poll projection / atomicity

PASS.

A normal poll:

1. resets only the old per-cycle processed projection;
2. reads all configured worksheet source rows;
3. computes the complete cross-worksheet dashboard snapshot;
4. publishes the snapshot only after the entire count read succeeds;
5. then enters the existing combined business cycle.

A later worksheet-read failure cannot publish partial totals. The prior successful snapshot remains intact until a subsequent successful normal poll.

The counters are not cumulative and are not changed by `_seen()`, manual reruns, Research history, quotation-history processing or notification delivery.

Before the first successful snapshot in a newly started run, the GUI displays `--`.

## Read-only / safety boundary

PASS.

The new count projection does not:

- write Google Sheets;
- create or recover workflow events/alerts;
- create notifications;
- mutate quotation holds;
- create purchase-follow-up episodes;
- alter source status;
- drive CDP/Research/INSO operations.

Existing internal `orders_found`, `completed`, `in_progress` and `pending` fields remain in the backend contract for workflow/countdown behavior; only their old misleading GUI presentation was replaced.

The additional Sheets read remains under the existing shared Google Sheets fault boundary. A failed source read does not produce a fabricated zero/partial dashboard snapshot.

## Worksheet / identity coverage

PASS.

The reviewed tests cover canonical cross-worksheet status mapping, including SHAHAB, duplicate worksheet entries, invalid pending rows, unbound quotation rows, ambiguous bindings, durable quotation holds, row movement and new sending episodes.

Overdue remains a subset of the current exact `发给采购` source population; rows already changed to `采购已报价`, `成交` or another status do not remain in the visible waiting count.

## Regression evidence

Executor reports for this increment:

- focused: **262 passed**;
- full safe/offline: **1571 passed / 1 skipped**;
- Ruff: **PASS**;
- `git diff --check`: **PASS**;
- V1.3 BuildOnly: **PASS**;
- release scan: **PASS**;
- frozen self-check: **PASS**;
- isolated frozen idle GUI: **PASS**.

Candidate EXE SHA256:

`DB11A02BCB4929EA9B45A973AD086A163D4FE1ED09AF72ED9AB0C222A8819E5E`

The currently deployed reviewed production EXE remains:

`4777E6000A861EC4E1C881CD9692E18B8B21FB8A1F6672DD82DF2115E5D6E6CC`

and was not replaced by this increment before review.

## Release decision

**APPROVED FOR CONTROLLED DEPLOYMENT.**

The `DB11A02B...` candidate may replace the current formal V1.3 release after taking a fresh backup and preserving V1.2, production workflow DB, OAuth/credentials/configuration and fixed Chrome/CDP assets.

No additional live purchase, quotation update, Apps Script or SMTP test is required merely to deploy this display/count correction.

## Final state

`REVIEW_REQUIRED -> REVIEWED_DONE`
