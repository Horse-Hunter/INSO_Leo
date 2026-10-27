from types import SimpleNamespace
from typing import Self

import pytest

from src.research.cdp_pages import (
    native_page_owner,
    new_background_page,
    shared_playwright_factory,
)


class Session:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []
        self.detached = False

    def send(self, command: str, params: dict[str, object]) -> dict[str, str]:
        self.calls.append((command, params))
        return {"success": True} if command == "Target.closeTarget" else {"targetId": "synthetic-target"}

    def detach(self) -> None:
        self.detached = True


class Context:
    def __init__(self, *, fail: bool = False) -> None:
        self.page = SimpleNamespace(evaluate=lambda _: None)
        self.pages = [self.page]
        self.fail = fail

    def expect_event(self, event, *, predicate, timeout: int) -> "Context":
        assert event == "page" and timeout == 1234
        self.predicate = predicate
        return self

    def new_cdp_session(self, page):
        return SimpleNamespace(send=lambda _: {"targetInfo": {"targetId": "synthetic-target"}},
                               detach=lambda: None)

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        if self.fail:
            raise TimeoutError("synthetic")

    @property
    def value(self) -> object:
        return self.page


def test_new_cdp_page_stays_in_background_and_detaches_session() -> None:
    session = Session()
    page = new_background_page(
        SimpleNamespace(new_browser_cdp_session=lambda: session),
        Context(), timeout_ms=1234,
    )
    assert page is not None
    assert session.calls == [
        ("Target.createTarget", {"url": session.calls[0][1]["url"], "background": True})
    ]
    assert session.detached


def test_new_cdp_page_targets_isolated_browser_context() -> None:
    session = Session()
    new_background_page(
        SimpleNamespace(new_browser_cdp_session=lambda: session),
        Context(), timeout_ms=1234, browser_context_id="ephemeral-context",
    )
    assert session.calls == [
        (
            "Target.createTarget",
            {
                "url": session.calls[0][1]["url"],
                "background": True,
                "browserContextId": "ephemeral-context",
            },
        )
    ]


def test_failed_page_creation_closes_its_target() -> None:
    session = Session()
    with pytest.raises(TimeoutError):
        new_background_page(
            SimpleNamespace(new_browser_cdp_session=lambda: session),
            Context(fail=True), timeout_ms=1234,
        )
    assert session.calls[-1] == (
        "Target.closeTarget", {"targetId": "synthetic-target"}
    )
    assert session.detached


class _FakeBrowser:
    def __init__(self, *, connected: bool = True) -> None:
        self._connected = connected

    def is_connected(self) -> bool:
        return self._connected


class _FakePlaywright:
    def __init__(self) -> None:
        self.stopped = False

    def stop(self) -> None:
        self.stopped = True


def test_shared_factory_reuses_the_live_cdp_browser_without_stopping_it() -> None:
    """The launcher's single Playwright attachment must be shared, never stopped.

    Playwright's synchronous API cannot be started twice in one thread, so every
    browser-backed source must connect through the launcher's existing session
    instead of opening its own.
    """

    browser = _FakeBrowser()
    playwright = _FakePlaywright()
    factory = shared_playwright_factory(lambda: (playwright, browser))

    with factory() as shared:
        assert shared.chromium.connect_over_cdp("http://127.0.0.1:9222") is browser
        # A second source in the same run reuses the very same attachment.
        assert shared.chromium.connect_over_cdp("http://127.0.0.1:9222") is browser

    assert playwright.stopped is False


@pytest.mark.parametrize(
    "provider",
    (
        lambda: None,
        lambda: (object(), _FakeBrowser(connected=False)),
    ),
    ids=("absent", "disconnected"),
)
def test_shared_factory_falls_back_to_a_private_session(
    provider, monkeypatch
) -> None:
    sentinel = object()
    monkeypatch.setattr(
        "playwright.sync_api.sync_playwright", lambda: sentinel, raising=True
    )

    assert shared_playwright_factory(provider)() is sentinel


