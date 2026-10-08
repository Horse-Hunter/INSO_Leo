"""Sign every research site in, one after another, over the one CDP browser.

Owner request (2026-10-01): a single dashboard button that walks the sites in
order, so a run is started with live sessions rather than discovering a login
wall halfway through an inquiry. The sweep reports one verdict per site -- both
"all good" and "these need you" -- and the operator then repairs the rest by
hand in Chrome.

It owns no login recipe of its own. Each site's own module exports the routine
that completes its login (:func:`ensure_lcsc_signed_in`,
:func:`ensure_icnet_signed_in`, ...), and the run's price reads call the very
same functions, so a sweep can never disagree with a read about what "signed
in" means.

Three things are deliberate:

* successful sites reuse one background tab; failed sites keep their exact
  page for manual repair, while subsequent sites use the same browser context;
* every failure is reported as a closed outcome code plus our own wording --
  never page text, a selector or a credential;
* nothing is guessed. A site whose form cannot be found is reported as a
  failure, not as "probably fine".
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from time import monotonic, sleep
from typing import Any

from src.core import CredentialProvider
from src.gui.contracts import SiteLoginOutcome, SiteLoginResult
from src.research.bom_ai import BOM_AI_SITE_ID, BomAiBrowserConfig, sign_in_bom_ai
from src.research.cdp_pages import new_background_page
from src.research.credentials import CoreResearchCredentials
from src.research.findchips import (
    FINDCHIPS_LOGIN_URL,
    FINDCHIPS_SITE_ID,
    ensure_findchips_signed_in,
    findchips_login_page_open,
)
from src.research.hqew import (
    HQEW_LOGIN_URL,
    HQEW_SITE_ID,
    ensure_hqew_signed_in,
    hqew_login_page_open,
)
from src.research.icnet import (
    ICNET_LOGIN_URL,
    ICNET_SITE_ID,
    ensure_icnet_signed_in,
    icnet_login_page_open,
)
from src.research.inso_history import INSO_SITE_ID
from src.research.lcsc import (
    LCSC_CREDENTIAL_SITE_ID,
    LCSC_LOGIN_URL,
    ensure_lcsc_signed_in,
    lcsc_enter_system_if_offered,
    lcsc_login_page_open,
)
from src.research.site_login import SiteLoginError

from .diagnostics import log_step
from .inso_session import (
    InsoAuthenticationError,
    InsoSessionGuard,
    InsoSessionOutcome,
)

_LOG = logging.getLogger("inso.site_login_sweep")

#: How long a sweep waits for a page to quiet down after a navigation. Small on
#: purpose: every site's own readiness signal is read from the page, not slept
#: for, so this only covers the document's first paint.
_DEFAULT_SETTLE_MS = 2_000

#: Reason codes that mean "a human has to do this one", mapped to the verdict
#: the dashboard shows. Anything not named here is a failure, not a guess.
_NEEDS_HUMAN_CODES = frozenset(
    {
        "MANUAL_VERIFICATION_REQUIRED",
        "INTERACTIVE_CHALLENGE_REQUIRED",
    }
)
_NO_CREDENTIAL_CODES = frozenset(
    {
        "CREDENTIALS_UNAVAILABLE",
        "CREDENTIAL_NOT_CONFIGURED",
        "LOGIN_REQUIRED",
        "AUTHENTICATION_REQUIRED",
        "AUTHENTICATED_SHELL_UNAVAILABLE",
        "SESSION_IDENTITY_UNVERIFIED",
        "SECURITY_EVENT",
    }
)
_REJECTED_CODES = frozenset({"CREDENTIAL_REJECTED"})

#: Our own wording for each reason code. The operator reads this, so it says
#: what to do; it never carries anything the site or the page wrote.
_DETAILS: dict[str, str] = {
    "MANUAL_VERIFICATION_REQUIRED": "站点要求人工验证（滑块／验证码／短信）",
    "INTERACTIVE_CHALLENGE_REQUIRED": "站点要求人工验证（滑块／验证码／短信）",
    "CREDENTIAL_REJECTED": "站点拒绝了账号或密码",
    "LOGIN_REJECTED": "站点返回登录失败，请检查账号或站点验证",
    "CREDENTIALS_UNAVAILABLE": "凭证库中没有可用的登录信息",
    "CREDENTIAL_NOT_CONFIGURED": "凭证库中没有可用的登录信息",
    "LOGIN_REQUIRED": "站点要求登录，但凭证不可用",
    "AUTHENTICATION_REQUIRED": "站点要求登录，但凭证不可用",
    "LOGIN_FORM_UNAVAILABLE": "站点登录表单已变化，找不到可填写的字段",
    "LOGIN_CONTROL_AMBIGUOUS": "站点登录表单已变化，无法唯一定位控件",
    "LOGIN_OPTION_UNCONFIRMED": "登录前的选项（免登录／记住密码）未能勾选",
    "LOGIN_SUBMIT_FAILED": "登录按钮未能按下",
    "LOGIN_NOT_CONFIRMED": "已提交，但站点没有确认登录",
    "RESULT_CHANGED": "站点登录页结构已变化",
    "SESSION_STALE": "站点会话已失效",
    "LOGIN_PAGE_UNAVAILABLE": "登录页面未正常加载，请检查网络后重试",
    "CDP_CONTEXT_UNAVAILABLE": "浏览器里没有可用的会话上下文",
}


class SiteSweepError(RuntimeError):
    """The sweep could not even be attempted, so no site was tried."""

    def __init__(self, reason_code: str) -> None:
        super().__init__(reason_code)
        self.reason_code = reason_code


@dataclass(frozen=True, slots=True)
class SweepTab:
    """What one step is handed: the reusable tab, and the browser behind it."""

    page: Any
    browser: Any
    context: Any


@dataclass(frozen=True, slots=True)
class SiteSignInStep:
    """One site's turn in the sweep, in the order the operator sees them.

    ``run`` returns ``True`` when the site was *already* signed in and nothing
    had to be typed, ``False`` when this call established the login. It raises
    on anything else -- a raised error is never reported as a success.
    """

    key: str
    label: str
    run: Callable[[SweepTab], bool]


def outcome_for(reason_code: str) -> SiteLoginOutcome:
    """Map one site's own reason code onto the verdict the dashboard shows."""

    code = reason_code.upper()
    if code in _NEEDS_HUMAN_CODES:
        return SiteLoginOutcome.NEEDS_HUMAN
    if code in _REJECTED_CODES:
        return SiteLoginOutcome.REJECTED
    if code in _NO_CREDENTIAL_CODES:
        return SiteLoginOutcome.NO_CREDENTIAL
    if "CHALLENGE" in code or "CAPTCHA" in code or "OTP" in code:
        return SiteLoginOutcome.NEEDS_HUMAN
    if "REJECTED" in code:
        return SiteLoginOutcome.REJECTED
    if "CREDENTIAL" in code or "AUTHENTIC" in code:
        return SiteLoginOutcome.NO_CREDENTIAL
    return SiteLoginOutcome.UNAVAILABLE


