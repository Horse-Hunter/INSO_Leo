"""One shared way for a research source to establish its own login.

Owner rule (2026-10-01): every source opens its page, makes sure it is signed
in **first**, does its work, and closes the page again -- the next step reopens
it. A login wall is a session problem to solve, never a business answer ("no
offers today").

Credentials come from the Core Provider only: ``docs/MODULE_INDEX.md`` pins
``sheets | research | inso | quotation -> core`` and ``docs/modules/RESEARCH.md``
says "Credential 只走 Core Provider". This module therefore never stores,
logs, or keeps a secret of its own -- it is handed an in-memory login for the
duration of a single submit.

Why it exists: the same "open the form, type, submit, wait for the site to
navigate away" flow had been written three separate times --
``CdpIcNetClient._restore_session``, ``CdpBomAiAuthenticatedBrowser``
``._login_once_if_required`` and ``CdpLcscClient._restore_session``. Every
source now shares this one implementation, so one fix reaches all of them.

Two invariants every source inherits from being here: nothing is typed into or
clicked on a control that is not the *only visible* match for its selector
(see :func:`unique_visible_control`), and a failure always leaves a reason code
instead of a page that quietly did nothing -- reported as soon as the site says
it, not at the end of a timeout (:func:`await_login_outcome`).

Two more capabilities live here because they are properties of *how these
sites ask for a login*, not of any one source:

* an ordinary form usually also offers options -- "30天内免登录", "记住密码".
  They must be *confirmed on*, never blindly toggled (:func:`apply_login_options`);
* a site that distrusts an attempt answers with a slider. Dragging it is a
  bounded, verifiable action, not a guess (:func:`solve_slider_challenge`).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

__all__ = [
    "REJECTED_PASSWORD_TEXT",
    "LoginCheckbox",
    "LoginForm",
    "SiteLoginError",
    "apply_login_options",
    "await_login_outcome",
    "challenge_present",
    "element_is_visible",
    "rejection_present",
    "solve_slider_challenge",
    "submit_login_form",
    "unique_visible_control",
    "visible_text_contains",
]

#: How often the settle loop re-asks the page whether it left the form. The
#: loop is bounded by the caller's timeout, never by a fixed pause.
_SETTLE_POLL_SECONDS = 0.25

#: How long the drag pauses between mouse moves so the widget's own mousemove
#: handler sees a trajectory rather than a teleport.
_DRAG_STEP_SECONDS = 0.02

#: The wording these sites use when they refuse the credential itself. Shared
#: because it means exactly the same thing everywhere, and because a site that
#: words it differently should have to say so explicitly. Measured live
#: 2026-10-01: Bom.Ai answers a rejected password with "密码错误".
REJECTED_PASSWORD_TEXT: tuple[str, ...] = (
    "密码错误",
    "账号或密码错误",
    "用户名或密码错误",
)

#: Reads the checkbox a site's styled option label stands for. Measured live
#: on ``www.bom.ai`` 2026-10-01: the label wraps its own input
#: (``label.closest('label').querySelector('input[type=checkbox]')`` resolves
#: "30天内免登录" -> ``#freelogin`` and "记住密码" -> ``#rememberPassword``).
#: ``null`` means the association could not be proven, and a control whose
#: state is unknown is never clicked -- that is how an option meant to be *on*
#: gets turned *off*.
_OPTION_STATE_JS = """
el => {
  const scope = (el.closest && el.closest('label')) || el;
  let input = scope.querySelector ? scope.querySelector('input[type="checkbox"]') : null;
  if (!input && scope.htmlFor && scope.ownerDocument) {
    input = scope.ownerDocument.getElementById(scope.htmlFor);
  }
  return input ? !!input.checked : null;
}
"""

#: Reads the geometry a drag needs. The track is the nearest ancestor at least
#: three times the handle's width -- measured against the widget rather than
#: assumed, so a resized or restyled slider still resolves.
_SLIDER_GEOMETRY_JS = """
el => {
  const box = node => {
    const r = node.getBoundingClientRect();
    return [r.x, r.y, r.width, r.height];
  };
  const handle = box(el);
  let track = el.parentElement;
  for (let up = 0; up < 3 && track; up++, track = track.parentElement) {
    const r = track.getBoundingClientRect();
    if (r.width >= handle[2] * 3) {
      return {handle: handle, track: [r.x, r.y, r.width, r.height]};
    }
  }
  const fallback = track ? box(track) : handle;
  return {handle: handle, track: fallback};
}
"""

#: A last-resort way to recognize a slide handle whose vendor we have never
#: seen: inside the drawn page there is exactly one small element the site
#: itself marks as draggable. Ambiguity is a refusal, not a coin toss.
_SLIDER_HANDLE_JS = """
() => {
  const shown = el => {
    const s = window.getComputedStyle(el);
    const r = el.getBoundingClientRect();
    return s.display !== 'none' && s.visibility !== 'hidden'
        && r.width > 8 && r.height > 8 && r.width <= 90 && r.height <= 90;
  };
  const draggable = /move|grab|col-resize/i;
  const found = [...document.querySelectorAll('*')].filter(el => {
    if (!shown(el)) return false;
    const s = window.getComputedStyle(el);
    return draggable.test(s.cursor) || draggable.test(el.getAttribute('style') || '');
  });
  return found.length === 1 ? found[0] : null;
}
"""

#: How many mouse moves one drag is made of, and how many drags a single
#: challenge may cost. The widget is the judge of both, so the numbers only
#: have to be bounded, not tuned -- but the bound is not free: measured live
#: 2026-10-01, a ``mouse.move`` with the button held costs ~0.98 s while the
#: chrome window is in the background (the same rendering stall that made
#: screenshots take 3 s), so a step is very nearly a second of wall clock.
#: Eight keeps one drag under ten seconds and still traces a curved, moving
#: path the widget accepts; the two attempts then fit inside a site's budget.
_DRAG_STEPS = 8
_SLIDER_ATTEMPTS = 2


class SiteLoginError(Exception):
    """One site's login could not be established.

    ``reason_code`` is a short, safe token -- never provider text, a selector,
    or any credential material -- and is what the caller records.
    """

    def __init__(self, reason_code: str) -> None:
        super().__init__(reason_code)
        self.reason_code = reason_code


@dataclass(frozen=True, slots=True)
class LoginCheckbox:
    """One option the site offers beside its form, e.g. "30天内免登录".

    ``control`` addresses what a human actually clicks -- the site's styled
    label, not the input. Measured live on ``www.bom.ai`` 2026-10-01: both of
    its option inputs are real, ``is_visible()`` returns True for them, and yet
    they sit at x = -119469, parked off the viewport; the label is the only
    thing on screen. A ``check()`` on the input would therefore act on
    something no human could reach.
    """

    control: str


@dataclass(frozen=True, slots=True)
class LoginForm:
    """The selectors one site's ordinary login form is addressed by."""

    username: str
    password: str
    submit: str | None = None
    #: Only some sites ask for it (Bom.Ai); ``None`` means "not on this form".
    company: str | None = None
    #: Shown by the site when it wants a human (captcha / SMS / device check).
    challenge: tuple[str, ...] = ()
    #: The same verdict for sites that say it in prose rather than with a
    #: control. Only markers measured *absent* before the submit belong here, or
    #: the form would be refused before it was ever tried.
    challenge_text: tuple[str, ...] = ()
    #: What the site prints when it refuses the credential itself
    #: ("密码错误"). A wrong password is not an unconfirmed login: it cannot be
    #: fixed by waiting, and only the Owner can repair it.
    rejection: tuple[str, ...] = ()
    #: Options to have *on* before submitting. Each is confirmed by reading the
    #: checkbox it stands for, so "the click went through" is never mistaken
    #: for "the option is set".
    options: tuple[LoginCheckbox, ...] = ()
    #: Candidate selectors for a "drag the handle to the far right" challenge,
    #: most specific first. Matching here is *not* the unique-visible rule: the
    #: widget only exists after a submit, so an empty list is the normal case
    #: and means "this site has no slider".
    slider: tuple[str, ...] = ()


