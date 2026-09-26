# Current Task

Status: READY_FOR_CEO_REVIEW

Goal: Complete bounded, strictly read-only interactive discovery of the live INSO inquiry history and purchase form. No persistent business action is authorized.

Acceptance:
- [x] Synced `feature/v1-2` to `8c2a40eb58c2f0e57a600e81a4c9b827538cc290` before discovery.
- [x] Reused the explicitly identified, already logged-in Edge tab; no arbitrary tab/context selection.
- [x] Inspected exact/left-match history queries, opened and closed a blank Add form and AI dialog, and opened/closed one existing record detail read-only.
- [x] Did not run AI recognition, save, send, write Sheets, or send SMTP.
- [x] Recorded observed facts and unresolved UNKNOWNs in `docs/modules/INSO.md` without retaining customer/order row values.
- [x] No screenshot or evidence image was captured.

Constraints:
- Discovery only. No INSO business mutation, Save Data, Save-and-Send, SMTP, Sheets write, production database write, or production smoke.
- V1.1 Research rules and existing runtime behavior remain unchanged.
- Production writer gate remains closed. No credentials, customer/order values, authenticated URLs, raw page payloads, or screenshots are committed.

Done:
- The live app shell showed title `英索实业`; active embedded page was `1.业务询价` at the verified list path recorded in `docs/modules/INSO.md`.
- Exact-mode full-model test results matched the queried model; the prefix test returned no final rows in exact mode and matches in left-match mode. This supports strict matching for tested examples only.
- Result rows used unique numeric `_Main` ids in the observed set; numeric `Bill_View_Open(...)` arguments differed. Equal-timestamp tie behavior and stable identity remain UNKNOWN.
- The blank Add form opened without an observed immediate record creation. Form, AI dialog, Save and Save-and-Send control metadata are recorded in `docs/modules/INSO.md`; no fields were filled and no business write action was used.
- AI result values/readiness remain UNKNOWN because recognition was not run. An existing read-only detail exposed a populated `BillID` field and read-only `PENO`; linkage to a stable list identity and post-save read-back remain UNKNOWN.
- The selected existing browser tab showed top title `英索实业`, origin `https://yingsuo.alperp.cn`, and the inquiry list iframe identity. `InsoSessionLease` endpoint/browser/context identity was not verified.
- The live page contained unrelated business details. No screenshot was taken; crop/redaction feasibility remains UNKNOWN.

Verification:
- Documentation-only change; `git diff --check` — passed.
- No automated runtime or live workflow was run.

Remaining / UNKNOWN:
- Full exact-search semantics beyond the tested examples.
- Stable history identity, list/detail identity mapping, and equal-timestamp tie-break.
- Live `InsoSessionLease` endpoint/browser/context/page ownership verification.
- Intended inquiry-type and purchaser controls; AI recognition output/readiness.
- New saved-draft identity, status/time read-back; safe screenshot crop/redaction.

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
