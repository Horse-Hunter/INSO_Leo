"""Read-only `DuplicateChecker` over the INSO duplicate-history adapter.

This module holds only the Workflow-side bridge: it converts INSO records into
the canonical decision input and delegates every business rule (canonical MPN,
rolling inclusive 168h window, latest-record selection, equal-timestamp
ambiguity) to :func:`src.workflow.v12_rules.evaluate_duplicate_history`.

A read failure is never reported as "not a duplicate".
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from src.inso.duplicate_history import (
    DuplicateHistoryCapture,
    DuplicateHistoryFailure,
    InsoDuplicateHistoryError,
)

from .v12_contracts import DuplicateCheckResult, DuplicateOutcome, ReasonCode
from .v12_rules import HistoricalInquiryRecord, evaluate_duplicate_history
from .v12_safety import MpnPolicy, normalize_mpn


class DuplicateHistoryReader(Protocol):
    """Source of raw INSO history for one exact search value."""

    def read(self, search_value: str) -> DuplicateHistoryCapture: ...


#: Read failures where records exist but cannot be reliably attributed.
AMBIGUOUS_READ_FAILURES = frozenset(
    {
        DuplicateHistoryFailure.RESULT_IDENTIFIER_AMBIGUOUS,
        DuplicateHistoryFailure.DETAIL_IDENTITY_MISMATCH,
    }
)


class InsoDuplicateHistoryChecker:
    """Implements the Workflow `DuplicateChecker` protocol; read-only."""

    def __init__(self, reader: DuplicateHistoryReader) -> None:
        self._reader = reader

    def check(
        self, inquiry_id: str, mpn: str, quantity: int, *, at: datetime
    ) -> DuplicateCheckResult:
        canonical = _canonical(mpn)
        if not canonical or isinstance(quantity, bool) or not isinstance(quantity, int):
            # Invalid input is never sent to INSO and is never a negative result.
            return evaluate_duplicate_history(
                inquiry_id=inquiry_id,
                target_mpn=mpn,
                current_quantity=quantity,
                records=(),
                checked_at=at,
            )
        try:
            capture = self._reader.read(canonical)
        except InsoDuplicateHistoryError as exc:
            return _read_failure(inquiry_id, canonical, at, exc.code)
        except Exception:  # noqa: BLE001 - any read error stays a non-decision
            return _read_failure(inquiry_id, canonical, at, None)
        records = tuple(
            HistoricalInquiryRecord(
                mpn=record.mpn,
                quoted_at=record.quoted_at,
                quantity=record.quantity,
                creator=record.creator,
                inso_quote=record.inso_quote,
                currency=record.currency,
            )
            for record in capture.records
        )
        return evaluate_duplicate_history(
            inquiry_id=inquiry_id,
            target_mpn=mpn,
            current_quantity=quantity,
            records=records,
            checked_at=at,
        )


def _canonical(mpn: object) -> str:
    if not isinstance(mpn, str):
        return ""
    try:
        return normalize_mpn(mpn, policy=MpnPolicy.DUP_MPN_V1)
    except (TypeError, ValueError):
        return ""


def _read_failure(
    inquiry_id: str,
    canonical: str,
    at: datetime,
    code: DuplicateHistoryFailure | None,
) -> DuplicateCheckResult:
    if code in AMBIGUOUS_READ_FAILURES:
        return DuplicateCheckResult(
            inquiry_id,
            DuplicateOutcome.AMBIGUOUS,
            canonical,
            at,
            reason_code=ReasonCode.DUPLICATE_LOOKUP_AMBIGUOUS,
        )
    return DuplicateCheckResult(
        inquiry_id,
        DuplicateOutcome.UNAVAILABLE,
        canonical,
        at,
        reason_code=ReasonCode.DUPLICATE_LOOKUP_UNAVAILABLE,
    )
