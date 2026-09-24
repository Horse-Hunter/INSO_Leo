"""Canonical Core Python Credential Provider.

This module is the only stable boundary that business modules (e.g. research,
workflow) may use to retrieve authorised logins from the existing Windows
Credential Vault.

Public Contract (see ``docs/modules/CORE.md``):

    * Business modules MUST depend on :class:`CredentialProvider` /
      :func:`get_login` only.
    * Business modules MUST NOT depend on PowerShell, DPAPI, vault file paths,
      or any other underlying mechanism. Those are Core private details.
    * When the requested ``site_id`` is not present, the site exists but has no
      password, the vault is malformed, or the backend is unavailable, the
      Provider MUST raise the matching typed exception below. The Provider
      MUST NOT return a placeholder / empty login.
    * Password material MUST NOT appear in ``repr(Login)`` or in any exception
      message raised by this module.

The default backend reuses the existing PowerShell module
``src/core/CredentialVault.psm1`` (Windows DPAPI, current-user scope). The
PowerShell module path, executable location, DPAPI scope and JSON vault file
path are Core private implementation details.
"""
from __future__ import annotations

import logging
import re
import shutil
from dataclasses import dataclass
from typing import Protocol

__all__ = [
    "CredentialError",
    "CredentialNotConfiguredError",
    "CredentialProvider",
    "CredentialProviderUnavailableError",
    "CredentialSiteNotFoundError",
    "CredentialVaultError",
    "Login",
    "_BackendError",
    "_BackendUnavailableError",
    "_NotConfiguredError",
    "_SiteNotFoundError",
    "_VaultBackend",
    "_VaultMalformedError",
    "default_provider",
    "get_login",
]


_log = logging.getLogger("inso.credential_provider")
if not _log.handlers:
    _log.addHandler(logging.NullHandler())

# Site ID validation mirrors the PowerShell vault: 1-64 characters,
# alphanumeric, '.', '_' or '-'; must start with alphanumeric.
_SITE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")

# Environment variables that business modules may set in tests / ops scripts.
# These are documented but the default behaviour (use canonical Windows
# Vault) does NOT require them.
_VAULT_PATH_ENV = "INSO_CREDENTIAL_VAULT_PATH"
_PWSH_EXECUTABLE_ENV = "INSO_CREDENTIAL_PWSH"


# ---------------------------------------------------------------------------
# Public dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Login:
    """Immutable credential record returned by :class:`CredentialProvider`.

    ``password`` is held only for the minimal lifetime required by the
    authenticated client; it MUST be deleted (``del login``) as soon as the
    caller is finished with it. The default ``__repr__`` redacts both the
    password and the username, which is treated as sensitive in this
    codebase.
    """

    site_id: str
    url: str
    username: str
    password: str
    company: str | None = None

    def __repr__(self) -> str:  # pragma: no cover - simple formatting
        return (
            "Login("
            f"site_id={self.site_id!r}, "
            f"url={self.url!r}, "
            "username='***REDACTED***', "
            f"company={self.company!r}, "
            "password='***REDACTED***'"
            ")"
        )


# ---------------------------------------------------------------------------
# Public exception hierarchy
# ---------------------------------------------------------------------------


class CredentialError(Exception):
    """Base class for every credential retrieval failure.

    Exception messages reference the ``site_id`` only. No password material
    is ever included.
    """

    def __init__(self, site_id: str, message: str) -> None:
        self.site_id = site_id
        super().__init__(message)


class CredentialSiteNotFoundError(CredentialError):
    """Raised when the requested ``site_id`` is not present in the vault."""


class CredentialNotConfiguredError(CredentialError):
    """Raised when the site exists but no password has been configured."""


class CredentialVaultError(CredentialError):
    """Raised when the vault file is missing, unreadable, or malformed."""


class CredentialProviderUnavailableError(CredentialError):
    """Raised when the underlying vault backend cannot be reached."""


# ---------------------------------------------------------------------------
# Public Provider interface
# ---------------------------------------------------------------------------


class CredentialProvider(Protocol):
    """Stable boundary for Python business modules.

    Implementations are owned by Core. Business modules depend only on this
    protocol; the concrete class (``_WindowsCredentialVaultProvider``) is a
    private Core detail and MUST NOT be imported directly by business code.
    """

    def get_login(self, site_id: str) -> Login:
        """Return a :class:`Login` for ``site_id``.

        Raises a :class:`CredentialError` subclass on every failure path.
        """
        ...


# ---------------------------------------------------------------------------
# Internal backend contract (Core-only)
# ---------------------------------------------------------------------------


class _BackendError(Exception):
    """Base class for backend-internal exceptions."""


class _SiteNotFoundError(_BackendError):
    """Backend reports that the site is not in the vault."""


class _NotConfiguredError(_BackendError):
    """Backend reports that the site has no configured password."""


class _VaultMalformedError(_BackendError):
    """Backend reports that the vault file is missing, unreadable, or
    malformed."""


class _BackendUnavailableError(_BackendError):
    """Backend reports that it cannot be reached (executable missing, etc.)."""


