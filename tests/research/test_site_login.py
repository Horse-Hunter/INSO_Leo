"""The shared login may only ever act on a control it has proven is the one.

These tests exist because the failure they prevent is *silent*. On
``passport.jlc.com`` (measured live 2026-10-01) the LCSC form's
``text="登录"`` also matched the page's own ``<h2>`` heading, which sits above
the form in DOM order. ``page.click`` is not strict, so it clicked the heading,
the login button was never pressed, the form was never submitted, and the run
only surfaced as an unexplained "not confirmed" a settle-timeout later.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from src.research.site_login import (
    LoginCheckbox,
    LoginForm,
    SiteLoginError,
    apply_login_options,
    await_login_outcome,
    rejection_present,
    solve_slider_challenge,
    submit_login_form,
    unique_visible_control,
)

TIMEOUT_MS = 1_000


class _Match:
    """One element a selector matched.

    ``checked`` models the checkbox a styled label stands for: ``None`` means
    the label owns no checkbox the page will admit to, which is the case the
    option logic has to refuse rather than guess at.
    """

    def __init__(
        self,
        page: _Page,
        name: str,
        *,
        visible: bool = True,
        checked: bool | None = None,
        geometry: dict | None = None,
        turns_on: bool = True,
    ) -> None:
        self._page = page
        self.name = name
        self._visible = visible
        self.checked = checked
        self.geometry = geometry
        self._turns_on = turns_on

    def is_visible(self) -> bool:
        return self._visible

    def fill(self, value: str, *, timeout: int) -> None:
        assert timeout > 0
        self._page.fills.append((self.name, value))

    def click(self, *, timeout: int) -> None:
        assert timeout > 0
        self._page.clicks.append(self.name)
        if self.checked is not None and self._turns_on:
            self.checked = not self.checked

    def evaluate(self, script: str) -> object:
        del script  # the fake answers for whichever script it is handed
        return self.geometry if self.geometry is not None else self.checked


class _Mouse:
    """Records the gesture so a drag can be read back as a path, not a blur."""

    def __init__(self, page: _Page) -> None:
        self._page = page
        self.events: list[tuple] = []

    def move(self, x: float, y: float) -> None:
        self.events.append(("move", round(x, 3), round(y, 3)))

    def down(self) -> None:
        self.events.append(("down",))

    def up(self) -> None:
        self.events.append(("up",))
        if self._page.on_drag_end is not None:
            self._page.on_drag_end()

    @property
    def xs(self) -> list[float]:
        return [event[1] for event in self.events if event[0] == "move"]

    def count(self, kind: str) -> int:
        return sum(1 for event in self.events if event[0] == kind)


class _ElementHandle:
    def __init__(self, element: _Match | None) -> None:
        self._element = element

    def as_element(self) -> _Match | None:
        return self._element


class _Selector:
    """What ``page.locator`` returns: the matches this page chose to pose."""

    def __init__(self, page: _Page, selector: str) -> None:
        self._page = page
        self._selector = selector

    def count(self) -> int:
        return len(self._page.matches.get(self._selector, ()))

    def nth(self, index: int) -> _Match:
        return self._page.matches[self._selector][index]

    @property
    def first(self) -> _Match:
        return self._page.matches[self._selector][0]

    def inner_text(self) -> str:
        """Rendered text, which is how a prose verdict is read."""

        return self._page.body_text


class _Page:
    """A page that answers each selector with the elements a test chose."""

    def __init__(self, body_text: str = "") -> None:
        self.matches: dict[str, list[_Match]] = {}
        self.fills: list[tuple[str, str]] = []
        self.clicks: list[str] = []
        self.body_text = body_text
        self.mouse = _Mouse(self)
        self.fallback_handle: _Match | None = None
        self.on_drag_end = None

    def locator(self, selector: str) -> _Selector:
        return _Selector(self, selector)

    def evaluate_handle(self, script: str) -> _ElementHandle:
        del script
        return _ElementHandle(self.fallback_handle)

    def match(self, name: str, **kwargs) -> _Match:
        return _Match(self, name, **kwargs)


class _Clock:
    """A clock and a sleep that only advance when the code under test sleeps."""

    def __init__(self) -> None:
        self.now = 0.0
        self.slept: list[float] = []

    def wait(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.now += seconds

    def read(self) -> float:
        return self.now


@dataclass(frozen=True, slots=True)
class _Login:
    username: str = "synthetic-user"
    password: str = "synthetic-password"


FORM = LoginForm(username="#account", password="#password", submit="button.submit")


def _control_page(*, submit_visible: int, submit_hidden: int = 0) -> _Page:
    page = _Page()
    page.matches["#account"] = [page.match("#account")]
    page.matches["#password"] = [page.match("#password")]
    page.matches["button.submit"] = [
        *[
            page.match(f"submit-hidden-{index}", visible=False)
            for index in range(submit_hidden)
        ],
        *[page.match(f"submit-visible-{index}") for index in range(submit_visible)],
    ]
    return page


def test_a_unique_visible_control_is_typed_into_and_clicked_once() -> None:
    page = _control_page(submit_visible=1)

    submit_login_form(page, form=FORM, login=_Login(), timeout_ms=TIMEOUT_MS)

    assert page.fills == [
        ("#account", "synthetic-user"),
        ("#password", "synthetic-password"),
    ]
    assert page.clicks == ["submit-visible-0"]


def test_a_hidden_duplicate_is_tolerated_and_the_visible_one_is_used() -> None:
    page = _control_page(submit_visible=1, submit_hidden=1)

    submit_login_form(page, form=FORM, login=_Login(), timeout_ms=TIMEOUT_MS)

    assert page.clicks == ["submit-visible-0"], "the hidden copy must not win"


def test_an_ambiguous_selector_is_refused_before_anything_is_typed() -> None:
    """The passport.jlc.com shape: a heading and the button both match."""

    page = _control_page(submit_visible=2)

    with pytest.raises(SiteLoginError) as error:
        submit_login_form(page, form=FORM, login=_Login(), timeout_ms=TIMEOUT_MS)

    assert error.value.reason_code == "LOGIN_CONTROL_AMBIGUOUS"
    assert page.clicks == [], "clicking the first match is what caused the outage"
    assert page.fills == [], "a form we cannot address exactly is not half-filled"


def test_a_missing_control_fails_closed_without_typing() -> None:
    page = _control_page(submit_visible=0)

    with pytest.raises(SiteLoginError) as error:
        submit_login_form(page, form=FORM, login=_Login(), timeout_ms=TIMEOUT_MS)

    assert error.value.reason_code == "LOGIN_FORM_UNAVAILABLE"
    assert page.fills == []


def test_the_site_asking_for_a_code_stops_the_submit() -> None:
    page = _control_page(submit_visible=1)
    page.matches["#captcha"] = [page.match("#captcha")]
    form = LoginForm(
        username="#account",
        password="#password",
        submit="button.submit",
        challenge=("#captcha",),
    )

    with pytest.raises(SiteLoginError) as error:
        submit_login_form(page, form=form, login=_Login(), timeout_ms=TIMEOUT_MS)

    assert error.value.reason_code == "MANUAL_VERIFICATION_REQUIRED"
    assert page.clicks == []


def test_missing_credentials_are_reported_before_the_form_is_touched() -> None:
    page = _control_page(submit_visible=1)

    with pytest.raises(SiteLoginError) as error:
        submit_login_form(page, form=FORM, login=None, timeout_ms=TIMEOUT_MS)

    assert error.value.reason_code == "CREDENTIALS_UNAVAILABLE"
    assert page.fills == []
    assert page.clicks == []


def test_unique_visible_control_reports_ambiguity_instead_of_guessing() -> None:
    page = _control_page(submit_visible=1, submit_hidden=1)

    unique = unique_visible_control(page, "button.submit")
    assert unique is not None and unique.name == "submit-visible-0"
    assert unique_visible_control(page, "#account") is not None
    assert unique_visible_control(page, "#absent") is None

    ambiguous = _control_page(submit_visible=2)
    assert unique_visible_control(ambiguous, "button.submit") is None


def test_settling_waits_for_the_site_to_leave_the_form_by_itself() -> None:
    """Submitting is not proof; the site's own redirect decides."""

    clock = _Clock()

    class Settling:
        def __init__(self) -> None:
            self.polls = 0

        def still_on_form(self) -> bool:
            self.polls += 1
            return self.polls < 3

    page = Settling()

    await_login_outcome(
        page,
        form=FORM,
        is_login_page=lambda candidate: candidate.still_on_form(),
        timeout_ms=TIMEOUT_MS,
        wait=clock.wait,
        clock=clock.read,
    )

    assert page.polls == 3, "the loop must re-ask until the form is gone"
    assert clock.slept, "the loop must sleep between polls, not spin"