def test_windowless_first_target_is_minimized_without_activation_or_foreground_fallback():
    session = Session()
    context = Context()
    context.pages = []
    new_background_page(SimpleNamespace(new_browser_cdp_session=lambda: session),
                        context, timeout_ms=1234)
    assert session.calls == [("Target.createTarget", {
        "url": session.calls[0][1]["url"], "background": True,
        "newWindow": True, "windowState": "minimized",
    })]
    assert session.detached

class RacingTargets:
    """Interleave another actor/human event before the requested target event."""

    def __init__(self, *, spoof=False, fail_proof=False):
        self.pages = []
        self.calls = []
        self.spoof, self.fail_proof = spoof, fail_proof
        self.closed = []

    def new_browser_cdp_session(self):
        return self

    def send(self, command, params):
        self.calls.append((command, params))
        if command == "Target.closeTarget":
            self.closed.append(params['targetId'])
            return {'success': True}
        target = f'owned-{len(self.calls)}'
        noise = SimpleNamespace(url='about:blank#INSO_CREATE:another-task', target='human')
        own = SimpleNamespace(url=params['url'], target='spoof' if self.spoof else target)
        own.owner_name = ""
        own.is_closed = lambda: False
        def evaluate(script, arg=None):
            if script == "() => history.replaceState(null, '', 'about:blank')":
                own.url = "about:blank"
            elif script == "() => window.name":
                return own.owner_name
            elif script == "name => { window.name = name; }":
                own.owner_name = arg
            else:
                raise AssertionError("unexpected evaluation")
        own.evaluate = evaluate
        self.pages.extend([noise, own])
        self.matched = [p for p in self.pages if self.predicate(p)]
        return {'targetId': target}

    def detach(self):
        pass

    def expect_event(self, event, *, predicate, timeout):
        assert event == 'page'
        self.predicate = predicate
        return self

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass

    @property
    def value(self):
        return self.matched[0]

    def new_cdp_session(self, page):
        assert page.target != 'human'
        def proof(_):
            if self.fail_proof:
                raise TimeoutError('synthetic-target-proof')
            return {'targetInfo': {'targetId': page.target}}
        return SimpleNamespace(send=proof, detach=lambda: None)


def test_creation_filters_foreign_event_then_proves_exact_native_target():
    protocol = RacingTargets()
    page = new_background_page(protocol, protocol, timeout_ms=1234)
    assert page.target == 'owned-1'
    assert protocol.pages[0].target == 'human'
    assert not protocol.closed
    second = new_background_page(protocol, protocol, timeout_ms=1234)
    assert protocol.calls[0][1]["url"] != protocol.calls[1][1]["url"]
    assert second.url == page.url == "about:blank"
    assert second.target == 'owned-2'


@pytest.mark.parametrize('kwargs,error', [({'spoof': True}, ValueError),
                                          ({'fail_proof': True}, TimeoutError)])
def test_mismatched_or_unprovable_target_closes_only_created_target(kwargs, error):
    protocol = RacingTargets(**kwargs)
    with pytest.raises(error):
        new_background_page(protocol, protocol, timeout_ms=1234, owner='market-task')
    assert protocol.closed == ['owned-1']
    assert protocol.pages[0].target == 'human'


def test_invalid_owner_creates_no_target_or_client_session():
    protocol = RacingTargets()
    with pytest.raises(ValueError, match='INVALID_TAB_OWNER'):
        new_background_page(protocol, protocol, timeout_ms=1234, owner='INVALID')
    assert protocol.calls == []


def test_exact_blank_restored_without_losing_task_ownership():
    from src.research.cdp_pages import page_owner
    protocol = RacingTargets()
    page = new_background_page(protocol, protocol, timeout_ms=1234, owner="market-task")
    assert page.url == "about:blank"
    assert page_owner(page) == "market-task"
    assert not protocol.closed