def detail_for(reason_code: str) -> str:
    """Our own one-line explanation for a reason code, or empty when unknown."""

    return _DETAILS.get(reason_code.upper(), "")


class SiteLoginSweep:
    """Walk the sites in order over one attached browser, and say what happened."""

    def __init__(
        self,
        browser: Any,
        *,
        timeout_ms: int = 45_000,
        settle_ms: int = _DEFAULT_SETTLE_MS,
        new_tab: Callable[..., Any] = new_background_page,
        wait: Callable[[float], None] = sleep,
        clock: Callable[[], float] = monotonic,
        present_failures: bool = True,
        stop_requested: Callable[[], bool] = lambda: False,
    ) -> None:
        contexts = tuple(getattr(browser, "contexts", ()) or ())
        if len(contexts) != 1:
            # Every step needs *the* browsing context; an ambiguous or absent
            # one must stop the sweep rather than be guessed at.
            raise SiteSweepError("CDP_CONTEXT_UNAVAILABLE")
        self._browser = browser
        self._context = contexts[0]
        self._timeout_ms = timeout_ms
        self._settle_ms = settle_ms
        self._new_tab = new_tab
        self._wait = wait
        self._clock = clock
        self._present_failures = present_failures
        self._stop_requested = stop_requested
        self._page: Any | None = None

    def run(self, steps: Sequence[SiteSignInStep]) -> tuple[SiteLoginResult, ...]:
        """Try every step once, in order, and never let one stop the next."""

        results = []
        for step in steps:
            if self._stop_requested():
                break
            results.append(self._attempt(step))
        return tuple(results)

    def close(self) -> None:
        """Give back the tab this sweep opened; the session lives in the cookies."""

        page, self._page = self._page, None
        if page is None:
            return
        try:
            page.close()
        except Exception as exc:  # noqa: BLE001 - closing a tab is best effort
            _LOG.debug("the login sweep tab could not be closed (%s)", type(exc).__name__)

    # -- internals ---------------------------------------------------------

    def _attempt(self, step: SiteSignInStep) -> SiteLoginResult:
        try:
            already = bool(step.run(self._tab()))
        except Exception as exc:  # noqa: BLE001 - one site's failure is not the next one's
            # Leave the exact failed page for the operator. The next site gets
            # a fresh tab in the SAME context, never another browser/profile.
            page, self._page = self._page, None
            if page is not None and self._present_failures:
                try:
                    page.bring_to_front()
                except Exception as presentation_error:  # noqa: BLE001
                    _LOG.debug("could not present manual login tab (%s)",
                               type(presentation_error).__name__)
            return self._failure(step, exc)
        return SiteLoginResult(
            step.label,
            SiteLoginOutcome.ALREADY_SIGNED_IN
            if already
            else SiteLoginOutcome.SIGNED_IN,
        )

    def _failure(self, step: SiteSignInStep, exc: BaseException) -> SiteLoginResult:
        code = _reason_code(exc)
        if code is None:
            # No safe code crosses the boundary, so nothing specific is claimed.
            log_step(f"sweep-{step.key}", cause=exc)
            return SiteLoginResult(step.label, SiteLoginOutcome.UNAVAILABLE)
        return SiteLoginResult(step.label, outcome_for(code), detail_for(code))

    def _tab(self) -> SweepTab:
        if self._page is None:
            self._page = self._new_tab(
                self._browser, self._context, timeout_ms=self._timeout_ms
            )
        return SweepTab(self._page, self._browser, self._context)


