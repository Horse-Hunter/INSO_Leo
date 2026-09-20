# Product Baseline

This document contains durable, evidence-backed product facts. Unknown facts remain explicitly marked `UNKNOWN`. Task-specific assumptions belong in a Task Packet, not here.

## Product purpose

- Product name: `UNKNOWN`
- Primary user groups: `UNKNOWN`
- Business problem: `UNKNOWN`
- Expected business outcome: `UNKNOWN`

## Confirmed system shape

- The project has five logical modules: `core`, `research`, `inso`, `quotation`, and `workflow`.
- `research` concerns webpage research and price-evidence collection.
- `inso` concerns INSO queries, inquiry actions, and result retrieval.
- `quotation` concerns quotation rules, generation, and output.
- `workflow` coordinates the three domain modules and does not own their concrete business behavior.
- This initial task provides architecture, collaboration rules, and module skeletons only.

## Business facts

- Supported products or services: `UNKNOWN`
- Markets, currencies, taxes, and locales: `UNKNOWN`
- Price evidence requirements and source-quality rules: `UNKNOWN`
- INSO system definition, ownership, endpoints, and access method: `UNKNOWN`
- Inquiry inputs, outputs, state transitions, and failure semantics: `UNKNOWN`
- Quotation formulas, rounding, margins, approvals, and validity periods: `UNKNOWN`
- Quotation output formats and recipients: `UNKNOWN`
- Workflow triggers, ordering, retries, and human-review points: `UNKNOWN`

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
- Authentication and secret-management approach: `UNKNOWN`
- Observability requirements: `UNKNOWN`
- CI/CD platform and release process: `UNKNOWN`
- Test, lint, formatting, and type-check toolchain: `UNKNOWN`

## Current safety constraints

- Do not implement webpage crawling or scraping.
- Do not log in to or call the INSO system.
- Do not implement quotation algorithms or infer missing pricing rules.
- Do not connect to production systems.
- Do not install dependencies without a concrete, reviewed need.
- Do not store secrets or sensitive live data in the repository.

## Updating this baseline

For each new fact, record a concise statement and its source or decision reference. If sources conflict, keep the item `UNKNOWN` and describe the conflict until an authorized decision resolves it.
