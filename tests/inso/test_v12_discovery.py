from __future__ import annotations

from src.inso.discovery import (
    ReadCapabilityMetadata,
    ReadOnlyDiscoveryInspector,
    SafeControlMetadata,
    SafePageMetadata,
)
from src.inso.session import BrowserIdentity, ContextIdentity, PageIdentity


class FakeReadOnlySession:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def read_page_metadata(self) -> SafePageMetadata:
        self.calls.append("page")
        return SafePageMetadata(
            "https://example.invalid",
            "/business-inquiry",
            "Synthetic inquiry page",
            (("data-app", "synthetic"),),
            BrowserIdentity("fake-endpoint", "fake-browser"),
            ContextIdentity("fake-browser", "fake-context"),
            PageIdentity("fake-context", "fake-page"),
            "REUSED",
        )

    def read_control_metadata(self) -> tuple[SafeControlMetadata, ...]:
        self.calls.append("controls")
        return (SafeControlMetadata("button", "保存数据", ("data-action",), 1),)

    def read_capabilities(self) -> ReadCapabilityMetadata:
        self.calls.append("capabilities")
        return ReadCapabilityMetadata(None, None, None, (), None, None)


def test_inspector_is_prepare_only_and_reads_fake_metadata() -> None:
    inspector = ReadOnlyDiscoveryInspector()
    session = FakeReadOnlySession()

    report = inspector.inspect(session)

    assert report.safe
    assert [control.selector_uniqueness for control in report.controls] == [1]
    assert session.calls == ["page", "controls", "capabilities"]
    assert not hasattr(inspector, "click")
    assert not hasattr(inspector, "fill")
    assert not hasattr(inspector, "save_data")
    assert not hasattr(inspector, "send")
