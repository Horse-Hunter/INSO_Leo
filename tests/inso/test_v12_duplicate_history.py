"""Deterministic tests for the read-only INSO duplicate-history adapter.

The page capability is a fake: no browser, no CDP endpoint and no live INSO
connection is used. The fake HTML carries only the verified `Bill_View_Open(n)`
link shape.
"""

from __future__ import annotations

from pathlib import Path
from typing import Self

import pytest

from src.inso import duplicate_history as module
from src.inso.duplicate_history import (
    BUSINESS_INQUIRY_LIST_PATH,
    DETAIL_BILL_ID_SELECTOR,
    EXACT_MATCH_CHECKBOX,
    MODEL_QUERY_INPUT,
    QUERY_BUTTON,
    RESULT_MODEL_CELL_SELECTOR,
    RESULT_QUANTITY_CELL_SELECTOR,
    RESULT_ROW_SELECTOR,
    RESULT_TIMESTAMP_CELL_SELECTOR,
    DuplicateHistoryFailure,
    DuplicateHistoryRowValues,
    InsoDuplicateHistoryError,
    InsoDuplicateHistoryReader,
)
from src.inso.session import SecurityViolation

LIST_URL = "https://example.invalid"
MPN = "STM32F103C8T6"


def row_html(bill_argument: str, extra: str = "") -> str:
    return f'<td><a onclick="Bill_View_Open({bill_argument})">查看</a></td>{extra}'


class FakePage:
    """Deterministic fake of the narrow read-only page capability."""

    def __init__(
        self,
        *,
        rows: tuple[tuple[str, str, DuplicateHistoryRowValues | None], ...] = (),
        detail_bill_ids: dict[str, str] | None = None,
        goto_error: BaseException | None = None,
        settle_error: BaseException | None = None,
        detail_never_opens: bool = False,
    ) -> None:
        self._rows = rows
        self._detail_bill_ids = detail_bill_ids or {}
        self._goto_error = goto_error
        self._settle_error = settle_error
        self._detail_never_opens = detail_never_opens
        self._open_argument: str | None = None
        self.calls: list[tuple] = []

    def goto(self, url: str) -> None:
        self.calls.append(("goto", url))
        if self._goto_error is not None:
            raise self._goto_error

    def set_text(self, selector: str, value: str) -> None:
        self.calls.append(("set_text", selector, value))

    def ensure_checked(self, selector: str) -> None:
        self.calls.append(("ensure_checked", selector))

    def click(self, selector: str) -> None:
        self.calls.append(("click", selector))
        if selector.startswith("[onclick*='Bill_View_Open("):
            self._open_argument = selector.split("(", 1)[1].split(")", 1)[0]

    def wait_for_query_settled(self, *, timeout_ms: int) -> None:
        self.calls.append(("wait_for_query_settled",))
        if self._settle_error is not None:
            raise self._settle_error

    def wait_for(self, selector: str, *, timeout_ms: int) -> None:
        self.calls.append(("wait_for", selector))
        if selector == DETAIL_BILL_ID_SELECTOR and (
            self._detail_never_opens or self._open_argument is None
        ):
            raise TimeoutError("detail did not open")

    def attributes(self, selector: str, name: str) -> tuple[str | None, ...]:
        self.calls.append(("attributes", selector, name))
        if selector == RESULT_ROW_SELECTOR and name == "id":
            return tuple(row_id for row_id, _, _ in self._rows)
        if selector == DETAIL_BILL_ID_SELECTOR and name == "value":
            argument = self._open_argument or ""
            return (self._detail_bill_ids.get(argument, argument),)
        return ()

    def html(self, selector: str) -> str | None:
        self.calls.append(("html", selector))
        for row_id, extra, _ in self._rows:
            if selector == f"#{row_id}":
                return extra
        return None

    def read_row_values(self, row_id: str) -> DuplicateHistoryRowValues | None:
        self.calls.append(("read_row_values", row_id))
        for candidate, _, values in self._rows:
            if candidate == row_id:
                return values
        return None


class _FakeOperationPage:
    def __init__(self, page: FakePage) -> None:
        self.page = page

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_: object) -> bool:
        return False


class FakeOperationAccess:
    def __init__(self, page: FakePage | None) -> None:
        self._page = page
        self.opened = 0

    def open_operation_page(self) -> _FakeOperationPage:
        self.opened += 1
        if self._page is None:
            raise SecurityViolation("session lease is not active")
        return _FakeOperationPage(self._page)


class FakeLease:
    """Minimal stand-in for the launcher-owned operation capability."""

    def __init__(self, page: FakePage) -> None:
        self._page = page

    def open_operation_page(self) -> _FakeOperationPage:
        return _FakeOperationPage(self._page)


def reader(
    page: FakePage | None,
    *,
    access: object | None = None,
) -> InsoDuplicateHistoryReader:
    supplied = access if access is not None else FakeOperationAccess(page)
    return InsoDuplicateHistoryReader(
        list_url=LIST_URL,
        operation_access=supplied,  # type: ignore[arg-type]
    )


