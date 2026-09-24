"""Research V1 production runtime composition.

Research owns its production runtime. This module builds the single
``ResearchService`` used by the Workflow V1 live smoke from an explicit,
Git-ignored, non-secret local configuration file (default
``runtime/research.json``), and it reports observable, fail-closed readiness for
every prerequisite:

    * canonical Core credential site availability, reported by ``site_id``
      only and never by value,
    * the loopback CDP endpoint required by the HQEW read-only session and by
      the optional IC.net CDP acquisition path,
    * presence and validity of the runtime configuration itself.

The configuration file must never contain a secret. Credentials are retrieved
only through ``src.core`` (see :mod:`src.research.credentials`).

Configuration schema (all values non-secret)::

    {
      "excel_output_path": "data/调研价格.xlsx",
      "browser": {"channel": "chrome", "headless": false,
                  "timeout_ms": 45000, "settle_ms": 3000},
      "cdp": {"cdp_url": "http://127.0.0.1:9222"},
      "icnet": {"mode": "credentials"},
      "bom_ai": {
        "login_url": "https://<bom.ai login page>",
        "result_url_template": "https://<bom.ai model page>/{mpn}",
        "username_selector": "...",
        "password_selector": "...",
        "login_button_selector": "...",
        "company_selector": null,
        "post_login_ready_selector": null
      },
      "inso": {
        "login_url": "https://<inso login page>",
        "cdp_url": "http://127.0.0.1:9222",
        "pagesize": 30
      }
    }

``excel_output_path``, ``bom_ai``, and ``inso`` are required; ``browser``,
``cdp``, and ``icnet`` fall back to defaults. ``icnet.mode`` is
``credentials`` (Core Provider login in a fresh browser) or ``cdp`` (read
through the Owner-authorized ordinary Chrome session on ``cdp.cdp_url``).
INSO is read through the same Owner-authorised CDP session on
``inso.cdp_url`` (falls back to ``cdp.cdp_url``); Stock_VenQuote history is
the only approved read surface.
"""

from __future__ import annotations

import argparse
import json
import socket
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from ipaddress import ip_address
from pathlib import Path
from urllib.parse import urlsplit

from src.core import CredentialProvider

from .bom_ai import (
    BomAiAdapter,
    BomAiAuthenticatedBrowser,
    BomAiBrowserConfig,
    BomAiCredentialedClient,
    PlaywrightBomAiAuthenticatedBrowser,
)
from .credentials import (
    RESEARCH_CREDENTIAL_SITE_IDS,
    CoreResearchCredentials,
    CredentialReadiness,
)
from .ecb_fx import EcbDailyUsdRmbProvider
from .excel_output import ResearchExcelOutput
from .findchips import FindchipsAdapter, FindchipsHttpClient, FindchipsPageClient
from .fx import UsdRmbProvider
from .hqew import CdpHqewClient, HqewAdapter, HqewPageClient
from .icnet import (
    CdpIcNetClient,
    IcNetAdapter,
    IcNetPageClient,
    PlaywrightIcNetClient,
)
from .inso_history import (
    InsoBrowserConfig,
    InsoCredentialedClient,
    InsoHistoryAdapter,
    InsoReadOnlyBrowser,
    PlaywrightInsoReadOnlyBrowser,
)
from .lcsc import LcscAdapter, LcscBrowserClient, LcscPageClient
from .service import ResearchService

DEFAULT_RUNTIME_CONFIG_RELATIVE_PATH = Path("runtime") / "research.json"


class ResearchRuntimeError(RuntimeError):
    """Base class for Research runtime composition failures."""


class ResearchRuntimeConfigError(ResearchRuntimeError):
    """The Git-ignored runtime configuration is missing or invalid."""


class ResearchRuntimePrerequisiteError(ResearchRuntimeError):
    """A required runtime prerequisite is unavailable, so Research fails closed."""


@dataclass(frozen=True, slots=True)
class BrowserRuntimeConfig:
    """Shared Playwright options for every Research browser acquisition."""

    channel: str = "chrome"
    headless: bool = False
    timeout_ms: int = 45_000
    settle_ms: int = 3_000

    def __post_init__(self) -> None:
        if not isinstance(self.channel, str):
            raise TypeError("browser channel must be a string")
        if not self.channel.strip():
            raise ValueError("browser channel must not be blank")
        if not isinstance(self.headless, bool):
            raise TypeError("browser headless must be a boolean")
        for name, value in (
            ("timeout_ms", self.timeout_ms),
            ("settle_ms", self.settle_ms),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"browser {name} must be a positive integer")


