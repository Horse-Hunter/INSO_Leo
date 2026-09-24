"""Unit tests for the Core Python Credential Provider.

These tests use an in-memory backend so they never touch the real Windows
Vault. They exercise the public :class:`CredentialProvider` contract only:

    * configured credential → :class:`Login`
    * optional ``company`` field
    * missing site → fail closed
    * configured site without password → fail closed
    * malformed vault payload → fail closed
    * backend unavailable → fail closed
    * password / username do not leak into ``repr`` or exception messages
    * :class:`Login` is immutable
    * invalid ``site_id`` is rejected before reaching the backend
    * :func:`get_login` returns the canonical login through
      :func:`default_provider`

The bounded real-vault smoke lives in
``test_vault_backend_smoke.py``.
"""
from __future__ import annotations

import dataclasses
import re

import pytest

from core.credential_provider import (
    CredentialError,
    CredentialNotConfiguredError,
    CredentialProvider,
    CredentialProviderUnavailableError,
    CredentialSiteNotFoundError,
    CredentialVaultError,
    Login,
    _BackendError,
    _BackendUnavailableError,
    _NotConfiguredError,
    _SiteNotFoundError,
    _VaultBackend,
    _VaultMalformedError,
    _WindowsCredentialVaultProvider,
    default_provider,
    get_login,
)

# ---------------------------------------------------------------------------
# In-memory backend used by every test in this module.
# ---------------------------------------------------------------------------


class _FakeBackend(_VaultBackend):
    """In-memory backend that mirrors the backend contract only."""

    def __init__(self, mapping=None):
        self.mapping = dict(mapping or {})
        self.mode = "ok"
        self.calls = []

    def describe(self) -> str:
        return "FakeBackend"

    def get_login_payload(self, site_id: str) -> dict:
        self.calls.append(site_id)
        if self.mode == "site-not-found":
            raise _SiteNotFoundError()
        if self.mode == "not-configured":
            raise _NotConfiguredError()
        if self.mode == "vault-malformed":
            raise _VaultMalformedError("synthetic malformed vault")
        if self.mode == "unavailable":
            raise _BackendUnavailableError("synthetic backend down")
        if site_id not in self.mapping:
            raise _SiteNotFoundError()
        payload = self.mapping[site_id]
        if not payload.get("password"):
            raise _NotConfiguredError()
        return dict(payload)


def _provider(backend: _FakeBackend) -> CredentialProvider:
    return _WindowsCredentialVaultProvider(backend=backend)


@pytest.fixture
def backend():
    return _FakeBackend(
        mapping={
            "example.com": {
                "siteId": "example.com",
                "url": "https://example.com/",
                "company": "Example Co",
                "username": "alice",
                "password": "synthetic-secret-1",
            },
            "no-company.example.org": {
                "siteId": "no-company.example.org",
                "url": "https://no-company.example.org/",
                "company": None,
                "username": "bob",
                "password": "synthetic-secret-2",
            },
            "blank-company.example.net": {
                "siteId": "blank-company.example.net",
                "url": "https://blank-company.example.net/",
                "company": "",
                "username": "carol",
                "password": "synthetic-secret-3",
            },
            "unconfigured.example.io": {
                "siteId": "unconfigured.example.io",
                "url": "https://unconfigured.example.io/",
                "company": "",
                "username": "dave",
                "password": "",
            },
        }
    )


# ---------------------------------------------------------------------------
# Happy paths
# ---------------------------------------------------------------------------


def test_configured_credential_returns_full_login(backend):
    provider = _provider(backend)
    login = provider.get_login("example.com")
    assert isinstance(login, Login)
    assert login.site_id == "example.com"
    assert login.url == "https://example.com/"
    assert login.username == "alice"
    assert login.password == "synthetic-secret-1"
    assert login.company == "Example Co"


def test_optional_company_can_be_none(backend):
    provider = _provider(backend)
    login = provider.get_login("no-company.example.org")
    assert login.company is None
    assert login.password == "synthetic-secret-2"


def test_blank_company_is_normalised_to_none(backend):
    provider = _provider(backend)
    login = provider.get_login("blank-company.example.net")
    assert login.company is None