@pytest.mark.parametrize("close_fails,detach_fails", [(True, False), (False, True), (True, True)])
def test_uncertain_cleanup_preserves_original_failure_and_blocks_client_reuse(close_fails, detach_fails):
    from src.research.cdp_pages import PageTargetCleanupError
    protocol = RacingTargets(spoof=True)
    send = protocol.send
    def broken_send(command, params):
        result = send(command, params)
        if command == "Target.closeTarget" and close_fails:
            raise OSError("synthetic close failure")
        return result
    protocol.send = broken_send
    def detach():
        if detach_fails:
            raise TimeoutError("synthetic detach failure")
    protocol.detach = detach
    with pytest.raises(PageTargetCleanupError) as caught:
        new_background_page(protocol, protocol, timeout_ms=1234)
    assert isinstance(caught.value.__cause__, ValueError)
    assert str(caught.value.__cause__) == "TAB_TARGET_ID_MISMATCH"
    assert protocol.closed == ["owned-1"]
    calls = list(protocol.calls)
    with pytest.raises(PageTargetCleanupError):
        new_background_page(protocol, protocol, timeout_ms=1234)
    assert protocol.calls == calls  # Not even another createTarget admission.


def test_successful_proof_but_failed_detach_never_returns_usable_page():
    from src.research.cdp_pages import PageTargetCleanupError
    protocol = RacingTargets()
    protocol.detach = lambda: (_ for _ in ()).throw(OSError("synthetic detach failure"))
    with pytest.raises(PageTargetCleanupError) as caught:
        new_background_page(protocol, protocol, timeout_ms=1234)
    assert isinstance(caught.value.__cause__, OSError)
    assert protocol.closed == ["owned-1"]
    assert protocol._inso_page_resource_failed is True


@pytest.mark.parametrize("spoof", [False, True])
def test_page_linked_session_detach_failure_preserves_primary_and_invalidates(spoof):
    from src.research.cdp_pages import PageTargetCleanupError
    protocol = RacingTargets(spoof=spoof)
    make_proof = protocol.new_cdp_session
    def broken_proof(page):
        proof = make_proof(page)
        proof.detach = lambda: (_ for _ in ()).throw(OSError("synthetic proof detach"))
        return proof
    protocol.new_cdp_session = broken_proof
    with pytest.raises(PageTargetCleanupError) as caught:
        new_background_page(protocol, protocol, timeout_ms=1234)
    assert isinstance(caught.value.__cause__, ValueError if spoof else OSError)
    assert protocol.closed == ["owned-1"]
    assert protocol._inso_page_resource_failed is True


@pytest.mark.parametrize("response", [{"success": False}, {}])
def test_native_target_close_requires_positive_protocol_confirmation(response):
    from src.research.cdp_pages import PageTargetCleanupError
    protocol = RacingTargets(spoof=True)
    send = protocol.send
    def unconfirmed(command, params):
        value = send(command, params)
        return response if command == "Target.closeTarget" else value
    protocol.send = unconfirmed
    with pytest.raises(PageTargetCleanupError):
        new_background_page(protocol, protocol, timeout_ms=1234)
    assert protocol.closed == ["owned-1"]
    assert protocol._inso_page_resource_failed is True

