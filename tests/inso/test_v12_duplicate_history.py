"""Deterministic tests for the read-only INSO duplicate-history adapter.

The page capability is a fake: no browser, no CDP endpoint and no live INSO
connection is used. The fake HTML carries only the verified `Bill_View_Open(n)`
link shape.
"""

from __future__ import annotations

import json
import re
import traceback
from decimal import Decimal
from pathlib import Path
from typing import Self
from urllib.parse import urlencode

import pytest

from src.inso import duplicate_history as module
from src.inso.duplicate_history import (
    BUSINESS_INQUIRY_LIST_PATH,
    DETAIL_BILL_ID_SELECTOR,
    EXACT_HISTORY_REQUEST_URL,
    EXACT_MATCH_CHECKBOX,
    MODEL_QUERY_INPUT,
    QUERY_BUTTON,
    RESULT_MODEL_CELL_SELECTOR,
    RESULT_QUANTITY_CELL_SELECTOR,
    RESULT_ROW_SELECTOR,
    RESULT_TIMESTAMP_CELL_SELECTOR,
    DuplicateHistoryFailure,
    DuplicateHistoryFieldSelectors,
    DuplicateHistoryRowValues,
    InsoDuplicateHistoryError,
    InsoDuplicateHistoryReader,
    PlaywrightDuplicateHistoryPage,
    _is_exact_history_request,
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

    def operation_page(self) -> _FakeOperationPage:
        self.opened += 1
        if self._page is None:
            raise SecurityViolation("session lease is not active")
        return _FakeOperationPage(self._page)


class FakeLease:
    """Minimal stand-in for the launcher-owned operation capability."""

    def __init__(self, page: FakePage) -> None:
        self._page = page

    def operation_page(self) -> _FakeOperationPage:
        return _FakeOperationPage(self._page)


class FakeSameDocumentFrame:
    def __init__(self, payload: dict[str, object] | None = None) -> None:
        self.url = (
            "https://yingsuo.alperp.cn/skins/etaoerp//InnerEnquiry/"
            "YeWuXJ/List.aspx"
        )
        self.payload = payload or {
            "total": 1,
            "rows": [
                {
                    "BillID": 7788,
                    "PartNo": "STM32F103C8T6",
                    "Qty": 10,
                    "PEDate": "2026-09-25 09:30:00",
                }
            ],
        }
        self.result_url = (
            "https://yingsuo.alperp.cn" + EXACT_HISTORY_REQUEST_URL
        )
        self.calls: list[tuple[object, ...]] = []

    def evaluate(self, script: str, argument: dict[str, str]):
        self.calls.append((script, argument))
        return {
            "ok": True,
            "status": 200,
            "url": self.result_url,
            "payload": self.payload,
        }


class FakeShellOperationPage:
    def __init__(self, frame: FakeSameDocumentFrame) -> None:
        self.shell_frame = frame
        self.page = object()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_: object) -> None:
        return None


class FakeShellOperationAccess:
    def __init__(self, frame: FakeSameDocumentFrame) -> None:
        self.frame = frame

    def operation_page(self) -> FakeShellOperationPage:
        return FakeShellOperationPage(self.frame)


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


def values(
    model: str = MPN,
    quantity: str = "10",
    quoted: str = "2026-09-25 09:30:00",
    creator: str | None = None,
    inso_quote: str | None = None,
):
    return DuplicateHistoryRowValues(model, quantity, quoted, creator, inso_quote)


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


# --- live Playwright page adapter (fake Playwright surface) ----------------


class FakeLocator:
    def __init__(self, page: FakePlaywrightPage, selector: str) -> None:
        self._page = page
        self._selector = selector
        self._count = page._count(selector)

    def count(self) -> int:
        return self._count

    def is_visible(self) -> bool:
        return self._count == 1

    def is_enabled(self) -> bool:
        return self._count == 1

    def is_checked(self) -> bool:
        value = self._page.elements.get(self._selector)
        return bool(value.get("checked")) if isinstance(value, dict) else False

    def check(self, **_: object) -> None:
        value = self._page.elements.get(self._selector)
        if isinstance(value, dict):
            value["checked"] = True
        self._page.calls.append(("check", self._selector))

    def fill(self, value: str, **_: object) -> None:
        current = self._page.elements.get(self._selector)
        if isinstance(current, dict):
            current["value"] = value
        self._page.calls.append(("fill", self._selector, value))

    def input_value(self) -> str:
        value = self._page.elements.get(self._selector)
        return str(value.get("value", "")) if isinstance(value, dict) else ""

    def inner_text(self) -> str:
        value = self._page.elements.get(self._selector)
        return str(value.get("text", "")) if isinstance(value, dict) else ""

    def click(self, **_: object) -> None:
        self._page.click(self._selector)


