# Workflow Module

## Purpose

Workflow owns cross-module orchestration. It coordinates module contracts and process state without taking ownership of each module's internal business logic.

## Scheduler and execution model

- Run the Sheet poller every 15 minutes.
- Keep the 15-minute Sheet poller decoupled from the Research worker.
- Allow only one Sheet poll at a time.
- Run Research with concurrency `1`.
- Use the `record_ref` / `record_identity` supplied by Sheets; never derive a permanent identity from row number alone.

## State and identity

- Persist Workflow state in a local SQLite runtime database. The runtime database must not enter Git.
- Workflow creates and persists each `inquiry_id` in the form `inq_<UUIDv4>`. It does not write `inquiry_id` to Google Sheets.
- V1 states are `QUEUED`, `RESEARCHING`, `RETRY_WAIT`, `COMPLETED`, `MANUAL_REVIEW`, and `FAILED`.

## Retry and restart recovery

- Default retry policy: one initial attempt plus three retries after 15, 30, and 60 minutes.
- When retries are exhausted, transition the Inquiry to `FAILED`.
- Do not use a fixed stale timeout for inherited `RESEARCHING` work.
- On restart, for each inherited `RESEARCHING` Inquiry, first use a public Research capability to determine whether the required output already completed; then recover the completed result or schedule retry as appropriate.

## V1 orchestration

```text
Google Sheet -> Workflow -> Research -> project-local `调研价格.xlsx`
```

Workflow sends the canonical V1 `ResearchInput`: `inquiry_id`, `mpn`, optional `brand`, and `quantity`; it does not pass `importance_raw`. Workflow consumes the canonical `ResearchResult`: `inquiry_id`, `status`, optional `resolved_brand`, optional `reason_code`, and optional `remarks`. V1 has no `output_ref`.

Workflow may pass `resolved_brand` to Sheets for the confirmed Brand update. A Sheets Brand conflict does not undo an already completed Research result or change that Inquiry from `COMPLETED`.

Workflow interprets Research results as follows:

- `SUCCESS` and qualifying `PARTIAL_SUCCESS` become `COMPLETED` only after Research has successfully produced the required inquiry-idempotent Excel output.
- `PARTIAL_SUCCESS` must contain at least one valid price.
- `MANUAL_REVIEW_REQUIRED` maps to `MANUAL_REVIEW`; automatic progression stops for human handling.
- `RETRYABLE_FAILURE`, including an Excel write failure, follows the Workflow retry policy.

INSO, Quotation, the final customer quotation, and final quotation write-back to Google Sheets belong to future versions. Their modules and long-term dependency relationships remain in the architecture.

## Boundaries and unknowns

- Workflow may depend on the public contracts of `core`, `sheets`, `research`, `inso`, and `quotation`.
- Workflow does not contain Google Sheets adapter details, web-research logic, Excel-writing logic, INSO protocol logic, or quotation calculations.
- SQLite schema and migrations, duplicate-prevention key/algorithm, detailed state-transition guards, Research completion-confirmation contract, scheduling mechanism, and operational recovery details remain `UNKNOWN` until implementation tasks.