def _reason_code(exc: BaseException) -> str | None:
    """The safe code an exception carries, whichever of our shapes it is."""

    for attribute in ("reason_code", "code"):
        value = getattr(exc, attribute, None)
        if isinstance(value, str) and value:
            return value
    return None


def build_site_sign_in_steps(
    *,
    bom_ai: BomAiBrowserConfig,
    provider: CredentialProvider | None = None,
    timeout_ms: int = 45_000,
    settle_ms: int = _DEFAULT_SETTLE_MS,
    wait: Callable[[float], None] = sleep,
    clock: Callable[[], float] = monotonic,
) -> tuple[SiteSignInStep, ...]:
    """The canonical sweep order, matching the order the sources are read in."""

    credentials = CoreResearchCredentials(provider)

    def settle(page: Any) -> None:
        try:
            page.wait_for_timeout(settle_ms)
        except Exception:  # noqa: BLE001 - a page that cannot be paused is still usable
            return

    def open_login(tab: SweepTab, url: str) -> None:
        response = tab.page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
        settle(tab.page)
        if (response is not None and response.status >= 400) or not tab.page.locator("body").inner_text().strip():
            # Missing login controls on a blank/error page is not a session.
            raise SiteLoginError("LOGIN_PAGE_UNAVAILABLE")

    def icnet(tab: SweepTab) -> bool:
        open_login(tab, ICNET_LOGIN_URL)
        if not icnet_login_page_open(tab.page):
            return True
        ensure_icnet_signed_in(
            tab.page,
            login=credentials.icnet.get_login(ICNET_SITE_ID),
            timeout_ms=timeout_ms,
            wait=wait,
            clock=clock,
        )
        return False

    def findchips(tab: SweepTab) -> bool:
        open_login(tab, FINDCHIPS_LOGIN_URL)
        if not findchips_login_page_open(tab.page):
            return True
        ensure_findchips_signed_in(
            tab.page,
            login=credentials.findchips.get_login(FINDCHIPS_SITE_ID),
            timeout_ms=timeout_ms,
            wait=wait,
            clock=clock,
        )
        return False

    def hqew(tab: SweepTab) -> bool:
        open_login(tab, HQEW_LOGIN_URL)
        if not hqew_login_page_open(tab.page):
            return True
        ensure_hqew_signed_in(
            tab.page,
            login=credentials.hqew.get_login(HQEW_SITE_ID),
            timeout_ms=timeout_ms,
            wait=wait,
            clock=clock,
        )
        return False

    def lcsc(tab: SweepTab) -> bool:
        open_login(tab, LCSC_LOGIN_URL)
        # JLC's SSO host serves two pages under one URL: the ordinary account
        # form, and an account that is already signed in there and only has to
        # be handed to the commerce site.
        if lcsc_enter_system_if_offered(tab.page, timeout_ms=timeout_ms):
            settle(tab.page)
            return True
        if not lcsc_login_page_open(tab.page):
            return True
        ensure_lcsc_signed_in(
            tab.page,
            login=credentials.lcsc.get_login(LCSC_CREDENTIAL_SITE_ID),
            timeout_ms=timeout_ms,
            wait=wait,
            clock=clock,
        )
        return False

    def bom_ai_step(tab: SweepTab) -> bool:
        open_login(tab, bom_ai.login_url)
        signed_in = sign_in_bom_ai(
            tab.page,
            config=bom_ai,
            login=credentials.bom_ai.get_login(BOM_AI_SITE_ID),
            timeout_ms=timeout_ms,
            wait=wait,
            clock=clock,
        )
        return not signed_in

    def inso(tab: SweepTab) -> bool:
        guard = InsoSessionGuard(
            login=credentials.inso.get_login(INSO_SITE_ID),
            context=lambda: tab.context,
            wait=wait,
            clock=clock,
        )
        status = guard.ensure_authenticated()
        if status.outcome is InsoSessionOutcome.DEAD:
            raise InsoAuthenticationError(
                status.reason_code or "AUTHENTICATION_REQUIRED"
            )
        _close_opened_page(guard.opened_page)
        return status.outcome is not InsoSessionOutcome.RESTORED

    return (
        SiteSignInStep("icnet", "IC 现货网", icnet),
        SiteSignInStep("findchips", "Findchips", findchips),
        SiteSignInStep("hqew", "华强电子网", hqew),
        SiteSignInStep("lcsc", "立创商城", lcsc),
        SiteSignInStep("bom-ai", "正能量（Bom.Ai）", bom_ai_step),
        SiteSignInStep("inso", "INSO ERP", inso),
    )


