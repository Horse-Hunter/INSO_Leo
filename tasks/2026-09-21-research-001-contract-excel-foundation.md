# Task: RESEARCH-001 — Research Contract & Excel Output Foundation

status: complete
owner: Research Codex
created: 2026-09-21
updated: 2026-09-21

## problem

Research V1 now has an approved module boundary and canonical public contract, but the repository still contains only a documentation skeleton under `src/research/` and `tests/research/`. The canonical `ResearchInput`, `ResearchResult`, status values, and Excel idempotency/output guarantees are documented but not implemented.

## goal

Implement the smallest Research-owned foundation needed for later source adapters: public Research dataclass/Enum contracts plus a local Excel output primitive for `调研价格.xlsx` that is idempotent by hidden `_inquiry_id` and safe for retry/crash recovery.

Do not implement any real website adapter or market-research logic in this task.

## current_facts

- Python/runtime: Python 3.12.
- Research contracts use dataclass / Enum.
- Research Excel access uses openpyxl.
- Canonical `ResearchInput`: `inquiry_id`, `mpn`, optional `brand`, `quantity`.
- Canonical `ResearchResult`: `inquiry_id`, `status`, optional `resolved_brand`, optional `reason_code`, optional `remarks`; V1 has no `output_ref`.
- Allowed status semantics: `SUCCESS`, `PARTIAL_SUCCESS`, `MANUAL_REVIEW_REQUIRED`, `RETRYABLE_FAILURE`.
- `PARTIAL_SUCCESS` requires at least one valid website price, but price/source modeling is outside this task.
- `调研价格.xlsx` is Research V1's official persisted output.
- Hidden `_inquiry_id` is the Excel technical idempotency key.
- Retry/crash recovery must reuse/update the same inquiry record and must not append duplicate normal records.
- `SUCCESS` / `PARTIAL_SUCCESS` may only be returned after required Excel output succeeds.
- Excel write failure maps to `RETRYABLE_FAILURE`.
- `MANUAL_REVIEW_REQUIRED` may only be returned after its human-intervention reason is persisted in that record's `备注` field.
- `NO_MATCHING_PRODUCT` is a confirmed reason code; the broader reason-code catalog remains UNKNOWN.
- Excel business-column schema beyond hidden `_inquiry_id` and the confirmed `备注` requirement remains UNKNOWN.
- Research may depend on `core` but must not depend on `sheets`, `workflow`, `inso`, or `quotation`.
- Source website logic, evidence schema, price-item schema, and real credentials are outside this task.

Sources: `docs/PRODUCT_BASELINE.md`, `docs/modules/RESEARCH.md`, `docs/MODULE_INDEX.md`.

## scope

- Add Research V1 public contract types under `src/research/`.
- Add the four confirmed Research status Enum values.
- Add only currently confirmed reason-code values; do not invent a complete reason-code catalog.
- Implement a Research-owned Excel output foundation using openpyxl.
- Ensure the workbook can maintain a hidden `_inquiry_id` technical column.
- Implement idempotent upsert behavior keyed only by `inquiry_id`: retry/recovery updates or reuses the existing inquiry row and does not append a duplicate normal row.
- Support the confirmed visible `备注` field needed for manual-review persistence.
- Fail closed if a workbook already contains more than one row for the same non-empty `_inquiry_id`; do not guess which row is canonical.
- Surface Excel persistence failure through a Research-owned failure type / result-finalization path that can produce `RETRYABLE_FAILURE`.
- Add unit tests using temporary local workbooks only.
- Keep business-column extensibility minimal so later tasks can add confirmed Research columns without redesigning idempotency.

## non_scope

- No IC.net, Findchips, HQEW, LCSC, or Bom.Ai HTTP/browser/login implementation.
- No Playwright use.
- No live network access.
- No Credential Provider calls and no credential handling.
- No source Evidence contract implementation.
- No price-item model, price aggregation, FX, MPN matching, stock, MOQ, brand-resolution, 20% comparison, or website-failure aggregation logic.
- No Google Sheets access or dependency.
- No Workflow scheduler/state/retry implementation.
- No INSO or Quotation behavior.
- No SQLite.
- No changes to cross-module ownership or dependency directions.
- Do not define currently UNKNOWN Excel business columns merely to make the workbook look complete.
- Do not add `output_ref`.
- Do not add packaging/CI infrastructure unless strictly required to run the scoped tests.

## requirements

### Public contracts