class FakePlaywrightPage:
    """Fake Playwright Page/Frame built from a selector -> value map.

    A ``str`` value stands for the element's text/HTML, a ``list`` of dicts for
    ``eval_on_selector_all`` with an attribute argument. Missing selectors behave
    as absent elements.
    """

    def __init__(
        self,
        *,
        elements: dict[str, object] | None = None,
        goto_error: BaseException | None = None,
    ) -> None:
        self.elements = dict(elements or {})
        self._goto_error = goto_error
        self.calls: list[tuple] = []
        self.url = "https://yingsuo.alperp.cn/skins/etaoerp//InnerEnquiry/YeWuXJ/List.aspx"
        self.frames = [self]
        self.main_frame = self
        self._listeners: dict[str, list[object]] = {"request": [], "response": []}
        self._sequence = 3
        self._pending = False
        self._pending_value: bool | None = False
        self._response = None
        self._response_rows = self._bill_ids_from_fixture()
        self._cache_bill_ids = [row["BillID"] for row in self._response_rows]
        self._dom_bill_ids = [row["BillID"] for row in self._response_rows]

    def goto(self, url: str, **_: object) -> None:
        self.calls.append(("goto", url))
        self.url = url
        if self._goto_error is not None:
            raise self._goto_error

    def fill(self, selector: str, value: str, **_: object) -> None:
        self.calls.append(("fill", selector, value))

    def check(self, selector: str, **_: object) -> None:
        self.calls.append(("check", selector))

    def click(self, selector: str, **_: object) -> None:
        self.calls.append(("click", selector))
        if selector == QUERY_BUTTON:
            self._sequence += 1
            search_data = {
                "DetailField": "PartNo",
                "DetailFieldValue": self.elements[MODEL_QUERY_INPUT]["value"],
                "nolike": "on",
            }
            request = _FakeRequest(
                "https://yingsuo.alperp.cn/services/innerEnquiry/yewuxj.ashx?action=List_Detail&BillPage=YeWuXJ",
                urlencode({"searchData": json.dumps(search_data)}),
            )
            response = _FakeResponse(request, self._response_rows)
            self._response = response
            for listener in tuple(self._listeners["request"]):
                listener(request)
            for listener in tuple(self._listeners["response"]):
                listener(response)
        elif selector.startswith("[onclick*='Bill_View_Open("):
            self._open_argument = selector.split("(", 1)[1].split(")", 1)[0]

    def _detail_locator_count(self, selector: str) -> int | None:
        match = re.fullmatch(r"\[onclick\*='Bill_View_Open\((\d+)\)'\]", selector)
        if match is None:
            return None
        argument = match.group(1)
        return sum(
            1
            for key, value in self.elements.items()
            if key.startswith("#")
            and key.endswith("_Main")
            and isinstance(value, str)
            and len(re.findall(r"Bill_View_Open\(\s*" + argument + r"\s*\)", value)) == 1
        )

    def on(self, event: str, listener: object) -> None:
        self._listeners[event].append(listener)

    def remove_listener(self, event: str, listener: object) -> None:
        self._listeners[event].remove(listener)

    def wait_for_event(self, event: str, *, predicate, timeout: int):
        del event, timeout
        if self._response is None or not predicate(self._response):
            raise TimeoutError("response not matched")
        return self._response

    def wait_for_function(self, _expression: str, *, arg, timeout: int) -> None:
        del timeout
        self.calls.append(("wait_for_function", arg))
        if (
            self._pending
            or self._sequence != arg["sequence"]
            or [row["BillID"] for row in self._response_rows] != arg["bill_ids"]
            or self._cache_bill_ids != arg["bill_ids"]
            or self._dom_bill_ids != arg["bill_ids"]
        ):
            raise TimeoutError("grid did not settle")

    def evaluate(self, _expression: str) -> dict[str, object]:
        checkbox = self.elements.get(EXACT_MATCH_CHECKBOX, {})
        return {
            "exact_checked": bool(checkbox.get("checked"))
            if isinstance(checkbox, dict)
            else False,
            "pending": self._pending_value,
            "sequence": self._sequence,
        }

    def wait_for_selector(self, selector: str, **_: object) -> None:
        self.calls.append(("wait_for_selector", selector))
        if self._count(selector) == 0:
            raise TimeoutError(f"not visible: {selector}")

    def locator(self, selector: str) -> FakeLocator:
        self.calls.append(("locator", selector))
        return FakeLocator(self, selector)

    def eval_on_selector(self, selector: str, expression: str) -> object:
        self.calls.append(("eval_on_selector", selector, expression))
        value = self._value(selector)
        if value is None:
            raise RuntimeError(f"no element: {selector}")
        return value

    def eval_on_selector_all(
        self, selector: str, _expression: str, arg: str | None = None
    ) -> list:
        self.calls.append(("eval_on_selector_all", selector, arg))
        values = self._value(selector)
        if not isinstance(values, list):
            return []
        if arg is None:
            return list(values)
        return [item.get(arg) if isinstance(item, dict) else None for item in values]

    def _value(self, selector: str) -> object:
        return self.elements.get(selector)

    def _count(self, selector: str) -> int:
        detail_count = self._detail_locator_count(selector)
        if detail_count is not None:
            return detail_count
        value = self.elements.get(selector)
        if value is None:
            return 0
        return len(value) if isinstance(value, list) else 1

    def _bill_ids_from_fixture(self) -> list[dict[str, str]]:
        rows = self.elements.get(RESULT_ROW_SELECTOR, [])
        result: list[dict[str, str]] = []
        for row in rows if isinstance(rows, list) else []:
            row_id = row.get("id", "") if isinstance(row, dict) else ""
            html = self.elements.get(f"#{row_id}", "")
            match = re.search(r"Bill_View_Open\(\s*(\d+)", str(html))
            if match:
                result.append({"BillID": match.group(1)})
        return result