@dataclass(frozen=True, slots=True)
class CdpRuntimeConfig:
    """Loopback CDP endpoint of the Owner-authorized ordinary Chrome session."""

    cdp_url: str = "http://127.0.0.1:9222"

    def __post_init__(self) -> None:
        try:
            parsed = urlsplit(self.cdp_url)
            port = parsed.port
        except ValueError as exc:
            raise ValueError("cdp_url must be a valid loopback URL") from exc
        if (
            parsed.scheme not in {"http", "https"}
            or parsed.hostname is None
            or not _is_loopback_hostname(parsed.hostname)
        ):
            raise ValueError("cdp_url must be a loopback http(s) URL")
        if port is None:
            raise ValueError("cdp_url must include an explicit port")


@dataclass(frozen=True, slots=True)
class IcNetRuntimeConfig:
    """IC.net acquisition path selector.

    ``credentials`` logs in with the Core Provider login in a freshly launched
    browser. ``cdp`` reads through the Owner-authorized ordinary Chrome session,
    which is required when IC.net serves an empty stub to a newly launched
    browser. Neither mode bypasses a login, challenge, or security check.
    """

    mode: str = "credentials"

    def __post_init__(self) -> None:
        if self.mode not in {"credentials", "cdp"}:
            raise ValueError("icnet mode must be 'credentials' or 'cdp'")


@dataclass(frozen=True, slots=True)
class ResearchRuntimeConfig:
    """Validated non-secret runtime configuration for the Research service."""

    excel_output_path: Path
    bom_ai: BomAiBrowserConfig
    inso: InsoBrowserConfig
    browser: BrowserRuntimeConfig = field(default_factory=BrowserRuntimeConfig)
    cdp: CdpRuntimeConfig = field(default_factory=CdpRuntimeConfig)
    icnet: IcNetRuntimeConfig = field(default_factory=IcNetRuntimeConfig)

    def __post_init__(self) -> None:
        if not isinstance(self.excel_output_path, Path):
            raise TypeError("excel_output_path must be a pathlib.Path")
        if not self.excel_output_path.name:
            raise ValueError("excel_output_path must name a workbook file")


@dataclass(frozen=True, slots=True)
class ResearchRuntimeReadiness:
    """Observable, non-secret readiness for the Research production runtime."""

    credentials: tuple[CredentialReadiness, ...]
    cdp_url: str
    cdp_reachable: bool

    @property
    def missing_site_ids(self) -> tuple[str, ...]:
        return tuple(
            item.site_id for item in self.credentials if not item.available
        )

    @property
    def ready(self) -> bool:
        return not self.missing_site_ids and self.cdp_reachable

    def issues(self) -> tuple[str, ...]:
        """Return non-secret readiness problems in canonical source order."""

        problems = [
            f"credential site not ready: {item.site_id} ({item.reason})"
            for item in self.credentials
            if not item.available
        ]
        if not self.cdp_reachable:
            problems.append(
                f"authenticated CDP endpoint not reachable: {self.cdp_url}"
            )
        return tuple(problems)

    def manual_action(self) -> str | None:
        """Return the single Owner action required, or ``None`` when ready."""

        actions: list[str] = []
        if self.missing_site_ids:
            actions.append(
                "在 Vault Manager 中补配置 Site ID: "
                + ", ".join(self.missing_site_ids)
            )
        if not self.cdp_reachable:
            actions.append(
                f"启动已授权的本地 Chrome 并开放 CDP: {self.cdp_url}"
            )
        return "；".join(actions) if actions else None


def _is_loopback_hostname(hostname: str) -> bool:
    if hostname.casefold() == "localhost":
        return True
    try:
        return ip_address(hostname).is_loopback
    except ValueError:
        return False


def default_runtime_config_path() -> Path:
    """Return the default Git-ignored runtime configuration path."""

    return (
        Path(__file__).resolve().parents[2] / DEFAULT_RUNTIME_CONFIG_RELATIVE_PATH
    )


