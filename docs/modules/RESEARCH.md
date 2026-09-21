# Research Module

## Purpose and contract

Research accepts a `ResearchInput`, performs read-only web market research, produces the required project-local Excel output, and returns a `ResearchResult`. It owns market-source interaction, price-evidence collection, source metadata, evidence provenance, and its Excel output behavior.

V1 `ResearchInput` contains:

- `inquiry_id`;
- model / MPN;
- brand;
- quantity.

`importance_raw` is not passed to Research. Research returns `resolved_brand` to Workflow when it resolves a Brand value. Remaining detailed `ResearchResult` fields are `UNKNOWN`.

## Confirmed sources

- IC.net
- Findchips
- 华强电子网
- LCSC / 立创商城
- Bom.Ai

Bom.Ai requires login. Research may request an authorized login using a stable `site_id` through the project Credential Provider. Research must not know or reproduce DPAPI, vault-file, or PowerShell storage details, and it must never log or persist a live secret.

## Excel output and result consistency

Research V1 saves its result to the project-local `调研价格.xlsx`; it does not write directly to Google Sheets.

- Excel output must be idempotent by `inquiry_id`.
- Research may return `SUCCESS` only after the required Excel output succeeds.
- Research may return `PARTIAL_SUCCESS` only when at least one valid price exists and the required Excel output succeeds.
- An Excel write failure returns `RETRYABLE_FAILURE`; it must not be reported as a successful result.
- Excel schema, workbook update mechanics, and the detailed idempotency implementation are `UNKNOWN`.

Local Excel output remains part of Research V1. A separate Excel or storage module should be considered only after multiple modules demonstrate a stable shared requirement.

## Boundaries

- Allowed dependency: `core`, including the Credential Provider capability, plus explicitly approved web and local Excel adapters.
- Forbidden dependencies: `sheets`, `workflow`, `inso`, and `quotation`.
- Research does not access Google Sheets, orchestrate the global workflow, perform INSO actions, or calculate quotations.
- Access is read-only and limited to the confirmed sources. It does not authorize arbitrary sites, customer messaging, external writes other than the required local Excel output, or production-data modification.
- Selectors, XPath, session mechanics, and other volatile website details belong in future implementation tasks, not this durable document.
