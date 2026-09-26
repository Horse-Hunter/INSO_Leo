# Current Task

Status: PRE_SAVE_READY / REAL_SAVE_GATED

Goal: Verify AI-to-parent-form import where safe, add explicit fail-closed production composition, and prepare the durable-before-dispatch Save Data path without enabling production writes.

Acceptance:
- [x] Cherry-picked WorkBuddy duplicate reader `fafc6b7f3101ff0c69c1872a9f094e2148398903`.
- [x] On two separate blank forms, selected `需要问全价格` and `普通询价` and read back the exact value from `#ImpValueF`; both forms were closed without saving.
- [x] Ran AI recognition with the authorized synthetic input and one public generic component. Confirmed the ready state and result inputs; no parent-form import/save was triggered.
- [x] Added exact quotation routing to `#ImpValueF`, verified by deterministic fake tests; only the two approved values are allowed.
- [x] Added a live AI result reader for the observed ready state and result fields.
- [x] Verified history result table mapping for model, quantity, and time; query settlement remains fail-closed pending a reliable completion seam.
- [x] On a blank inquiry form, one authorized public-component AI recognition completed; `重新识别` became ready and the result row read `LM358 / Texas Instruments / 123`.
- [x] The embedded AI panel's footer control was `保存数据`, not a verified non-persistent import action. It was not clicked; parent-form import/read-back remains UNKNOWN.
- [x] Added a gated `#btnSave` path requiring unique, visible, enabled, exact `保存` semantics and durable `begin_save_dispatch()` before the private dispatch boundary. Production gate remains closed; no real click occurred.
- [x] Added explicit launcher composition for the coordinator, duplicate checker, purchase writer, notification worker/transport and recipients. Missing live adapters leave V1.2 uncomposed; no fake is substituted.
- [x] Connected launcher reconciliation to the existing read-only store contract. Without a verified live record reader it returns UNKNOWN and moves the item to manual review.
- [x] No Save Data, Save-and-Send, Send, SMTP, Sheets write, production migration, or screenshot file/evidence was saved.

Constraints:
- No INSO Save Data, Save-and-Send, Send, SMTP, Sheets write, production DB migration, or production smoke.
- V1.1 Research rules and existing runtime behavior remain unchanged.
- Production writer gate remains closed. No credentials, real customer/order values, authenticated URLs, raw page payloads, or screenshots are committed.

Done:
- The blank form maps `采购人员` to `#UserName_text` / `#UserName`, and `业务员` to `#OwnerID_text` / `#OwnerID`.
- Business `quotation_type` now maps to the confirmed `重要程度` input `#ImpValueF`; exact allowlist is `需要问全价格` and `普通询价`. Both values were selected and read back on separate blank forms.
- On one existing record, the detail `BillID` matched the numeric `Bill_View_Open(...)` argument; the `_Main` row id differed. A repeated open attempt timed out, so cross-open/query identity stability remains UNKNOWN.
- `#btnSave` showed `保存`; `#btnSave2` showed `保存并发送`; `#bcSend` is a send control in an existing record. None was activated.
- `TEST-MPN-001      TEST-BRAND      123` produced an alert and no result. A public generic component input `LM358      Texas Instruments      123` produced a result and `重新识别` state.
- AI result read-back is `#preview-body > tr` with `input[data-f="PartNo"]`, `input[data-f="Brand"]`, and `input[data-f="Qty"]`; ready is `button#ai-recognize` text `重新识别`. The writer reader requires one row, unique fields, and a positive integer quantity.
- The AI page became visible inside the blank form after opening `AI录单`. Recognition reached `重新识别` and returned the public test values. Its footer button was `保存数据`; because that was not verified as a non-persistent import action, it was left untouched and the parent detail row remained blank.
- `InsoDuplicateHistoryReader` and `InsoDuplicateHistoryChecker` are integrated with the existing Workflow `DuplicateChecker` seam. Latest equal timestamps remain AMBIGUOUS. The live list headers map model/quantity/time to row cell indexes 8/10/13 (CSS `td:nth-child(9/11/14)`) under `#_id_dg`.
- A synthetic exact query returned an empty result with visible `.layui-table-none`, zero visible rows, and zero count. A general nonempty-query settled signal is not yet proven; no live row extractor or settled callback is enabled.
- `src/inso/purchase_writer.py` maps exact route values to `#ImpValueF`, reads verified AI result controls, and contains one durable-before-dispatch `#btnSave` path behind the closed production gate. It has no Save-and-Send or Send method/path.
- `ProductionBackend` can compose V1.2 only with an explicit complete live adapter bundle; this checkout has no coordinator-compatible live purchase `prepare` adapter (`InsoPurchaseWriter` still lacks the verified parent-import step), settled duplicate reader, or canonical research-facts provider, so the production V1.2 flow remains disabled. V1.1 poller/worker behavior is unchanged.
- Lease/CDP identity is deferred to runtime acceptance before the first real Save, per CEO direction; it is not a current coding blocker.
- No screenshot evidence was saved; crop/redaction feasibility remains UNKNOWN.

Verification:
- `ruff check src tests` — passed.
- Deterministic INSO, Workflow, and Launcher tests — 221 passed, 1 skipped.
- `git diff --check` — passed.
- Current blank-form screenshot was viewed only to inspect the AI panel; it was not saved as evidence or committed.
- Live discovery used only the authorized synthetic/public component inputs and a synthetic exact history query. No Save or Send action occurred.

Remaining / UNKNOWN:
- Parent-form AI import/read-back. The visible footer says `保存数据`; its non-persistent transfer behavior is UNKNOWN and it was not clicked.
- Whether purchaser selection updates `#UserName` for the exact selected display text; the adapter refuses to proceed if the backing ID remains empty.
- New saved-draft identity/status/time read-back and repeated stability of history `BillID`/link identity.
- Final local-CDP endpoint/browser/context/operation-page runtime acceptance before the first real Save.
- Confirmed nonempty duplicate-query settled signal and injected live row-value extractor. Read failures continue to fail closed.
- Safe screenshot crop/redaction.

No persistent INSO write, Save Data, Save-and-Send, Send, SMTP, or Sheets write occurred. Keep the production Save gate closed until parent-form AI propagation, read-only saved-record reconciliation, and the required local-CDP runtime acceptance are verified and Owner authorizes the first real Save.

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
- CEO performs the daily Safety Review, focused on the five protections above and obvious regressions.
- Prefer simple exact selectors, explicit checks, and fail-closed behavior over elaborate frameworks. A recommendation is not a blocker unless it can realistically cause wrong-order mutation, duplicate Save Data, forbidden send, secret leakage, or breaking the accepted V1.1 runtime.