def element_is_visible(page: Any, selector: str) -> bool:
    """True only when *selector* resolves to something actually shown."""

    return bool(_visible_controls(page, selector))


def _control_is_visible(control: Any) -> bool:
    try:
        return bool(control.is_visible())
    except Exception:  # noqa: BLE001 - an unreadable control proves nothing
        return False


def _visible_controls(page: Any, selector: str) -> list[Any] | None:
    """Every visible match of *selector*, or ``None`` when the page says nothing."""

    try:
        locator = page.locator(selector)
        matches = [locator.nth(index) for index in range(locator.count())]
    except Exception:  # noqa: BLE001 - an unreadable page proves nothing
        return None
    return [match for match in matches if _control_is_visible(match)]


def unique_visible_control(page: Any, selector: str) -> Any | None:
    """The single *visible* control *selector* names, or ``None`` otherwise.

    ``page.fill``/``page.click`` are not strict: when a selector resolves to
    more than one element they silently use the first one in DOM order. That
    made a login button unclickable for a whole afternoon. Measured live on
    ``passport.jlc.com`` 2026-10-01: after the "账号登录" tab is opened, the
    LCSC form's ``text="登录"`` matches **two** visible elements -- the page's
    own ``<h2>`` heading, which sits above the form in DOM order, and the
    submit button's inner ``<span>``. The heading was clicked, the button never
    was, the form was never submitted, and the run only surfaced as an
    unexplained "not confirmed" a settle-timeout later.

    So a control is addressed only when we have proven it is the *only* visible
    match: hidden duplicates are tolerated, real ambiguity fails closed. The
    returned handle is a lazy Playwright ``Locator``, so it survives the
    site's re-render between typing and clicking.
    """

    controls = _visible_controls(page, selector)
    return controls[0] if controls is not None and len(controls) == 1 else None


