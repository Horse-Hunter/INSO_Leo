"""Deterministic tests for the INSO-backed Workflow DuplicateChecker bridge.

The reader is a fake; no INSO connection is made. The bridge must delegate all
business rules to `evaluate_duplicate_history` and must never turn a read
failure into a "not a duplicate".
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from src.inso.duplicate_history import (
    DuplicateHistoryCapture,
    DuplicateHistoryFailure,
    DuplicateHistoryRecord,
    InsoDuplicateHistoryError,
)
from src.workflow import v12_duplicate as module
from src.workflow.v12_contracts import DuplicateOutcome, ReasonCode
from src.workflow.v12_duplicate import InsoDuplicateHistoryChecker
from src.workflow.v12_rules import PostResearchRoute, route_after_research

NOW = datetime(2026, 9, 25, 8, tzinfo=UTC)
INQUIRY = "inq_0123456789abcdef01234567"
MPN = "STM32F103C8T6"


def record(
    *,
    mpn: str = MPN,
    quantity: int = 10,
    quoted_at: datetime | None = None,
    bill_id: str = "7788",
    creator: str | None = "制单人甲",
) -> DuplicateHistoryRecord:
    return DuplicateHistoryRecord(
        bill_id=bill_id,
        mpn=mpn,
        quantity=quantity,
        quoted_at=quoted_at or (NOW - timedelta(hours=2)),
        creator=creator,
    )


class FakeReader:
    def __init__(self, result: DuplicateHistoryCapture | BaseException) -> None:
        self._result = result
        self.search_values: list[str] = []

    def read(self, search_value: str) -> DuplicateHistoryCapture:
        self.search_values.append(search_value)
        if isinstance(self._result, BaseException):
            raise self._result
        return self._result


def capture(*records: DuplicateHistoryRecord, target_mpn: str = MPN) -> DuplicateHistoryCapture:
    return DuplicateHistoryCapture(target_mpn, tuple(records), "https://example.invalid", NOW)


def checker_for(result: DuplicateHistoryCapture | BaseException):
    reader = FakeReader(result)
    return InsoDuplicateHistoryChecker(reader), reader


def test_recent_matching_record_is_a_confirmed_duplicate() -> None:
    checker, reader = checker_for(capture(record()))

    result = checker.check(INQUIRY, MPN, 10, at=NOW)

    assert result.outcome is DuplicateOutcome.CONFIRMED
    assert result.repeated is True
    assert result.target_mpn_canonical == MPN
    assert result.historical_mpn == MPN
    assert result.historical_quantity == 10
    assert result.quantity_equal is True
    assert result.creator == "制单人甲"
    assert result.historical_date == NOW - timedelta(hours=2)
    assert reader.search_values == [MPN]


def test_canonical_search_value_is_sent_to_the_reader() -> None:
    checker, reader = checker_for(capture())

    checker.check(INQUIRY, "  stm32f103c8t6  ", 10, at=NOW)

    assert reader.search_values == [MPN]


def test_lowercase_history_model_still_matches() -> None:
    checker, _ = checker_for(capture(record(mpn="stm32f103c8t6")))

    assert checker.check(INQUIRY, MPN, 10, at=NOW).repeated is True


def test_non_matching_model_is_not_a_duplicate() -> None:
    checker, _ = checker_for(capture(record(mpn="LM358")))

    result = checker.check(INQUIRY, MPN, 10, at=NOW)

    assert result.outcome is DuplicateOutcome.CONFIRMED
    assert result.repeated is False


def test_empty_history_is_not_a_duplicate() -> None:
    checker, _ = checker_for(capture())

    result = checker.check(INQUIRY, MPN, 10, at=NOW)

    assert (result.outcome, result.repeated) == (DuplicateOutcome.CONFIRMED, False)


def test_window_is_inclusive_at_exactly_168_hours() -> None:
    inside, _ = checker_for(capture(record(quoted_at=NOW - timedelta(hours=168))))
    outside, _ = checker_for(
        capture(record(quoted_at=NOW - timedelta(hours=168, seconds=1)))
    )

    assert inside.check(INQUIRY, MPN, 10, at=NOW).repeated is True
    assert outside.check(INQUIRY, MPN, 10, at=NOW).repeated is False


def test_latest_record_within_the_window_decides() -> None:
    older = record(quantity=1, quoted_at=NOW - timedelta(hours=100), bill_id="1")
    newer = record(quantity=7, quoted_at=NOW - timedelta(hours=3), bill_id="2")
    checker, _ = checker_for(capture(older, newer))

    result = checker.check(INQUIRY, MPN, 7, at=NOW)

    assert result.historical_quantity == 7
    assert result.quantity_equal is True


def test_earlier_record_outside_window_does_not_decide() -> None:
    stale = record(quantity=999, quoted_at=NOW - timedelta(hours=200), bill_id="1")
    fresh = record(quantity=5, quoted_at=NOW - timedelta(hours=4), bill_id="2")
    checker, _ = checker_for(capture(stale, fresh))

    result = checker.check(INQUIRY, MPN, 5, at=NOW)

    assert result.historical_quantity == 5


@pytest.mark.parametrize("reverse", [False, True])
def test_equal_latest_timestamps_are_ambiguous_in_any_order(reverse: bool) -> None:
    stamp = NOW - timedelta(hours=1)
    first = record(quantity=3, quoted_at=stamp, bill_id="1")
    second = record(quantity=4, quoted_at=stamp, bill_id="2")
    ordered = (second, first) if reverse else (first, second)
    checker, _ = checker_for(capture(*ordered))

    result = checker.check(INQUIRY, MPN, 3, at=NOW)

    # DOM order can never act as a tie-break.
    assert result.outcome is DuplicateOutcome.AMBIGUOUS
    assert result.reason_code is ReasonCode.DUPLICATE_LOOKUP_AMBIGUOUS
    assert result.historical_date is None


def test_lookup_unavailable_never_becomes_nonduplicate() -> None:
    checker, _ = checker_for(
        InsoDuplicateHistoryError(DuplicateHistoryFailure.HISTORY_LIST_UNAVAILABLE)
    )

    result = checker.check(INQUIRY, MPN, 10, at=NOW)

    assert result.outcome is DuplicateOutcome.UNAVAILABLE
    assert result.reason_code is ReasonCode.DUPLICATE_LOOKUP_UNAVAILABLE
    assert result.repeated is None
    assert route_after_research(result) is PostResearchRoute.DUPLICATE_CONFIRMATION_REQUIRED


@pytest.mark.parametrize(
    "code",
    [
        DuplicateHistoryFailure.RESULT_IDENTIFIER_AMBIGUOUS,
        DuplicateHistoryFailure.DETAIL_IDENTITY_MISMATCH,
    ],
)
def test_ambiguous_read_maps_to_ambiguous_outcome(code: DuplicateHistoryFailure) -> None:
    checker, _ = checker_for(InsoDuplicateHistoryError(code))

    result = checker.check(INQUIRY, MPN, 10, at=NOW)

    assert result.outcome is DuplicateOutcome.AMBIGUOUS
    assert result.reason_code is ReasonCode.DUPLICATE_LOOKUP_AMBIGUOUS
    assert route_after_research(result) is PostResearchRoute.DUPLICATE_CONFIRMATION_REQUIRED


def test_session_lease_failure_is_unavailable() -> None:
    checker, _ = checker_for(
        InsoDuplicateHistoryError(DuplicateHistoryFailure.SESSION_LEASE_REQUIRED)
    )

    result = checker.check(INQUIRY, MPN, 10, at=NOW)

    assert result.outcome is DuplicateOutcome.UNAVAILABLE


def test_unexpected_reader_error_is_unavailable_and_sanitized() -> None:
    checker, _ = checker_for(RuntimeError("raw payload SECRET_CANARY_1234"))

    result = checker.check(INQUIRY, MPN, 10, at=NOW)

    assert result.outcome is DuplicateOutcome.UNAVAILABLE
    assert result.reason_code is ReasonCode.DUPLICATE_LOOKUP_UNAVAILABLE
    assert "SECRET_CANARY" not in repr(result)


@pytest.mark.parametrize("bad_mpn", ["", "   ", None, 123])
def test_invalid_mpn_never_reaches_reader(bad_mpn: object) -> None:
    checker, reader = checker_for(capture())

    result = checker.check(INQUIRY, bad_mpn, 10, at=NOW)  # type: ignore[arg-type]

    assert result.outcome is DuplicateOutcome.INVALID_RESPONSE
    assert result.reason_code is ReasonCode.DUPLICATE_HISTORY_INVALID
    assert reader.search_values == []


def test_invalid_quantity_never_reaches_reader() -> None:
    checker, reader = checker_for(capture())

    result = checker.check(INQUIRY, MPN, True, at=NOW)  # type: ignore[arg-type]

    assert result.outcome is DuplicateOutcome.INVALID_RESPONSE
    assert reader.search_values == []


def test_bridge_exposes_no_write_or_send_capability() -> None:
    checker, _ = checker_for(capture())

    for forbidden in ("save", "save_data", "send", "submit", "save_and_send"):
        assert not hasattr(checker, forbidden)

    source = Path(module.__file__).read_text(encoding="utf-8")
    for forbidden in ("btnSave", "btnSave2", "bcSend", "smtplib"):
        assert forbidden not in source
