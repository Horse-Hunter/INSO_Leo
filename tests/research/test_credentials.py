import ast
from pathlib import Path

import pytest

from src.core import CredentialNotConfiguredError, Login
from src.research import credentials as credentials_module
from src.research.bom_ai import BOM_AI_SITE_ID, BomAiLogin
from src.research.credentials import (
    RESEARCH_CREDENTIAL_SITE_IDS,
    BomAiCoreCredentialProvider,
    CoreLoginBridge,
    CoreResearchCredentials,
    IcNetCoreLoginProvider,
    InsoCoreCredentialProvider,
)
from src.research.icnet import ICNET_SITE_ID, IcNetLogin
from src.research.inso_history import INSO_SITE_ID, InsoLogin

FORBIDDEN_CODE_TOKENS = (
    "_vault_backend",
    "credential_provider",
    "subprocess",
    "CredentialVault",
    ".psm1",
    "powershell",
    "pwsh",
    "DPAPI",
    "credential-vault.json",
)


class FakeProvider:
    """Minimal Core CredentialProvider double; never touches a real vault."""

    def __init__(self, logins: dict, errors: dict | None = None) -> None:
        self._logins = logins
        self._errors = errors or {}
        self.requested: list[str] = []

    def get_login(self, site_id: str) -> Login | None:
        self.requested.append(site_id)
        error = self._errors.get(site_id)
        if error is not None:
            raise error
        return self._logins.get(site_id)


def _login(site_id: str, company: str | None = None) -> Login:
    return Login(
        site_id=site_id,
        url=f"https://{site_id}/login",
        username="synthetic-user",
        password="synthetic-password",
        company=company,
    )


def test_canonical_site_ids_match_the_source_modules() -> None:
    assert RESEARCH_CREDENTIAL_SITE_IDS == (ICNET_SITE_ID, BOM_AI_SITE_ID, INSO_SITE_ID)
    assert RESEARCH_CREDENTIAL_SITE_IDS == ("ic.net.cn", "bom.ai", "yingsuo.alperp.cn")


def test_bridge_translates_core_login_into_each_native_login() -> None:
    provider = FakeProvider(
        {
            ICNET_SITE_ID: _login(ICNET_SITE_ID),
            BOM_AI_SITE_ID: _login(BOM_AI_SITE_ID, company="Synthetic Co"),
            INSO_SITE_ID: _login(INSO_SITE_ID, company="Synthetic Co"),
        }
    )
    bridge = CoreLoginBridge(provider)

    icnet = IcNetCoreLoginProvider(bridge).get_login(ICNET_SITE_ID)
    bom_ai = BomAiCoreCredentialProvider(bridge).get_login(BOM_AI_SITE_ID)
    inso = InsoCoreCredentialProvider(bridge).get_login(INSO_SITE_ID)

    assert isinstance(icnet, IcNetLogin)
    assert (icnet.username, icnet.password) == (
        "synthetic-user",
        "synthetic-password",
    )
    assert isinstance(bom_ai, BomAiLogin)
    assert (bom_ai.username, bom_ai.password, bom_ai.company) == (
        "synthetic-user",
        "synthetic-password",
        "Synthetic Co",
    )
    assert isinstance(inso, InsoLogin)
    assert inso.company == "Synthetic Co"
    assert provider.requested == [ICNET_SITE_ID, BOM_AI_SITE_ID, INSO_SITE_ID]
    for native in (icnet, bom_ai, inso):
        assert "synthetic-password" not in repr(native)


def test_bridge_fails_closed_without_leaking_provider_messages() -> None:
    provider = FakeProvider(
        {},
        errors={
            INSO_SITE_ID: CredentialNotConfiguredError(
                INSO_SITE_ID, "password=leaked-secret"
            )
        },
    )
    bridge = CoreLoginBridge(provider)

    assert bridge.login(INSO_SITE_ID) is None
    readiness = bridge.check(INSO_SITE_ID)
    assert readiness.available is False
    assert readiness.reason == "CredentialNotConfiguredError"
    assert "leaked-secret" not in repr(readiness)


def test_bridge_fails_closed_when_provider_returns_no_login() -> None:
    bridge = CoreLoginBridge(FakeProvider({}))

    assert bridge.login(BOM_AI_SITE_ID) is None
    assert bridge.check(BOM_AI_SITE_ID).reason == "CredentialProviderReturnedNoLogin"


def test_bridge_fails_closed_on_unexpected_provider_failure() -> None:
    provider = FakeProvider({}, errors={ICNET_SITE_ID: RuntimeError("boom")})

    readiness = CoreLoginBridge(provider).check(ICNET_SITE_ID)

    assert readiness.available is False
    assert readiness.reason == "RuntimeError"


def test_readiness_reports_each_missing_site_by_id_only() -> None:
    provider = FakeProvider(
        {
            ICNET_SITE_ID: _login(ICNET_SITE_ID),
            BOM_AI_SITE_ID: _login(BOM_AI_SITE_ID),
        }
    )
    credentials = CoreResearchCredentials(provider)

    readiness = credentials.site_readiness()

    assert [item.site_id for item in readiness] == list(
        RESEARCH_CREDENTIAL_SITE_IDS
    )
    assert [item.available for item in readiness] == [True, True, False]
    assert readiness[2].reason == "CredentialProviderReturnedNoLogin"


def _executable_source(path: Path) -> str:
    """Return module source with docstrings removed, for a strict code scan."""

    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(
            node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            continue
        body = node.body
        if (
            body
            and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)
        ):
            node.body = body[1:]
    return ast.unparse(tree)


@pytest.mark.parametrize("module_name", ["credentials.py", "runtime.py"])
def test_runtime_code_never_touches_vault_or_powershell_internals(
    module_name: str,
) -> None:
    package_dir = Path(credentials_module.__file__).parent
    code = _executable_source(package_dir / module_name)

    for token in FORBIDDEN_CODE_TOKENS:
        assert token not in code
    assert "from src.core import" in code
