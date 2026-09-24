# Core tests

Tests for `src/core/`. Use synthetic values; never include a live credential or vault value. Canonical boundary: `docs/modules/CORE.md`.

## Layout

- `CredentialVault.Tests.ps1` — PowerShell regression test for the existing
  `CredentialVault.psm1` module. Invoked with Windows PowerShell 5.1.
- `test_credential_provider.py` — Unit tests for the public Core Python
  Credential Provider (`core.credential_provider`). Uses an in-memory
  `_FakeBackend` so it never touches the real Windows Vault.
- `test_vault_backend_smoke.py` — Bounded real-vault smoke. Builds a
  synthetic, OS-controlled vault, then exercises the full default
  infrastructure (PowerShell + DPAPI + JSON file) end to end.
- `conftest.py` — Pytest bootstrap that adds `src/` to `sys.path` so the
  Provider is importable without an installed package.

## Running

```powershell
# PowerShell regression
powershell.exe -NoProfile -ExecutionPolicy Bypass `
    -File "tests\core\CredentialVault.Tests.ps1"

# Python unit + smoke (requires py -3.12 with pytest)
py -3.12 -m pytest tests/core -v

# Lint
py -3.12 -m ruff check src/core tests/core
```

The bounded smoke is auto-skipped on hosts without a PowerShell executable or
Windows DPAPI.
