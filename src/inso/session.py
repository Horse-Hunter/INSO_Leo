"""A lease for the already-authenticated INSO shell page."""

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
    def is_closed(self) -> bool: ...


class PageHandle(Protocol):
    def is_closed(self) -> bool: ...


class IdentityProbe(Protocol):
    def endpoint_id(self, browser: BrowserHandle) -> str | None: ...

    def browser_id(self, browser: BrowserHandle) -> str | None: ...

    def context_id(self, context: ContextHandle) -> str | None: ...

    def page_identity(self, page: PageHandle) -> PageIdentity | None: ...


class OperationPage:
    """Borrowed view of the pinned shell page; leaving it never closes it."""

    __slots__ = ("_lease",)

    def __init__(self, lease: InsoSessionLease) -> None:
        self._lease = lease

    @property
    def page(self) -> PageHandle:
        self._lease._assert_identity()
        return self._lease._operation_page_handle

    @property
    def identity(self) -> PageIdentity:
        self._lease._assert_identity()
        return self._lease.operation_page_identity

    @property
    def shell_frame(self) -> Any:
        self._lease._assert_identity()
        return self._lease._operation_frame

    def __enter__(self) -> Self:
        _ = self.page
        return self

    def __exit__(self, *_: object) -> None:
        # The page belongs to the authenticated session, not this operation.
        self._lease._assert_identity()


class InsoOperationAccess:
    """Narrow capability to reuse the verified authenticated shell page."""

    __slots__ = ("_lease", "_operation_id")

    def __init__(self, lease: InsoSessionLease, operation_id: str) -> None:
        self._lease = lease
        self._operation_id = operation_id

    def operation_page(self) -> OperationPage:
        if not self._operation_id:
            raise SecurityViolation("operation identity is required")
        self._lease._assert_identity()
        return OperationPage(self._lease)


class InsoSessionLease:
    """Composition-root-owned lease pinned to one verified shell page."""

    def __init__(
        self,
        *,
        ownership: BrowserOwnership,
        browser: BrowserHandle,
        context: ContextHandle,
        operation_page: PageHandle,
        operation_frame: Any,
        browser_identity: BrowserIdentity,
        context_identity: ContextIdentity,
        operation_page_identity: PageIdentity,
        identity_probe: IdentityProbe,
        operation_page_is_valid: Callable[[PageHandle], bool],
        cycle_id: str,
        cycle_is_drained: Callable[[str], bool],
    ) -> None:
        self.ownership = BrowserOwnership(ownership)
        self.browser_identity = browser_identity
        self.context_identity = context_identity
        self.operation_page_identity = operation_page_identity
        self.cycle_id = cycle_id
        self._cycle_is_drained = cycle_is_drained
        self._browser = browser
        self._context = context
        self._operation_page_handle = operation_page
        self._operation_frame = operation_frame
        self._identity_probe = identity_probe
        self._operation_page_is_valid = operation_page_is_valid
        self._state = LeaseState.ACTIVE
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
        """Launcher-only lifecycle call after the full workflow cycle drains."""

        if self.ownership is BrowserOwnership.APP_OWNED and not self._cycle_is_drained(
            self.cycle_id
        ):
            raise SecurityViolation("app-owned browser cycle has not drained")
        if self._state is LeaseState.RELEASED:
            return
        if self.ownership is BrowserOwnership.APP_OWNED:
            self._browser.close()
        # A reused browser and its authenticated shell page remain open.
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
        if self._operation_page_handle.is_closed():
            self.invalidate()
            raise SecurityViolation("verified shell page is closed")
        if (
            self._identity_probe.page_identity(self._operation_page_handle)
            != self.operation_page_identity
        ):
            self.invalidate()
            raise SecurityViolation("verified shell page identity changed")
        try:
            valid_shell = self._operation_page_is_valid(self._operation_page_handle)
        except Exception:  # noqa: BLE001 - validation failures close the lease
            valid_shell = False
        if not valid_shell:
            self.invalidate()
            raise SecurityViolation("verified INSO shell identity is stale")


__all__ = [
    "BrowserIdentity",
    "BrowserOwnership",
    "ContextIdentity",
    "InsoOperationAccess",
    "InsoSessionLease",
    "LeaseState",
    "OperationPage",
    "PageIdentity",
    "SecurityViolation",
]
