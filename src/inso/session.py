"""Explicit browser/context/page ownership primitives for INSO operations.

The root lease is held by the launcher. Module adapters receive only the
operation-scoped capability and can close only pages they opened themselves.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol, Self


class SecurityViolation(RuntimeError):
    """A requested browser operation could not be proven safe."""


class BrowserOwnership(StrEnum):
    APP_OWNED = "APP_OWNED"
    REUSED = "REUSED"


class LeaseState(StrEnum):
    ACTIVE = "ACTIVE"
    INVALIDATED = "INVALIDATED"
    RELEASED = "RELEASED"


@dataclass(frozen=True, slots=True)
class BrowserIdentity:
    endpoint_id: str
    browser_id: str


@dataclass(frozen=True, slots=True)
class ContextIdentity:
    browser_id: str
    context_id: str


@dataclass(frozen=True, slots=True)
class PageIdentity:
    context_id: str
    target_id: str


class BrowserHandle(Protocol):
    def is_connected(self) -> bool: ...

    def close(self) -> None: ...


class ContextHandle(Protocol):
    def new_page(self) -> Any: ...

    def is_closed(self) -> bool: ...


class PageHandle(Protocol):
    def is_closed(self) -> bool: ...

    def close(self) -> None: ...


class IdentityProbe(Protocol):
    def endpoint_id(self, browser: BrowserHandle) -> str | None: ...

    def browser_id(self, browser: BrowserHandle) -> str | None: ...

    def context_id(self, context: ContextHandle) -> str | None: ...

    def page_identity(self, page: PageHandle) -> PageIdentity | None: ...


@dataclass(slots=True)
class _OwnedChild:
    page: PageHandle
    identity: PageIdentity
    operation_id: str


class OperationPage:
    """Capability for one child page; it cannot release/close the browser."""

    __slots__ = ("_child", "_closed", "_lease")

    def __init__(self, lease: InsoSessionLease, child: _OwnedChild) -> None:
        self._lease = lease
        self._child = child
        self._closed = False

    @property
    def page(self) -> PageHandle:
        if self._closed:
            raise SecurityViolation("operation page is already closed")
        self._lease._validate_child(self._child)
        return self._child.page

    @property
    def identity(self) -> PageIdentity:
        self._lease._validate_child(self._child)
        return self._child.identity

    def close(self) -> None:
        if self._closed:
            return
        self._lease._close_child(self._child)
        self._closed = True

    def __enter__(self) -> Self:
        _ = self.page
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


class InsoOperationAccess:
    """Narrow adapter capability; intentionally has no browser close method."""

    __slots__ = ("_lease", "_operation_id")

    def __init__(self, lease: InsoSessionLease, operation_id: str) -> None:
        self._lease = lease
        self._operation_id = operation_id

    def open_operation_page(self) -> OperationPage:
        return self._lease._open_child(self._operation_id)


class InsoSessionLease:
    """Composition-root-owned lease over explicit verified handles/identity."""

    def __init__(
        self,
        *,
        ownership: BrowserOwnership,
        browser: BrowserHandle,
        context: ContextHandle,
        browser_identity: BrowserIdentity,
        context_identity: ContextIdentity,
        identity_probe: IdentityProbe,
        cycle_id: str,
        cycle_is_drained: Callable[[str], bool],
    ) -> None:
        self.ownership = BrowserOwnership(ownership)
        self.browser_identity = browser_identity
        self.context_identity = context_identity
        self.cycle_id = cycle_id
        self._cycle_is_drained = cycle_is_drained
        self._browser = browser
        self._context = context
        self._identity_probe = identity_probe
        self._state = LeaseState.ACTIVE
        self._children: dict[str, _OwnedChild] = {}
        self._assert_identity()

    @property
    def state(self) -> LeaseState:
        return self._state

    def adapter_access(self, operation_id: str) -> InsoOperationAccess:
        self._assert_identity()
        if not operation_id:
            raise SecurityViolation("operation identity is required")
        return InsoOperationAccess(self, operation_id)

    def invalidate(self) -> None:
        if self._state is LeaseState.ACTIVE:
            self._state = LeaseState.INVALIDATED

    def close_after_drain(self) -> None:
        """Launcher-only lifecycle call; refuses release while children exist."""

        if self._children:
            raise SecurityViolation("cannot release session with active child pages")
        if self.ownership is BrowserOwnership.APP_OWNED and not self._cycle_is_drained(
            self.cycle_id
        ):
            raise SecurityViolation("app-owned browser cycle has not drained")
        if self._state is LeaseState.RELEASED:
            return
        if self.ownership is BrowserOwnership.APP_OWNED:
            self._browser.close()
        # A reused browser is deliberately never closed by this lease.
        self._state = LeaseState.RELEASED

    def _assert_identity(self) -> None:
        if self._state is not LeaseState.ACTIVE:
            raise SecurityViolation("session lease is not active")
        if not self._browser.is_connected() or self._context.is_closed():
            self.invalidate()
            raise SecurityViolation("browser or context is stale")
        if self._identity_probe.endpoint_id(self._browser) != self.browser_identity.endpoint_id:
            self.invalidate()
            raise SecurityViolation("browser endpoint identity changed")
        if self._identity_probe.browser_id(self._browser) != self.browser_identity.browser_id:
            self.invalidate()
            raise SecurityViolation("browser identity changed")
        if self.context_identity.browser_id != self.browser_identity.browser_id:
            self.invalidate()
            raise SecurityViolation("context belongs to a different browser")
        if self._identity_probe.context_id(self._context) != self.context_identity.context_id:
            self.invalidate()
            raise SecurityViolation("context identity changed")

    def _open_child(self, operation_id: str) -> OperationPage:
        self._assert_identity()
        page = self._context.new_page()
        identity = self._identity_probe.page_identity(page)
        if (
            identity is None
            or identity.context_id != self.context_identity.context_id
            or not identity.target_id
            or page.is_closed()
        ):
            # This page was created by this operation, so it is the only target
            # that may be closed on failed verification.
            try:
                page.close()
            finally:
                raise SecurityViolation("new page identity could not be verified")
        if identity.target_id in self._children:
            try:
                page.close()
            finally:
                raise SecurityViolation("duplicate child page identity")
        child = _OwnedChild(page, identity, operation_id)
        self._children[identity.target_id] = child
        return OperationPage(self, child)

    def _validate_child(self, child: _OwnedChild) -> None:
        self._assert_identity()
        current = self._children.get(child.identity.target_id)
        if current is not child or child.page.is_closed():
            self.invalidate()
            raise SecurityViolation("operation page is stale or not owned")
        identity = self._identity_probe.page_identity(child.page)
        if identity != child.identity or identity.context_id != self.context_identity.context_id:
            self.invalidate()
            raise SecurityViolation("operation page identity changed")

    def _close_child(self, child: _OwnedChild) -> None:
        tracked = self._children.get(child.identity.target_id)
        if tracked is not child:
            raise SecurityViolation("operation page is not owned by this lease")
        if child.page.is_closed():
            # The operation-owned target is already gone; remove only its lease
            # bookkeeping entry without touching any other page or context.
            del self._children[child.identity.target_id]
            return
        self._validate_child(child)
        child.page.close()
        del self._children[child.identity.target_id]
