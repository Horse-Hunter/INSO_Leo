# Task: Preserve exact source MPN in quote input with actual-model note and alert

status: completed
owner: Codex
created: 2026-10-08
updated: 2026-10-08

## authority / goal
Owner explicitly requires quotation-input B to equal the original Google source model exactly. If selected quotation model differs, append 报价实际型号：XXX to L, on a new line if existing remarks; send one reminder to 229 and shawn. Validate then package and overwrite formal V1.3.

## requirements / acceptance
- Fresh canonical source relocation/binding returns raw source model and status together. Preserve raw case/whitespace/punctuation; never use normalized lookup prefix or historical ledger model for B. Reject raw source-model changes between preparation and write/submit, no stale B.
- Keep immutable INSO raw14 quote evidence. Derive a separate fourteen-string input payload: B=source model; only if raw quote B differs, L=original remarks plus newline plus 报价实际型号： + original quote B. All other cells untouched. No extra row cleanup.
- Use existing durable notification outbox/worker/recipient retry behavior, no new SMTP system/schema. Alert 229 linan229@qq.com and shawn shawn@inso-hk.com once per inquiry/source-model/selected quotation identity; retries/restarts cannot duplicate. Exact raw-model equality produces no model-difference alert; ordinary error recipients unchanged. Alert says detected/prepared, not a claim of completed update.
- Preserve matched lookup policy, 72h/minimum supplier-net-price/zero fallback/raw14 capture, repeated-write/readback proofs, script popup retry/30-second state check/hold, procurement exact identity and second-send guards, background Chrome and scheduler.
- Offline tests only for business paths; no live procurement, Google writes/update/Apps Script, SMTP, replay or business poll. Authorized controlled deployment backs up current release and changes EXE/_internal assets only, protect V1.2/runtime DB/backups/config/OAuth/credentials/Chrome profile/CDP.

## verification
Focused update/integration/Google input/mail regressions; full safe tests/Ruff/diff; BuildOnly/frozen/release scan/idle GUI; deployed self-check/CDP/asset scan and protected inventory hashes.

## completion
- Production changes: source-model fix 726fc30; separator retrieval fix 9365917b0043bc3e3b139ff5b0654300f31b7e52.
- Focused: 378 passed. Full safe/offline: 1664 passed / 1 skipped (Windows symlink unavailable). Ruff and git diff --check PASS.
- Exact-source B / immutable raw14 / additive L remarks / inserted and already-exists / fresh-model race guards PASS; durable notification two-recipient independent retry and restart dedup PASS.
- Three canonical INSO consumers share literal initial candidate query, then unchanged full Owner fuzzy filter; separated MPN zero-USD/no-stock selection regression PASS. Read-only live comparison reproduces old empty vs original-model result and verifies corrected canonical quote reader selects the valid zero record. No live update or replay.
- Currency audit: Research INSO converts USD to RMB, supports RMB/USD; other history currencies are skipped. V1.3 comparison converts USD/HKD to RMB with shared FX, accepts RMB/CNY aliases; unsupported positive currency fails closed. Zero quotes require no FX. Google input retains source quote currency/price. Duplicate detection compares model/date/quantity, keeps original currency for informational price.
- BuildOnly / candidate frozen self-check / idle GUI / release scan PASS. Final deployed frozen / idle / CDP / scan PASS; business threads not started by validation.
- Formal path: D:\Program_Leo\INSO_Leo\dist\INSO_V1.3
- EXE SHA256: 8E4E060797C3C730B2A7E12111A8646C1E3F2D725DB7DEDC4135BFF0629A0760
- Complete timestamped backup: D:\Program_Leo\INSO_Leo\dist\release-backups\INSO_V1.3_20261008_195650_fd66fc09
- All 2179 deployed release assets match candidate manifest; all 3953 protected hashes unchanged. Runtime DB / backups / V1.2 / OAuth / credentials / configs / fixed Chrome profile preserved. Fixed CDP connected, unique context, one page.
- V1.2 before/after SHA256: 340D7F7E7E818FA74DE36B138B205F5905F320406FD8D391EF860BD052529E5F
- Existing formal GUI stopped through its normal graceful close handler before asset-only replacement. No forced process kill. No purchase, Save-and-Send, Google quote input write/update, Apps Script, SMTP test or historical replay performed by this task.
- Local evidence only: D:\Program_Leo\INSO_Leo\.tmp\v13-deploy-20261008_195650_fd66fc09. Raw production quote/customer data not committed. No remote push for this task.
- Remaining limitation: non-RMB/USD Research INSO currencies are not converted; no unsupported exchange rates invented. Apps Script internal currency transformation is UNKNOWN; this change preserves its existing original-currency input contract.

## additional Owner read-only checks
After the input fix, inspect currency handling in all lower-history consumers and read-only source/INSO/local logs for RM342-059-581-7200 no-stock quote. Authorizes targeted read-only production diagnosis, not replay/update/SMTP. Preserve UNKNOWN until evidence is read.

## read-only diagnosis and necessary correction
Actual ERP evidence proves normalized separator-concatenated query misses a valid separated model. Correct only the three canonical INSO candidate queries using a shared initial literal token; retain full normalized Owner match, bounded verified pagination, date/currency/zero rules. No live update/replay/SMTP. Add separator retrieval regressions and re-run full validation/build.