class _FakeRequest:
    method = "POST"

    def __init__(self, url: str, post_data: str) -> None:
        self.url = url
        self.post_data = post_data


class _FakeResponse:
    status = 200

    def __init__(self, request: _FakeRequest, rows: list[dict[str, str]]) -> None:
        self.request = request
        self._rows = rows

    def json(self) -> dict[str, object]:
        return {"rows": self._rows}


def playwright_rows(
    *,
    row_id: str = "1001_Main",
    bill_argument: str = "7788",
    cells: dict[str, str] | None = None,
) -> dict[str, object]:
    table: dict[str, object] = {
        MODEL_QUERY_INPUT: {"value": ""},
        EXACT_MATCH_CHECKBOX: {"checked": False},
        QUERY_BUTTON: {"text": "查询"},
        RESULT_ROW_SELECTOR: [{"id": row_id}],
        f"#{row_id}": row_html(bill_argument),
        DETAIL_BILL_ID_SELECTOR: [{"value": bill_argument}],
    }
    resolved = {
        RESULT_MODEL_CELL_SELECTOR: MPN,
        RESULT_QUANTITY_CELL_SELECTOR: "10",
        RESULT_TIMESTAMP_CELL_SELECTOR: "2026-09-25 09:30:00",
    }
    resolved.update(cells or {})
    for cell_selector, text in resolved.items():
        table[f"#{row_id} {cell_selector}"] = text
    return table


def playwright_adapter(
    *,
    elements: dict[str, object] | None = None,
    selectors: DuplicateHistoryFieldSelectors | None = None,
    goto_error: BaseException | None = None,
) -> tuple[PlaywrightDuplicateHistoryPage, FakePlaywrightPage]:
    page = FakePlaywrightPage(elements=elements, goto_error=goto_error)
    return (
        PlaywrightDuplicateHistoryPage(
            page, selectors=selectors or DuplicateHistoryFieldSelectors()
        ),
        page,
    )


def test_playwright_row_extractor_uses_only_the_verified_cells() -> None:
    adapter, page = playwright_adapter(elements=playwright_rows())

    extracted = adapter.read_row_values("1001_Main")

    assert extracted == DuplicateHistoryRowValues(
        model=MPN, quantity_text="10", quoted_at_text="2026-09-25 09:30:00"
    )
    for cell_selector in (
        RESULT_MODEL_CELL_SELECTOR,
        RESULT_QUANTITY_CELL_SELECTOR,
        RESULT_TIMESTAMP_CELL_SELECTOR,
    ):
        assert ("locator", f"#1001_Main {cell_selector}") in page.calls
    assert ("eval_on_selector_all", RESULT_ROW_SELECTOR, "id") not in page.calls