def visible_text_contains(page: Any, markers: tuple[str, ...]) -> bool:
    """True when any *marker* is in the text the page is actually showing.

    Prose verdicts ("密码错误", "安全验证") have no stable selector, so they can
    only be read as text. ``inner_text`` returns rendered text, so a panel that
    is merely present-but-hidden does not fire this -- which is what makes it
    safe to look for these markers before submitting.
    """

    if not markers:
        return False
    try:
        rendered = page.locator("body").inner_text()
    except Exception:  # noqa: BLE001 - an unreadable page proves nothing
        return False
    folded = rendered.casefold()
    return any(marker.casefold() in folded for marker in markers)


def challenge_present(page: Any, form: LoginForm) -> bool:
    """True when the site is asking for a human rather than for a password."""

    return any(
        element_is_visible(page, selector) for selector in form.challenge
    ) or visible_text_contains(page, form.challenge_text)


def rejection_present(page: Any, form: LoginForm) -> bool:
    """True when the site has refused the credential we just sent."""

    return visible_text_contains(page, form.rejection)


def _required_control(page: Any, selector: str) -> Any:
    """Resolve one field, failing closed instead of guessing which one it is.

    "Not there" and "not specific enough" are different repairs -- a missing
    form versus a selector that also matches something else on the page -- so
    they are reported differently rather than collapsing into one silence.
    """

    controls = _visible_controls(page, selector)
    if not controls:
        raise SiteLoginError("LOGIN_FORM_UNAVAILABLE")
    if len(controls) > 1:
        raise SiteLoginError("LOGIN_CONTROL_AMBIGUOUS")
    return controls[0]


def _option_state(control: Any) -> bool | None:
    """``True``/``False`` for the checkbox *control* stands for, else ``None``."""

    try:
        state = control.evaluate(_OPTION_STATE_JS)
    except Exception:  # noqa: BLE001 - an unreadable state proves nothing
        return None
    return None if state is None else bool(state)


