# Current Task

Status: BLOCKED

Goal: Complete final bounded INSO discovery needed to prepare a minimal purchase writer. No persistent business action is authorized in this task.

Acceptance:
- [x] Synced `feature/v1-2` to `cf0ecc90098832cd59f4d1b5ca33dc8062bdcc58` before discovery.
- [x] Reused the explicitly identified, already logged-in Edge tab; no arbitrary tab/context selection.
- [x] Rechecked purchase form fields and read-only history identity; opened and closed a blank Add form and existing detail.
- [ ] Run one AI recognition using only the authorized synthetic input and record exact read-back fields/ready state. BLOCKED: AI dialog did not become visible.
- [x] Did not save, send, write Sheets, or send SMTP.
- [x] Recorded observed facts and unresolved UNKNOWNs in `docs/modules/INSO.md` without retaining customer/order row values.
- [x] No screenshot or evidence image was captured.

Constraints:
- Discovery only. No INSO business mutation, Save Data, Save-and-Send, SMTP, Sheets write, production database write, or production smoke.
- V1.1 Research rules and existing runtime behavior remain unchanged.
- Production writer gate remains closed. No credentials, customer/order values, authenticated URLs, raw page payloads, or screenshots are committed.

Done:
- The blank form maps `采购人员` to `#UserName_text` (backing `#UserName`) and `业务员` to `#OwnerID_text` (backing `#OwnerID`). `重要程度` uses `#ImpValueF`; no separate `询价类型` label was found and option semantics remain unverified.
- On one existing record, the detail `BillID` matched the numeric `Bill_View_Open(...)` argument; the `_Main` row id differed. A repeated open attempt timed out, so cross-open/query identity stability remains UNKNOWN.
- `#btnSave` showed `保存`; `#btnSave2` showed `保存并发送`; `#bcSend` is a send control in an existing record. None was activated.
- No AI recognition was run. `#ai_import_` did not leave `#winIframe_dialog1` visible during this attempt, so the authorized synthetic input and AI read-back remain unverified.
- `runtime/research.json` is absent and the code-default loopback CDP endpoint on port 9222 is unreachable. The selected Edge extension tab cannot supply the launcher `InsoSessionLease` context/page identity.
- No screenshot was taken; crop/redaction feasibility remains UNKNOWN.

Verification:
- Documentation-only change; `git diff --check` — passed.
- No automated runtime or live workflow was run.

Remaining / UNKNOWN:
- AI dialog and exact recognition-result/readiness selectors: live writer cannot safely compare recognized data before Save Data until this is verified.
- Live `InsoSessionLease` endpoint/browser/context/operation-page identity: live writer cannot safely establish page ownership until configured CDP access is available.
- Repeated stability of the observed history `BillID`/link mapping, inquiry-type option semantics, and new-draft status/time read-back.
- Safe screenshot crop/redaction.

No persistent INSO write, Save Data, Save-and-Send, Send, SMTP, or Sheets write occurred. Do not start a live purchase writer until the AI read-back and lease ownership blockers are resolved and separately reviewed.

Branch: `feature/v1-2`
V1.1 rollback baseline: `be9d0a51d0375884dfa3e5e9e4317958899fdc75`


Owner Lean-Safety Decision:
- Safety for V1.2 should be pragmatic and lightweight, not a separate over-engineered architecture project.
- Keep only the high-value, low-complexity protections as mandatory:
  1. No code/API/action path for `保存并发送`.
  2. Before any INSO write, require one exact intended control; zero/multiple/changed target -> stop.
  3. After an uncertain `保存数据` outcome, never auto-click Save Data again; require read-only confirmation or manual handling.
  4. Never persist/log SMTP authorization codes, cookies/tokens, or raw external exception text.
  5. Do not close a reused user browser or select an arbitrary first tab/context.
- SQLite safety should stay simple: create one verified consistent backup before the first V1.2 migration, keep migration additive, and avoid automatic destructive downgrade. Do not turn backup/recovery into a large subsystem.
- Safety Supervisor is a lightweight reviewer. It should focus on the five protections above and obvious regressions, not continuously add new gates, abstractions, or exhaustive threat-model requirements.
- Prefer simple exact selectors, explicit checks, and fail-closed behavior over elaborate frameworks. A recommendation is not a blocker unless it can realistically cause wrong-order mutation, duplicate Save Data, forbidden send, secret leakage, or breaking the accepted V1.1 runtime.