def test_playwright_reads_row_ids_and_html_from_the_verified_table() -> None:
    adapter, _ = playwright_adapter(elements=playwright_rows())

    assert adapter.attributes(RESULT_ROW_SELECTOR, "id") == ("1001_Main",)
    assert adapter.html("#1001_Main") == row_html("7788")
    assert adapter.html("#9999_Main") is None


def test_playwright_missing_cell_yields_no_values() -> None:
    elements = playwright_rows()
    del elements[f"#1001_Main {RESULT_QUANTITY_CELL_SELECTOR}"]
    adapter, _ = playwright_adapter(elements=elements)

    assert adapter.read_row_values("1001_Main") is None


def test_playwright_creator_and_quote_are_not_read_by_default() -> None:
    adapter, page = playwright_adapter(elements=playwright_rows())

    extracted = adapter.read_row_values("1001_Main")

    assert extracted is not None
    assert extracted.creator is None
    assert extracted.inso_quote_text is None
    # No unverified column may be touched.
    assert sum(1 for call in page.calls if call[0] == "locator") == 3


def test_playwright_reads_creator_and_quote_once_confirmed() -> None:
    elements = playwright_rows()
    elements["#1001_Main td:nth-child(6)"] = "制单人甲"
    elements["#1001_Main td:nth-child(12)"] = "12.50"
    adapter, _ = playwright_adapter(
        elements=elements,
        selectors=DuplicateHistoryFieldSelectors(
            creator="td:nth-child(6)", inso_quote="td:nth-child(12)"
        ),
    )

    extracted = adapter.read_row_values("1001_Main")

    assert extracted is not None
    assert extracted.creator == "制单人甲"
    assert extracted.inso_quote_text == "12.50"


def test_playwright_query_steps_use_the_verified_controls() -> None:
    adapter, page = playwright_adapter(elements=playwright_rows())
    list_url = "https://yingsuo.alperp.cn" + BUSINESS_INQUIRY_LIST_PATH

    adapter.goto(list_url)
    adapter.set_text(MODEL_QUERY_INPUT, MPN)
    adapter.ensure_checked(EXACT_MATCH_CHECKBOX)
    adapter.click(QUERY_BUTTON)

    assert ("goto", list_url) in page.calls
    assert ("fill", MODEL_QUERY_INPUT, MPN) in page.calls
    assert ("check", EXACT_MATCH_CHECKBOX) in page.calls
    assert ("click", QUERY_BUTTON) in page.calls
    assert not any("#leftlike" in repr(call) for call in page.calls)


def test_verified_live_settlement_requires_current_exact_request_and_grid() -> None:
    adapter, page = playwright_adapter(elements=playwright_rows())

    adapter.goto("https://yingsuo.alperp.cn" + BUSINESS_INQUIRY_LIST_PATH)
    adapter.set_text(MODEL_QUERY_INPUT, MPN)
    adapter.ensure_checked(EXACT_MATCH_CHECKBOX)
    adapter.click(QUERY_BUTTON)
    adapter.wait_for_query_settled(timeout_ms=1000)

    assert any(call[0] == "wait_for_function" for call in page.calls)
    assert page._listeners == {"request": [], "response": []}


def test_query_dispatch_fails_when_pending_state_is_not_explicitly_idle() -> None:
    adapter, page = playwright_adapter(elements=playwright_rows())
    page._pending_value = None

    adapter.goto("https://yingsuo.alperp.cn" + BUSINESS_INQUIRY_LIST_PATH)
    adapter.set_text(MODEL_QUERY_INPUT, MPN)
    adapter.ensure_checked(EXACT_MATCH_CHECKBOX)
    with pytest.raises(InsoDuplicateHistoryError) as failure:
        adapter.click(QUERY_BUTTON)

    assert failure.value.code is DuplicateHistoryFailure.QUERY_SETTLEMENT_UNCONFIRMED
    assert not any(call == ("click", QUERY_BUTTON) for call in page.calls)


