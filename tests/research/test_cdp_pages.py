from types import SimpleNamespace
from typing import Self

import pytest

from src.research.cdp_pages import new_background_page, shared_playwright_factory


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
