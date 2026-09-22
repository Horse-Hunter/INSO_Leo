# Sheets Module

## Public contract

Sheets performs one Google Sheets operation per explicit Workflow call: read pending records or execute an explicitly requested safe field update. It returns structured records and opaque `record_ref` / `record_identity` values; it does not schedule or poll.

## V1 read

| Column | Meaning |
| --- | --- |
| A | status |
| C | raw importance |
| E | model / MPN |
| F | Brand |
| G | quantity |

A record is pending only when A is exactly `未发`. Workflow receives C unchanged as `importance_raw`.

## Identity and write

- Record identity combines worksheet identity, row position, and an identifying snapshot; row number alone is never permanent identity.
- Before a write, relocate and validate exactly one record. Ambiguous/missing identity returns conflict and writes nothing.
- V1 adds no stable Sheet ID column.
- Brand F may be written only while F is still empty. Re-read F immediately before writing; a human value returns conflict and is never overwritten.
- Every write is a targeted field update; never replace a full row to update one field.

The preferred integration is Google Sheets API with OAuth User Authorization. All live writes also follow `BOUNDARIES.md`.

## Boundary and UNKNOWN

Workflow owns the 15-minute trigger, global state, retry, and duplicate prevention. Dependency direction is owned by `MODULE_INDEX.md`.

Still `UNKNOWN`: spreadsheet/worksheet configuration, identifying-snapshot fields and relocation algorithm, OAuth token storage/scopes/consent/refresh details, and writable fields beyond Brand.