def test_exact_request_matching_requires_current_mpn_and_nolike() -> None:
    request = _FakeRequest(
        "https://yingsuo.alperp.cn/services/innerEnquiry/yewuxj.ashx?action=List_Detail&BillPage=YeWuXJ",
        urlencode(
            {
                "searchData": json.dumps(
                    {"DetailField": "PartNo", "DetailFieldValue": MPN, "nolike": "on"}
                )
            }
        ),
    )

    assert _is_exact_history_request(request, MPN)
    request.url = request.url.replace("yingsuo.alperp.cn", "example.invalid")
    assert not _is_exact_history_request(request, MPN)
    request.url = request.url.replace("example.invalid", "yingsuo.alperp.cn")
    request.post_data = urlencode(
        {
            "searchData": json.dumps(
                {"DetailField": "PartNo", "DetailFieldValue": MPN, "leftlike": "on"}
            )
        }
    )
    assert not _is_exact_history_request(request, MPN)


def test_exact_request_preserves_plus_in_form_encoded_mpn() -> None:
    target = "LM+358"
    request = _FakeRequest(
        "https://yingsuo.alperp.cn/services/innerEnquiry/yewuxj.ashx?action=List_Detail&BillPage=YeWuXJ",
        urlencode(
            {
                "searchData": json.dumps(
                    {
                        "DetailField": "PartNo",
                        "DetailFieldValue": target,
                        "nolike": "on",
                    }
                )
            }
        ),
    )

    assert _is_exact_history_request(request, target)


def test_settlement_fails_when_returned_billids_do_not_match_grid() -> None:
    adapter, page = playwright_adapter(elements=playwright_rows())
    page._response_rows = [{"BillID": "9999"}]

    adapter.goto("https://yingsuo.alperp.cn" + BUSINESS_INQUIRY_LIST_PATH)
    adapter.set_text(MODEL_QUERY_INPUT, MPN)
    adapter.ensure_checked(EXACT_MATCH_CHECKBOX)
    adapter.click(QUERY_BUTTON)
    with pytest.raises(InsoDuplicateHistoryError) as failure:
        adapter.wait_for_query_settled(timeout_ms=1000)

    assert failure.value.code is DuplicateHistoryFailure.QUERY_SETTLEMENT_UNCONFIRMED


def test_playwright_settlement_is_fail_closed() -> None:
    adapter, _ = playwright_adapter(
        elements=playwright_rows(),
        # The verified empty-state marker is present; it must still not be used
        # as a nonempty completion signal.
    )
    adapter._page.elements[".layui-table-none"] = ""

    with pytest.raises(InsoDuplicateHistoryError) as failure:
        adapter.wait_for_query_settled(timeout_ms=1000)

    assert failure.value.code is DuplicateHistoryFailure.QUERY_SETTLEMENT_UNCONFIRMED


def test_reader_over_the_playwright_adapter_reads_only_settled_matching_rows() -> None:
    adapter, _ = playwright_adapter(elements=playwright_rows())
    v12_reader = InsoDuplicateHistoryReader(
        list_url="https://yingsuo.alperp.cn",
        operation_access=FakeOperationAccess(adapter),  # type: ignore[arg-type]
    )

    capture = v12_reader.read(MPN)

    assert capture.target_mpn == MPN
    assert len(capture.records) == 1
    assert capture.records[0].bill_id == "7788"


def test_no_settle_path_relies_on_a_fixed_sleep() -> None:
    source = Path(module.__file__).read_text(encoding="utf-8")

    assert not re.search(r"\bsleep\s*\(", source)
    assert "wait_for_timeout" not in source


def test_same_document_exact_query_uses_only_confirmed_request_contract() -> None:
    frame = FakeSameDocumentFrame()
    adapter = PlaywrightDuplicateHistoryPage(frame)

    payload = adapter.query_exact_response(MPN)

    assert payload is frame.payload
    script, argument = frame.calls[0]
    assert argument == {"endpoint": EXACT_HISTORY_REQUEST_URL, "target": MPN}
    assert "fetch(requestUrl.toString()" in script
    assert "credentials: 'same-origin'" in script
    assert "bill_get_pagesize('dg')" in script
    assert "searchParams.set('pageindex', '1')" in script
    assert "searchParams.set('pagesize', String(pageSize))" in script
    assert "body.set('DetailField', 'PartNo')" in script
    assert "body.set('DetailFieldValue', target)" in script
    assert "body.set('nolike', 'on')" in script
    assert "searchData[" not in script
    assert "locator" not in repr(frame.calls).casefold()
    assert "#nolike" not in script


