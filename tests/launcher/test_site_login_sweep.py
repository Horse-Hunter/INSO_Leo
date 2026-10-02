"""The one-button login sweep: what it claims, and what it refuses to claim.

This file is the sweep's contract. The sweep is the thing the operator runs
before a round of inquiry, and its verdict decides whether they walk to Chrome
or not, so the interesting cases are the *failures*: a challenge must never be
reported as a success, one dead site must not swallow the other five, and an
unrecognized error must leave no claim behind at all.

The site-level login routines themselves are covered next to their own sites; a
few of them are stubbed here because what is under test is the sweep's
bookkeeping, not their markup.
"""

from __future__ import annotations

import logging

import pytest

from src.core import Login
from src.gui.contracts import SiteLoginOutcome, SiteLoginResult
from src.launcher import site_login_sweep as sweep_module
from src.launcher.inso_session import InsoAuthenticationError, InsoSessionOutcome
from src.launcher.site_login_sweep import (
    SiteLoginSweep,
    SiteSignInStep,
    SiteSweepError,
    build_site_sign_in_steps,
    detail_for,
    outcome_for,
    sweep_sites,
)
from src.research.site_login import SiteLoginError

TIMEOUT_MS = 1_000


class _Clickable:
    """What ``page.get_by_text`` answers with."""

    def __init__(self, page: _Page, count: int) -> None:
        self._page = page
        self._count = count

    def count(self) -> int:
        return self._count

    def click(self, *, timeout: int | None = None) -> None:
        self._page.clicks.append("text")

    def inner_text(self) -> str:
        return self._page.body_text


class _Body:
    """What ``page.locator("body")`` answers with."""

    def __init__(self, page: _Page) -> None:
        self._page = page

    def inner_text(self) -> str:
        return self._page.body_text

    def count(self) -> int:
        return 1

    @property
    def first(self) -> _Body:
        return self

    def click(self, *, timeout: int | None = None) -> None:
        self._page.clicks.append("body")


class _Page:
    """A tab that records what the sweep asked of it and nothing else."""

    def __init__(self, *, body_text: str = "synthetic site content", enter_system_count: int = 0) -> None:
        self.url = ""
        self.body_text = body_text
        self.enter_system_count = enter_system_count
        self.gotos: list[str] = []
        self.pauses: list[int] = []
        self.clicks: list[str] = []
        self.closed = False

    def goto(self, url: str, *, wait_until: str, timeout: int) -> None:
        assert wait_until == "domcontentloaded"
        assert timeout == TIMEOUT_MS
        self.gotos.append(url)
        self.url = url

    def wait_for_timeout(self, milliseconds: int) -> None:
        self.pauses.append(milliseconds)

    def locator(self, selector: str) -> _Body:
        assert selector == "body"
        return _Body(self)

    def get_by_text(self, text: str, *, exact: bool) -> _Clickable:
        assert exact is True
        count = self.enter_system_count if text == "进入系统" else 0
        return _Clickable(self, count)

    def close(self) -> None:
        self.closed = True


class _Context:
    """One browsing context, which is what the sweep insists on."""


class _Browser:
    def __init__(self, contexts: list | None = None) -> None:
        self.contexts = [_Context()] if contexts is None else contexts


class _Provider:
    """The Core provider boundary, answered from a dict."""

    def __init__(self) -> None:
        self.asked: list[str] = []

    def get_login(self, site_id: str) -> Login | None:
        self.asked.append(site_id)
        return Login(
            site_id=site_id,
            url=f"https://{site_id}/",
            username="the-user",
            password="the-password",
            company="深圳市英索实业有限公司",
        )


def _sweep(browser: _Browser | None = None) -> tuple[SiteLoginSweep, list[_Page]]:
    pages: list[_Page] = []

    def new_tab(_browser, _context, *, timeout_ms: int) -> _Page:
        assert timeout_ms == TIMEOUT_MS
        page = _Page()
        pages.append(page)
        return page

    return SiteLoginSweep(browser or _Browser(), timeout_ms=TIMEOUT_MS, new_tab=new_tab), pages


def _step(key: str, run) -> SiteSignInStep:
    return SiteSignInStep(key, key.upper(), run)


