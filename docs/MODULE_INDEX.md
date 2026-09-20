# Module Index

This document defines module ownership and allowed dependency direction. A dependency includes direct imports, shared domain types, hidden filesystem coupling, and assumptions about another module's internal representation.

## Dependency summary

```text
workflow  -> research
          -> inso
          -> quotation

research  -> core
inso      -> core
quotation -> core
workflow  -> core
core      -> standard library / approved third-party libraries only
```

Cross-module calls should use explicit public contracts. No module may import another module's private implementation.

## `core`

- Responsibility: cross-cutting primitives and infrastructure-neutral utilities that are genuinely shared by multiple modules, such as common result/error contracts, configuration interfaces, logging interfaces, and time/identifier abstractions.
- Code path: `src/core/`
- Test path: `tests/core/`
- Allowed dependencies: language standard library and explicitly approved general-purpose third-party libraries.
- Forbidden dependencies: `research`, `inso`, `quotation`, `workflow`; business-specific rules; external-system workflows.

## `research`

- Responsibility: webpage research and collection of price evidence, including source metadata and evidence provenance. Actual crawling behavior is not yet implemented.
- Code path: `src/research/`
- Test path: `tests/research/`
- Allowed dependencies: `core`; explicitly approved research/network adapters when a future task authorizes them.
- Forbidden dependencies: `inso`, `quotation`, `workflow`; quotation decisions; INSO session or query logic.

## `inso`

- Responsibility: INSO system query, inquiry submission, and retrieval of INSO results. Authentication and live-system behavior are not yet implemented.
- Code path: `src/inso/`
- Test path: `tests/inso/`
- Allowed dependencies: `core`; explicitly approved INSO adapters when a future task authorizes them.
- Forbidden dependencies: `research`, `quotation`, `workflow`; quotation rules; direct ownership of web-research evidence.

## `quotation`

- Responsibility: quotation rules, quotation generation, and quotation result output. Actual pricing rules are not yet known or implemented.
- Code path: `src/quotation/`
- Test path: `tests/quotation/`
- Allowed dependencies: `core`; inputs supplied through explicit contracts.
- Forbidden dependencies: `research`, `inso`, `workflow`; direct network, browser, login, or external-system access.

## `workflow`

- Responsibility: orchestrate use cases across `research`, `inso`, and `quotation`; manage sequencing and pass data through public contracts.
- Code path: `src/workflow/`
- Test path: `tests/workflow/`
- Allowed dependencies: `core`, `research`, `inso`, `quotation` public interfaces.
- Forbidden dependencies: concrete business rules, price calculation logic, webpage parsing details, INSO protocol details, or direct external-system access.

## Boundary-change rule

Any change to ownership or dependency direction must update this document in the same task and explain the reason in the Task Packet. Shared code is not automatically `core`; promote it only after at least two modules need the same stable abstraction.
