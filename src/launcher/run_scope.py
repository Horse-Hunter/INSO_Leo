"""Explicit run scope for a controlled trial start (RFQ-021 / B5).

A release build must never fall back to an unscoped full start. The scope names
the only orders, the only modules and the only external write targets one run
may touch, plus the Owner approval that unlocked those writes.

Two rules keep this honest:

* A scope can only **narrow**. It is consulted in addition to the existing
  production gates, so an unapproved scope cannot re-open a control that the
  production path keeps closed.
* A missing or invalid scope is refused at Start, not defaulted. There is no
  code path that silently upgrades a refused scope into a full run.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

#: Business modules that may be enabled for one scoped run.
MODULES = frozenset({"inquiry", "quotation", "tp", "notification"})

#: External write families a run may be allowed to reach.
WRITE_TARGETS = frozenset({"google", "inso", "smtp"})

#: Modules that cannot do anything useful without their write family. Used for
#: operator warnings only; the runtime still fails closed on its own.
_MODULE_WRITES = {
    "quotation": "google",
    "tp": "google",
    "notification": "smtp",
    "inquiry": "inso",
}

_INQUIRY_ID = re.compile(r"inq_[a-f0-9]{24,32}")
_APPROVAL = re.compile(r"OWNER-APPROVED:[A-Za-z0-9._:-]{4,64}")


class ScopeError(ValueError):
    """A scope that cannot be honoured. The caller must refuse to start."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def _split(value: str | None) -> frozenset[str]:
    if not value:
        return frozenset()
    return frozenset(part.strip() for part in re.split(r"[,\s]+", value) if part.strip())


@dataclass(frozen=True, slots=True)
class RunScope:
    """The reviewed boundary of one controlled run."""

    inquiry_ids: frozenset[str]
    modules: frozenset[str]
    write_targets: frozenset[str]
    approval_reference: str = ""

    def __post_init__(self) -> None:
        if not self.inquiry_ids:
            raise ScopeError("SCOPE_REQUIRES_INQUIRY_IDS")
        invalid = sorted(item for item in self.inquiry_ids if not _INQUIRY_ID.fullmatch(item))
        if invalid:
            raise ScopeError("SCOPE_INVALID_INQUIRY_ID")
        unknown = sorted(self.modules - MODULES)
        if unknown:
            raise ScopeError("SCOPE_UNKNOWN_MODULE")
        # The inquiry driver owns the poll loop this process runs; a "scope"
        # that switches it off would not be a scope, it would be a different
        # program. Optional modules are what actually get added.
        if "inquiry" not in self.modules:
            raise ScopeError("SCOPE_REQUIRES_INQUIRY_MODULE")
        unknown = sorted(self.write_targets - WRITE_TARGETS)
        if unknown:
            raise ScopeError("SCOPE_UNKNOWN_WRITE_TARGET")
        if self.write_targets and not _APPROVAL.fullmatch(self.approval_reference):
            raise ScopeError("SCOPE_WRITES_REQUIRE_OWNER_APPROVAL")

    def allows_module(self, name: str) -> bool:
        return name in self.modules

    def allows_write(self, target: str) -> bool:
        return target in self.write_targets

    def describe(self) -> dict[str, object]:
        """Sanitized, log-safe summary. Never contains customer field values."""
        return {
            "orders": len(self.inquiry_ids),
            "modules": sorted(self.modules),
            "write_targets": sorted(self.write_targets),
            "approved": bool(self.write_targets),
            "warnings": self.warnings(),
        }

    def warnings(self) -> list[str]:
        missing = [
            f"{module}->{target}"
            for module, target in sorted(_MODULE_WRITES.items())
            if module in self.modules and target not in self.write_targets
        ]
        return [f"MODULE_WRITES_DISABLED:{item}" for item in missing]


def parse_run_scope(
    *,
    inquiry_ids: str | None,
    modules: str | None,
    write_targets: str | None = None,
    approval: str | None = None,
) -> RunScope:
    """Build a validated scope from CLI text. Raises ``ScopeError``."""
    return RunScope(
        inquiry_ids=_split(inquiry_ids),
        modules=_split(modules),
        write_targets=_split(write_targets),
        approval_reference=(approval or "").strip(),
    )


class ScopeViolation(RuntimeError):
    """An external effect was attempted outside the approved scope."""

    def __init__(self, reason: str = "EXTERNAL_WRITE_NOT_IN_SCOPE") -> None:
        super().__init__(reason)
        self.reason = reason


class ExternalWritePolicy:
    """One answer, shared by every adapter, to "may this write happen?".

    ``enforced=False`` keeps the legacy composition unchanged for unit tests and
    for the historical source-mode entry points. The packaged release entry
    always enforces it, and an enforced policy with no scope denies everything.
    """

    def __init__(self, scope: RunScope | None = None, *, enforced: bool = False) -> None:
        self._scope = scope
        self._enforced = bool(enforced)
        self._blocked_reason = ""

    @property
    def scope(self) -> RunScope | None:
        return self._scope

    @property
    def enforced(self) -> bool:
        return self._enforced

    def block_all_writes(self, reason: str) -> None:
        """Fail closed: a broken safety record disables every external write."""
        self._blocked_reason = str(reason) or "EXTERNAL_WRITE_BLOCKED"

    @property
    def blocked_reason(self) -> str:
        return self._blocked_reason

    def allows(self, target: str) -> bool:
        if self._blocked_reason:
            return False
        if not self._enforced:
            return True
        if self._scope is None:
            return False
        return self._scope.allows_write(target)

    def denial_reason(self, target: str) -> str:
        if self._blocked_reason:
            return self._blocked_reason
        if not self._enforced:
            return ""
        if self._scope is None:
            return "SCOPE_MISSING"
        return "" if self._scope.allows_write(target) else "EXTERNAL_WRITE_NOT_IN_SCOPE"

    def require(self, target: str) -> None:
        if not self.allows(target):
            raise ScopeViolation(self.denial_reason(target) or "EXTERNAL_WRITE_NOT_IN_SCOPE")


class ScopedInsoWriteGate:
    """Narrow the existing INSO write gate to the approved scope.

    The wrapped gate is unchanged, so ``SAVE_DATA`` stays closed exactly as the
    production path defines it; this only adds a refusal in front of it.
    """

    def __init__(self, inner, policy: ExternalWritePolicy, target: str = "inso") -> None:
        self._inner = inner
        self._policy = policy
        self._target = target

    def require_open(self) -> None:
        self._policy.require(self._target)
        self._inner.require_open()

    def require_save_and_send(self) -> None:
        self._policy.require(self._target)
        authorize = getattr(self._inner, "require_save_and_send", None)
        if not callable(authorize):
            raise ScopeViolation("SAVE_AND_SEND_NOT_AUTHORIZED")
        authorize()