class _VaultBackend(Protocol):
    """Internal Core-only protocol for vault access.

    Implementations return a JSON-decoded ``dict`` containing the canonical
    keys ``siteId``, ``url``, ``company``, ``username`` and ``password`` for
    a configured site. Backend-internal failure paths raise one of the
    ``_BackendError`` subclasses above. Business modules MUST NOT depend on
    this protocol.
    """

    def get_login_payload(self, site_id: str) -> dict:
        ...

    def describe(self) -> str:
        ...


# ---------------------------------------------------------------------------
# Public module-level helpers
# ---------------------------------------------------------------------------


_default_provider_singleton: CredentialProvider | None = None


def default_provider() -> CredentialProvider:
    """Return the canonical Core Credential Provider for this process.

    Business modules should call this function (or the convenience wrapper
    :func:`get_login`) rather than instantiating concrete classes directly.
    The returned object is process-wide.
    """

    global _default_provider_singleton
    if _default_provider_singleton is None:
        from ._vault_backend import _build_default_backend  # local import

        backend = _build_default_backend()
        _default_provider_singleton = _WindowsCredentialVaultProvider(backend=backend)
    return _default_provider_singleton


def get_login(site_id: str) -> Login:
    """Convenience wrapper around :func:`default_provider`."""
    return default_provider().get_login(site_id)


def _reset_default_provider_for_tests() -> None:  # pragma: no cover - test helper
    """Clear the cached default provider. Tests only."""
    global _default_provider_singleton
    _default_provider_singleton = None


# ---------------------------------------------------------------------------
# Implementation
# ---------------------------------------------------------------------------


class _WindowsCredentialVaultProvider:
    """Core's canonical Windows Vault-backed Provider.

    Construction is normally performed by :func:`default_provider`. Tests may pass
    an in-memory ``_VaultBackend`` directly to bypass the real backend. The
    PowerShell executable, module path, DPAPI scope and vault JSON file path
    are Core private implementation details; business modules MUST NOT depend
    on them.
    """

    def __init__(self, *, backend: _VaultBackend) -> None:
        if backend is None:
            raise ValueError("backend is required")
        self._backend = backend

    def get_login(self, site_id: str) -> Login:
        if not isinstance(site_id, str) or not _SITE_ID_PATTERN.match(site_id):
            raise CredentialError(
                site_id=site_id if isinstance(site_id, str) else "<invalid>",
                message=(
                    "site_id must be 1-64 characters using letters, digits, "
                    "'.', '_' or '-'."
                ),
            )

        try:
            payload = self._backend.get_login_payload(site_id)
        except _SiteNotFoundError:
            raise CredentialSiteNotFoundError(
                site_id=site_id,
                message=f"Credential site not found: {site_id}",
            )
        except _NotConfiguredError:
            raise CredentialNotConfiguredError(
                site_id=site_id,
                message=f"Credential is not configured for site: {site_id}",
            )
        except _VaultMalformedError as exc:
            raise CredentialVaultError(
                site_id=site_id,
                message=(
                    "Credential vault is missing, unreadable or malformed "
                    f"for site: {site_id}"
                ),
            ) from exc
        except _BackendUnavailableError as exc:
            raise CredentialProviderUnavailableError(
                site_id=site_id,
                message=(
                    "Credential provider backend is unavailable "
                    f"for site: {site_id}"
                ),
            ) from exc

        return _payload_to_login(site_id, payload)


def _payload_to_login(site_id: str, payload: dict) -> Login:
    """Translate a backend payload dict into a :class:`Login`.

    The payload is treated as untrusted. Missing / empty required fields
    raise :class:`CredentialVaultError` so the Provider can fail closed
    instead of returning a partial record.
    """

    if not isinstance(payload, dict):
        raise CredentialVaultError(
            site_id=site_id,
            message=f"Credential vault payload is invalid for site: {site_id}",
        )
    password = payload.get("password")
    username = payload.get("username")
    url = payload.get("url")
    if not isinstance(password, str) or password == "":
        raise CredentialVaultError(
            site_id=site_id,
            message=f"Credential vault payload has no password for site: {site_id}",
        )
    if not isinstance(username, str) or username == "":
        raise CredentialVaultError(
            site_id=site_id,
            message=(
                f"Credential vault payload has no username for site: {site_id}"
            ),
        )
    raw_company = payload.get("company")
    if raw_company is None or (isinstance(raw_company, str) and raw_company == ""):
        company: str | None = None
    elif isinstance(raw_company, str):
        company = raw_company
    else:
        raise CredentialVaultError(
            site_id=site_id,
            message=(
                f"Credential vault payload has invalid company for site: "
                f"{site_id}"
            ),
        )
    return Login(
        site_id=site_id,
        url=str(url) if isinstance(url, str) else "",
        username=username,
        password=password,
        company=company,
    )


# ---------------------------------------------------------------------------
# Internal discovery helpers (Core-only)
# ---------------------------------------------------------------------------


def _discover_pwsh() -> str | None:
    """Return the first available PowerShell executable, or ``None``."""
    for name in ("pwsh.exe", "pwsh", "powershell.exe", "powershell"):
        path = shutil.which(name)
        if path:
            return path
    return None