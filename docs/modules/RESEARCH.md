# Research Module

## Purpose and contract

Research accepts a `ResearchInput`, performs read-only web market research, and returns a `ResearchResult`. It owns market-source interaction, price-evidence collection, source metadata, and evidence provenance.

The detailed field schemas for `ResearchInput` and `ResearchResult` are `UNKNOWN`.

## Confirmed sources

- IC.net
- Findchips
- 华强电子网
- LCSC / 立创商城
- Bom.Ai

Bom.Ai requires login. Research may request an authorized login using a stable `site_id` through the project Credential Provider. Research must not know or reproduce DPAPI, vault-file, or PowerShell storage details, and it must never log or persist a live secret.

## Output

Research V1 currently saves its result to a local Excel file; it does not write directly to Google Sheets. The Excel schema, naming, and retention policy are `UNKNOWN`.

Local Excel output remains part of Research V1. A separate Excel or storage module should be considered only after multiple modules demonstrate a stable shared requirement.

## Boundaries

- Allowed dependency: `core`, including the Credential Provider capability, plus explicitly approved web and local Excel adapters.
- Forbidden dependencies: `sheets`, `workflow`, `inso`, and `quotation`.
- Research does not access Google Sheets, orchestrate the global workflow, perform INSO actions, or calculate quotations.
- Access is read-only and limited to the confirmed sources. It does not authorize arbitrary sites, customer messaging, external writes, or production-data modification.
- Selectors, XPath, session mechanics, and other volatile website details belong in future implementation tasks, not this durable document.