# ---------------------------------------------------------------------------
# Verdicts
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        ("MANUAL_VERIFICATION_REQUIRED", SiteLoginOutcome.NEEDS_HUMAN),
        ("INTERACTIVE_CHALLENGE_REQUIRED", SiteLoginOutcome.NEEDS_HUMAN),
        ("captcha_required", SiteLoginOutcome.NEEDS_HUMAN),
        ("CREDENTIAL_REJECTED", SiteLoginOutcome.REJECTED),
        ("CREDENTIALS_UNAVAILABLE", SiteLoginOutcome.NO_CREDENTIAL),
        ("CREDENTIAL_NOT_CONFIGURED", SiteLoginOutcome.NO_CREDENTIAL),
        ("AUTHENTICATION_REQUIRED", SiteLoginOutcome.NO_CREDENTIAL),
        ("RESULT_CHANGED", SiteLoginOutcome.UNAVAILABLE),
        ("LOGIN_NOT_CONFIRMED", SiteLoginOutcome.UNAVAILABLE),
    ],
)
def test_reason_codes_map_onto_the_verdicts_the_operator_reads(code, expected) -> None:
    assert outcome_for(code) is expected


def test_an_unknown_reason_code_is_not_guessed_at() -> None:
    assert outcome_for("SOMETHING_NEW") is SiteLoginOutcome.UNAVAILABLE
    assert detail_for("SOMETHING_NEW") == ""


def test_every_known_verdict_has_our_own_wording() -> None:
    """A code the operator can see must come with an explanation they can act on."""

    for code in (
        "MANUAL_VERIFICATION_REQUIRED",
        "CREDENTIAL_REJECTED",
        "CREDENTIALS_UNAVAILABLE",
        "LOGIN_FORM_UNAVAILABLE",
    ):
        assert detail_for(code)
        assert "http" not in detail_for(code)


# ---------------------------------------------------------------------------
# The sweep itself
# ---------------------------------------------------------------------------


def test_each_step_says_whether_it_had_to_type_anything() -> None:
    sweep, _pages = _sweep()
    report = sweep.run(
        [
            _step("already", lambda _tab: True),
            _step("fresh", lambda _tab: False),
        ]
    )

    assert report == (
        SiteLoginResult("ALREADY", SiteLoginOutcome.ALREADY_SIGNED_IN),
        SiteLoginResult("FRESH", SiteLoginOutcome.SIGNED_IN),
    )


def test_one_sites_failure_does_not_stop_the_others() -> None:
    def refuses(_tab):
        raise SiteLoginError("MANUAL_VERIFICATION_REQUIRED")

    sweep, _pages = _sweep()
    report = sweep.run(
        [_step("first", refuses), _step("second", lambda _tab: True)]
    )

    assert [result.outcome for result in report] == [
        SiteLoginOutcome.NEEDS_HUMAN,
        SiteLoginOutcome.ALREADY_SIGNED_IN,
    ]
    assert "人工验证" in report[0].detail


def test_failed_pages_survive_the_next_site_and_sweep_cleanup() -> None:
    def refuses(tab):
        tab.page.url = "https://example.invalid/manual-login"
        raise SiteLoginError("MANUAL_VERIFICATION_REQUIRED")

    sweep, pages = _sweep()
    sweep.run([_step("first", refuses), _step("second", lambda _tab: True)])
    sweep.close()
    assert len(pages) == 2
    assert pages[0].url.endswith("manual-login")
    assert not pages[0].closed
    assert pages[1].closed


def test_dead_erp_session_keeps_its_manual_login_page(monkeypatch) -> None:
    opened = _Page()

    class Guard:
        def __init__(self, **_kwargs):
            self.opened_page = opened

        def ensure_authenticated(self):
            from types import SimpleNamespace
            return SimpleNamespace(outcome=InsoSessionOutcome.DEAD,
                                   reason_code="MANUAL_VERIFICATION_REQUIRED")

    monkeypatch.setattr(sweep_module, "InsoSessionGuard", Guard)
    steps = build_site_sign_in_steps(bom_ai=_bom_ai_config(), provider=_Provider())
    with pytest.raises(InsoAuthenticationError):
        steps[-1].run(sweep_module.SweepTab(_Page(), _Browser(), _Context()))
    assert not opened.closed


def test_a_refused_credential_is_not_reported_as_a_challenge() -> None:
    """These two need different repairs, so they are never merged."""

    def refused(_tab):
        raise SiteLoginError("CREDENTIAL_REJECTED")

    sweep, _pages = _sweep()
    (result,) = sweep.run([_step("bom-ai", refused)])

    assert result.outcome is SiteLoginOutcome.REJECTED
    assert result.outcome is not SiteLoginOutcome.NEEDS_HUMAN


