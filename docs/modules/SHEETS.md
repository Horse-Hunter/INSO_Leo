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
- an identifying snapshot containing the observed A/C/E/F/G values.

Sheets exposes this composite identity through its public `record_ref` / `record_identity` contract; Workflow treats that reference as opaque. A row number alone is not a permanent identity. Before any write, Sheets must relocate and validate the record. If the record cannot be identified uniquely, the operation fails closed and returns a conflict; it must not guess a target row. V1 does not add a stable Sheet ID column.

For Brand writes, F does not participate in relocation disambiguation. Relocation requires exactly one current worksheet row matching the observed A/C/E/G values. Zero or multiple candidates produce a conflict and fail closed. After the record is uniquely located, Sheets independently checks the current F value.

## V1 write contract

- Brand in column F may be written only while F is still empty.
- Immediately before writing Brand, Sheets must re-read F.
- If a human has already populated F, Sheets must not overwrite it and must return a conflict.
- Brand writes use a targeted `values.update` for one F cell. Updating one field must never overwrite an entire row.
- Other V1 writable fields, if any, are `UNKNOWN`.

## Workflow boundary and product path

Workflow owns the scheduler and calls Sheets once every 15 minutes. Sheets does not poll by itself. Sheets returns the records currently pending under the V1 criterion, and Workflow decides the next action.

The current V1 path is:

```text
Google Sheet -> Workflow -> Research -> project-local `调研价格.xlsx`
```

INSO, Quotation, the final customer quotation, and final quotation write-back to Google Sheets belong to future versions.

## Integration approach and dependencies

- The Google Sheets API reader and OAuth User Authorization helpers are implemented.
- Read authorization uses only `https://www.googleapis.com/auth/spreadsheets.readonly`.
- Write authorization uses only `https://www.googleapis.com/auth/spreadsheets`.
- Sheets does not request a Google Drive scope.
- Current OAuth helpers do not persist tokens.
- Read-only runtime configuration is selected explicitly by
  `INSO_SHEETS_READ_CONFIG_FILE` and loaded from a local JSON file containing
  the OAuth client-secret file path, spreadsheet ID, and complete ordered
  worksheet-title list. Missing, malformed, blank, duplicate, or unexpected
  configuration fails closed.
- `*.local.json` runtime configuration is Git ignored. Production identities,
  OAuth client files, tokens, and Sheet contents remain local runtime data.
- Live reading of worksheet 2026 has been validated.
- Live Brand writing has not been validated because no safe production candidate was available. This is an operational validation limitation, not a V1 implementation blocker.
- Allowed dependency: `core` and explicitly approved Google Sheets adapters.
- Forbidden dependencies: `research`, `inso`, `quotation`, and `workflow`.

## Remaining UNKNOWN

- Long-term OAuth token persistence, consent, and refresh behavior.
- Whether V1 production will require more than one spreadsheet per runtime.
- Google API atomic compare-and-set or transaction capability across precondition reads and writes.
- Writable fields beyond Brand in column F.
