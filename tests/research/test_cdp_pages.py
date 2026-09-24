from types import SimpleNamespace
from typing import Self

import pytest

from src.research.cdp_pages import new_background_page


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
