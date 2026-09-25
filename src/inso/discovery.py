"""Prepare-only, read-only INSO discovery inspector.

This module is not wired to a browser provider and is not executed in Stage 2A.
Its protocol has reads only; it exposes no mutation capability.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .session import BrowserIdentity, ContextIdentity, PageIdentity, SecurityViolation


@dataclass(frozen=True, slots=True)
class SafePageMetadata:
    origin: str
    path: str
    title: str
    app_identity: tuple[tuple[str, str], ...]
    browser: BrowserIdentity
    context: ContextIdentity
    page: PageIdentity
    ownership: str


@dataclass(frozen=True, slots=True)
class SafeControlMetadata:
    control_id: str
    role: str
    accessible_name: str
    stable_attribute_names: tuple[str, ...]
    selector_uniqueness: int


@dataclass(frozen=True, slots=True)
class ReadCapabilityMetadata:
    history_stable_id_available: bool | None
    timestamp_tie_behavior_known: bool | None
    saved_draft_identity_feasible: bool | None
    readback_fields: tuple[str, ...]
    screenshot_crop_safe: bool | None
    screenshot_redaction_safe: bool | None


@dataclass(frozen=True, slots=True)
class DiscoveryReport:
    page: SafePageMetadata
    controls: tuple[SafeControlMetadata, ...]
    read_capabilities: ReadCapabilityMetadata
    safe: bool


class ReadOnlyDiscoverySession(Protocol):
    """Read-only metadata queries; deliberately no click/fill/clear methods."""

    def read_page_metadata(self) -> SafePageMetadata: ...

    def read_control_metadata(self) -> tuple[SafeControlMetadata, ...]: ...

    def read_capabilities(self) -> ReadCapabilityMetadata: ...


class ReadOnlyDiscoveryInspector:
    def inspect(
        self,
        session: ReadOnlyDiscoverySession,
        *,
        required_control_ids: frozenset[str],
    ) -> DiscoveryReport:
        """Inspect an explicitly provided safe session; caller must authorize run."""

        page = session.read_page_metadata()
        controls = session.read_control_metadata()
        capabilities = session.read_capabilities()
        identity_safe = (
            bool(page.origin)
            and bool(page.path)
            and bool(page.title)
            and bool(page.browser.endpoint_id)
            and page.browser.browser_id != ""
            and bool(page.context.context_id)
            and page.context.browser_id == page.browser.browser_id
            and page.page.context_id == page.context.context_id
            and bool(page.page.target_id)
            and page.ownership in {"APP_OWNED", "REUSED"}
        )
        control_counts = {
            control_id: sum(control.control_id == control_id for control in controls)
            for control_id in required_control_ids
        }
        required_unique = bool(required_control_ids) and all(
            count == 1
            and next(
                control.selector_uniqueness
                for control in controls
                if control.control_id == control_id
            ) == 1
            for control_id, count in control_counts.items()
        )
        unique = all(0 <= control.selector_uniqueness <= 1 for control in controls)
        if not identity_safe:
            raise SecurityViolation("read-only inspector identity is not verified")
        return DiscoveryReport(page, controls, capabilities, safe=unique and required_unique)