def test_same_document_query_fails_closed_for_wrong_mpn_or_duplicate_billid() -> None:
    wrong_model = FakeSameDocumentFrame(
        {
            "rows": [
                {
                    "BillID": "7788",
                    "PartNo": "STM32F103C8T6X",
                    "Qty": 10,
                    "PEDate": "2026-09-25 09:30:00",
                }
            ]
        }
    )
    with pytest.raises(InsoDuplicateHistoryError) as failure:
        PlaywrightDuplicateHistoryPage(wrong_model).query_exact_response(MPN)
    assert failure.value.code is DuplicateHistoryFailure.QUERY_SETTLEMENT_UNCONFIRMED

    duplicate_ids = FakeSameDocumentFrame(
        {
            "rows": [
                {"BillID": "7788", "PartNo": MPN, "Qty": 1, "PEDate": "2026-09-25"},
                {"BillID": "7788", "PartNo": MPN, "Qty": 2, "PEDate": "2026-09-24"},
            ]
        }
    )
    with pytest.raises(InsoDuplicateHistoryError) as failure:
        PlaywrightDuplicateHistoryPage(duplicate_ids).query_exact_response(MPN)
    assert failure.value.code is DuplicateHistoryFailure.QUERY_SETTLEMENT_UNCONFIRMED


def test_verified_shell_reader_uses_response_fields_and_billid() -> None:
    frame = FakeSameDocumentFrame()
    capture = InsoDuplicateHistoryReader(
        list_url="https://yingsuo.alperp.cn",
        operation_access=FakeShellOperationAccess(frame),  # type: ignore[arg-type]
    ).read(MPN)

    assert capture.target_mpn == MPN
    assert len(capture.records) == 1
    assert capture.records[0].bill_id == "7788"
    assert capture.records[0].mpn == MPN
    assert capture.records[0].quantity == 10


# --- creator / quote data path --------------------------------------------


def test_creator_and_quote_reach_the_record_when_supplied() -> None:
    page = FakePage(
        rows=(
            (
                "1001_Main",
                row_html("7788"),
                values(creator="制单人甲", inso_quote="12.50"),
            ),
        )
    )

    capture = reader(page).read(MPN)

    assert capture.records[0].creator == "制单人甲"
    assert capture.records[0].inso_quote == Decimal("12.50")


def test_blank_creator_is_none_and_absent_quote_is_none() -> None:
    page = FakePage(
        rows=(("1001_Main", row_html("7788"), values(creator="   ", inso_quote="")),)
    )

    record = reader(page).read(MPN).records[0]

    assert record.creator is None
    assert record.inso_quote is None


@pytest.mark.parametrize("quote", ["abc", "-1", "1,2,3.4.5"])
def test_unusable_quote_is_invalid(quote: str) -> None:
    page = FakePage(
        rows=(("1001_Main", row_html("7788"), values(inso_quote=quote)),)
    )

    with pytest.raises(InsoDuplicateHistoryError) as failure:
        reader(page).read(MPN)

    assert failure.value.code is DuplicateHistoryFailure.RECORD_FIELDS_INVALID


# --- sanitized wrapping ----------------------------------------------------


def test_wrapped_page_failure_keeps_no_raw_cause() -> None:
    raw = "raw page payload SECRET_CANARY_7788"
    page = FakePage(goto_error=RuntimeError(raw))

    with pytest.raises(InsoDuplicateHistoryError) as failure:
        reader(page).read(MPN)

    error = failure.value
    assert error.__cause__ is None
    assert error.__suppress_context__ is True
    rendered = "".join(
        traceback.format_exception(type(error), error, error.__traceback__)
    )
    assert "SECRET_CANARY" not in rendered
    assert "raw page payload" not in rendered
    assert raw not in str(error)


def test_wrapped_parse_failure_keeps_no_raw_cause() -> None:
    page = FakePage(
        rows=(("1001_Main", row_html("7788"), values(quoted="2026-13-45 99:99:99")),)
    )

    with pytest.raises(InsoDuplicateHistoryError) as failure:
        reader(page).read(MPN)

    error = failure.value
    assert error.code is DuplicateHistoryFailure.RECORD_FIELDS_INVALID
    assert error.__cause__ is None
    assert error.__suppress_context__ is True
