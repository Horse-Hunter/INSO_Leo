# Current Task

Status: READY_FOR_CEO_REVIEW

Goal: Complete bounded, strictly read-only discovery of the live INSO business inquiry page without opening forms or performing business actions.

Acceptance:
- [x] Synced `feature/v1-2` to `9a156ba2406bde10132a451837cc300c50fce2b8` before discovery.
- [x] Reused the explicitly identified, already logged-in browser tab; no arbitrary tab/context selection.
- [x] Read the INSO page identity, business inquiry history list/query controls, and current result-row identity shape.
- [x] Did not click `新增`, submit a query, open or execute AI entry, save, send, write Sheets, or send SMTP.
- [x] Recorded observed facts and unresolved UNKNOWNs in `docs/modules/INSO.md` without retaining customer/order row values.
- [x] No screenshot or evidence image was captured.

Constraints:
- Discovery only. No INSO mutation, Save Data, Save-and-Send, SMTP, Sheets write, production database write, or production smoke.
- V1.1 Research rules and existing runtime behavior remain unchanged.
- Production writer gate remains closed. No credentials, customer/order values, authenticated URLs, raw page payloads, or screenshots are committed.

Done:
- The live app shell showed title `英索实业`; active embedded page was `1.业务询价` at the verified list path recorded in `docs/modules/INSO.md`.
- The list exposes one visible `新增` button and a model search field, query button, `左匹配` and `精确` options. No query was run; exact-match backend behavior remains unverified.
- Visible list rows have unique numeric `_Main` DOM ids within the current table, but the row id differs from the detail-link argument. Stable persisted history identity is not established.
- The purchase form was not opened. Purchase controls, AI results, Save Data target, and saved-record read-back were not inspected and remain UNKNOWN.
- The current page contains unrelated business details. Full-page screenshot was unsafe; no screenshot was taken, and crop/redaction feasibility remains UNKNOWN.
- The read-only browser inspection used the selected existing user tab; the application `InsoSessionLease` identity metadata was not available through that browser-control path. No new child page was opened.

Verification:
- Documentation-only change; `git diff --check` — passed.
- No automated runtime or live workflow was run.

Remaining / UNKNOWN:
- Whether exact search performs strict server-side model equality.
- Stable history record ID and deterministic timestamp tie-break.
- Live account/company and lease-level browser/context/page identity verification.
- Purchase-form metadata, AI recognition read-back fields, and saved draft identity/read-back.
- Safe repeatable evidence crop/redaction.

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
