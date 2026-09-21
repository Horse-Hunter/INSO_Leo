# Research Module

## Purpose and contract

Research accepts a `ResearchInput`, performs read-only web market research, produces the required project-local Excel output, and returns a `ResearchResult`. It owns market-source interaction, price-evidence collection, source metadata, evidence provenance, and its Excel output behavior.

### ResearchInput V1

- `inquiry_id`
- `mpn`
- optional `brand`
- `quantity`

`importance_raw` is not passed to Research.

### ResearchResult V1

- `inquiry_id`
- `status`
- optional `resolved_brand`
- optional `reason_code`
- optional `remarks`

V1 `ResearchResult` does not contain `output_ref`. Allowed `status` values are:

- `SUCCESS`
- `PARTIAL_SUCCESS`
- `MANUAL_REVIEW_REQUIRED`
- `RETRYABLE_FAILURE`

Research returns `resolved_brand` to Workflow when it resolves a Brand value. Detailed price-item schema, validation rules, and reason-code catalog beyond confirmed cases remain `UNKNOWN`.

## Confirmed sources

- IC.net
- Findchips
- 华强电子网 (HQEW)
- LCSC / 立创商城
- Bom.Ai

Bom.Ai requires login. Research may request an authorized login using a stable `site_id` through the project Credential Provider. Research must not know or reproduce DPAPI, vault-file, or PowerShell storage details, and it must never log or persist a live secret.

## Excel output and result consistency

The project-local `调研价格.xlsx` is the official persisted output of Research V1. It uses a hidden `_inquiry_id` field as the technical idempotency key.

- Retry or crash recovery must not create duplicate normal records for the same `inquiry_id`.
- Research may return `SUCCESS` only after the required Excel output succeeds.
- Research may return `PARTIAL_SUCCESS` only when at least one valid price exists and the required Excel output succeeds.
- An Excel write failure returns `RETRYABLE_FAILURE`; it must not be reported as a successful result.
- Business-column schema, workbook update/locking mechanics, and the detailed idempotency implementation remain `UNKNOWN`.

Local Excel output remains part of Research V1. A separate Excel or storage module should be considered only after multiple modules demonstrate a stable shared requirement.

## NO_MATCHING_PRODUCT

`NO_MATCHING_PRODUCT` is valid only when all four price sources—Findchips, HQEW, LCSC, and Bom.Ai—were queried successfully and none returned a strict MPN match.

- A technical failure must not be counted as “no match.”
- If Bom.Ai finds a strict matching model but its price is expired or unavailable, the result must not be classified as `NO_MATCHING_PRODUCT`.
- The mapping from this reason code to user-facing remarks and any broader reason-code catalog remain `UNKNOWN`.

## Boundaries

- Allowed dependency: `core`, including the Credential Provider capability, plus explicitly approved web and local Excel adapters.
- Forbidden dependencies: `sheets`, `workflow`, `inso`, and `quotation`.
- Research does not access Google Sheets, orchestrate the global workflow, perform INSO actions, or calculate quotations.
- Access is read-only and limited to the confirmed sources. It does not authorize arbitrary sites, customer messaging, external writes other than the required local Excel output, or production-data modification.
- Selectors, XPath, session mechanics, and other volatile website details belong in future implementation tasks, not this durable document.