def test_a_missing_credential_is_reported_as_a_missing_credential() -> None:
    def missing(_tab):
        raise SiteLoginError("CREDENTIALS_UNAVAILABLE")

    sweep, _pages = _sweep()
    (result,) = sweep.run([_step("inso", missing)])

    assert result.outcome is SiteLoginOutcome.NO_CREDENTIAL


def test_the_erp_reports_a_dead_session_the_same_way_as_any_other_site() -> None:
    def dead(_tab):
        raise InsoAuthenticationError("AUTHENTICATION_REQUIRED")

    sweep, _pages = _sweep()
    (result,) = sweep.run([_step("inso", dead)])

    assert result.outcome is SiteLoginOutcome.NO_CREDENTIAL
    assert result.detail


def test_an_unrecognized_failure_claims_nothing_and_leaves_a_step_behind(caplog) -> None:
    """Nothing safe can be said, so nothing is said -- but the step is recorded."""

    def broken(_tab):
        raise RuntimeError("page text that must never be reported")

    sweep, _pages = _sweep()
    with caplog.at_level(logging.WARNING, logger="inso.diagnostics"):
        (result,) = sweep.run([_step("hqew", broken)])

    assert result.outcome is SiteLoginOutcome.UNAVAILABLE
    assert result.detail == ""
    steps = [getattr(record, "inso_step", None) for record in caplog.records]
    assert "sweep-hqew" in steps


def test_the_sweep_opens_one_tab_and_gives_it_back() -> None:
    sweep, pages = _sweep()
    sweep.run([_step("a", lambda _tab: True), _step("b", lambda _tab: True)])

    assert len(pages) == 1, "six sites must not leave six tabs behind"
    assert pages[0].closed is False
    sweep.close()
    assert pages[0].closed is True
    sweep.close()  # closing twice is not an error


def test_a_tab_that_will_not_close_does_not_break_the_sweep() -> None:
    sweep, pages = _sweep()
    sweep.run([_step("a", lambda _tab: True)])

    def explode() -> None:
        raise RuntimeError("already gone")

    pages[0].close = explode
    sweep.close()  # must not raise


def test_a_browser_without_exactly_one_context_is_refused_before_anything_is_tried() -> None:
    for contexts in ([], [_Context(), _Context()]):
        with pytest.raises(SiteSweepError) as error:
            SiteLoginSweep(_Browser(contexts), timeout_ms=TIMEOUT_MS)
        assert error.value.reason_code == "CDP_CONTEXT_UNAVAILABLE"


def test_a_page_that_cannot_be_paused_is_still_usable() -> None:
    """Settling is courtesy, not a prerequisite: a refusal must not become a crash."""

    calls: list[str] = []

    def run(tab) -> bool:
        calls.append(tab.page.url)
        return True

    sweep, pages = _sweep()

    def explode(milliseconds: int) -> None:
        raise RuntimeError("no such page")

    sweep.run([_step("a", run)])
    pages[0].wait_for_timeout = explode
    sweep.run([_step("b", run)])

    assert calls == ["", ""]


def test_sweep_sites_gives_the_tab_back_even_when_the_sweep_raises() -> None:
    pages: list[_Page] = []

    class _RaisingSweep:
        def __init__(self, _browser, **_kwargs) -> None:
            self.closed = False

        def run(self, _steps):
            raise RuntimeError("boom")

        def close(self) -> None:
            self.closed = True
            pages.append(_Page())

    with pytest.raises(RuntimeError):
        sweep_sites(
            _Browser(),
            bom_ai=object(),  # type: ignore[arg-type]
            provider=_Provider(),
            timeout_ms=TIMEOUT_MS,
            sweep_factory=_RaisingSweep,
        )

    assert len(pages) == 1, "the sweep is closed in a finally, not on the happy path"


# ---------------------------------------------------------------------------
# The canonical order, and the one shortcut it is allowed to take
# ---------------------------------------------------------------------------


def test_the_sweep_covers_every_source_the_run_will_read() -> None:
    steps = build_site_sign_in_steps(
        bom_ai=_bom_ai_config(), provider=_Provider(), timeout_ms=TIMEOUT_MS
    )

    assert [step.key for step in steps] == [
        "icnet",
        "findchips",
        "hqew",
        "lcsc",
        "bom-ai",
        "inso",
    ]
    assert all(step.label for step in steps)


