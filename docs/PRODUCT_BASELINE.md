# Product Baseline

This document contains durable, evidence-backed product facts. Unknown facts remain explicitly marked `UNKNOWN`. Task-specific assumptions belong in a Task Packet, not here.

## Product purpose

- Product name: `UNKNOWN`
- Primary user groups: `UNKNOWN`
- Business problem: `UNKNOWN`
- Expected business outcome: `UNKNOWN`

## Confirmed system shape

- The project has six logical modules: `core`, `sheets`, `research`, `workflow`, `inso`, and `quotation`.
- `sheets` is the Google Sheets external-integration boundary for one-shot reads, pending-record queries, specified-field reads, raw record location, and explicitly commanded safe field updates.
- `research` concerns webpage research and price-evidence collection.
- `inso` concerns INSO queries, inquiry actions, and result retrieval.
- `quotation` concerns quotation rules, generation, and output.
- `workflow` owns global orchestration, scheduling, `inquiry_id` and global state, retry, duplicate prevention, and module handoffs; it does not own concrete module business behavior.
- Every 15 minutes, the Workflow scheduler calls `sheets` once; `sheets` returns the current pending records, and Workflow decides the next action. Sheets does not run its own polling loop.

## V1 product scope

V1 implements only this path:

```text
Workflow scheduler (every 15 minutes)
-> Sheets queries Google Sheet records whose inquiry status is "未发"
-> Workflow establishes or identifies the inquiry
-> Research performs market research
-> Research results are written to the project-local `调研价格.xlsx`
```

V1 does not implement INSO, Quotation, the final customer quotation, or writing a final quotation back to Google Sheets. The `inso` and `quotation` modules remain part of the long-term architecture and dependency graph, but their business behavior belongs to a future version.

### ResearchResult handling in V1

- `SUCCESS`: write the result to `调研价格.xlsx`. After the write succeeds, the Inquiry is `COMPLETED` in V1.
- `PARTIAL_SUCCESS`: when at least one valid website price exists, write the available result to `调研价格.xlsx`. After the write succeeds, the Inquiry is `COMPLETED` in V1.
- `MANUAL_REVIEW_REQUIRED`: retain or write the record to `调研价格.xlsx`, put a concise reason for human intervention in that record's `备注` column, stop automatic progression, and wait for human handling. It is not treated as `COMPLETED` by the current V1 definition.
- `RETRYABLE_FAILURE`: do not generate a false normal price. Workflow owns subsequent retry; retry count and interval are `UNKNOWN`.

For V1, `COMPLETED` therefore means that a `SUCCESS` result, or a `PARTIAL_SUCCESS` result containing at least one valid website price, has been successfully written to `调研价格.xlsx`.

## Sheets V1 contract

- Confirmed column mapping: A = status; C = raw importance level; E = model / MPN; F = brand; G = quantity.
- A record is pending when column A is exactly `未发`.
- Workflow calls Sheets once every 15 minutes; Sheets does not poll by itself.
- Record identity is the combination of worksheet identity, row position, and an identifying snapshot. Row number alone is not a permanent identity.
- Before any write, Sheets must relocate and validate the record. If it cannot identify exactly one matching record, it fails closed and returns a conflict rather than guessing.
- V1 does not add a stable Sheet ID column.
- Brand may be written to column F only when F remains empty immediately before the write. Sheets must re-read F; if a human has populated it, Sheets returns a conflict and does not overwrite it.
- Every write must be a targeted field update; updating one field must not overwrite an entire row.
- The preferred V1 integration is Google Sheets API with OAuth User Authorization.
- Spreadsheet/worksheet configuration, identifying-snapshot fields, relocation and matching details, OAuth token storage, OAuth scopes, consent/refresh behavior, and any writable fields beyond the confirmed Brand rule remain `UNKNOWN` for implementation tasks.

## Research V1

