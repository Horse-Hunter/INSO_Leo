# Workflow Module

## Purpose

Workflow owns cross-module orchestration. It coordinates module contracts and process state without taking ownership of each module's internal business logic.

## Confirmed responsibilities

- Run the scheduler every 15 minutes.
- Call Sheets to query the Google Sheet records currently marked as pending `未发` inquiries.
- Establish or identify an `inquiry_id`.
- Manage global process state, retry, and duplicate prevention.
- Decide the next action from module results and coordinate module handoffs.

## V1 scope

```text
Scheduler -> Sheets -> Research -> project-local `调研价格.xlsx`
```

V1 stops after the Research result is handled in the local Excel file. INSO, Quotation, final customer quotation, and final quotation write-back to Google Sheets belong to future versions. Their modules and long-term dependency relationships remain in the architecture.

Workflow interprets Research results as follows:

- `SUCCESS` and qualifying `PARTIAL_SUCCESS` become `COMPLETED` only after a successful write to `调研价格.xlsx`.
- `MANUAL_REVIEW_REQUIRED` is retained in the Excel file with a concise reason in `备注`; automatic progression stops for human handling.
- `RETRYABLE_FAILURE` does not produce a false normal price and remains eligible for Workflow-controlled retry.

## Boundaries and unknowns

- Workflow may depend on the public contracts of `core`, `sheets`, `research`, `inso`, and `quotation`.
- Workflow does not contain Google Sheets adapter details, web-research logic, INSO protocol logic, or quotation calculations.
- Inquiry ID generation, state-transition details, duplicate keys, retry count and interval, and failure handling for the local Excel write are `UNKNOWN`.
