# Sheets Module

## Purpose

Sheets is the Google Sheets external-integration boundary. It performs one operation per explicit caller request and returns structured results through public contracts.

## Responsibilities

- Read a Google Sheet once per call.
- Query the records currently considered pending.
- Read specified fields.
- Preserve enough raw Sheet record location to identify the source row or record safely.
- After an explicit update command, safely update only the specified fields.
- Own the Google Sheets API and adapter boundary.

## Workflow boundary

Workflow owns the scheduler and calls Sheets every 15 minutes. Sheets returns the current pending records; Workflow owns the decision about what happens next.

Sheets does not own a polling loop, Research or INSO behavior, quotation calculations, global workflow state, global retry, or duplicate prevention.

## Dependencies and unknowns

- Allowed dependency: `core` and explicitly approved Google Sheets adapters.
- Forbidden dependencies: `research`, `inso`, `quotation`, and `workflow`.
- Google Sheet identity, worksheet selection, column mappings, pending-record criteria, writable fields, and record-location contract: `UNKNOWN`.
- Authentication details and API implementation are outside this architecture-baseline task.