def test_a_refused_credential_is_reported_at_once_not_at_the_deadline() -> None:
    """Bom.Ai prints 密码错误 in ~1.5 s; the caller used to wait 45 s for it.

    The two verdicts need different repairs -- a stale password is the Owner's
    to fix, an unconfirmed session is ours -- so collapsing them into
    ``LOGIN_NOT_CONFIRMED`` at the end of the timeout sent the investigation the
    wrong way.
    """

    clock = _Clock()
    form = LoginForm(
        username="#account",
        password="#password",
        submit="button.submit",
        rejection=("密码错误",),
    )
    page = _Page(body_text="微信登录 账号登录 手机号登录\n公司名\n账号\n密码错误")

    with pytest.raises(SiteLoginError) as error:
        await_login_outcome(
            page,
            form=form,
            is_login_page=lambda _candidate: True,
            timeout_ms=45_000,
            wait=clock.wait,
            clock=clock.read,
        )

    assert error.value.reason_code == "CREDENTIAL_REJECTED"
    assert clock.slept == [], "it must not sleep on its way to a verdict it has"


def test_the_sites_own_slider_is_reported_at_once() -> None:
    """passport.jlc.com answers a distrusted login with a slider, not a form."""

    clock = _Clock()
    form = LoginForm(
        username="#account",
        password="#password",
        submit="button.submit",
        challenge_text=("安全验证", "请按住滑块"),
    )
    page = _Page(
        body_text="登录\n安全验证\n为了您的账号安全，请完成验证\n请按住滑块，拖动到最右边"
    )

    with pytest.raises(SiteLoginError) as error:
        await_login_outcome(
            page,
            form=form,
            is_login_page=lambda _candidate: True,
            timeout_ms=45_000,
            wait=clock.wait,
            clock=clock.read,
        )

    assert error.value.reason_code == "MANUAL_VERIFICATION_REQUIRED"
    assert clock.slept == []