def load_runtime_config(path: str | Path | None = None) -> ResearchRuntimeConfig:
    """Read and validate the non-secret runtime configuration.

    Raises :class:`ResearchRuntimeConfigError` when the file is missing, is not
    JSON, or omits/invalidates a required non-secret setting.
    """

    config_path = Path(path) if path is not None else default_runtime_config_path()
    if not config_path.is_file():
        raise ResearchRuntimeConfigError(
            f"runtime configuration file not found: {config_path}"
        )
    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ResearchRuntimeConfigError(
            f"runtime configuration is not readable JSON: {config_path}"
        ) from exc
    if not isinstance(raw, Mapping):
        raise ResearchRuntimeConfigError(
            "runtime configuration root must be a JSON object"
        )
    return _config_from_mapping(raw)


def assess_readiness(
    cdp_url: str,
    *,
    provider: CredentialProvider | None = None,
    cdp_probe: Callable[[str], bool] | None = None,
) -> ResearchRuntimeReadiness:
    """Report credential and CDP readiness without exposing credential values.

    ``cdp_url`` is the only runtime input required, so readiness for the
    credential and HQEW prerequisites can be checked before the DOM-level
    runtime configuration exists.
    """

    credentials = CoreResearchCredentials(provider)
    probe = cdp_probe or probe_loopback_endpoint
    return ResearchRuntimeReadiness(
        credentials=tuple(
            credentials.check(site_id)
            for site_id in RESEARCH_CREDENTIAL_SITE_IDS
        ),
        cdp_url=cdp_url,
        cdp_reachable=probe(cdp_url),
    )


def require_ready(readiness: ResearchRuntimeReadiness) -> None:
    """Fail closed with an observable error when a prerequisite is missing."""

    if not readiness.ready:
        raise ResearchRuntimePrerequisiteError("; ".join(readiness.issues()))


def probe_loopback_endpoint(url: str, *, timeout: float = 1.0) -> bool:
    """Return whether a loopback TCP endpoint accepts a connection."""

    try:
        parsed = urlsplit(url)
        port = parsed.port
    except ValueError as exc:
        raise ValueError("endpoint must be a valid loopback URL") from exc
    host = parsed.hostname
    if host is None or not _is_loopback_hostname(host):
        raise ValueError("only loopback endpoints may be probed")
    if port is None:
        port = 443 if parsed.scheme == "https" else 80
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def build_icnet_client(
    config: ResearchRuntimeConfig,
    credentials: CoreResearchCredentials,
    *,
    icnet_client: IcNetPageClient | None = None,
) -> IcNetPageClient:
    """Select the configured IC.net acquisition path."""

    if icnet_client is not None:
        return icnet_client
    browser = config.browser
    if config.icnet.mode == "cdp":
        return CdpIcNetClient(
            cdp_url=config.cdp.cdp_url,
            timeout_ms=browser.timeout_ms,
            settle_ms=browser.settle_ms,
        )
    return PlaywrightIcNetClient(
        credentials.icnet,
        timeout_ms=browser.timeout_ms,
        headless=browser.headless,
        channel=browser.channel,
    )


