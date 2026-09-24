# Research

Research V1 implementation. Public contract and durable rules: `docs/modules/RESEARCH.md`. Run module tests from Repo root with `python -m pytest tests/research`.

## Production runtime composition

`src/research/runtime.py` builds the single `ResearchService` consumed by the Workflow V1 live smoke from an explicit, Git-ignored, non-secret local configuration file (default `runtime/research.json`). The schema is documented in that module's docstring. Run the read-only readiness check from the Repo root with:

```text
py -3.12 -m src.research.runtime --config runtime/research.json
```

The command exits `0` only when every prerequisite is ready; otherwise it prints the exact missing credential `site_id` and the single Owner action. Readiness reports `site_id` and safe failure class names only, never a credential value.

Credentials are retrieved exclusively through the canonical Core Provider (`src.core`); Research never calls PowerShell, DPAPI, a vault path, or a second credential store. Bom.Ai and INSO URLs and selectors are runtime configuration, not durable contract.

`icnet.mode` selects the IC.net read-only acquisition path:

- `credentials` (default) logs in with the Core Provider login in a freshly launched browser.
- `cdp` reads through the Owner-authorized ordinary Chrome session on `cdp.cdp_url`, which is required when IC.net serves an empty stub to a freshly launched browser.

Neither mode bypasses a login, CAPTCHA, OTP, or device check. `build_production_research_service` fails closed with `ResearchRuntimePrerequisiteError` when a prerequisite is missing.