def values(model: str = MPN, quantity: str = "10", quoted: str = "2026-09-25 09:30:00"):
    return DuplicateHistoryRowValues(model, quantity, quoted)


def test_exact_query_uses_only_the_verified_selectors() -> None:
    page = FakePage(rows=(("1001_Main", row_html("7788"), values()),))

    capture = reader(page).read(MPN)

    assert capture.target_mpn == MPN
    assert capture.url == f"{LIST_URL}{BUSINESS_INQUIRY_LIST_PATH}"
    assert [record.bill_id for record in capture.records] == ["7788"]
    assert capture.records[0].mpn == MPN
    assert capture.records[0].quantity == 10
    assert capture.records[0].creator is None
    assert capture.records[0].inso_quote is None
    assert capture.records[0].quoted_at.isoformat() == "2026-09-25T01:30:00+00:00"

    assert ("set_text", MODEL_QUERY_INPUT, MPN) in page.calls
    assert ("ensure_checked", EXACT_MATCH_CHECKBOX) in page.calls
    assert ("click", QUERY_BUTTON) in page.calls
    assert ("goto", f"{LIST_URL}{BUSINESS_INQUIRY_LIST_PATH}") in page.calls
    # Exact mode only: the left-match control is never used.
    assert not any("#leftlike" in repr(call) for call in page.calls)


def test_row_id_and_bill_argument_are_not_interchangeable() -> None:
    page = FakePage(rows=(("1001_Main", row_html("7788"), values()),))

    capture = reader(page).read(MPN)

    assert capture.records[0].bill_id == "7788"
    assert capture.records[0].bill_id != "1001_Main"


def test_detail_is_verified_in_this_runtime_before_a_record_is_returned() -> None:
    page = FakePage(rows=(("1001_Main", row_html("7788"), values()),))

    reader(page).read(MPN)

    assert ("click", "[onclick*='Bill_View_Open(7788)']") in page.calls
    assert ("attributes", DETAIL_BILL_ID_SELECTOR, "value") in page.calls
    # One query to enumerate, one more to re-open the record for verification.
    assert sum(1 for call in page.calls if call[0] == "goto") == 2


def test_detail_identity_mismatch_fails_closed() -> None:
    page = FakePage(
        rows=(("1001_Main", row_html("7788"), values()),),
        detail_bill_ids={"7788": "9999"},
    )

    with pytest.raises(InsoDuplicateHistoryError) as failure:
        reader(page).read(MPN)

    assert failure.value.code is DuplicateHistoryFailure.DETAIL_IDENTITY_MISMATCH


def test_blank_detail_bill_id_fails_closed() -> None:
    page = FakePage(
        rows=(("1001_Main", row_html("7788"), values()),),
        detail_bill_ids={"7788": "   "},
    )

    with pytest.raises(InsoDuplicateHistoryError) as failure:
        reader(page).read(MPN)

    assert failure.value.code is DuplicateHistoryFailure.DETAIL_IDENTITY_MISMATCH


def test_missing_operation_access_fails_closed() -> None:
    with pytest.raises(InsoDuplicateHistoryError) as failure:
        InsoDuplicateHistoryReader(list_url=LIST_URL).read(MPN)

    assert failure.value.code is DuplicateHistoryFailure.SESSION_LEASE_REQUIRED


def test_inactive_lease_maps_to_session_lease_required() -> None:
    with pytest.raises(InsoDuplicateHistoryError) as failure:
        reader(FakePage(), access=FakeOperationAccess(None)).read(MPN)

    assert failure.value.code is DuplicateHistoryFailure.SESSION_LEASE_REQUIRED


def test_duplicate_row_ids_are_ambiguous() -> None:
    page = FakePage(
        rows=(
            ("1001_Main", row_html("7788"), values()),
            ("1001_Main", row_html("7788"), values()),
        )
    )

    with pytest.raises(InsoDuplicateHistoryError) as failure:
        reader(page).read(MPN)

    assert failure.value.code is DuplicateHistoryFailure.RESULT_IDENTIFIER_AMBIGUOUS


def test_row_without_a_detail_link_is_unreadable() -> None:
    page = FakePage(rows=(("1001_Main", "<td>no link</td>", values()),))

    with pytest.raises(InsoDuplicateHistoryError) as failure:
        reader(page).read(MPN)

    assert failure.value.code is DuplicateHistoryFailure.RESULT_ROW_UNREADABLE


def test_row_with_two_distinct_detail_links_is_ambiguous() -> None:
    page = FakePage(
        rows=(
            ("1001_Main", row_html("7788") + row_html("7799"), values()),
        )
    )

    with pytest.raises(InsoDuplicateHistoryError) as failure:
        reader(page).read(MPN)

    assert failure.value.code is DuplicateHistoryFailure.RESULT_IDENTIFIER_AMBIGUOUS


def test_missing_row_values_is_unavailable() -> None:
    page = FakePage(rows=(("1001_Main", row_html("7788"), None),))

    with pytest.raises(InsoDuplicateHistoryError) as failure:
        reader(page).read(MPN)

    assert failure.value.code is DuplicateHistoryFailure.RECORD_FIELDS_UNAVAILABLE