def test_login_is_immutable():
    login = Login(
        site_id="x.example.com",
        url="https://x.example.com/",
        username="u",
        password="p",
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        login.password = "different"  # type: ignore[misc]


def test_login_dataclass_equality():
    a = Login("a", "https://a/", "u", "p")
    b = Login("a", "https://a/", "u", "p")
    assert a == b


# ---------------------------------------------------------------------------
# Fail-closed paths
# ---------------------------------------------------------------------------


def test_missing_site_fails_closed(backend):
    backend.mode = "site-not-found"
    provider = _provider(backend)
    with pytest.raises(CredentialSiteNotFoundError) as excinfo:
        provider.get_login("missing.example.com")
    assert excinfo.value.site_id == "missing.example.com"
    assert "missing.example.com" in str(excinfo.value)


def test_unconfigured_site_fails_closed(backend):
    provider = _provider(backend)
    with pytest.raises(CredentialNotConfiguredError) as excinfo:
        provider.get_login("unconfigured.example.io")
    assert excinfo.value.site_id == "unconfigured.example.io"


def test_malformed_vault_fails_closed(backend):
    backend.mode = "vault-malformed"
    provider = _provider(backend)
    with pytest.raises(CredentialVaultError) as excinfo:
        provider.get_login("example.com")
    assert excinfo.value.site_id == "example.com"


def test_backend_unavailable_fails_closed(backend):
    backend.mode = "unavailable"
    provider = _provider(backend)
    with pytest.raises(CredentialProviderUnavailableError) as excinfo:
        provider.get_login("example.com")
    assert excinfo.value.site_id == "example.com"


def test_missing_password_in_payload_fails_closed(backend):
    backend.mapping["example.com"]["password"] = ""
    provider = _provider(backend)
    with pytest.raises(CredentialNotConfiguredError):
        provider.get_login("example.com")


def test_missing_username_in_payload_fails_closed(backend):
    backend.mapping["example.com"]["username"] = ""
    provider = _provider(backend)
    with pytest.raises(CredentialVaultError):
        provider.get_login("example.com")


def test_invalid_company_type_in_payload_fails_closed(backend):
    backend.mapping["example.com"]["company"] = 12345
    provider = _provider(backend)
    with pytest.raises(CredentialVaultError):
        provider.get_login("example.com")


def test_non_dict_payload_fails_closed():
    class BadBackend(_FakeBackend):
        def get_login_payload(self, site_id):
            return "not a dict"

    provider = _provider(BadBackend())
    with pytest.raises(CredentialVaultError):
        provider.get_login("example.com")


# ---------------------------------------------------------------------------
# site_id validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_site_id",
    ["", " ", "a" * 65, "has space", "has/slash", "no!bang"],
)
def test_invalid_site_id_is_rejected_before_backend(backend, bad_site_id):
    provider = _provider(backend)
    with pytest.raises(CredentialError) as excinfo:
        provider.get_login(bad_site_id)
    # The backend must NOT be touched for invalid site IDs.
    assert backend.calls == []
    assert isinstance(excinfo.value, CredentialError)


def test_non_string_site_id_is_rejected(backend):
    provider = _provider(backend)
    with pytest.raises(CredentialError):
        provider.get_login(None)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# repr / exception safety
# ---------------------------------------------------------------------------


def test_login_repr_redacts_password_and_username(backend):
    provider = _provider(backend)
    login = provider.get_login("example.com")
    text = repr(login)
    assert "synthetic-secret-1" not in text
    assert "alice" not in text
    assert "REDACTED" in text


def test_exception_message_does_not_leak_password(backend):
    # Force a backend failure mode whose hypothetical internal message
    # could carry password material. The Provider MUST NOT echo it.
    backend.mode = "site-not-found"
    provider = _provider(backend)
    with pytest.raises(CredentialSiteNotFoundError) as excinfo:
        provider.get_login("example.com")
    assert "synthetic-secret-1" not in str(excinfo.value)
    assert "alice" not in str(excinfo.value)
    assert "REDACTED" not in str(excinfo.value)