def _close_opened_page(page: Any | None) -> None:
    """Close the ERP tab the guard had to open; the session lives in the cookies."""

    if page is None:
        return
    try:
        page.close()
    except Exception as exc:  # noqa: BLE001 - closing a tab is best effort
        _LOG.debug("the INSO login tab could not be closed (%s)", type(exc).__name__)


def sweep_sites(
    browser: Any,
    *,
    bom_ai: BomAiBrowserConfig,
    provider: CredentialProvider | None = None,
    timeout_ms: int = 45_000,
    settle_ms: int = _DEFAULT_SETTLE_MS,
    wait: Callable[[float], None] = sleep,
    clock: Callable[[], float] = monotonic,
    sweep_factory: Callable[..., SiteLoginSweep] = SiteLoginSweep,
    present_failures: bool = True,
    stop_requested: Callable[[], bool] = lambda: False,
) -> tuple[SiteLoginResult, ...]:
    """Sweep the shared browser, closing only the successful reusable tab."""

    options = {}
    if not present_failures:
        options["present_failures"] = False
    if stop_requested():
        return ()
    if not present_failures:
        options["stop_requested"] = stop_requested
    sweep = sweep_factory(
        browser,
        **options,
        timeout_ms=timeout_ms,
        settle_ms=settle_ms,
        wait=wait,
        clock=clock,
    )
    try:
        return sweep.run(
            build_site_sign_in_steps(
                bom_ai=bom_ai,
                provider=provider,
                timeout_ms=timeout_ms,
                settle_ms=settle_ms,
                wait=wait,
                clock=clock,
            )
        )
    finally:
        sweep.close()