def test_a_challenge_control_appearing_after_the_submit_is_reported_at_once() -> None:
    clock = _Clock()
    form = LoginForm(
        username="#account",
        password="#password",
        submit="button.submit",
        challenge=("#slider",),
    )
    page = _control_page(submit_visible=1)
    page.matches["#slider"] = [page.match("#slider")]

    with pytest.raises(SiteLoginError) as error:
        await_login_outcome(
            page,
            form=form,
            is_login_page=lambda _candidate: True,
            timeout_ms=45_000,
            wait=clock.wait,
            clock=clock.read,
        )

    assert error.value.reason_code == "MANUAL_VERIFICATION_REQUIRED"
    assert clock.slept == []


def test_a_site_that_says_nothing_cannot_report_success_at_the_deadline() -> None:
    """HQEW/Findchips must not count a silent submit as a completed login."""

    clock = _Clock()
    page = _Page(body_text="登录")

    with pytest.raises(SiteLoginError, match="LOGIN_NOT_CONFIRMED"):
        await_login_outcome(
            page, form=FORM, is_login_page=lambda _candidate: True,
            timeout_ms=TIMEOUT_MS, wait=clock.wait, clock=clock.read,
        )

    assert clock.now >= TIMEOUT_MS / 1000.0, "it must keep waiting, not give up early"


def test_hidden_challenge_duplicate_does_not_mask_visible_challenge():
    page = _control_page(submit_visible=1)
    page.matches["#challenge"] = [page.match("hidden", visible=False), page.match("visible")]
    form = LoginForm(username="#account", password="#password", submit="button.submit",
                     challenge=("#challenge",))
    with pytest.raises(SiteLoginError, match="MANUAL_VERIFICATION_REQUIRED"):
        submit_login_form(page, form=form, login=_Login(), timeout_ms=TIMEOUT_MS)
    assert not page.fills
    assert not page.clicks