@pytest.mark.parametrize('failure_mode', ['raise', 'missing', 'invalid'])
def test_ambiguous_native_creation_blocks_all_bound_clients_without_guessing(failure_mode):
    from src.research.cdp_pages import (
        PageResourceAdmission,
        PageTargetCreationUncertain,
        bind_page_admission,
    )
    admission = PageResourceAdmission()
    first, second = RacingTargets(), RacingTargets()
    bind_page_admission(first, admission)
    bind_page_admission(second, admission)
    original = first.send
    def uncertain(command, params):
        value = original(command, params)  # Chrome did create the page.
        if command == 'Target.createTarget':
            if failure_mode == 'raise':
                raise OSError('synthetic response lost')
            return {} if failure_mode == 'missing' else {'targetId': 123}
        return value
    first.send = uncertain
    with pytest.raises(PageTargetCreationUncertain) as caught:
        new_background_page(first, first, timeout_ms=1234, owner='task-one')
    assert caught.value.__cause__ is not None
    assert len(first.pages) == 2  # Foreign/human + uncertain owned target, not guessed closed.
    assert first.closed == []
    with pytest.raises(PageTargetCreationUncertain):
        new_background_page(second, second, timeout_ms=1234)
    assert second.calls == []
    with pytest.raises(PageTargetCreationUncertain):
        bind_page_admission(RacingTargets(), admission)  # Reconnect cannot reset it.


def test_known_cleanup_failure_blocks_distinct_wrapper_without_remote_calls():
    from src.research.cdp_pages import (
        PageResourceAdmission,
        PageTargetCleanupError,
        bind_page_admission,
    )
    admission = PageResourceAdmission()
    first, second = RacingTargets(spoof=True), RacingTargets()
    bind_page_admission(first, admission)
    bind_page_admission(second, admission)
    original = first.send
    def failed_close(command, params):
        if command == 'Target.closeTarget':
            raise OSError('synthetic close failure')
        return original(command, params)
    first.send = failed_close
    with pytest.raises(PageTargetCleanupError):
        new_background_page(first, first, timeout_ms=1234)
    with pytest.raises(PageTargetCleanupError):
        new_background_page(second, second, timeout_ms=1234)
    assert second.calls == []


def test_postnavigation_owner_uses_native_target_not_destroyed_javascript_context():
    from src.research.cdp_pages import native_page_owner
    protocol = RacingTargets()
    page = new_background_page(protocol, protocol, timeout_ms=1234, owner='task-one')
    page.url = 'https://synthetic.invalid/redirected'
    page.owner_name = ''  # Site may change window.name.
    page.evaluate = lambda *args: (_ for _ in ()).throw(RuntimeError('context destroyed'))
    assert native_page_owner(page) == 'task-one'
    page.is_closed = lambda: True
    assert native_page_owner(page) is None


def test_postnavigation_target_mismatch_fails_closed_without_closing_a_foreign_page():
    from src.research.cdp_pages import (
        PageResourceAdmission,
        PageTargetOwnershipError,
        bind_page_admission,
    )
    admission = PageResourceAdmission()
    protocol = RacingTargets()
    bind_page_admission(protocol, admission)
    page = new_background_page(protocol, protocol, timeout_ms=1234, owner='task-one')
    page.target = 'human'
    # Native target changed under the claimed wrapper: reject, never adopt/re-tag.
    protocol.new_cdp_session = lambda _: SimpleNamespace(
        send=lambda _: {'targetInfo': {'targetId': 'human'}}, detach=lambda: None)
    with pytest.raises(PageTargetOwnershipError):
        native_page_owner(page)
    assert protocol.closed == []
    with pytest.raises(PageTargetOwnershipError):
        admission.require_open()


def test_invalid_admission_rebinding_cannot_clear_fault():
    from src.research.cdp_pages import (
        PageResourceAdmission,
        PageTargetOwnershipError,
        bind_page_admission,
    )
    browser = RacingTargets()
    first, second = PageResourceAdmission(), PageResourceAdmission()
    bind_page_admission(browser, first)
    with pytest.raises(PageTargetOwnershipError):
        bind_page_admission(browser, second)
    for admission in (first, second):
        with pytest.raises(PageTargetOwnershipError):
            admission.require_open()
    assert browser.calls == []

