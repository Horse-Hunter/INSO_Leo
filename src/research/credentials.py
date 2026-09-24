"""Research-side binding to the canonical Core Python Credential Provider.

Business modules consume credentials only through ``src.core``. Research must
never call PowerShell, read DPAPI, read a vault path, parse
``credential-vault.json``, or build a second credential store. This module is
the single Research-owned adapter that:

    * calls the canonical Core Provider (``get_login`` / ``default_provider``),
    * translates a Core :class:`~src.core.Login` into the Research-native login
      objects expected by the existing source adapters,
    * fails closed on every provider failure, and
    * reports per-site readiness without ever exposing credential values.

A failed resolution yields ``None`` so the source adapters keep producing an
observable ``SOURCE_UNAVAILABLE`` result instead of attempting a fake login.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.core import CredentialProvider, Login, get_login

from .bom_ai import BOM_AI_SITE_ID, BomAiLogin
from .icnet import ICNET_SITE_ID, IcNetLogin
from .inso_history import INSO_SITE_ID, InsoLogin

RESEARCH_CREDENTIAL_SITE_IDS: tuple[str, ...] = (
    ICNET_SITE_ID,
    BOM_AI_SITE_ID,
    INSO_SITE_ID,
)
"""Canonical login sites the Research production runtime requires."""


@dataclass(frozen=True, slots=True)
class CredentialReadiness:
    """Non-secret availability summary for one canonical credential site."""

    site_id: str
    available: bool
    reason: str | None = None

    def __post_init__(self) -> None:
        if self.available and self.reason is not None:
            raise ValueError("available credentials must not carry a reason")
        if not self.available and not self.reason:
            raise ValueError("unavailable credentials must record a safe reason")


def _safe_reason(exc: BaseException) -> str:
    """Return only the exception class name, never a provider message."""

    name = type(exc).__name__
    return name if name else "CredentialError"


class CoreLoginBridge:
    """Single fail-closed boundary around the canonical Core Provider."""

    def __init__(self, provider: CredentialProvider | None = None) -> None:
        self._provider = provider

    def resolve(self, site_id: str) -> tuple[Login | None, str | None]:
        """Return ``(login, None)`` or ``(None, safe_reason)``; never raises."""

        try:
            login = (
                self._provider.get_login(site_id)
                if self._provider is not None
                else get_login(site_id)
            )
        except Exception as exc:  # noqa: BLE001 - any provider failure fails closed
            return None, _safe_reason(exc)
        if not isinstance(login, Login):
            return None, "CredentialProviderReturnedNoLogin"
        return login, None

    def login(self, site_id: str) -> Login | None:
        """Return the Core login or ``None`` when unavailable."""

        return self.resolve(site_id)[0]

    def check(self, site_id: str) -> CredentialReadiness:
        """Report availability for one site without keeping the credential."""

        login, reason = self.resolve(site_id)
        available = login is not None
        del login
        return CredentialReadiness(
            site_id=site_id,
            available=available,
            reason=None if available else reason,
        )


class IcNetCoreLoginProvider:
    """Research IC.net credential capability backed by the Core Provider."""

    def __init__(self, bridge: CoreLoginBridge) -> None:
        self._bridge = bridge

    def get_login(self, site_id: str) -> IcNetLogin | None:
        login = self._bridge.login(site_id)
        if login is None:
            return None
        return IcNetLogin(username=login.username, password=login.password)


class BomAiCoreCredentialProvider:
    """Research Bom.Ai credential capability backed by the Core Provider."""

    def __init__(self, bridge: CoreLoginBridge) -> None:
        self._bridge = bridge

    def get_login(self, site_id: str) -> BomAiLogin | None:
        login = self._bridge.login(site_id)
        if login is None:
            return None
        return BomAiLogin(login.username, login.password, login.company)


class InsoCoreCredentialProvider:
    """Research INSO credential capability backed by the Core Provider."""

    def __init__(self, bridge: CoreLoginBridge) -> None:
        self._bridge = bridge

    def get_login(self, site_id: str) -> InsoLogin | None:
        login = self._bridge.login(site_id)
        if login is None:
            return None
        return InsoLogin(login.username, login.password, login.company)


class CoreResearchCredentials:
    """Research credential bundle bound once to the canonical Core Provider."""

    def __init__(self, provider: CredentialProvider | None = None) -> None:
        self._bridge = CoreLoginBridge(provider)
        self.icnet = IcNetCoreLoginProvider(self._bridge)
        self.bom_ai = BomAiCoreCredentialProvider(self._bridge)
        self.inso = InsoCoreCredentialProvider(self._bridge)

    def check(self, site_id: str) -> CredentialReadiness:
        """Report availability for one canonical site."""

        return self._bridge.check(site_id)

    def site_readiness(self) -> tuple[CredentialReadiness, ...]:
        """Report availability for every Research-required site."""

        return tuple(
            self._bridge.check(site_id)
            for site_id in RESEARCH_CREDENTIAL_SITE_IDS
        )