def test_a_site_that_is_already_signed_in_is_never_typed_into(monkeypatch) -> None:
    """JLC hands an existing SSO session over; typing a password there is wrong."""

    def explode(*_args, **_kwargs) -> None:
        raise AssertionError("an already-signed-in site must not be logged into")

    monkeypatch.setattr(sweep_module, "ensure_lcsc_signed_in", explode)
    steps = build_site_sign_in_steps(
        bom_ai=_bom_ai_config(), provider=_Provider(), timeout_ms=TIMEOUT_MS
    )
    lcsc = next(step for step in steps if step.key == "lcsc")
    page = _Page(body_text="已登录账号 13940038A，点击【进入系统】", enter_system_count=1)
    tab = sweep_module.SweepTab(page, _Browser(), _Context())

    assert lcsc.run(tab) is True
    assert page.clicks == ["text"], "the handoff is taken, not the form"
    assert page.gotos and page.gotos[-1].endswith("passport.jlc.com/login")


def test_a_site_still_showing_its_form_is_typed_into_with_the_vault_credential(
    monkeypatch,
) -> None:
    seen: list[object] = []

    def record(_page, *, login, **_kwargs) -> None:
        seen.append(login)

    monkeypatch.setattr(sweep_module, "ensure_lcsc_signed_in", record)
    provider = _Provider()
    steps = build_site_sign_in_steps(
        bom_ai=_bom_ai_config(), provider=provider, timeout_ms=TIMEOUT_MS
    )
    lcsc = next(step for step in steps if step.key == "lcsc")
    page = _Page()  # no 「进入系统」 handout, so the URL stays on the SSO host
    tab = sweep_module.SweepTab(page, _Browser(), _Context())

    assert lcsc.run(tab) is False
    assert len(seen) == 1
    assert seen[0].username == "the-user"
    assert provider.asked == ["szlcsc.com"], "JLC is keyed by its commerce domain"


@pytest.mark.parametrize("key", ["icnet", "findchips", "hqew", "lcsc", "bom-ai"])
def test_blank_login_page_never_means_already_signed_in(key):
    steps = build_site_sign_in_steps(bom_ai=_bom_ai_config(), provider=_Provider(),
                                    timeout_ms=TIMEOUT_MS)
    step = next(step for step in steps if step.key == key)
    with pytest.raises(SiteLoginError, match="LOGIN_PAGE_UNAVAILABLE"):
        step.run(sweep_module.SweepTab(_Page(body_text=""), _Browser(), _Context()))


@pytest.mark.parametrize("key", ["icnet", "findchips", "hqew", "lcsc", "bom-ai"])
def test_http_error_login_page_never_means_already_signed_in(key):
    from types import SimpleNamespace
    provider = _Provider()
    steps = build_site_sign_in_steps(bom_ai=_bom_ai_config(), provider=provider,
                                    timeout_ms=TIMEOUT_MS)
    page = _Page(body_text="Service unavailable")
    page.goto = lambda *_args, **_kwargs: SimpleNamespace(status=503)
    step = next(step for step in steps if step.key == key)
    with pytest.raises(SiteLoginError, match="LOGIN_PAGE_UNAVAILABLE"):
        step.run(sweep_module.SweepTab(page, _Browser(), _Context()))
    assert provider.asked == []


def test_the_erp_tab_the_guard_had_to_open_is_closed_again(monkeypatch) -> None:
    opened = _Page()

    class _Status:
        outcome = InsoSessionOutcome.RESTORED
        reason_code = None

    class _Guard:
        def __init__(self, **_kwargs) -> None:
            self.opened_page = opened

        def ensure_authenticated(self):
            return _Status()

    monkeypatch.setattr(sweep_module, "InsoSessionGuard", _Guard)
    steps = build_site_sign_in_steps(
        bom_ai=_bom_ai_config(), provider=_Provider(), timeout_ms=TIMEOUT_MS
    )
    inso = next(step for step in steps if step.key == "inso")
    tab = sweep_module.SweepTab(_Page(), _Browser(), _Context())

    assert inso.run(tab) is False, "RESTORED means this sweep did the logging in"
    assert opened.closed is True


def _bom_ai_config():
    return sweep_module.BomAiBrowserConfig(
        login_url="https://www.bom.ai/",
        result_url_template="https://www.bom.ai/components-price/{mpn}.html",
        username_selector="#accountName",
        password_selector="#smspassword",
        login_button_selector="#smsLoginBtn",
        company_selector="#companyName",
    )