@pytest.mark.parametrize("quantity", ["", "abc", "0", "-3", "1.5"])
def test_unusable_quantity_is_invalid(quantity: str) -> None:
    page = FakePage(
        rows=(("1001_Main", row_html("7788"), values(quantity=quantity)),)
    )

    with pytest.raises(InsoDuplicateHistoryError) as failure:
        reader(page).read(MPN)

    assert failure.value.code is DuplicateHistoryFailure.RECORD_FIELDS_INVALID


def test_unusable_timestamp_is_invalid() -> None:
    page = FakePage(
        rows=(("1001_Main", row_html("7788"), values(quoted="not-a-date")),)
    )

    with pytest.raises(InsoDuplicateHistoryError) as failure:
        reader(page).read(MPN)

    assert failure.value.code is DuplicateHistoryFailure.RECORD_FIELDS_INVALID


def test_blank_model_is_invalid() -> None:
    page = FakePage(rows=(("1001_Main", row_html("7788"), values(model="  ")),))

    with pytest.raises(InsoDuplicateHistoryError) as failure:
        reader(page).read(MPN)

    assert failure.value.code is DuplicateHistoryFailure.RECORD_FIELDS_INVALID


def test_page_failure_is_sanitized_and_never_leaks_page_text() -> None:
    page = FakePage(goto_error=RuntimeError("raw page payload <html>secret</html>"))

    with pytest.raises(InsoDuplicateHistoryError) as failure:
        reader(page).read(MPN)

    assert failure.value.code is DuplicateHistoryFailure.HISTORY_LIST_UNAVAILABLE
    assert "secret" not in str(failure.value)
    assert "secret" not in repr(failure.value)


def test_unsettled_search_is_unavailable() -> None:
    page = FakePage(settle_error=TimeoutError("grid never settled"))

    with pytest.raises(InsoDuplicateHistoryError) as failure:
        reader(page).read(MPN)

    assert failure.value.code is DuplicateHistoryFailure.HISTORY_LIST_UNAVAILABLE


def test_detail_that_never_opens_is_unavailable() -> None:
    page = FakePage(
        rows=(("1001_Main", row_html("7788"), values()),),
        detail_never_opens=True,
    )

    with pytest.raises(InsoDuplicateHistoryError) as failure:
        reader(page).read(MPN)

    assert failure.value.code is DuplicateHistoryFailure.HISTORY_LIST_UNAVAILABLE


def test_search_is_settled_before_rows_are_read() -> None:
    page = FakePage(rows=(("1001_Main", row_html("7788"), values()),))

    reader(page).read(MPN)

    assert ("wait_for_query_settled",) in page.calls


def test_no_matching_row_returns_an_empty_capture() -> None:
    page = FakePage(rows=())

    capture = reader(page).read(MPN)

    assert capture.records == ()
    assert capture.target_mpn == MPN


def test_adapter_applies_no_window_or_tie_logic() -> None:
    # Both same-timestamp rows are returned raw; the decision belongs to Workflow.
    page = FakePage(
        rows=(
            ("1001_Main", row_html("7788"), values(quoted="2026-09-25 09:30:00")),
            ("1002_Main", row_html("7799"), values(quoted="2026-09-25 09:30:00")),
        )
    )

    capture = reader(page).read(MPN)

    assert {record.bill_id for record in capture.records} == {"7788", "7799"}


@pytest.mark.parametrize("search", ["", "   "])
def test_blank_search_value_is_rejected(search: str) -> None:
    with pytest.raises(InsoDuplicateHistoryError) as failure:
        reader(FakePage()).read(search)

    assert failure.value.code is DuplicateHistoryFailure.RECORD_FIELDS_INVALID


def test_non_https_list_url_is_rejected() -> None:
    with pytest.raises(ValueError):
        InsoDuplicateHistoryReader(list_url="http://example.invalid")


def test_adapter_exposes_no_write_capability() -> None:
    adapter = reader(FakePage())

    for forbidden in ("save", "save_data", "send", "submit", "save_and_send"):
        assert not hasattr(adapter, forbidden)

    source = Path(module.__file__).read_text(encoding="utf-8")
    for forbidden in ("btnSave", "btnSave2", "bcSend", "#ai-recognize"):
        assert forbidden not in source

    # The page capability it depends on is read-only too.
    assert not hasattr(module.DuplicateHistoryPage, "save")
    assert not hasattr(module.DuplicateHistoryPage, "send")


def test_live_result_selectors_are_scoped_to_confirmed_history_table() -> None:
    assert RESULT_ROW_SELECTOR == "#_id_dg tr[id$='_Main']"
    assert RESULT_MODEL_CELL_SELECTOR == "td:nth-child(9)"
    assert RESULT_QUANTITY_CELL_SELECTOR == "td:nth-child(11)"
    assert RESULT_TIMESTAMP_CELL_SELECTOR == "td:nth-child(14)"