def apply_login_options(page: Any, *, form: LoginForm, timeout_ms: int) -> None:
    """Turn on every option the site offers before the form is submitted.

    An option is only a preference, but it is a preference that costs a real
    login when it is dropped -- "30天内免登录" is exactly what keeps a session
    alive between runs. So it is not best-effort-and-forget: the control is
    resolved under the same unique-visible invariant as the credential fields,
    the state is read *before* clicking (clicking an option that is already on
    turns it off), and the state is read again afterwards, because "the click
    went through" is not "the option is set".
    """

    for option in form.options:
        control = _required_control(page, option.control)
        state = _option_state(control)
        if state is None:
            # We cannot prove which checkbox this label owns. Leaving the
            # option alone is wrong; toggling it blind is worse.
            raise SiteLoginError("LOGIN_OPTION_UNCONFIRMED")
        if state:
            continue
        try:
            control.click(timeout=timeout_ms)
        except Exception as error:
            raise SiteLoginError("LOGIN_OPTION_UNCONFIRMED") from error
        if _option_state(control) is not True:
            raise SiteLoginError("LOGIN_OPTION_UNCONFIRMED")


def submit_login_form(
    page: Any,
    *,
    form: LoginForm,
    login: Any,
    timeout_ms: int,
) -> None:
    """Type one site's own form and submit it exactly once.

    A half-typed form must never be submitted as if it were a login attempt,
    so anything missing fails closed instead of clicking the button anyway.
    Every control is resolved to a single visible element before the first
    keystroke, so a credential is never typed into a field we only assumed.
    """

    if login is None:
        raise SiteLoginError("CREDENTIALS_UNAVAILABLE")
    if form.submit is None:
        raise SiteLoginError("LOGIN_FORM_UNAVAILABLE")
    if challenge_present(page, form):
        raise SiteLoginError("MANUAL_VERIFICATION_REQUIRED")
    username = _required_control(page, form.username)
    password = _required_control(page, form.password)
    company = (
        _required_control(page, form.company) if form.company is not None else None
    )
    submit = _required_control(page, form.submit)
    try:
        username.fill(login.username, timeout=timeout_ms)
        password.fill(login.password, timeout=timeout_ms)
        if company is not None:
            company.fill(login.company or "", timeout=timeout_ms)
    except Exception as error:  # never leak page or provider text upward
        raise SiteLoginError("LOGIN_FORM_UNAVAILABLE") from error
    if form.options:
        apply_login_options(page, form=form, timeout_ms=timeout_ms)
    if challenge_present(page, form):
        # The site wants a code we must not guess. Stop before submitting.
        raise SiteLoginError("MANUAL_VERIFICATION_REQUIRED")
    try:
        submit.click(timeout=timeout_ms)
    except Exception as error:  # never leak page or provider text upward
        raise SiteLoginError("LOGIN_SUBMIT_FAILED") from error


def await_login_outcome(
    page: Any,
    *,
    form: LoginForm,
    is_login_page: Callable[[Any], bool],
    timeout_ms: int,
    wait: Callable[[float], None],
    clock: Callable[[], float],
    poll_seconds: float = _SETTLE_POLL_SECONDS,
) -> None:
    """Wait for the site's answer to the submit, and report the first verdict.

    Submitting is not proof: the form posts through the site's own JavaScript,
    which then navigates. Reading the result immediately races that redirect --
    measured live on INSO 2026-10-01, where it turned a login that had in fact
    succeeded into a reported failure. A form still open at the deadline is
    unconfirmed, never a successful return to the caller.

    But two answers arrive long before the form settles, and waiting for the
    deadline before reporting either of them helpfully is what made a login
    failure take 45 silent seconds (measured live 2026-10-01):

    * the site wants a human -- a slider, an SMS code. No amount of waiting
      helps, and the tab is held open for nothing;
    * the site refused the credential. Bom.Ai printed "密码错误" within ~1.5 s
      while the caller waited the full 45 s and then reported
      ``LOGIN_NOT_CONFIRMED`` -- a verdict that points at the session and not at
      the password, so it sent the investigation the wrong way.

    Both are raised the moment they appear. A site that says nothing and keeps
    its form open raises LOGIN_NOT_CONFIRMED at the deadline.
    """

    deadline = clock() + timeout_ms / 1000.0
    while True:
        if challenge_present(page, form):
            raise SiteLoginError("MANUAL_VERIFICATION_REQUIRED")
        if rejection_present(page, form):
            raise SiteLoginError("CREDENTIAL_REJECTED")
        if not is_login_page(page):
            return
        if clock() >= deadline:
            raise SiteLoginError("LOGIN_NOT_CONFIRMED")
        wait(min(poll_seconds, max(0.0, deadline - clock())))


