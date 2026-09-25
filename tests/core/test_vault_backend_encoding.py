"""Regression tests for the Core Python Credential Provider encoding protocol.

These tests pin the deterministic UTF-8 contract between the Python side
(``_vault_backend.py``) and the PowerShell subprocess:

    * The embedded PowerShell script writes only UTF-8 bytes via
      ``[Console]::Out.WriteLine`` / ``[Console]::Error.WriteLine`` after
      forcing ``[Console]::OutputEncoding = UTF8``.
    * The Python side decodes ``subprocess.run(..., text=False)`` bytes with
      ``errors='strict'`` and maps any decode failure to a typed Core
      exception. ``UnicodeDecodeError`` MUST NOT escape the Provider; it
      MUST NOT appear as ``AttributeError`` downstream either.

All fixtures here are deliberately synthetic and non-Secret. No real
``site_id``, username, password, URL, token, or cookie is ever written to
the repository.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import uuid

import pytest

from src.core import credential_provider as cp
from src.core._vault_backend import (
    _EMBEDDED_PWSH_SCRIPT,
    _POWER_SHELL_ENCODING,
    _BackendUnavailableError,
    _decode_strict_utf8,
    _PowerShellVaultBackend,
    _VaultMalformedError,
)

# Synthetic, non-Secret fixtures. Chosen to span multi-byte and combining
# sequences across common script families so encoding regressions surface
# quickly. None of these values is a real Secret, URL, username, or cookie.
_NON_ASCII_USERNAME = "用户名-Ω-test"
_NON_ASCII_COMPANY = "公司-🎉-Co"
_NON_ASCII_PASSWORD = "密码-αβγ-Ω🎉-αβγ"
_NON_ASCII_URL = "https://测试.example.com/登录"


# ---------------------------------------------------------------------------
# Helper-level decoding tests (no PowerShell required).
# ---------------------------------------------------------------------------


def test_canonical_encoding_constant_is_utf_8():
    # The Python side and the PowerShell side both agree on UTF-8. If this
    # constant drifts, the contract has drifted with it.
    assert _POWER_SHELL_ENCODING == "utf-8"
    assert "OutputEncoding = [System.Text.Encoding]::UTF8" in _EMBEDDED_PWSH_SCRIPT


def test_decode_helper_round_trip_non_ascii():
    text = _NON_ASCII_USERNAME + "/" + _NON_ASCII_COMPANY + "/" + _NON_ASCII_PASSWORD
    decoded = _decode_strict_utf8(text.encode("utf-8"), kind="stdout")
    assert decoded == text


def test_decode_helper_maps_stdout_unicode_error_to_vault_malformed():
    # 0xff / 0xfe is never valid UTF-8.
    with pytest.raises(_VaultMalformedError):
        _decode_strict_utf8(b"\xff\xfe\xfd", kind="stdout")


def test_decode_helper_maps_stderr_unicode_error_to_backend_unavailable():
    with pytest.raises(_BackendUnavailableError):
        _decode_strict_utf8(b"\xff\xfe\xfd", kind="stderr")


def test_decode_helper_maps_none_stdout_to_vault_malformed():
    with pytest.raises(_VaultMalformedError):
        _decode_strict_utf8(None, kind="stdout")


def test_decode_helper_maps_none_stderr_to_backend_unavailable():
    with pytest.raises(_BackendUnavailableError):
        _decode_strict_utf8(None, kind="stderr")


def test_vault_powershell_runs_without_visible_console(monkeypatch, tmp_path):
    module = tmp_path / "CredentialVault.psm1"
    module.write_text("", encoding="utf-8")
    backend = _PowerShellVaultBackend(
        pwsh_executable="powershell.exe", module_path=str(module), vault_path=None
    )
    captured = {}

    def fake_run(args, **kwargs):
        captured.update(kwargs)
        return subprocess.CompletedProcess(args, 30, b"", b"BACKEND:SiteNotFound")

    monkeypatch.setattr(subprocess, "run", fake_run)
    with pytest.raises(cp.CredentialSiteNotFoundError):
        cp._WindowsCredentialVaultProvider(backend=backend).get_login(
            "synthetic.example"
        )
    assert captured["creationflags"] == getattr(subprocess, "CREATE_NO_WINDOW", 0)
    assert captured["capture_output"] is True
    assert captured["text"] is False


# ---------------------------------------------------------------------------
# End-to-end synthetic round-trip. Skipped on hosts without PowerShell +
# Windows DPAPI so it remains CI-friendly.
# ---------------------------------------------------------------------------


def _discover_pwsh():
    from shutil import which
    for name in ("pwsh.exe", "pwsh", "powershell.exe", "powershell"):
        path = which(name)
        if path:
            return path
    return None


def _is_windows() -> bool:
    return sys.platform.startswith("win") or os.name == "nt"


def _windows_dpapi_supported(pwsh: str) -> bool:
    probe = (
        "try { "
        "Add-Type -AssemblyName System.Security -ErrorAction Stop; "
        "[Security.Cryptography.ProtectedData]::Protect("
        "[Text.Encoding]::UTF8.GetBytes('probe'), "
        "[Text.Encoding]::UTF8.GetBytes('entropy'), "
        "[Security.Cryptography.DataProtectionScope]::CurrentUser"
        ") | Out-Null; "
        "[Console]::Out.WriteLine('OK')"
        " } catch { [Console]::Error.WriteLine('NO') }"
    )
    try:
        completed = subprocess.run(
            [pwsh, "-NoProfile", "-NonInteractive", "-Command", probe],
            capture_output=True,
            text=False,
            timeout=15,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False
    # Note: probe stdout may be UTF-8 with BOMs on some hosts; ``OK`` match
    # is the strongest stable signal.
    try:
        out = (
            completed.stdout.decode("utf-8", errors="replace")
            if completed.stdout
            else ""
        )
    except (UnicodeDecodeError, AttributeError, ValueError):  # pragma: no cover
        return False
    return completed.returncode == 0 and "OK" in out


@pytest.fixture(scope="module")
def pwsh_executable():
    pwsh = _discover_pwsh()
    if not pwsh:
        pytest.skip("No PowerShell executable on PATH; encoding smoke skipped.")
    if not _is_windows():
        pytest.skip("Windows Vault requires Windows DPAPI; encoding smoke skipped.")
    if not _windows_dpapi_supported(pwsh):
        pytest.skip("PowerShell host cannot use Windows DPAPI; encoding smoke skipped.")
    return pwsh


@pytest.fixture(scope="module")
def non_ascii_synthetic_vault(pwsh_executable):
    """Build a synthetic Vault with non-ASCII username/company/password.

    The Vault is created at an OS-controlled temp path; the canonical
    ``%LOCALAPPDATA%\\INSO_Leo\\credential-vault.json`` is NEVER touched.
    Yields the resolved Vault path; on teardown removes the file.
    """
    from src.core._vault_backend import _default_module_path

    test_root = os.path.join(
        os.environ.get("TEMP") or os.environ.get("TMP") or os.getcwd(),
        f"inso-pytest-encoding-{uuid.uuid4().hex}",
    )
    os.makedirs(test_root, exist_ok=True)
    vault_path = os.path.join(test_root, "vault.json")
    site_id = "encoding-pytest.example.com"
    try:
        module_path = _default_module_path()
        # Build the PowerShell snippet. Non-ASCII values are passed via
        # PowerShell's string parser, which is fully Unicode-aware; only
        # the cross-process encoding on ``[Console]::Out.WriteLine`` is
        # under test here.
        ps_script_lines = [
            "$ErrorActionPreference = 'Stop'",
            f"Import-Module -Name '{module_path}' -Force -ErrorAction Stop",
            (
                f"Initialize-InsoVault -VaultPath '{vault_path}' "
                "-ErrorAction Stop | Out-Null"
            ),
            (
                f"$pw = ConvertTo-SecureString -String '{_NON_ASCII_PASSWORD}' "
                "-AsPlainText -Force"
            ),
            (
                "Set-InsoVaultCredential "
                f"-SiteId '{site_id}' "
                f"-Url '{_NON_ASCII_URL}' "
                f"-Company '{_NON_ASCII_COMPANY}' "
                f"-Username '{_NON_ASCII_USERNAME}' "
                "-Password $pw "
                f"-VaultPath '{vault_path}' -ErrorAction Stop"
            ),
        ]
        ps_script = "\n".join(ps_script_lines)
        completed = subprocess.run(
            [pwsh_executable, "-NoProfile", "-NonInteractive", "-Command", ps_script],
            capture_output=True,
            text=False,
            timeout=30,
            check=False,
        )
        if completed.returncode != 0:
            pytest.fail(
                f"non-ASCII vault bootstrap failed: exit={completed.returncode}"
            )
        yield site_id, vault_path
    finally:
        try:
            os.remove(vault_path)
        except OSError:
            pass
        try:
            os.rmdir(test_root)
        except OSError:
            pass


@pytest.fixture
def backend_factory(pwsh_executable, monkeypatch):
    """Build a fresh backend pointed at the supplied vault path."""

    from src.core._vault_backend import _default_module_path

    def _factory(vault_path):
        monkeypatch.setenv("INSO_CREDENTIAL_VAULT_PATH", vault_path)
        monkeypatch.setenv("INSO_CREDENTIAL_PWSH", pwsh_executable)
        cp._reset_default_provider_for_tests()
        return _PowerShellVaultBackend(
            pwsh_executable=pwsh_executable,
            module_path=_default_module_path(),
            vault_path=vault_path,
        )

    yield _factory
    cp._reset_default_provider_for_tests()


def test_non_ascii_username_round_trips(non_ascii_synthetic_vault, backend_factory):
    site_id, vault_path = non_ascii_synthetic_vault
    backend = backend_factory(vault_path)
    payload = backend.get_login_payload(site_id)
    assert payload.get("username") == _NON_ASCII_USERNAME
    assert payload.get("siteId") == site_id


def test_non_ascii_company_round_trips(non_ascii_synthetic_vault, backend_factory):
    site_id, vault_path = non_ascii_synthetic_vault
    backend = backend_factory(vault_path)
    payload = backend.get_login_payload(site_id)
    assert payload.get("company") == _NON_ASCII_COMPANY


def test_non_ascii_password_round_trips(non_ascii_synthetic_vault, backend_factory):
    site_id, vault_path = non_ascii_synthetic_vault
    backend = backend_factory(vault_path)
    payload = backend.get_login_payload(site_id)
    # JSON round-trip on the password MUST be byte-identical to the input
    # we wrote. ``json.dumps`` would normalise some sequences, but we use
    # the raw payload from the backend (which round-tripped through the
    # UTF-8 contract) and compare for equality.
    assert isinstance(payload.get("password"), str)
    assert payload.get("password") == _NON_ASCII_PASSWORD


def test_non_ascii_url_round_trips(non_ascii_synthetic_vault, backend_factory):
    site_id, vault_path = non_ascii_synthetic_vault
    backend = backend_factory(vault_path)
    payload = backend.get_login_payload(site_id)
    assert payload.get("url") == _NON_ASCII_URL


def test_non_ascii_provider_get_login_round_trips(
    non_ascii_synthetic_vault, monkeypatch
):
    """End-to-end: default_provider().get_login() returns full non-ASCII Login."""
    site_id, vault_path = non_ascii_synthetic_vault
    monkeypatch.setenv("INSO_CREDENTIAL_VAULT_PATH", vault_path)
    monkeypatch.setenv("INSO_CREDENTIAL_PWSH", _discover_pwsh())
    cp._reset_default_provider_for_tests()
    try:
        login = cp.get_login(site_id)
    finally:
        cp._reset_default_provider_for_tests()
    assert login.site_id == site_id
    assert login.username == _NON_ASCII_USERNAME
    assert login.company == _NON_ASCII_COMPANY
    assert login.password == _NON_ASCII_PASSWORD
    assert login.url == _NON_ASCII_URL


def test_non_ascii_repr_still_redacts_password_and_username(
    non_ascii_synthetic_vault, monkeypatch
):
    site_id, vault_path = non_ascii_synthetic_vault
    monkeypatch.setenv("INSO_CREDENTIAL_VAULT_PATH", vault_path)
    monkeypatch.setenv("INSO_CREDENTIAL_PWSH", _discover_pwsh())
    cp._reset_default_provider_for_tests()
    try:
        login = cp.get_login(site_id)
    finally:
        cp._reset_default_provider_for_tests()
    text = repr(login)
    assert _NON_ASCII_PASSWORD not in text
    assert _NON_ASCII_USERNAME not in text
    assert "REDACTED" in text


# ---------------------------------------------------------------------------
# Direct injection of non-UTF-8 bytes through the embedded script. We
# bypass the canonical Vault entirely by routing a custom PowerShell
# script that emits a malformed stream directly to ``[Console]::Error``
# / ``[Console]::Out``. This pins that the strict UTF-8 contract on the
# Python side actually surfaces as typed exceptions.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Malformed PowerShell output -> typed Core exception contract.
#
# We drive the same strict UTF-8 path the backend uses after
# ``subprocess.run`` returns. The provider-level mapping is pinned by the
# existing fail-closed tests in ``test_credential_provider``; here we only
# verify the bytes->str contract that prevents ``UnicodeDecodeError`` and
# ``AttributeError`` from escaping the backend.
# ---------------------------------------------------------------------------


def test_malformed_stdout_maps_to_vault_malformed():
    """When the PowerShell stream emits non-UTF-8 bytes, the backend MUST
    raise ``_VaultMalformedError`` (and the Provider MUST map that to
    ``CredentialVaultError``), not ``UnicodeDecodeError`` / ``AttributeError``.
    """
    with pytest.raises(_VaultMalformedError):
        _decode_strict_utf8(b"\xff\xfe\xfd\xfc", kind="stdout")


def test_malformed_stderr_maps_to_backend_unavailable():
    with pytest.raises(_BackendUnavailableError):
        _decode_strict_utf8(b"\xff\xfe\xfd\xfc", kind="stderr")


def test_provider_maps_malformed_stdout_to_credential_vault_error(monkeypatch):
    """End-to-end through the Provider: a backend that raises
    ``_VaultMalformedError`` for malformed bytes MUST surface as
    ``CredentialVaultError``, not a raw ``UnicodeDecodeError`` /
    ``AttributeError``.
    """

    class _MalformedBytesBackend:
        def describe(self) -> str:
            return "MalformedBytesBackend"

        def get_login_payload(self, site_id):
            # Simulate what the real backend does on non-UTF-8 stdout.
            raise _VaultMalformedError(
                "PowerShell stdout could not be decoded as UTF-8"
            )

    provider = cp._WindowsCredentialVaultProvider(
        backend=_MalformedBytesBackend()
    )
    with pytest.raises(cp.CredentialVaultError):
        provider.get_login("encoding-pytest.example.com")


def test_json_round_trip_after_non_ascii_decode():
    """Pure-Python check that ``json.loads`` survives the same UTF-8
    decode path the backend takes when the JSON contains non-ASCII keys /
    values.
    """
    payload = {
        "siteId": "encoding-pytest.example.com",
        "url": _NON_ASCII_URL,
        "company": _NON_ASCII_COMPANY,
        "username": _NON_ASCII_USERNAME,
        "password": _NON_ASCII_PASSWORD,
    }
    text = json.dumps(payload, ensure_ascii=False)
    decoded = _decode_strict_utf8(text.encode("utf-8"), kind="stdout")
    reparsed = json.loads(decoded)
    assert reparsed == payload


def test_embedded_script_declares_utf8_protocol():
    """Pin the embedded script's UTF-8 protocol. If a refactor accidentally
    drops the explicit ``[Console]::OutputEncoding`` assignment, this test
    fails immediately.
    """
    assert "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8" in _EMBEDDED_PWSH_SCRIPT
    # The setting MUST happen before the first Import-Module call so module
    # diagnostics written via Write-Host also follow the contract.
    encoding_idx = _EMBEDDED_PWSH_SCRIPT.find("[Console]::OutputEncoding = [System.Text.Encoding]::UTF8")
    import_idx = _EMBEDDED_PWSH_SCRIPT.find("Import-Module -Name $ModulePath")
    assert encoding_idx != -1
    assert import_idx != -1
    assert encoding_idx < import_idx
    # And it MUST be wrapped in a try/catch that maps a host that does not
    # permit the assignment to a backend-unavailable exit code.
    assert "[Console]::Error.WriteLine(\"BACKEND:Unavailable:OutputEncoding:" in _EMBEDDED_PWSH_SCRIPT
    assert "exit 33" in _EMBEDDED_PWSH_SCRIPT
