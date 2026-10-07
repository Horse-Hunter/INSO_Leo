from contextlib import nullcontext
from datetime import datetime, timedelta
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

from src.inso.duplicate_history import (
    InsoDuplicateHistoryError,
    PlaywrightProcurementHistoryPage,
)
from src.inso.quotation_read import (
    QUOTATION_COLUMNS,
    InsoQuotationReader,
    V13QuotationRow,
    capture_quotation_page,
    select_recent_latest,
)
from tests.inso.test_procurement_duplicate_history import LowerFrame, row

NOW = datetime(2026, 10, 7, 0, 5, tzinfo=ZoneInfo("Asia/Shanghai"))


def quote(at=NOW, model="MPN", **kwargs):
    payload = (at.strftime("%Y-%m-%d %H:%M:%S"), model, "different brand", "", "奇币", "",
               "0001.2300", "", "0000", "", "", "  原样\n备注  ", "备注2\t", "")
    return V13QuotationRow(at, kwargs.get("payload", payload))


@pytest.mark.parametrize("age,accepted", [
    (timedelta(hours=71, minutes=59), True), (timedelta(hours=72), True),
    (timedelta(hours=72, microseconds=1), False), (timedelta(microseconds=-1), False),
])
def test_inclusive_72h_boundaries_and_future(age, accepted):
    record = quote(NOW-age)
    assert (select_recent_latest([record], queried_mpn="MPN", now=NOW) is record) is accepted


@pytest.mark.parametrize("now", [
    datetime(2026, 10, 7, 0, 5, tzinfo=ZoneInfo("Asia/Shanghai")),
    datetime(2026, 10, 1, 0, 5, tzinfo=ZoneInfo("Asia/Shanghai")),
    datetime(2027, 1, 1, 0, 5, tzinfo=ZoneInfo("Asia/Shanghai")),
])
def test_midnight_month_and_year_transitions(now):
    accepted, old = quote(now-timedelta(hours=72)), quote(now-timedelta(hours=72, seconds=1))
    assert select_recent_latest([old, accepted], queried_mpn="MPN", now=now) is accepted


def test_empty_one_multiple_unsorted_old_and_exact_normalization():
    latest = quote(NOW-timedelta(minutes=1), model=" ｍｐｎ ")
    older = quote(NOW-timedelta(hours=2))
    stale = quote(NOW-timedelta(hours=73))
    fuzzy = quote(NOW, model="MPN suffix")
    assert select_recent_latest([], queried_mpn="MPN", now=NOW) is None
    assert select_recent_latest([older], queried_mpn="MPN", now=NOW) is older
    assert select_recent_latest([older, latest, stale, fuzzy], queried_mpn="MPN", now=NOW) is latest


def test_aware_clocks_only_and_same_instant_other_zone():
    with pytest.raises(ValueError):
        select_recent_latest([], queried_mpn="MPN", now=NOW.replace(tzinfo=None))
    with pytest.raises(ValueError):
        quote(NOW.replace(tzinfo=None))
    record = quote(NOW.astimezone(ZoneInfo("UTC")))
    assert select_recent_latest([record], queried_mpn="MPN", now=NOW) is record


class DisplayFrame(LowerFrame):
    def __init__(self, pages, displays, total):
        super().__init__(pages, total)
        self.displays = displays

    def evaluate(self, expression, arg=None):
        if arg is None:
            return super().evaluate(expression)
        assert arg["columns"] == list(QUOTATION_COLUMNS)
        assert arg["ids"] == [r["id"] for r in self.pages[self.number-1]]
        return self.displays[self.number-1]


def access(frame):
    return SimpleNamespace(operation_page=lambda: nullcontext(SimpleNamespace(shell_frame=frame)))


def test_real_native_pagination_then_raw_reader_latest_across_all_pages():
    old, latest = quote(NOW-timedelta(hours=2)), quote(NOW-timedelta(minutes=1))
    frame = DisplayFrame([[row(1), row(2)], [row(3)]],
                         [[list(old.payload), list(old.payload)], [list(latest.payload)]], 3)
    records = InsoQuotationReader().read(access(frame), " mpn ")
    assert len(records) == 3
    selected = select_recent_latest(records, queried_mpn="MPN", now=NOW)
    assert selected.payload == latest.payload
    assert frame.number == 2
    assert frame.value == "MPN"
    assert len(selected.payload) == 14
    assert selected.payload[3] == ""
    assert selected.payload[6] == "0001.2300"
    assert selected.payload[11] == "  原样\n备注  "
    assert selected.payload[13] == ""
    assert selected.quote_record_time == latest.quote_record_time
    assert all("Save" not in selector for _, selector in frame.calls)


def test_every_empty_business_cell_is_allowed_and_preserved():
    raw = ("2026/10/07 00:04", "MPN") + ("",)*12
    frame = DisplayFrame([[row(1, quantity="bad")]], [[list(raw)]], 1)
    records = InsoQuotationReader().read(access(frame), "MPN")
    assert records[0].payload == raw
    assert records[0].quote_record_time == NOW-timedelta(minutes=1)


@pytest.mark.parametrize("display", [None, [], [["missing"]], [[None]*14]])
def test_missing_structure_is_query_failure_not_empty(display):
    frame = DisplayFrame([[row(1)]], [display], 1)
    with pytest.raises(InsoDuplicateHistoryError):
        InsoQuotationReader().read(access(frame), "MPN")


def test_native_failure_does_not_return_empty_and_fuzzy_result_does_not_compete():
    frame = DisplayFrame([[row(1)]], [[list(quote().payload)]], 3)
    with pytest.raises(InsoDuplicateHistoryError):
        InsoQuotationReader().read(access(frame), "MPN")
    fuzzy = row(1)
    fuzzy["PartNo"] = "MPN suffix"
    frame = DisplayFrame([[fuzzy]], [[list(quote(model="MPN suffix").payload)]], 1)
    assert InsoQuotationReader().read(access(frame), "MPN") == ()


def test_invalid_exact_date_is_failure_not_no_recent_quote():
    raw = ("date unavailable", "MPN") + ("",)*12
    frame = DisplayFrame([[row(1)]], [[list(raw)]], 1)
    with pytest.raises(InsoDuplicateHistoryError):
        InsoQuotationReader().read(access(frame), "MPN")


def test_native_empty_query_is_successfully_captured():
    frame = DisplayFrame([[]], [[]], 0)
    assert InsoQuotationReader().read(access(frame), "MPN") == ()


def test_same_timestamp_selects_one_latest_without_content_tiebreaking():
    first, second = quote(), quote(model="mpn")
    assert select_recent_latest([first, second], queried_mpn="MPN", now=NOW) is first


def test_raw_capture_rejects_wrong_model_and_preserves_headers_contract():
    class Frame:
        def evaluate(self, expression, arg):
            assert "data-field" in expression
            assert "labels[start + i]" in expression
            assert "textContent" in expression
            return [list(quote(model="different").payload)]
    with pytest.raises(InsoDuplicateHistoryError):
        capture_quotation_page(Frame(), [row(1)])


def test_capture_hook_does_not_change_default_v12_native_payload():
    frame = LowerFrame([[row(1)]], total=1)
    assert PlaywrightProcurementHistoryPage(frame).query_exact_response("MPN") == {"rows": [row(1)]}