@pytest.mark.parametrize("already_agreed", [False, True])
def test_hqew_agrees_privacy_before_submit_and_advertisement_is_not_captcha(already_agreed):
    from src.research.hqew import HQEW_LOGIN_FORM
    page = _Page()
    for selector in (HQEW_LOGIN_FORM.username, HQEW_LOGIN_FORM.password, HQEW_LOGIN_FORM.submit):
        page.matches[selector] = [page.match(selector)]
    consent = HQEW_LOGIN_FORM.options[0].control
    checkbox = page.match(consent, checked=already_agreed)
    page.matches[consent] = [checkbox]
    page.matches["#J_uislider"] = [page.match("advertisement")]
    submit_login_form(page, form=HQEW_LOGIN_FORM, login=_Login(), timeout_ms=TIMEOUT_MS)
    assert checkbox.checked
    assert page.clicks == ([consent] if not already_agreed else []) + [HQEW_LOGIN_FORM.submit]


def test_rejection_markers_are_only_read_when_a_form_declares_them() -> None:
    page = _Page(body_text="密码错误")

    assert rejection_present(page, FORM) is False, "no markers declared, no verdict"
    assert (
        rejection_present(
            page,
            LoginForm(
                username="#account",
                password="#password",
                submit="button.submit",
                rejection=("密码错误",),
            ),
        )
        is True
    )


# ---------------------------------------------------------------------------
# Options beside the form ("30天内免登录", "记住密码")
#
# Measured live on www.bom.ai 2026-10-01: both option inputs report
# ``is_visible() == True`` while parked at x = -119469, and "记住密码" defaults
# to *on*. So an option is only ever a click on its label, and only after the
# checkbox behind that label has been read.
# ---------------------------------------------------------------------------

OPTION_FORM = LoginForm(
    username="#account",
    password="#password",
    submit="button.submit",
    options=(LoginCheckbox(control='text="30天内免登录"'),),
)


def _option_page(**kwargs) -> _Page:
    page = _control_page(submit_visible=1)
    page.matches['text="30天内免登录"'] = [
        page.match("option-label-0", **kwargs)
    ]
    return page


def test_an_option_that_is_already_on_is_left_alone() -> None:
    """"记住密码" defaults to on; clicking it again would turn it off."""

    page = _option_page(checked=True)

    submit_login_form(page, form=OPTION_FORM, login=_Login(), timeout_ms=TIMEOUT_MS)

    assert page.clicks == ["submit-visible-0"], "only the submit button is clicked"
    assert page.matches['text="30天内免登录"'][0].checked is True


def test_an_option_that_is_off_is_turned_on_and_read_back() -> None:
    page = _option_page(checked=False)

    submit_login_form(page, form=OPTION_FORM, login=_Login(), timeout_ms=TIMEOUT_MS)

    assert page.clicks == ["option-label-0", "submit-visible-0"]
    assert page.matches['text="30天内免登录"'][0].checked is True


def test_an_option_whose_state_cannot_be_read_is_never_toggled() -> None:
    """No checkbox behind the label: we cannot know which way a click goes."""

    page = _option_page(checked=None)

    with pytest.raises(SiteLoginError) as error:
        submit_login_form(page, form=OPTION_FORM, login=_Login(), timeout_ms=TIMEOUT_MS)

    assert error.value.reason_code == "LOGIN_OPTION_UNCONFIRMED"
    assert page.clicks == [], "a blind toggle is how an option meant to be on goes off"


def test_an_option_that_does_not_turn_on_is_not_reported_as_success() -> None:
    """"The click landed" is not "the option is set"."""

    page = _option_page(checked=False, turns_on=False)

    with pytest.raises(SiteLoginError) as error:
        submit_login_form(page, form=OPTION_FORM, login=_Login(), timeout_ms=TIMEOUT_MS)

    assert error.value.reason_code == "LOGIN_OPTION_UNCONFIRMED"
    assert page.clicks == ["option-label-0"], "it must not submit a form it failed on"


def test_an_absent_option_is_reported_rather_than_silently_skipped() -> None:
    """A renamed label costs a durable session; that is loud, not invisible."""

    page = _control_page(submit_visible=1)

    with pytest.raises(SiteLoginError) as error:
        submit_login_form(page, form=OPTION_FORM, login=_Login(), timeout_ms=TIMEOUT_MS)

    assert error.value.reason_code == "LOGIN_FORM_UNAVAILABLE"
    assert page.clicks == []


