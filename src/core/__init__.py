"""Core: shared primitives and infrastructure capabilities.

Public surface is intentionally minimal. Business modules (research, workflow,
sheets, inso, quotation) MUST import only from this package and MUST NOT
reach into private modules (those prefixed with ``_``).

Canonical contract: ``docs/modules/CORE.md``.
"""

from .credential_provider import (
    CredentialError,
    CredentialNotConfiguredError,
    CredentialProvider,
    CredentialProviderUnavailableError,
    CredentialSiteNotFoundError,
    CredentialVaultError,
    Login,
    default_provider,
    get_login,
)
from .runtime_diagnostics import RuntimeDiagnostics, run_monitored, watch_runtime

__all__ = [
    "CredentialError",
    "CredentialNotConfiguredError",
    "CredentialProvider",
    "CredentialProviderUnavailableError",
    "CredentialSiteNotFoundError",
    "CredentialVaultError",
    "Login",
    "RuntimeDiagnostics",
    "default_provider",
    "get_login",
    "run_monitored",
    "watch_runtime",
]
