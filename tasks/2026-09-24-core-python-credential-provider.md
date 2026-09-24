# Task: Core Python Credential Provider

status: ready
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
- Existing tests PASS as of `ce265c5` on this branch.
- No `pwsh` (PowerShell 7+) is installed; only Windows PowerShell 5.1 is.
- `ruff 0.16.8` is available via `py -3.12 -m ruff`.
- Python 3.8.7 is on PATH (default `python`); 3.12.10 available via `py`.

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
- `tests/core/conftest.py`
- `tests/core/test_credential_provider.py`
- `tests/core/test_vault_backend_smoke.py`
- `tests/core/README.md`
- `docs/modules/CORE.md`
- `tasks/2026-09-24-core-python-credential-provider.md`

## Scope

- One stable public Python Provider API.
- Backed by the existing PowerShell `CredentialVault.psm1`.
- Fail closed; secrets safe in repr and exceptions.

## Non-scope

- Rewriting the vault in pure Python.
- Cross-platform abstractions.
- Modifying `src/research/**`, `src/workflow/**`, `src/sheets/**`.
- Modifying INSO, Quotation, or AI/governance docs.
- Replacing the canonical Windows Vault.

## Requirements

1. Business modules depend only on the new Python Provider.
2. Business modules never see PowerShell / DPAPI / vault path.
3. No second credential store.
4. Fail closed on missing site / unconfigured credential / malformed vault /
   provider unavailable.
5. No plaintext / env / repo-file fallback.
6. `repr(Login)` and exception messages redact password material.
7. Existing PowerShell Vault tests do not regress.

## Acceptance

- [ ] Public Python Provider exposes `get_login(site_id) -> Login`.
- [ ] Missing site raises `CredentialSiteNotFoundError`.
- [ ] Unconfigured site raises `CredentialNotConfiguredError`.
- [ ] Malformed vault raises `CredentialVaultError`.
- [ ] Backend unavailable raises `CredentialProviderUnavailableError`.
- [ ] `repr(Login)` does not contain password or username.
- [ ] Exceptions never include password material.
- [ ] `docs/modules/CORE.md` describes the new public contract.
- [ ] Existing `tests/core/CredentialVault.Tests.ps1` still PASS.
- [ ] New Python tests PASS under `pytest`.
- [ ] `ruff check` PASS.
- [ ] Bounded real-vault smoke returns PASS / FAIL without leaking secrets.

## Execution

- Stay on `buddy/core-python-credential-provider` based on `origin/main`.
- Use an in-memory `_FakeBackend` for unit tests so tests never touch the real
  vault.
- The PowerShell backend uses Windows PowerShell 5.1 (no `pwsh` installed)
  through `subprocess.run`. Use distinct exit codes for typed backend errors.
- Run `ruff check` on the new Python files.
- Run the bounded smoke against a temporary synthetic vault file, then
  delete it. Do not print / log / commit any secret.
- Commit on the same branch; push on success.

## Final Report

See parent task spec for required fields.