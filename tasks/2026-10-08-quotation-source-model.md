# Task: Preserve exact source MPN in quote input with actual-model note and alert

status: in_progress
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
pending

## additional Owner read-only checks
After the input fix, inspect currency handling in all lower-history consumers and read-only source/INSO/local logs for RM342-059-581-7200 no-stock quote. Authorizes targeted read-only production diagnosis, not replay/update/SMTP. Preserve UNKNOWN until evidence is read.

## read-only diagnosis and necessary correction
Actual ERP evidence proves normalized separator-concatenated query misses a valid separated model. Correct only the three canonical INSO candidate queries using a shared initial literal token; retain full normalized Owner match, bounded verified pagination, date/currency/zero rules. No live update/replay/SMTP. Add separator retrieval regressions and re-run full validation/build.
