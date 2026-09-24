# Task: Core Python Credential Provider

status: complete
actor_role: Utility Codex
executor_tool: OTHER  # CodeBuddy
module: core
reports_to: CEO / Architecture Chat
execution_mode: FAST_V1
architecture_impact: REQUIRED

## Problem

Core owns the canonical Windows Credential Vault (PowerShell + Windows DPAPI).
The PowerShell / GUI / CLI surfaces work, but Python business modules (e.g.
Research V1 production runtime) cannot depend on the existing surface because:

- The existing public surfaces expose PowerShell, DPAPI, vault file path.
- `docs/modules/CORE.md` mandates that business modules only depend on a stable
  Credential Provider boundary.
- The Python application Credential Provider API is currently `UNKNOWN`.

This blocks Research V1 production runtime.

## Goal

Implement a minimal, stable Core Python Credential Provider so that Python
business modules can safely fetch authorised logins from the existing Windows
Vault by `site_id` without learning any of the underlying mechanism.

## Current Facts

- Windows Credential Vault exists and is canonical on `main`.
- Underlying implementation uses PowerShell + Windows CurrentUser DPAPI.
- `vault.json` lives outside the repo at `%LOCALAPPDATA%\INSO_Leo\credential-vault.json`.
- `tests/core/CredentialVault.Tests.ps1` already verifies the PowerShell module.
- No `pwsh` (PowerShell 7+) is installed; only Windows PowerShell 5.1 is.
- `ruff 0.16.8` is available via `py -3.12 -m ruff`.
- Python 3.8.7 is on PATH (default `python`); 3.12.10 available via `py`.
- The canonical Python import path is `src.core.*` (mirrors
  `src.research.*`, `src.sheets.*`, `src.workflow.*`).

## Required Context

- `AGENTS.md`
- `docs/AI_START_HERE.md`
- `docs/AI_TEAM.md`
- `docs/TASK_PROTOCOL.md`
- `docs/BOUNDARIES.md`
- `docs/MODULE_INDEX.md`
- `docs/modules/CORE.md`
- `src/core/CredentialVault.psm1`
- `src/core/vault.ps1`
- `src/core/vault-manager.ps1`
- `src/core/open-vault.cmd`
- `tests/core/CredentialVault.Tests.ps1`
- `tests/core/README.md`
- `src/core/README.md`

## Write Scope

- `src/core/credential_provider.py`
- `src/core/__init__.py`
- `src/core/_vault_backend.py`
- `tests/core/conftest.py` (removed — sole purpose was sys.path hack)
- `tests/core/test_credential_provider.py`
- `tests/core/test_vault_backend_smoke.py`
- `tests/core/README.md`
- `docs/modules/CORE.md`
- `tasks/2026-09-24-core-python-credential-provider.md`

## Scope

- One stable public Python Provider API at `src.core`.
- Backed by the existing PowerShell `CredentialVault.psm1`.
- Fail closed; secrets safe in repr and exceptions.

## Non-scope

- Rewriting the vault in pure Python.
- Cross-platform abstractions.
- Modifying `src/research/**`, `src/workflow/**`, `src/sheets/**`.
- Modifying INSO, Quotation, or AI/governance docs.
- Replacing the canonical Windows Vault.
- New packaging / install framework.

## Requirements

1. Business modules depend only on `src.core.credential_provider` /
   `src.core.get_login`.
2. Business modules never see PowerShell / DPAPI / vault path.
3. No second credential store.
4. Fail closed on missing site / unconfigured credential / malformed vault /
   provider unavailable.
5. No plaintext / env / repo-file fallback.
6. `repr(Login)` and exception messages redact password material.
7. Existing PowerShell Vault tests do not regress.

## Acceptance

- [x] Public Python Provider exposes `get_login(site_id) -> Login` via
      `from src.core import get_login`.
- [x] Missing site raises `CredentialSiteNotFoundError`.
- [x] Unconfigured site raises `CredentialNotConfiguredError`.
- [x] Malformed vault raises `CredentialVaultError`.
- [x] Backend unavailable raises `CredentialProviderUnavailableError`.
- [x] `repr(Login)` does not contain password or username.
- [x] Exceptions never include password material.
- [x] `docs/modules/CORE.md` describes the new public contract.
- [x] Existing `tests/core/CredentialVault.Tests.ps1` still PASS.
- [x] New Python tests PASS under `pytest` (full repo: 240 passed).
- [x] `ruff check` PASS.
- [x] Bounded real-vault smoke returns PASS / FAIL without leaking secrets.
- [x] Repo-root `py -3.12 -c "from src.core import get_login, Login,
      CredentialError; print('IMPORT_OK')"` prints exactly `IMPORT_OK`.

## Final Result

- Stable public contract lives at `src.core` (mirrors the project's existing
  `src.*` convention). Business modules now do
  `from src.core import get_login, CredentialError`.
- A Core-private `_vault_backend.py` wraps the existing
  `CredentialVault.psm1` via PowerShell 5.1 (`-File` mode for reliable
  argument binding) and returns typed backend errors. The PowerShell module
  path, executable location, DPAPI scope and vault JSON path are not exposed
  in any Public Contract.
- All secret material is decrypted only inside the PowerShell process; the
  Python side holds the password only inside the `Login` instance for the
  caller's lifetime.

## Verification

- `py -3.12 -m pytest -q` -> 240 passed in 4.11s
- `py -3.12 -m ruff check src/core tests/core` -> All checks passed
- `powershell.exe -NoProfile -ExecutionPolicy Bypass -File tests\core\CredentialVault.Tests.ps1` -> PASS
- `py -3.12 -c "from src.core import get_login, Login, CredentialError; print('IMPORT_OK')"` -> `IMPORT_OK`
- Secret scan over `git diff` -> no real Secret / real username / real URL.

## Commit / Push

- Branch: `buddy/core-python-credential-provider` (continues from
  `8f369ffad356207ed9ba34fd287634f05ca0bcd8`).
- Push: SUCCESS against `https://github.com/Horse-Hunter/INSO_Leo.git`.

## Remaining

- NONE inside this Task scope.
- Future V2 candidates explicitly out of scope here: process-internal
  caching / TTL, batched site_id queries, cross-platform abstractions,
  Research / Workflow migration, new packaging framework.