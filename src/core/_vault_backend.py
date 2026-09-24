"""Core-private PowerShell backend for the canonical Windows Vault.

This module is Core-internal. Business modules MUST NOT import from it. It
exists to bridge the canonical PowerShell module
``src/core/CredentialVault.psm1`` to the Python Provider in
:mod:`core.credential_provider`.

Behaviour summary:

    * The default backend (``_build_default_backend``) launches the existing
      PowerShell module through ``subprocess.run``. Passwords are decrypted
      only inside the PowerShell process using Windows DPAPI
      (CurrentUser scope); this module never persists or logs them.
    * Backend failures are mapped to the typed exception hierarchy in
      :mod:`core.credential_provider` via the distinct exit codes below.
    * The PowerShell executable location, the module path and the JSON vault
      file path are private details of this backend.

Do not extend this module to create a second credential store. The canonical
Vault on disk remains the only source of truth.
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from .credential_provider import (
    _BackendUnavailableError,
    _NotConfiguredError,
    _SiteNotFoundError,
    _VaultBackend,
    _VaultMalformedError,
)

# Exit codes returned by the embedded PowerShell script. Distinct codes let
# the Python side distinguish typed backend failures without leaking the
# PowerShell error text.
_EXIT_OK = 0
_EXIT_SITE_NOT_FOUND = 30
_EXIT_NOT_CONFIGURED = 31
_EXIT_VAULT_MALFORMED = 32
_EXIT_UNAVAILABLE = 33


_EMBEDDED_PWSH_SCRIPT = r"""
param([string]$ModulePath, [string]$SiteId)

$ErrorActionPreference = 'Stop'

try {
    Import-Module -Name $ModulePath -Force -ErrorAction Stop
}
catch {
    [Console]::Error.WriteLine("BACKEND:Unavailable:ImportModule:$($_.Exception.Message)")
    exit 33
}

$vaultArgs = @{}
if (-not [string]::IsNullOrWhiteSpace($env:INSO_CREDENTIAL_VAULT_PATH)) {
    $vaultArgs['VaultPath'] = $env:INSO_CREDENTIAL_VAULT_PATH
}

try {
    $login = Get-InsoVaultLogin -SiteId $SiteId @vaultArgs -ErrorAction Stop
}
catch {
    $errorMessage = [string]$_.Exception.Message
    if ($errorMessage -like 'Credential site not found*') {
        [Console]::Error.WriteLine('BACKEND:SiteNotFound')
        exit 30
    }
    if ($errorMessage -like 'Credential is not configured*') {
        [Console]::Error.WriteLine('BACKEND:NotConfigured')
        exit 31
    }
    if (
        $errorMessage -like '*Unsupported credential vault version*' -or
        $errorMessage -like '*Credential vault does not exist*' -or
        $errorMessage -like '*requires Windows DPAPI*' -or
        $errorMessage -like '*JsonReaderException*' -or
        $errorMessage -like '*Cannot convert*Json*' -or
        $errorMessage -like '*The site list contains*'
    ) {
        [Console]::Error.WriteLine("BACKEND:VaultMalformed:$errorMessage")
        exit 32
    }
    [Console]::Error.WriteLine("BACKEND:Unavailable:GetLogin:$errorMessage")
    exit 33
}

if ($null -eq $login) {
    [Console]::Error.WriteLine('BACKEND:SiteNotFound')
    exit 30
}

$company = $login.Company
if ([string]::IsNullOrWhiteSpace($company)) { $company = $null }
$url = $login.Url
if ($null -eq $url) { $url = '' }

$payload = [ordered]@{
    siteId   = [string]$login.SiteId
    url      = [string]$url
    company  = $company
    username = [string]$login.Credential.UserName
    password = [string]$login.Credential.GetNetworkCredential().Password
}

