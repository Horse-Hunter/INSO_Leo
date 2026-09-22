# Product Baseline

This file owns product scope and durable cross-module business rules only. Module rules belong in `docs/modules/`; safety in `BOUNDARIES.md`; dependencies in `MODULE_INDEX.md`; implementation status comes from Git `main`, the current Task, and Module Final Reports.

## Product goal

- Project: `INSO_Leo`.
- The confirmed V1 outcome is a repeatable inquiry-to-market-research flow.
- Broader business goal, primary users, and measurable outcome: `UNKNOWN`.

## Current V1 user flow

```text
Workflow scheduler (every 15 minutes)
-> Sheets reads Google Sheet records with status “未发”
-> Workflow creates or recognizes an inquiry
-> Research performs market research
-> Research persists the result in local `调研价格.xlsx`
```

## V1 includes

- Google Sheet pending-record reads and the confirmed safe Brand update path.
- Workflow identity/state, duplicate prevention, retry, and Sheets → Research orchestration.
- Research across the five confirmed sources and Research-owned Excel output.
- `SUCCESS` or qualifying `PARTIAL_SUCCESS` becomes Workflow `COMPLETED` only after required inquiry-idempotent Excel persistence succeeds.
- `MANUAL_REVIEW_REQUIRED` stops automation for human handling; `RETRYABLE_FAILURE` does not create a false normal price and follows Workflow retry.
- Sheet column-C `importance_raw` passes through Workflow unchanged and affects only Research’s Excel display; it does not change research behavior or define future INSO importance.
- Research may return `resolved_brand`; a safe Sheets Brand conflict does not undo completed Research.

Detailed Sheets, Research, and Workflow contracts are owned by their module docs.

## V1 does not include

- INSO behavior, Quotation, a final customer quotation, or final quotation write-back to Google Sheets.
- A shared Excel/storage module.
- Redis, Celery, Kafka, Docker, or a large Workflow engine.

`inso` and `quotation` remain registered future-version modules.

## Future scope and product UNKNOWN

- INSO system definition, access, inquiry behavior, and results.
- Quotation formulas, rounding, margins, approvals, validity, output, and recipients.
- Product/service coverage, markets, taxes, locales, customer-data classification, retention, audit, and regulatory obligations.
- V1 production operating model and success metrics beyond the confirmed flow.

Unknowns that affect only one module stay in that module’s Task or module doc, not here.