def _slider_handle(page: Any, form: LoginForm) -> Any | None:
    """The draggable handle the site just drew, or ``None`` if unprovable."""

    for selector in form.slider:
        candidate = unique_visible_control(page, selector)
        if candidate is not None:
            return candidate
    # The widget is injected lazily, so its markup cannot be read ahead of
    # time; when every known selector misses, fall back to the site's own
    # draggable mark and refuse unless exactly one exists.
    try:
        handle = page.evaluate_handle(_SLIDER_HANDLE_JS)
        return handle.as_element()
    except Exception:  # noqa: BLE001 - an unreadable page proves nothing
        return None


def _drag_to_the_far_right(
    page: Any,
    handle: Any,
    *,
    wait: Callable[[float], None],
) -> bool:
    """One human-ish drag from the handle's centre to the track's right edge."""

    try:
        geometry = handle.evaluate(_SLIDER_GEOMETRY_JS)
        hx, _hy, handle_width, handle_height = geometry["handle"]
        tx, _ty, track_width, _th = geometry["track"]
    except Exception:  # noqa: BLE001 - no geometry, no drag
        return False
    start_x = hx + handle_width / 2
    start_y = _hy + handle_height / 2
    end_x = tx + track_width - handle_width / 2 - 1
    if end_x <= start_x:
        return False
    mouse = page.mouse
    try:
        mouse.move(start_x, start_y)
        mouse.down()
        for step in range(1, _DRAG_STEPS + 1):
            progress = step / _DRAG_STEPS
            eased = progress * progress * (3 - 2 * progress)
            mouse.move(
                start_x + (end_x - start_x) * eased,
                start_y + (1 if step % 7 == 0 else 0),
            )
            wait(_DRAG_STEP_SECONDS)
        mouse.move(end_x, start_y)
        mouse.up()
    except Exception:  # noqa: BLE001 - a broken gesture is a failed drag
        return False
    return True


def solve_slider_challenge(
    page: Any,
    *,
    form: LoginForm,
    wait: Callable[[float], None],
    clock: Callable[[], float],
    settle_ms: int = 10_000,
    attempts: int = _SLIDER_ATTEMPTS,
) -> bool:
    """Drag the slider the site just showed until the site stops asking.

    Only ever called when the site has actually presented a challenge, and it
    returns ``True`` only once that challenge is *gone*. The drag is a
    proposal; the site's own answer is the verdict. Reporting a drag we could
    not confirm would replace "a human has to do this" with "we think we did
    it" -- exactly the kind of claim this module exists to prevent, so failing
    here leaves the caller's ``MANUAL_VERIFICATION_REQUIRED`` standing.

    A widget that resets after a failed drag is why there is more than one
    attempt; the handle is re-resolved each time, because a reset usually
    replaces it.
    """

    if not form.slider:
        # The site never declared a slider; the fallback hunt still gets a
        # chance, but it is scoped to one attempt so an unrelated draggable
        # element cannot be worked over twice.
        attempts = 1
    for _attempt in range(max(1, attempts)):
        handle = _slider_handle(page, form)
        if handle is None:
            return False
        if not _drag_to_the_far_right(page, handle, wait=wait):
            return False
        deadline = clock() + settle_ms / 1000.0
        while clock() < deadline:
            if not challenge_present(page, form):
                return True
            wait(min(_SETTLE_POLL_SECONDS, max(0.0, deadline - clock())))
    return False
