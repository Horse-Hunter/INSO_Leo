# Research Module

## Purpose and contract

Research accepts a `ResearchInput`, performs read-only web market research, produces the required project-local Excel output, and returns a `ResearchResult`. It owns market-source interaction, price-evidence collection, source metadata, evidence provenance, and its Excel output behavior.

### ResearchInput V1

- `inquiry_id`
- `mpn`
- optional `brand`
- `quantity`
- `importance_raw`

`importance_raw` originates from Google Sheet column C. Sheets reads the raw value, Workflow forwards it unchanged, and Research uses it only for display in `调研价格.xlsx`: exact `A` or `B` displays as `重要`; every other value displays as `普通`.

`importance_raw` must not affect website selection, research order, pricing algorithms, prices, MPN handling, evidence, Research status, retry, `NO_MATCHING_PRODUCT`, or any other Research behavior. Future INSO order-importance behavior belongs to a future version and must not implicitly reuse this display rule.

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

Bom.Ai price records are valid for one month. If one or more valid prices exist within the most recent 7 days, Bom.Ai contributes the lowest valid 7-day price. If no valid 7-day price exists but one or more valid prices exist within one month, it contributes the lowest valid one-month price. Prices older than one month are not valid Bom.Ai price candidates.

## Excel output and result consistency

The project-local `调研价格.xlsx` is the official persisted output of Research V1. It uses a hidden `_inquiry_id` field as the technical idempotency key.

- Retry or crash recovery must not create duplicate normal records for the same `inquiry_id`.
- Research may return `SUCCESS` only after the required Excel output succeeds.
- Research may return `PARTIAL_SUCCESS` only when at least one valid price exists and the required Excel output succeeds.
- An Excel write failure returns `RETRYABLE_FAILURE`; it must not be reported as a successful result.
- The visible `重要等级` and `备注` columns are confirmed. Other business-column schema, workbook update/locking mechanics, and detailed idempotency implementation remain `UNKNOWN`.

Local Excel output remains part of Research V1. A separate Excel or storage module should be considered only after multiple modules demonstrate a stable shared requirement.

## NO_MATCHING_PRODUCT

Return `MANUAL_REVIEW_REQUIRED` with `reason_code = NO_MATCHING_PRODUCT` only when all four price sources—Findchips, HQEW, LCSC, and Bom.Ai—were queried successfully and none returned a strict MPN match.

- A technical failure must not be counted as “no match.”
- If Bom.Ai finds a strict MPN match, the result must not be classified as `NO_MATCHING_PRODUCT`, even when the price is older than two months, unavailable, or absent.
- Product existence and price validity are separate decisions.
- User-facing remarks wording and the broader reason-code catalog remain `UNKNOWN`.

## Boundaries

- Allowed dependency: `core`, including the Credential Provider capability, plus explicitly approved web and local Excel adapters.
- Forbidden dependencies: `sheets`, `workflow`, `inso`, and `quotation`.
- Research does not access Google Sheets, orchestrate the global workflow, perform INSO actions, or calculate quotations.
- Access is read-only and limited to the confirmed sources. It does not authorize arbitrary sites, customer messaging, external writes other than the required local Excel output, or production-data modification.
- Selectors, XPath, session mechanics, and other volatile website details belong in future implementation tasks, not this durable document.