def build_research_service(
    config: ResearchRuntimeConfig,
    *,
    provider: CredentialProvider | None = None,
    fx_provider: UsdRmbProvider | None = None,
    clock: Callable[[], datetime] | None = None,
    icnet_client: IcNetPageClient | None = None,
    findchips_client: FindchipsPageClient | None = None,
    hqew_client: HqewPageClient | None = None,
    lcsc_client: LcscPageClient | None = None,
    bom_ai_browser: BomAiAuthenticatedBrowser | None = None,
    inso_browser: InsoReadOnlyBrowser | None = None,
) -> ResearchService:
    """Compose the canonical ``ResearchService`` from validated runtime config.

    Every acquisition boundary is injectable so deterministic tests can prove
    that all canonical sources are wired without touching the network. Missing
    per-source prerequisites still surface as observable fail-closed results at
    execution time.
    """

    credentials = CoreResearchCredentials(provider)
    fx = fx_provider or EcbDailyUsdRmbProvider()
    browser = config.browser

    icnet_client = build_icnet_client(
        config, credentials, icnet_client=icnet_client
    )
    findchips_client = findchips_client or FindchipsHttpClient()
    hqew_client = hqew_client or CdpHqewClient(
        cdp_url=config.cdp.cdp_url,
        timeout_ms=browser.timeout_ms,
        settle_ms=browser.settle_ms,
    )
    lcsc_client = lcsc_client or LcscBrowserClient(
        timeout_ms=browser.timeout_ms,
        settle_ms=browser.settle_ms,
        browser_channel=browser.channel,
        headless=browser.headless,
    )
    bom_ai_browser = bom_ai_browser or PlaywrightBomAiAuthenticatedBrowser(
        config.bom_ai,
        timeout_ms=browser.timeout_ms,
        settle_ms=browser.settle_ms,
        browser_channel=browser.channel,
        headless=browser.headless,
    )
    inso_browser = inso_browser or PlaywrightInsoReadOnlyBrowser(
        config.inso,
        timeout_ms=browser.timeout_ms,
        settle_ms=browser.settle_ms,
    )

    return ResearchService(
        icnet=IcNetAdapter(icnet_client, clock=clock),
        findchips=FindchipsAdapter(findchips_client, fx, clock=clock),
        hqew=HqewAdapter(hqew_client, clock=clock),
        lcsc=LcscAdapter(lcsc_client, fx, clock=clock),
        bom_ai=BomAiAdapter(
            BomAiCredentialedClient(credentials.bom_ai, bom_ai_browser),
            fx_provider=fx,
            clock=clock,
        ),
        inso=InsoHistoryAdapter(
            InsoCredentialedClient(credentials.inso, inso_browser),
            fx,
            clock=clock,
        ),
        output=ResearchExcelOutput(config.excel_output_path),
    )


def build_production_research_service(
    config: ResearchRuntimeConfig | None = None,
    *,
    config_path: str | Path | None = None,
    provider: CredentialProvider | None = None,
    cdp_probe: Callable[[str], bool] | None = None,
) -> ResearchService:
    """Load config, verify every prerequisite, then compose; fail closed."""

    resolved = config if config is not None else load_runtime_config(config_path)
    require_ready(
        assess_readiness(
            resolved.cdp.cdp_url, provider=provider, cdp_probe=cdp_probe
        )
    )
    return build_research_service(resolved, provider=provider)


