"""Bounded real-vault smoke for the Core Python Credential Provider.

This test exercises the *full* default infrastructure path: a temporary,
synthetic Windows Vault file is created in the OS temp directory, the
PowerShell backend is launched against it, and the canonical Provider is
invoked through :func:`core.credential_provider.default_provider`.

The test is intentionally bounded:

    * The Vault is created at a synthetic, OS-controlled location; the
      canonical ``%LOCALAPPDATA%\\INSO_Leo\\credential-vault.json`` is NEVER
      touched.
    * Only a synthetic password is ever written. No real Secret, real
      username, real URL, real company name, real token, or real cookie
      appears in the fixture.
    * The test prints only PASS / FAIL / nothing. It never prints password
      material, and the assertions intentionally compare opaque values via
      boolean checks, not via ``assert ==``.
    * The test is auto-skipped when no PowerShell executable is available so
      it remains CI-friendly on non-Windows hosts. On hosts without
      Windows DPAPI (i.e. real Vault support), it is also skipped.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import uuid

import pytest

from core import credential_provider as cp
from core._vault_backend import (
    _EMBEDDED_PWSH_SCRIPT,
    _build_default_backend,
    _default_module_path,
    _PowerShellVaultBackend,
)

_SMOKE_SITE_ID = "smoke-pytest.example.com"
_SMOKE_USERNAME = "smoke-pytest-user"
_SMOKE_PASSWORD = "smoke-pytest-only"
_SMOKE_URL = "https://smoke-pytest.example.com/login"
_SMOKE_COMPANY = "Smoke Pytest Co"


def _discover_pwsh():
    for name in ("pwsh.exe", "pwsh", "powershell.exe", "powershell"):
        path = _which(name)
        if path:
            return path
    return None


def _which(name):
    from shutil import which
    return which(name)


def _is_windows() -> bool:
    return sys.platform.startswith("win") or os.name == "nt"


def _windows_dpapi_supported(pwsh: str) -> bool:
    """Probe whether the host PowerShell can actually use Windows DPAPI.

    The probe writes a tiny .ps1 to a temp file and runs it. If DPAPI works
    in the current process, the probe returns ``True``; otherwise it
    returns ``False``. We do not log / commit / print any secret here.
    """
    probe = (
        "try { "
        "Add-Type -AssemblyName System.Security -ErrorAction Stop; "
        "[Security.Cryptography.ProtectedData]::Protect("
        "[Text.Encoding]::UTF8.GetBytes('probe'), "
        "[Text.Encoding]::UTF8.GetBytes('entropy'), "
        "[Security.Cryptography.DataProtectionScope]::CurrentUser"
        ") | Out-Null; "
        "[Console]::Out.WriteLine('OK') "
        "} catch { [Console]::Error.WriteLine('NO') }"
    )
    try:
        completed = subprocess.run(
            [pwsh, "-NoProfile", "-NonInteractive", "-Command", probe],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False
    return completed.returncode == 0 and "OK" in (completed.stdout or "")


@pytest.fixture(scope="module")
def pwsh_executable():
    pwsh = _discover_pwsh()
    if not pwsh:
        pytest.skip("No PowerShell executable on PATH; smoke skipped.")
    if not _is_windows():
        pytest.skip("Windows Vault requires Windows DPAPI; smoke skipped.")
    if not _windows_dpapi_supported(pwsh):
        pytest.skip("PowerShell host cannot use Windows DPAPI; smoke skipped.")
    return pwsh


@pytest.fixture(scope="module")
def synthetic_vault(pwsh_executable):
    """Create a temporary synthetic Vault file for the smoke run.

    Yields the resolved Vault path; on teardown removes the file.
    """
    test_root = os.path.join(
        os.environ.get("TEMP") or os.environ.get("TMP") or os.getcwd(),
        f"inso-pytest-smoke-{uuid.uuid4().hex}",
    )
    os.makedirs(test_root, exist_ok=True)
    vault_path = os.path.join(test_root, "vault.json")
    try:
        # Bootstrap a fresh synthetic vault through the existing PowerShell
        # module. We use the module directly so the existing tests stay the
        # source of truth for the Vault schema.
        module_path = _default_module_path()
        ps_script = (
            "$ErrorActionPreference = 'Stop'\n"
            f"Import-Module -Name '{module_path}' -Force -ErrorAction Stop\n"
            f"Initialize-InsoVault -VaultPath '{vault_path}' -ErrorAction Stop | Out-Null\n"
            f"Set-InsoVaultCredential -SiteId '{_SMOKE_SITE_ID}' "
            f"-Url '{_SMOKE_URL}' -Company '{_SMOKE_COMPANY}' "
            f"-Username '{_SMOKE_USERNAME}' "
            f"-Password (ConvertTo-SecureString -String '{_SMOKE_PASSWORD}' -AsPlainText -Force) "
            f"-VaultPath '{vault_path}' -ErrorAction Stop\n"
        )
        completed = subprocess.run(
            [pwsh_executable, "-NoProfile", "-NonInteractive", "-Command", ps_script],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if completed.returncode != 0:
            # No secrets in stderr; surface the failure abstractly.
            pytest.fail(
                f"smoke vault bootstrap failed: exit={completed.returncode}"
            )
        yield vault_path
    finally:
        try:
            os.remove(vault_path)
        except OSError:
            pass
        try:
            os.rmdir(test_root)
        except OSError:
            pass


def test_default_backend_can_be_built_with_overrides(pwsh_executable, synthetic_vault, monkeypatch):
    """Round-trip: PowerShell backend returns a payload that the Provider
    accepts, without leaking any secret value via assertion text.
    """
    monkeypatch.setenv("INSO_CREDENTIAL_VAULT_PATH", synthetic_vault)
    monkeypatch.setenv("INSO_CREDENTIAL_PWSH", pwsh_executable)
    cp._reset_default_provider_for_tests()

    backend = _build_default_backend()
    assert isinstance(backend, _PowerShellVaultBackend)

    payload = backend.get_login_payload(_SMOKE_SITE_ID)
    # Sanity: payload is a dict with the canonical keys.
    assert isinstance(payload, dict)
    assert payload.get("siteId") == _SMOKE_SITE_ID
    assert payload.get("username") == _SMOKE_USERNAME
    # We DO NOT assert on payload["password"] content beyond presence; the
    # secret value is opaque to the smoke test.
    assert isinstance(payload.get("password"), str)
    assert payload.get("password") != ""

    # Now route through the public Provider.
    provider = cp.default_provider()
    login = provider.get_login(_SMOKE_SITE_ID)
    assert login.site_id == _SMOKE_SITE_ID
    assert login.username == _SMOKE_USERNAME
    assert isinstance(login.password, str)
    assert login.password != ""
    # repr must redact; the synthetic username MUST NOT appear.
    text = repr(login)
    assert _SMOKE_USERNAME not in text
    assert "REDACTED" in text


def test_smoke_missing_site_fails_closed(pwsh_executable, synthetic_vault, monkeypatch):
    monkeypatch.setenv("INSO_CREDENTIAL_VAULT_PATH", synthetic_vault)
    monkeypatch.setenv("INSO_CREDENTIAL_PWSH", pwsh_executable)
    cp._reset_default_provider_for_tests()
    provider = cp.default_provider()
    with pytest.raises(cp.CredentialSiteNotFoundError):
        provider.get_login("does-not-exist.example.com")


def test_smoke_corrupt_vault_fails_closed(pwsh_executable, synthetic_vault, monkeypatch):
    # Corrupt the vault JSON in-memory only.
    with open(synthetic_vault, "rb") as handle:
        original_bytes = handle.read()
    try:
        with open(synthetic_vault, "wb") as handle:
            handle.write(b'{"version": 999, "entries": "not-a-list"}')
        monkeypatch.setenv("INSO_CREDENTIAL_VAULT_PATH", synthetic_vault)
        monkeypatch.setenv("INSO_CREDENTIAL_PWSH", pwsh_executable)
        cp._reset_default_provider_for_tests()
        provider = cp.default_provider()
        with pytest.raises(cp.CredentialVaultError):
            provider.get_login(_SMOKE_SITE_ID)
    finally:
        with open(synthetic_vault, "wb") as handle:
            handle.write(original_bytes)
        cp._reset_default_provider_for_tests()


def test_smoke_missing_powershell_fails_closed(synthetic_vault, monkeypatch):
    # Point the Provider at a non-existent PowerShell to exercise the
    # "backend unavailable" path without touching the real Vault.
    monkeypatch.setenv("INSO_CREDENTIAL_PWSH",
                       r"C:\does-not-exist\pwsh.exe")
    monkeypatch.setenv("INSO_CREDENTIAL_VAULT_PATH", synthetic_vault)
    cp._reset_default_provider_for_tests()
    provider = cp.default_provider()
    with pytest.raises(cp.CredentialProviderUnavailableError):
        provider.get_login(_SMOKE_SITE_ID)
    cp._reset_default_provider_for_tests()


def test_embedded_powershell_script_contains_no_secret_placeholder():
    """The embedded PowerShell script must not bake in any fixture secret.

    This guards against a future refactor accidentally hard-coding the
    smoke password into the embedded script.
    """
    assert _SMOKE_PASSWORD not in _EMBEDDED_PWSH_SCRIPT
    assert _SMOKE_SITE_ID not in _EMBEDDED_PWSH_SCRIPT
    assert _SMOKE_USERNAME not in _EMBEDDED_PWSH_SCRIPT
    # No JSON-style passwords in the embedded script either.
    assert json.dumps(_SMOKE_PASSWORD)[1:-1] not in _EMBEDDED_PWSH_SCRIPT