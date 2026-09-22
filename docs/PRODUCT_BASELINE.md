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
- `RETRYABLE_FAILURE`: do not generate a false normal price. Workflow applies its default retry policy: one initial attempt plus retries after 15, 30, and 60 minutes; exhaustion transitions to `FAILED`.

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

## Workflow V1 architecture

- Workflow persists state in a local SQLite runtime database; the runtime database must not enter Git.
- Workflow creates and persists `inquiry_id` as `inq_<UUIDv4>` and does not write it to Google Sheets.
- The 15-minute Sheet poller and Research worker are decoupled. Only one Sheet poll may run at a time, and Research concurrency is `1`.
- V1 states are `QUEUED`, `RESEARCHING`, `RETRY_WAIT`, `COMPLETED`, `MANUAL_REVIEW`, and `FAILED`.
- Default retry is one initial attempt plus three retries after 15, 30, and 60 minutes. Exhaustion transitions the Inquiry to `FAILED`.
- Workflow does not use a fixed stale timeout. After restart, inherited `RESEARCHING` work is checked through a public Research capability to confirm whether output completed before Workflow chooses recovery or retry.
- Research Excel output must be idempotent by `inquiry_id`. `SUCCESS` and `PARTIAL_SUCCESS` may be returned only after the required Excel output succeeds; an Excel write failure is `RETRYABLE_FAILURE`.
- `PARTIAL_SUCCESS` requires at least one valid price.
- V1 `ResearchInput` contains `inquiry_id`, `mpn` / model, optional `brand`, `quantity`, and `importance_raw`. Sheets reads column C raw, Workflow forwards it unchanged, and Research uses it only to display exact A/B as `重要` and all other values as `普通` in `调研价格.xlsx`; it must not influence Research behavior, and future INSO importance must not implicitly reuse this display rule.
- Research returns `resolved_brand` to Workflow for the Sheets Brand update. A Brand conflict does not undo completed Research or change the Inquiry from `COMPLETED`.
- Workflow uses the `record_ref` / `record_identity` supplied by Sheets and never treats row number alone as a permanent identity.

## Research V1

- Canonical `ResearchInput`: `inquiry_id`, `mpn` / model, optional `brand`, `quantity`, and `importance_raw`.
- Canonical `ResearchResult`: `inquiry_id`, `status`, optional `resolved_brand`, optional `reason_code`, and optional `remarks`. V1 does not include `output_ref`.
- Allowed Research statuses: `SUCCESS`, `PARTIAL_SUCCESS`, `MANUAL_REVIEW_REQUIRED`, and `RETRYABLE_FAILURE`.
- Confirmed sources: IC.net, Findchips, 华强电子网 / HQEW, LCSC / 立创商城, and Bom.Ai.
- Bom.Ai requires login and may obtain authorized credentials through the project Credential Provider.
- Bom.Ai price validity is one calendar month: use the same wall-clock time in
  the previous month, clamped to that month's final day. If valid prices exist
  within the most recent 7 days, use the lowest valid 7-day price; otherwise,
  use the lowest valid calendar-month price. Older prices are not valid.
- Research uses ECB daily reference rates as the live USD/RMB source. It derives
  CNY per USD through same-date USD/EUR and CNY/EUR observations using exact
  decimal arithmetic. There is no fallback FX rate or hidden rounding.
- The temporary HQEW operating policy is non-blocking: when its safety challenge
  makes the source unavailable but another price source supplies a valid
  candidate, Research writes the available result and returns
  `PARTIAL_SUCCESS` without waiting for human intervention.
- The Research market reference is the lowest normalized RMB price. It adds a
  newline and the second-lowest price plus source only when the lowest is at
  least 20% lower (`lowest <= second * 0.80`). Estimated total is lowest unit
  price times quantity using exact decimal arithmetic.
- Research uses `importance_raw` only for the V1 Excel `重要等级` display: exact `A` / `B` -> `重要`; every other value -> `普通`. This display rule must not affect market research behavior and must not be treated as the future INSO importance rule.
- Research does not access Google Sheets and does not depend on `sheets`, `workflow`, `inso`, or `quotation`.
- The project-local `调研价格.xlsx` is the official persisted Research V1 output.
  Its visible columns, in order, are `型号`, `品牌`, `数量`, `重要等级`,
  `货量标识`, `预计订单总价`, `市场最低参考价`, and `备注`. Its hidden
  `_inquiry_id` field is the technical idempotency key; retry or crash recovery
  must not create duplicate normal records.
- `SUCCESS` and `PARTIAL_SUCCESS` may be returned only after the required Excel output succeeds. `PARTIAL_SUCCESS` also requires at least one valid price. Excel write failure returns `RETRYABLE_FAILURE`.
- `NO_MATCHING_PRODUCT` maps to `MANUAL_REVIEW_REQUIRED` and is valid only when Findchips, HQEW, LCSC, and Bom.Ai all query successfully and none has a strict MPN match. Technical failure is not “no match”; a strict Bom.Ai match is not `NO_MATCHING_PRODUCT` even when pricing is older than two months, unavailable, or absent. Product existence and price validity are distinct.
- Do not create a separate Excel/storage module unless later evidence shows a stable shared need across modules.

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
- Detailed source-quality rules beyond the confirmed strict-MPN, quantity-tier,
  time-window, and source-specific price rules: `UNKNOWN`
- INSO system definition, ownership, endpoints, and access method: `UNKNOWN`
- Inquiry fields beyond the confirmed ID, Research input, and V1 state set; detailed transition guards and failure semantics: `UNKNOWN`
- Quotation formulas, rounding, margins, approvals, and validity periods: `UNKNOWN`
- Quotation output formats and recipients: `UNKNOWN`
- Workflow implementation details not confirmed above, including SQLite schema/migrations, duplicate-prevention key/algorithm, detailed state-transition guards, scheduling mechanism, Research completion-confirmation contract, and operational recovery details: `UNKNOWN`
- Google Sheet spreadsheet/worksheet configuration, identifying-snapshot fields, record-relocation matching algorithm, OAuth details, and writable fields beyond the confirmed Brand rule: `UNKNOWN`
- Research input normalization/validation rules beyond the confirmed `importance_raw` display mapping, price-item schema, status-specific field requirements, and reason-code catalog beyond confirmed cases: `UNKNOWN`
- Research workbook layout beyond the confirmed columns, concurrent locking
  mechanics, display precision, and retention policy: `UNKNOWN`

## Data and compliance

- Data classification: `UNKNOWN`
- Personal or customer data involved: `UNKNOWN`
- Retention and deletion requirements: `UNKNOWN`
- Audit requirements: `UNKNOWN`
- Regulatory or contractual constraints: `UNKNOWN`

## Technical baseline

- Deployment: single-machine Windows.
- Language/runtime: Python 3.12.
- Tests: pytest.
- Lint/format baseline: ruff.
- Workflow state: SQLite through Python `sqlite3`; runtime database files must not enter Git.
- Research Excel access: openpyxl.
- Sheets integration: Google Sheets API with OAuth User Authorization.
- Web access: prefer ordinary HTTP; use Playwright for websites that require JavaScript or login.
- Credentials: use the existing project Credential Provider; do not embed secrets in code or configuration committed to Git.
- V1 does not introduce Redis, Celery, Kafka, Docker, or a large Workflow Engine.
- Packaging, dependency pinning, CI/CD, observability, OAuth token/scope/refresh details, browser-version management, and deployment automation: `UNKNOWN`.

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