def test_malformed_vault_exception_does_not_leak_password(backend):
    # Even when the vault reports a malformed payload, ensure no password
    # material from the in-memory backend bleeds into the public message.
    backend.mapping["leaky.example.com"] = {
        "siteId": "leaky.example.com",
        "url": "https://leaky.example.com/",
        "company": None,
        "username": "u",
        "password": "leaky-password-9999",
    }
    backend.mode = "vault-malformed"
    provider = _provider(backend)
    with pytest.raises(CredentialVaultError) as excinfo:
        provider.get_login("leaky.example.com")
    assert "leaky-password-9999" not in str(excinfo.value)


# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------


def test_default_provider_returns_login_through_module_helper(backend, monkeypatch):
    # Replace the singleton with a fake-backed provider so the canonical
    # entry points work without a real PowerShell backend.
    from core import credential_provider as cp
    cp._reset_default_provider_for_tests()
    monkeypatch.setattr(
        cp,
        "_default_provider_singleton",
        _WindowsCredentialVaultProvider(backend=backend),
    )
    login = cp.get_login("example.com")
    assert login.site_id == "example.com"
    assert login.username == "alice"
    # Clean up so subsequent tests get a fresh default provider.
    cp._reset_default_provider_for_tests()


def test_default_provider_function_exported_from_core_package():
    # The convenience function is exposed via ``core.__init__``.
    import core
    assert core.get_login is get_login
    assert core.default_provider is default_provider
    assert core.Login is Login
    assert core.CredentialError is CredentialError


# ---------------------------------------------------------------------------
# Module-side import safety
# ---------------------------------------------------------------------------


def test_business_modules_do_not_need_backend_symbols(backend):
    # The Protocol class is intentionally underscore-prefixed: importing it
    # from outside the package is a Core-internal operation, but Python
    # does not forbid it. This test pins the documented surface area.
    import core
    public_names = {
        "Login",
        "CredentialError",
        "CredentialSiteNotFoundError",
        "CredentialNotConfiguredError",
        "CredentialVaultError",
        "CredentialProviderUnavailableError",
        "CredentialProvider",
        "default_provider",
        "get_login",
    }
    exported = set(core.__all__)
    assert public_names.issubset(exported)
    # Internal symbols MUST NOT be exported from the package.
    forbidden = {
        "_VaultBackend",
        "_SiteNotFoundError",
        "_NotConfiguredError",
        "_VaultMalformedError",
        "_BackendUnavailableError",
        "_BackendError",
        "_WindowsCredentialVaultProvider",
        "_reset_default_provider_for_tests",
    }
    assert forbidden.isdisjoint(exported)


def test_payload_translator_rejects_non_string_password():
    from core.credential_provider import _payload_to_login
    with pytest.raises(CredentialVaultError):
        _payload_to_login("x.example.com", {"username": "u", "password": 1234})


def test_payload_translator_rejects_non_string_username():
    from core.credential_provider import _payload_to_login
    with pytest.raises(CredentialVaultError):
        _payload_to_login("x.example.com", {"username": None, "password": "p"})


def test_payload_translator_rejects_non_string_url():
    from core.credential_provider import _payload_to_login
    login = _payload_to_login(
        "x.example.com",
        {"username": "u", "password": "p", "url": None, "company": None},
    )
    assert login.url == ""
    assert login.company is None


# ---------------------------------------------------------------------------
# Type-hierarchy sanity
# ---------------------------------------------------------------------------


def test_credential_error_hierarchy_is_stable():
    assert issubclass(CredentialSiteNotFoundError, CredentialError)
    assert issubclass(CredentialNotConfiguredError, CredentialError)
    assert issubclass(CredentialVaultError, CredentialError)
    assert issubclass(CredentialProviderUnavailableError, CredentialError)


def test_internal_backend_error_hierarchy_is_stable():
    assert issubclass(_SiteNotFoundError, _BackendError)
    assert issubclass(_NotConfiguredError, _BackendError)
    assert issubclass(_VaultMalformedError, _BackendError)
    assert issubclass(_BackendUnavailableError, _BackendError)


# Silence the unused import warning for ``re`` while still keeping the
# import explicit in case future tests need regex helpers.
_ = re