- Contract shape: `ResearchInput` -> read-only web market research -> `ResearchResult`.
- Confirmed sources: IC.net, Findchips, 华强电子网, LCSC / 立创商城, and Bom.Ai.
- Bom.Ai requires login and may obtain authorized credentials through the project Credential Provider.
- Research does not access Google Sheets and does not depend on `sheets`, `workflow`, `inso`, or `quotation`.
- Research results currently output to a local Excel file rather than directly to Google Sheets.
- Local Excel output remains part of Research V1. Do not create a separate Excel/storage module unless later evidence shows a stable shared need across modules.

## Credential Provider

- The project has a local Windows Credential Provider backed by Windows DPAPI CurrentUser encryption.
- The local vault is stored outside the repository at `%LOCALAPPDATA%\INSO_Leo\credential-vault.json`.
- Business modules depend only on the Credential Provider capability, not DPAPI, the JSON path, or PowerShell implementation details.
- A stable `site_id` identifies a site's login; the current PowerShell interface is `Get-InsoVaultLogin -SiteId <id>`.
- PowerShell 7 and Windows PowerShell 5.1 have been tested.
- The vault is for one local Windows user and does not support cross-computer synchronization or multi-user sharing.
- Real usernames, passwords, tokens, cookies, secrets, vault data, and secret-bearing examples must never enter the repository, Task Packets, logs, fixtures, or examples.
- Credential Provider is infrastructure capability, not a separate business module.

## Business facts

- Supported products or services: `UNKNOWN`
- Markets, currencies, taxes, and locales: `UNKNOWN`
- Detailed price-evidence acceptance and source-quality rules: `UNKNOWN`
- INSO system definition, ownership, endpoints, and access method: `UNKNOWN`
- Inquiry inputs, outputs, state transitions, and failure semantics: `UNKNOWN`
- Quotation formulas, rounding, margins, approvals, and validity periods: `UNKNOWN`
- Quotation output formats and recipients: `UNKNOWN`
- Workflow ordering, retry policies, duplicate keys, state transitions, and human-review points beyond the confirmed 15-minute Sheet check: `UNKNOWN`
- Google Sheet spreadsheet/worksheet configuration, identifying-snapshot fields, record-relocation matching algorithm, OAuth details, and writable fields beyond the confirmed Brand rule: `UNKNOWN`
- `ResearchInput` and `ResearchResult` field schemas: `UNKNOWN`
- Local Research Excel schema, filename policy, and retention: `UNKNOWN`

## Data and compliance

- Data classification: `UNKNOWN`
- Personal or customer data involved: `UNKNOWN`
- Retention and deletion requirements: `UNKNOWN`
- Audit requirements: `UNKNOWN`
- Regulatory or contractual constraints: `UNKNOWN`

## Technical baseline

- Programming language and version: `UNKNOWN`
- Runtime and deployment target: `UNKNOWN`
- Persistence technology: `UNKNOWN`
- Authentication and secret-management approach outside the confirmed local Credential Provider: `UNKNOWN`
- Observability requirements: `UNKNOWN`
- CI/CD platform and release process: `UNKNOWN`
- Test, lint, formatting, and type-check toolchain: `UNKNOWN`

## Current safety constraints

- Research V1 may perform read-only market research against IC.net, Findchips, 华强电子网, LCSC / 立创商城, and Bom.Ai only.
- Bom.Ai access may use authorized login credentials obtained through the project Credential Provider.
- This Research authorization does not permit arbitrary website access, unauthorized writes, customer messaging, INSO actions, production-data modification, or storing secrets in the repository.
- Do not log in to or call the INSO system.
- Do not implement quotation algorithms or infer missing pricing rules.
- Do not connect to production systems except for the explicitly authorized read-only Research V1 source access above.
- Do not install dependencies without a concrete, reviewed need.
- Do not store secrets or sensitive live data in the repository.

## Updating this baseline

For each new fact, record a concise statement and its source or decision reference. If sources conflict, keep the item `UNKNOWN` and describe the conflict until an authorized decision resolves it.
