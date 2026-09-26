# Current Task

Status: BLOCKED

Goal: Confirm AI/type controls and implement the minimum purchase-preparation path up to, but not including, Save Data.

Acceptance:
- [x] Synced `feature/v1-2` to `5199ab3f8040378f9da0da8297a7df105423952c` before work.
- [x] Reused the explicitly identified, already logged-in Edge tab; no arbitrary tab/context selection.
- [x] Directly opened the known AI page in an independent tab, entered only the authorized synthetic string, and clicked AI recognition once.
- [ ] Confirm recognized model/brand/quantity and ready selector. BLOCKED: the AI page showed no result and did not enter the `重新识别` state.
- [x] Searched blank-form text, inputs, hidden fields, selects, and popup for inquiry-type labels/options.
- [x] Implemented the closed-gate save-before adapter with exact observed selectors; Save Data and Send have no writer path.
- [x] Did not Save, Send, write Sheets, or send SMTP.
- [x] Recorded findings and remaining UNKNOWNs in `docs/modules/INSO.md` without retaining real customer/order values.
- [x] No screenshot or evidence image was captured.

Constraints:
- No INSO Save Data, Save-and-Send, Send, SMTP, Sheets write, production DB migration, or production smoke.
- V1.1 Research rules and existing runtime behavior remain unchanged.
- Production writer gate remains closed. No credentials, real customer/order values, authenticated URLs, raw page payloads, or screenshots are committed.

Done:
- The blank form maps `采购人员` to `#UserName_text` / `#UserName`, and `业务员` to `#OwnerID_text` / `#OwnerID`.
- No separate `询价类型` field was found. `#ImpValueF` is labeled `重要程度`; its associated popup contains exact options `需要问全价格` and `普通询价`. The writer does not operate this field or infer it is the inquiry type.
- On one existing record, the detail `BillID` matched the numeric `Bill_View_Open(...)` argument; the `_Main` row id differed. A repeated open attempt timed out, so cross-open/query identity stability remains UNKNOWN.
- `#btnSave` showed `保存`; `#btnSave2` showed `保存并发送`; `#bcSend` is a send control in an existing record. None was activated.
- One synthetic recognition attempt used `TEST-MPN-001      TEST-BRAND      123` on `/skins/etaoerp/product/Import_ai.aspx`. `#ai-recognize` did not produce result fields or the `重新识别` state; no retry was made.
- `src/inso/purchase_writer.py` adds exact-selector new-draft, customer, purchaser, importance, direct AI-page, input, recognition, and result-reader seams. The default production gate is closed. The writer exposes no Save or Send method and registers no Save selector. Inquiry type and AI result reading fail closed.
- Lease/CDP identity is deferred to runtime acceptance before the first real Save, per CEO direction; it is not a current coding blocker.
- No screenshot was taken; crop/redaction feasibility remains UNKNOWN.

Verification:
- Python syntax parse and `git diff --check` — passed.
- `ruff` is unavailable in the bundled Python environment; automated tests were not run.
- Live discovery used only the exact synthetic AI input. No Save or Send action occurred.

Remaining / UNKNOWN:
- AI recognition result selectors/values and deterministic ready state. The current writer result reader fails closed until a selector is verified.
- Whether purchaser selection updates `#UserName` for the exact selected display text; the adapter refuses to proceed if the backing ID remains empty.
- New saved-draft identity/status/time read-back and repeated stability of history `BillID`/link identity.
- Final local-CDP endpoint/browser/context/operation-page runtime acceptance before the first real Save.
- Safe screenshot crop/redaction.

No persistent INSO write, Save Data, Save-and-Send, Send, SMTP, or Sheets write occurred. Do not enable Save Data until AI read-back and post-save reconciliation selectors are verified and the required local-CDP runtime acceptance passes.

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
