# Sheets Module

## Purpose

Sheets is the Google Sheets external-integration boundary. It performs one operation per explicit Workflow call and returns structured results through public contracts.

## V1 read contract

| Column | Confirmed meaning |
| --- | --- |
| A | Status |
| C | Raw importance level |
| E | Model / MPN |
| F | Brand |
| G | Quantity |

A record is pending in V1 when column A is exactly `未发`.

## Record identity and safe relocation

A V1 record is identified by the combination of:

- worksheet identity;
- row position;
- an identifying snapshot.

Sheets exposes this composite identity through its public `record_ref` / `record_identity` contract; Workflow treats that reference as opaque. A row number alone is not a permanent identity. Before any write, Sheets must relocate and validate the record. If the record cannot be identified uniquely, the operation fails closed and returns a conflict; it must not guess a target row. V1 does not add a stable Sheet ID column.

The exact fields included in the identifying snapshot and the matching algorithm are `UNKNOWN`.

## V1 write contract

- Brand in column F may be written only while F is still empty.
- Immediately before writing Brand, Sheets must re-read F.
- If a human has already populated F, Sheets must not overwrite it and must return a conflict.
- Every write is a targeted field update. Updating one field must never overwrite an entire row.
- Other V1 writable fields, if any, are `UNKNOWN`.

## Workflow boundary and product path

Workflow owns the scheduler and calls Sheets once every 15 minutes. Sheets does not poll by itself. Sheets returns the records currently pending under the V1 criterion, and Workflow decides the next action.

The current V1 path is:

```text
Google Sheet -> Workflow -> Research -> project-local `调研价格.xlsx`
```

INSO, Quotation, the final customer quotation, and final quotation write-back to Google Sheets belong to future versions.

## Integration approach and dependencies

- Preferred V1 integration: Google Sheets API with OAuth User Authorization.
- Allowed dependency: `core` and explicitly approved Google Sheets adapters.
- Forbidden dependencies: `research`, `inso`, `quotation`, and `workflow`.
- Spreadsheet/worksheet configuration, OAuth token storage, OAuth scopes, consent and refresh behavior, identifying-snapshot fields, relocation/matching algorithm, and other writable fields remain `UNKNOWN` until an implementation Task.
