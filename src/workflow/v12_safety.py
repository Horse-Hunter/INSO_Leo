"""Narrow, allowlisted external-error classification for V1.2."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal

from .v12_contracts import ReasonCode


class ErrorCategory(StrEnum):
    TRANSIENT = "TRANSIENT"
    PERMANENT = "PERMANENT"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class SafeError:
    reason_code: ReasonCode
    category: ErrorCategory


@dataclass(frozen=True, slots=True)
class SafeV12LogEntry:
    occurred_at: datetime
    phase: str
    reason_code: ReasonCode


class V12SafeLogger:
    """Tiny logging boundary that accepts only a phase and allowlisted code."""

    def __init__(
        self,
        sink: Callable[[SafeV12LogEntry], None],
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._sink = sink
        self._clock = clock or (lambda: datetime.now(UTC))

    def record_external_error(self, phase: str, error: BaseException) -> ReasonCode:
        if phase not in {"duplicate", "notification", "purchase", "session", "sqlite"}:
            phase = "unknown"
        summary = sanitize_external_error(error, subsystem=phase)  # type: ignore[arg-type]
        self._sink(SafeV12LogEntry(self._clock(), phase, summary.reason_code))
        return summary.reason_code


def sanitize_external_error(
    error: BaseException,
    *,
    subsystem: Literal["duplicate", "notification", "purchase", "session", "sqlite", "other"] = "other",
) -> SafeError:
    """Map exception types to a closed reason code without reading its message."""

    if subsystem == "notification" and isinstance(
        error, (TimeoutError, ConnectionError, OSError)
    ):
        return SafeError(ReasonCode.NOTIFICATION_TRANSIENT, ErrorCategory.TRANSIENT)
    if subsystem == "duplicate" and isinstance(
        error, (TimeoutError, ConnectionError, OSError)
    ):
        return SafeError(ReasonCode.DUPLICATE_LOOKUP_UNAVAILABLE, ErrorCategory.TRANSIENT)
    if subsystem == "sqlite" and isinstance(error, sqlite3.IntegrityError):
        return SafeError(ReasonCode.SQLITE_MIGRATION_INVALID, ErrorCategory.PERMANENT)
    if subsystem == "sqlite" and isinstance(error, sqlite3.OperationalError):
        return SafeError(ReasonCode.SQLITE_BACKUP_INVALID, ErrorCategory.TRANSIENT)
    return SafeError(
        ReasonCode.UNKNOWN_EXTERNAL_FAILURE,
        ErrorCategory.UNKNOWN,
    )


class MpnPolicy(StrEnum):
    DUP_MPN_V1 = "dup-mpn-v1"
    AI_MPN_V1 = "ai-mpn-v1"


def normalize_mpn(value: str, *, policy: MpnPolicy) -> str:
    """Normalize according to a named/versioned exact-match policy."""

    if not isinstance(value, str):
        raise TypeError("mpn must be a string")
    if policy not in {MpnPolicy.DUP_MPN_V1, MpnPolicy.AI_MPN_V1}:
        raise ValueError("unsupported MPN policy")
    import unicodedata

    normalized = unicodedata.normalize("NFKC", value).strip()
    return "".join(
        chr(ord(char) - 32) if "a" <= char <= "z" else char
        for char in normalized
    )


def mpn_matches(left: str, right: str, *, policy: MpnPolicy) -> bool:
    return normalize_mpn(left, policy=policy) == normalize_mpn(right, policy=policy)
