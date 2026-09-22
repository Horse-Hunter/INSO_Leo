# Workflow Module

## Public responsibility

Workflow owns cross-module orchestration, scheduling, `inquiry_id`, process state, retry, duplicate prevention, and module handoffs. It consumes module public contracts and never embeds their internal business logic.

## V1 execution

- Trigger one Sheets pending-record poll every 15 minutes; only one poll may run at once.
- Decouple the poller from the Research worker; Research concurrency is `1`.
- Use Sheets-supplied `record_ref` / `record_identity` as opaque identity; never derive permanent identity from row number.
- Create and persist `inquiry_id` as `inq_<UUIDv4>` in local SQLite; do not write it to Google Sheets.
- States: `QUEUED`, `RESEARCHING`, `RETRY_WAIT`, `COMPLETED`, `MANUAL_REVIEW`, `FAILED`.
- Send Research the canonical input in `RESEARCH.md`, forwarding `importance_raw` unchanged.
- Map Research `SUCCESS` and qualifying `PARTIAL_SUCCESS` to `COMPLETED` only after Research confirms idempotent Excel persistence. Map `MANUAL_REVIEW_REQUIRED` to `MANUAL_REVIEW`; retry `RETRYABLE_FAILURE`.
- Pass `resolved_brand` to the confirmed Sheets Brand update. A Sheets Brand conflict does not undo completed Research.

## Retry and recovery

Default is one initial attempt plus three retries after 15, 30, and 60 minutes; exhaustion becomes `FAILED`. Do not use a fixed stale timeout. On restart, inspect inherited `RESEARCHING` work through a public Research completion capability before recovering completion or scheduling retry.

## Boundary and UNKNOWN

V1 orchestrates Sheets → Research → local Excel only; INSO and Quotation are future-version handoffs. Dependency direction is owned by `MODULE_INDEX.md`; Workflow never embeds collaborator adapters or business internals.

Still `UNKNOWN`: SQLite schema/migrations, duplicate-prevention algorithm, detailed transition guards, scheduling mechanism, Research completion-confirmation contract, and operational recovery mechanics.