def test_an_option_declared_twice_visibly_is_refused() -> None:
    page = _control_page(submit_visible=1)
    page.matches['text="30天内免登录"'] = [
        page.match("option-visible-0", checked=False),
        page.match("option-visible-1", checked=False),
    ]

    with pytest.raises(SiteLoginError) as error:
        submit_login_form(page, form=OPTION_FORM, login=_Login(), timeout_ms=TIMEOUT_MS)

    assert error.value.reason_code == "LOGIN_CONTROL_AMBIGUOUS"
    assert page.clicks == []


def test_options_are_only_acted_on_when_a_form_declares_them() -> None:
    page = _control_page(submit_visible=1)
    page.matches['text="30天内免登录"'] = [page.match("option-label-0", checked=False)]

    apply_login_options(page, form=FORM, timeout_ms=TIMEOUT_MS)

    assert page.clicks == [], "a form with no options has nothing to click"


# ---------------------------------------------------------------------------
# The slider a site shows when it distrusts the attempt
# ---------------------------------------------------------------------------

TRACK = {"handle": [100.0, 200.0, 40.0, 40.0], "track": [100.0, 200.0, 300.0, 40.0]}


def _slider_form(**kwargs) -> LoginForm:
    return LoginForm(
        username="#account",
        password="#password",
        submit="button.submit",
        challenge_text=("请按住滑块",),
        slider=("#handle",),
        **kwargs,
    )


def _slider_page(*, geometry: dict | None = TRACK, solves: bool = True) -> _Page:
    page = _Page(body_text="安全验证 请按住滑块，拖动到最右边")
    page.matches["#handle"] = [page.match("#handle", geometry=geometry)]
    if solves:
        page.on_drag_end = lambda: setattr(page, "body_text", "登录后")
    return page


def test_the_slider_is_dragged_to_the_far_right_and_the_challenge_clears() -> None:
    clock = _Clock()
    page = _slider_page()

    assert solve_slider_challenge(
        page, form=_slider_form(), wait=clock.wait, clock=clock.read
    )

    xs = page.mouse.xs
    assert page.mouse.count("down") == 1 and page.mouse.count("up") == 1
    assert xs == sorted(xs), "a slider is dragged rightwards, never back"
    assert xs[0] == 120.0, "the gesture starts on the handle's centre"
    assert xs[-1] == 379.0, "and ends at the track's right edge, minus half a handle"
    assert xs[-1] > TRACK["track"][0] + TRACK["track"][2] - TRACK["handle"][2]


def test_a_drag_that_does_not_clear_the_challenge_is_not_reported_as_solved() -> None:
    """The drag is a proposal; only the site's answer makes it a success."""

    clock = _Clock()
    page = _slider_page(solves=False)

    assert not solve_slider_challenge(
        page, form=_slider_form(), wait=clock.wait, clock=clock.read
    )
    assert page.mouse.count("down") == 2, "a resetting widget gets one bounded retry"
    assert page.mouse.count("down") == page.mouse.count("up"), "no gesture is left open"


def test_no_draggable_handle_means_no_drag_at_all() -> None:
    clock = _Clock()
    page = _Page(body_text="请按住滑块")

    assert not solve_slider_challenge(
        page, form=_slider_form(), wait=clock.wait, clock=clock.read
    )
    assert page.mouse.events == [], "an unfound handle must not be flailed at"


def test_a_handle_that_cannot_be_measured_is_not_dragged() -> None:
    clock = _Clock()
    page = _slider_page(geometry=None)

    assert not solve_slider_challenge(
        page, form=_slider_form(), wait=clock.wait, clock=clock.read
    )
    assert page.mouse.events == [], "no geometry, no gesture"


def test_a_solved_slider_leaves_the_challenge_markers_gone() -> None:
    """Proves the recovery the site module relies on, using the same predicates."""

    clock = _Clock()
    form = _slider_form()
    page = _slider_page()

    assert solve_slider_challenge(page, form=form, wait=clock.wait, clock=clock.read)
    assert not any(
        marker in page.body_text for marker in form.challenge_text
    ), "the next settle check must not see the old challenge"