- Use Python 3.12 dataclasses and Enum.
- `ResearchInput` fields:
  - `inquiry_id: str`
  - `mpn: str`
  - `brand: str | None`
  - `quantity: int`
- `ResearchResult` fields:
  - `inquiry_id: str`
  - `status: ResearchStatus`
  - `resolved_brand: str | None`
  - `reason_code: ResearchReasonCode | None`
  - `remarks: str | None`
- Do not silently add normalization/validation rules that remain UNKNOWN.

### Excel foundation

- Use openpyxl only.
- The workbook must contain a technical `_inquiry_id` column and keep that column hidden.
- The foundation must support the visible `备注` column because manual-review persistence is already confirmed.
- Do not freeze any other business-column schema in this task.
- Upsert is keyed by exact `inquiry_id`.
- Repeating an upsert for the same `inquiry_id` must reuse/update the existing row.
- A failed save must not be reported as success.
- Save behavior should preserve the previous usable workbook when a replacement write fails where reasonably achievable on Windows.
- If duplicate non-empty `_inquiry_id` rows already exist, raise a scoped Research Excel consistency error instead of selecting one.
- Never use row number as durable inquiry identity.

### Result/persistence consistency

- Provide a small Research-owned finalization/persistence helper sufficient to enforce:
  - successful required persistence before `SUCCESS` / `PARTIAL_SUCCESS` can be finalized;
  - manual-review reason persisted before `MANUAL_REVIEW_REQUIRED` can be finalized;
  - Excel persistence failure yields a `RETRYABLE_FAILURE` result with the original `inquiry_id`.
- This helper must not implement source aggregation or decide whether PARTIAL_SUCCESS has a valid website price; that precondition belongs to a later Research task.
- Do not leak low-level exception text into user-facing remarks by default.

### Safety and dependency boundaries

- Changes stay under `src/research/`, `tests/research/`, and this Task Packet unless a strictly necessary Research-local documentation update is identified.
- No import from `sheets`, `workflow`, `inso`, or `quotation`.
- No secrets, production data, or live external side effects.
- Tests must use temporary paths / generated local workbooks.

## acceptance

- [x] `ResearchInput`, `ResearchResult`, `ResearchStatus`, and the confirmed minimal `ResearchReasonCode` exist and match the documented V1 contract.
- [x] `ResearchResult` has no `output_ref`.
- [x] Excel output uses openpyxl and maintains hidden `_inquiry_id`.
- [x] Repeated upsert of the same `inquiry_id` does not create a second normal record.
- [x] Existing duplicate non-empty `_inquiry_id` rows fail closed.
- [x] `备注` can be written/updated for the same inquiry.
- [x] Excel write/save failure is represented as `RETRYABLE_FAILURE`, not success.
- [x] `MANUAL_REVIEW_REQUIRED` is finalized only after its manual-review reason is successfully persisted.
- [x] `SUCCESS` / `PARTIAL_SUCCESS` finalization requires successful Excel persistence.
- [x] Tests do not call live websites, Sheets, Workflow, INSO, Quotation, SQLite, Playwright, or Credential Provider.
- [x] No real website adapter or source-specific business logic is introduced.
- [x] Research code has no forbidden cross-module imports.

## verification

- Run the scoped Research unit tests with Python 3.12 / pytest.
- Run ruff on files changed by this task if ruff is available in the execution environment.
- Inspect the complete task diff.
- Confirm no forbidden module imports.
- Confirm no real URLs, credentials, selectors, or network/browser calls were added.
- Confirm temporary test workbooks are not committed.
- Record any environment limitation if pytest, ruff, or openpyxl is unavailable instead of pretending verification succeeded.

## completion

- status: complete
- changed: added canonical Research V1 dataclass/Enum contracts, Research-owned idempotent Excel output with hidden `_inquiry_id`, manual-review remarks persistence, atomic replacement save behavior, and result finalization that maps Excel persistence failure to `RETRYABLE_FAILURE`; added scoped unit tests
- verified: scoped pytest reproduction of the branch files passed 10 tests; reviewed the branch diff and confirmed no real website adapters, live URLs/credentials, forbidden cross-module imports, SQLite, Playwright, or network/browser calls were introduced
- limitations: ruff could not be executed in the available validation environment; Excel business columns beyond `_inquiry_id` and `备注`, source/evidence schemas, price aggregation, source adapters, PARTIAL_SUCCESS price-validity decision logic, and the broader reason-code catalog remain outside this task.
