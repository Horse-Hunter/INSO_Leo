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
        return {"targetId": "synthetic-target"}

    def detach(self) -> None:
        self.detached = True


class Context:
    def __init__(self, *, fail: bool = False) -> None:
        self.page = object()
        self.fail = fail

    def expect_page(self, *, timeout: int) -> "Context":
        assert timeout == 1234
        return self

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
        ("Target.createTarget", {"url": "about:blank", "background": True})
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
                "url": "about:blank",
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
