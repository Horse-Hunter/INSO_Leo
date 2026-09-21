# Module Index

This document defines module ownership and allowed dependency direction. A dependency includes direct imports, shared domain types, hidden filesystem coupling, and assumptions about another module's internal representation.

## Dependency summary

```text
workflow  -> sheets
          -> research
          -> inso
          -> quotation
          -> core

sheets    -> core
research  -> core
inso      -> core
quotation -> core
core      -> standard library / approved third-party libraries only
```

Cross-module calls should use explicit public contracts. No module may import another module's private implementation.

## `core`

- Responsibility: cross-cutting primitives and shared infrastructure capabilities, such as common result/error contracts, configuration and logging interfaces, time/identifier abstractions, and the Credential Provider boundary.
- Code path: `src/core/`
- Test path: `tests/core/`
- Allowed dependencies: language standard library and explicitly approved general-purpose third-party libraries.
- Forbidden dependencies: `sheets`, `research`, `workflow`, `inso`, `quotation`; business-specific rules; external-system workflows.

## `sheets`

- Responsibility: perform one Google Sheet operation per explicit call: read a sheet, query pending records, read specified fields, preserve raw record location, and safely update specified fields after an explicit update command. Own the Google Sheets API/adapter boundary.
- Code path: `src/sheets/`
- Test path: `tests/sheets/`
- Allowed dependencies: `core`; explicitly approved Google Sheets adapters when a future implementation task authorizes them.
- Forbidden dependencies: `research`, `inso`, `quotation`, `workflow`; schedulers or polling loops; global state machines; global retry or duplicate prevention; domain business rules.

## `research`

- Responsibility: accept a `ResearchInput`, perform read-only web market research, and return a `ResearchResult` with price evidence, source metadata, and provenance. Research V1 currently outputs results to a local Excel file.
- Code path: `src/research/`
- Test path: `tests/research/`
- Allowed dependencies: `core`, including the Credential Provider capability for authorized Bom.Ai login; explicitly approved research/network and local Excel output adapters.
- Forbidden dependencies: `sheets`, `workflow`, `inso`, `quotation`; Google Sheet access; quotation decisions; INSO session or query logic.

## `workflow`

- Responsibility: own global process orchestration, scheduling, `inquiry_id` and global state, retry, duplicate prevention, and module handoffs. The scheduler invokes `sheets` every 15 minutes, receives the current pending records, and decides the next action.
- Code path: `src/workflow/`
- Test path: `tests/workflow/`
- Allowed dependencies: `core`, `sheets`, `research`, `inso`, and `quotation` public interfaces.
- Forbidden dependencies: concrete module business rules, price calculation logic, webpage parsing details, Google Sheets adapter details, INSO protocol details, or direct external-system access.

## `inso`

- Responsibility: INSO system query, inquiry submission, and retrieval of INSO results. Authentication and live-system behavior are not yet implemented.
- Code path: `src/inso/`
- Test path: `tests/inso/`
- Allowed dependencies: `core`; explicitly approved INSO adapters when a future task authorizes them.
- Forbidden dependencies: `sheets`, `research`, `quotation`, `workflow`; quotation rules; direct ownership of web-research evidence.

## `quotation`

- Responsibility: quotation rules, quotation generation, and quotation result output. Actual pricing rules are not yet known or implemented.
- Code path: `src/quotation/`
- Test path: `tests/quotation/`
- Allowed dependencies: `core`; inputs supplied through explicit contracts.
- Forbidden dependencies: `sheets`, `research`, `inso`, `workflow`; direct network, browser, login, or external-system access.

## Boundary-change rule

Any change to ownership or dependency direction must update this document in the same task and explain the reason in the Task Packet. Shared code is not automatically `core`; promote it only after at least two modules need the same stable abstraction.