$json = $payload | ConvertTo-Json -Compress -Depth 8
[Console]::Out.WriteLine($json)
exit 0
"""


class _PowerShellVaultBackend:
    """``subprocess`` wrapper around the canonical PowerShell Vault module.

    Construction is performed by :func:`_build_default_backend`; tests may
    construct instances directly with explicit ``module_path``,
    ``pwsh_executable`` and ``vault_path`` arguments.
    """

    def __init__(
        self,
        *,
        pwsh_executable: str | None,
        module_path: str | None,
        vault_path: str | None,
    ) -> None:
        if not pwsh_executable:
            raise _BackendUnavailableError("PowerShell executable not configured")
        if not module_path:
            raise _BackendUnavailableError("PowerShell module path not configured")
        self._pwsh = pwsh_executable
        self._module_path = module_path
        self._vault_path = vault_path
        # Validate that the module path exists. We surface this as a
        # _VaultMalformedError so the Provider fails closed cleanly.
        if not Path(module_path).is_file():
            raise _VaultMalformedError(
                f"CredentialVault.psm1 not found at {module_path}"
            )

    def describe(self) -> str:  # pragma: no cover - debug helper
        return (
            f"PowerShellVaultBackend(pwsh={self._pwsh!r}, "
            f"module={self._module_path!r})"
        )

    def get_login_payload(self, site_id: str) -> dict:
        # The embedded PowerShell script is written to a temporary file so
        # we can launch it via ``-File``. This avoids PowerShell 5.1 quoting
        # surprises that occur when a multi-line ``param(...)`` script is
        # passed through ``-Command`` with named arguments.
        import tempfile

        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".ps1",
            delete=False,
            encoding="utf-8",
            newline="\n",
        ) as handle:
            handle.write(_EMBEDDED_PWSH_SCRIPT)
            script_path = handle.name

        args: list = [
            self._pwsh,
            "-NoProfile",
            "-NonInteractive",
            "-File",
            script_path,
            "-ModulePath",
            self._module_path,
            "-SiteId",
            site_id,
        ]
        env = os.environ.copy()
        if self._vault_path:
            # Documented escape hatch for tests / ops scripts. Not required
            # for the canonical Vault.
            env["INSO_CREDENTIAL_VAULT_PATH"] = self._vault_path
        try:
            try:
                completed = subprocess.run(
                    args,
                    capture_output=True,
                    text=True,
                    timeout=20,
                    check=False,
                    env=env,
                )
            except FileNotFoundError as exc:
                raise _BackendUnavailableError(
                    f"PowerShell executable not found: {exc}"
                )
            except subprocess.TimeoutExpired as exc:
                raise _BackendUnavailableError(
                    f"PowerShell invocation timed out: {exc}"
                )
            except OSError as exc:
                raise _BackendUnavailableError(
                    f"PowerShell invocation failed: {exc}"
                )
        finally:
            try:
                os.remove(script_path)
            except OSError:
                pass

        if completed.returncode == _EXIT_SITE_NOT_FOUND:
            raise _SiteNotFoundError()
        if completed.returncode == _EXIT_NOT_CONFIGURED:
            raise _NotConfiguredError()
        if completed.returncode == _EXIT_VAULT_MALFORMED:
            # Strip the BACKEND:VaultMalformed: prefix from stderr.
            raise _VaultMalformedError(
                _strip_backend_prefix(completed.stderr, "VaultMalformed")
            )
        if completed.returncode != _EXIT_OK:
            raise _BackendUnavailableError(
                _strip_backend_prefix(completed.stderr, "Unavailable")
                or completed.stdout.strip()
                or f"PowerShell exited with code {completed.returncode}"
            )

        stdout = completed.stdout.strip()
        if not stdout:
            raise _VaultMalformedError(
                "PowerShell produced no payload for the requested site"
            )
        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise _VaultMalformedError(
                f"Could not parse PowerShell payload: {exc}"
            )
        if not isinstance(payload, dict):
            raise _VaultMalformedError("PowerShell payload was not an object")
        return payload


def _strip_backend_prefix(stderr: str | None, kind: str) -> str:
    """Strip ``BACKEND:<kind>:`` prefix from a single stderr line, if present.

    Returns the human-readable backend error text. Never returns the literal
    prefix to the Provider — the Provider maps to typed exceptions only.
    """
    if not stderr:
        return ""
    prefix = f"BACKEND:{kind}:"
    text = stderr.strip()
    if text.startswith(prefix):
        return text[len(prefix):].strip()
    # Fallback: split on first newline and use the last non-empty line.
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return lines[-1] if lines else ""


def _build_default_backend() -> _VaultBackend:
    """Build the canonical Core PowerShell backend.

    Honours the documented environment overrides
    ``INSO_CREDENTIAL_PWSH`` and ``INSO_CREDENTIAL_VAULT_PATH``. The canonical
    Windows Vault location (default for the PowerShell module) is used when
    no override is provided.
    """
    from .credential_provider import (
        _PWSH_EXECUTABLE_ENV,
        _VAULT_PATH_ENV,
        _discover_pwsh,
    )

    pwsh = os.environ.get(_PWSH_EXECUTABLE_ENV) or _discover_pwsh()
    module_path = _default_module_path()
    vault_path = os.environ.get(_VAULT_PATH_ENV) or None
    return _PowerShellVaultBackend(
        pwsh_executable=pwsh,
        module_path=module_path,
        vault_path=vault_path,
    )


def _default_module_path() -> str:
    """Locate the canonical ``CredentialVault.psm1`` shipped with Core.

    Falls back to a sibling file lookup so the module remains usable when
    Core is shipped as a subpackage of a larger Python project.
    """
    here = Path(__file__).resolve().parent
    candidate = here / "CredentialVault.psm1"
    return str(candidate)