def format_readiness(readiness: ResearchRuntimeReadiness) -> str:
    """Render a non-secret readiness report for Owner/ops use."""

    lines = ["Research runtime readiness"]
    for item in readiness.credentials:
        state = "READY" if item.available else f"NOT READY ({item.reason})"
        lines.append(f"  credential {item.site_id}: {state}")
    cdp_state = "READY" if readiness.cdp_reachable else "NOT REACHABLE"
    lines.append(f"  authorized cdp {readiness.cdp_url}: {cdp_state}")
    lines.append(f"runtime readiness: {'READY' if readiness.ready else 'BLOCKED'}")
    action = readiness.manual_action()
    if action:
        lines.append(f"manual action: {action}")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the read-only Research runtime readiness check as a CLI."""

    parser = argparse.ArgumentParser(
        description="Research V1 read-only runtime readiness check"
    )
    parser.add_argument(
        "--config",
        default=None,
        help=(
            "path to the Git-ignored non-secret runtime configuration JSON "
            f"(default: {DEFAULT_RUNTIME_CONFIG_RELATIVE_PATH})"
        ),
    )
    args = parser.parse_args(argv)
    try:
        config = load_runtime_config(args.config)
    except ResearchRuntimeConfigError as exc:
        print(f"runtime config error: {exc}")
        return 2
    readiness = assess_readiness(config.cdp.cdp_url)
    print(format_readiness(readiness))
    return 0 if readiness.ready else 1


def _config_from_mapping(raw: Mapping) -> ResearchRuntimeConfig:
    browser_section = _optional_mapping(raw, "browser")
    cdp_section = _optional_mapping(raw, "cdp")
    icnet_section = _optional_mapping(raw, "icnet")
    bom_ai_section = _require_mapping(raw, "bom_ai")
    inso_section = _require_mapping(raw, "inso")

    inso_kwargs: dict = {
        "login_url": _require_text(inso_section, "login_url", prefix="inso"),
        "cdp_url": _optional_text(inso_section, "cdp_url")
        or CdpRuntimeConfig().cdp_url,
        "pagesize": _optional_int(inso_section, "pagesize", default=30),
    }

    try:
        return ResearchRuntimeConfig(
            excel_output_path=Path(
                _require_text(raw, "excel_output_path")
            ),
            bom_ai=BomAiBrowserConfig(
                login_url=_require_text(
                    bom_ai_section, "login_url", prefix="bom_ai"
                ),
                result_url_template=_require_text(
                    bom_ai_section, "result_url_template", prefix="bom_ai"
                ),
                username_selector=_require_text(
                    bom_ai_section, "username_selector", prefix="bom_ai"
                ),
                password_selector=_require_text(
                    bom_ai_section, "password_selector", prefix="bom_ai"
                ),
                login_button_selector=_require_text(
                    bom_ai_section, "login_button_selector", prefix="bom_ai"
                ),
                company_selector=_optional_text(
                    bom_ai_section, "company_selector"
                ),
                post_login_ready_selector=_optional_text(
                    bom_ai_section, "post_login_ready_selector"
                ),
            ),
            inso=InsoBrowserConfig(**inso_kwargs),
            browser=BrowserRuntimeConfig(
                channel=_optional_text(browser_section, "channel") or "chrome",
                headless=_optional_bool(
                    browser_section, "headless", default=False
                ),
                timeout_ms=_optional_int(
                    browser_section, "timeout_ms", default=45_000
                ),
                settle_ms=_optional_int(
                    browser_section, "settle_ms", default=3_000
                ),
            ),
            cdp=CdpRuntimeConfig(
                cdp_url=_optional_text(cdp_section, "cdp_url")
                or CdpRuntimeConfig().cdp_url
            ),
            icnet=IcNetRuntimeConfig(
                mode=_optional_text(icnet_section, "mode") or "credentials"
            ),
        )
    except (TypeError, ValueError) as exc:
        raise ResearchRuntimeConfigError(
            "runtime configuration value is invalid"
        ) from exc


def _require_mapping(raw: Mapping, key: str) -> Mapping:
    value = raw.get(key)
    if not isinstance(value, Mapping):
        raise ResearchRuntimeConfigError(
            f"runtime configuration requires a JSON object at '{key}'"
        )
    return value


def _optional_mapping(raw: Mapping, key: str) -> Mapping:
    value = raw.get(key)
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise ResearchRuntimeConfigError(
            f"runtime configuration '{key}' must be a JSON object"
        )
    return value


def _require_text(raw: Mapping, key: str, *, prefix: str | None = None) -> str:
    value = raw.get(key)
    label = f"{prefix}.{key}" if prefix else key
    if not isinstance(value, str) or not value.strip():
        raise ResearchRuntimeConfigError(
            f"runtime configuration requires a non-empty string at '{label}'"
        )
    return value


def _optional_text(raw: Mapping, key: str, *, prefix: str | None = None) -> str | None:
    value = raw.get(key)
    if value is None:
        return None
    label = f"{prefix}.{key}" if prefix else key
    if not isinstance(value, str) or not value.strip():
        raise ResearchRuntimeConfigError(
            f"runtime configuration '{label}' must be a non-empty string"
        )
    return value


def _optional_bool(raw: Mapping, key: str, *, default: bool) -> bool:
    value = raw.get(key)
    if value is None:
        return default
    if not isinstance(value, bool):
        raise ResearchRuntimeConfigError(
            f"runtime configuration '{key}' must be a boolean"
        )
    return value


def _optional_int(raw: Mapping, key: str, *, default: int) -> int:
    value = raw.get(key)
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, int):
        raise ResearchRuntimeConfigError(
            f"runtime configuration '{key}' must be an integer"
        )
    return value


def _optional_text_sequence(raw: Mapping, key: str) -> tuple[str, ...] | None:
    value = raw.get(key)
    if value is None:
        return None
    if not isinstance(value, list) or not value:
        raise ResearchRuntimeConfigError(
            f"runtime configuration '{key}' must be a non-empty list"
        )
    if any(
        not isinstance(item, str) or not item.strip() for item in value
    ):
        raise ResearchRuntimeConfigError(
            f"runtime configuration '{key}' must contain non-empty strings"
        )
    return tuple(value)


if __name__ == "__main__":  # pragma: no cover - manual readiness entry point
    raise SystemExit(main())