def test_native_owner_detach_failure_invalidates_shared_admission():
    from src.research.cdp_pages import (
        PageResourceAdmission,
        PageTargetCleanupError,
        bind_page_admission,
    )
    admission = PageResourceAdmission()
    protocol = RacingTargets()
    bind_page_admission(protocol, admission)
    page = new_background_page(protocol, protocol, timeout_ms=1234, owner='task-one')
    make = protocol.new_cdp_session
    def broken(page):
        session = make(page)
        session.detach = lambda: (_ for _ in ()).throw(OSError('synthetic detach'))
        return session
    protocol.new_cdp_session = broken
    with pytest.raises(PageTargetCleanupError):
        native_page_owner(page)
    with pytest.raises(PageTargetCleanupError):
        admission.require_open()
    assert protocol.closed == []


def test_another_client_fault_during_creation_prevents_return_and_closes_only_own_target():
    from src.research.cdp_pages import (
        PageResourceAdmission,
        PageTargetCreationUncertain,
        bind_page_admission,
    )
    admission = PageResourceAdmission()
    protocol = RacingTargets()
    bind_page_admission(protocol, admission)
    make = protocol.new_cdp_session
    def proof(page):
        session = make(page)
        admission.invalidate(PageTargetCreationUncertain((OSError('other client response lost'),)))
        return session
    protocol.new_cdp_session = proof
    with pytest.raises(PageTargetCreationUncertain):
        new_background_page(protocol, protocol, timeout_ms=1234, owner='task-one')
    assert protocol.closed == ['owned-1']
    assert protocol.pages[0].target == 'human'


def test_shared_admission_fault_metadata_is_thread_safe_and_does_not_reuse_exception_objects():
    from concurrent.futures import ThreadPoolExecutor

    from src.research.cdp_pages import (
        PageResourceAdmission,
        PageTargetCreationUncertain,
    )
    admission = PageResourceAdmission()
    admission.invalidate(PageTargetCreationUncertain((OSError('sensitive synthetic text'),)))
    def check(_):
        try:
            admission.require_open()
        except PageTargetCreationUncertain as error:
            assert str(error) == 'CDP_PAGE_CREATION_UNCONFIRMED'
            assert error.failure_classes == ('OSError',)
            return error
        pytest.fail('must reject')
    with ThreadPoolExecutor(max_workers=2) as executor:
        errors = list(executor.map(check, range(4)))
    assert len({id(error) for error in errors}) == 4

@pytest.mark.parametrize('shared', [False, True])
def test_injected_admission_covers_reused_and_fallback_clients_without_closing_browser(shared, monkeypatch):
    from src.research.cdp_pages import (
        PageResourceAdmission,
        PageTargetCreationUncertain,
    )
    browser = _FakeBrowser()
    calls = []
    class Manager:
        def __enter__(self):
            calls.append('enter')
            return SimpleNamespace(chromium=SimpleNamespace(
                connect_over_cdp=lambda *a, **k: calls.append('connect') or browser))
        def __exit__(self, *exc):
            calls.append('exit')
            return False
    monkeypatch.setattr('playwright.sync_api.sync_playwright', lambda: Manager())
    admission = PageResourceAdmission()
    provider = (lambda: (object(), browser)) if shared else (lambda: None)
    factory = shared_playwright_factory(provider, admission=admission)
    with factory() as playwright:
        assert playwright.chromium.connect_over_cdp('http://127.0.0.1:9222') is browser
        assert browser._inso_page_admission is admission
    assert calls == ([] if shared else ['enter', 'connect', 'exit'])
    admission.invalidate(PageTargetCreationUncertain((OSError('synthetic lost response'),)))
    with pytest.raises(PageTargetCreationUncertain):
        factory()
    assert calls == ([] if shared else ['enter', 'connect', 'exit'])


def test_native_identity_does_not_override_legacy_write_marker_quarantine():
    from src.research.cdp_pages import page_owner
    protocol = RacingTargets()
    page = new_background_page(protocol, protocol, timeout_ms=1234, owner='google-operation')
    page.owner_name = ''
    assert page_owner(page) is None  # Existing write/quarantine contract unchanged.
    assert native_page_owner(page) == 'google-operation'  # Explicit read-only capability only.
