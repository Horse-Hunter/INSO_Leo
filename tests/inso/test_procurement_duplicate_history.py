from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from src.inso.duplicate_history import (
    InsoDuplicateHistoryError,
    InsoDuplicateHistoryReader,
    PlaywrightProcurementHistoryPage,
)


def row(identity, *, quantity="200.000", date="2026-10-02 09:00:00"):
    return {
        "id": str(identity), "BillID": "99", "PartNo": "MPN", "Qty": quantity,
        "CreateTime": date, "UserName": "制单人", "InPrice": "0", "CurrencyID": "RMB",
    }


def test_procurement_mapping_retains_creator_quantity_and_zero_price():
    reader = InsoDuplicateHistoryReader(list_url="https://yingsuo.alperp.cn", procurement_history=True)
    records = reader._records_from_response({"rows": [row(1), row(2)]})
    assert [record.bill_id for record in records] == ["1", "2"]
    assert records[0].creator == "制单人"
    assert records[0].quantity == 200
    assert records[0].inso_quote == 0


@pytest.mark.parametrize("quantity", ["", "0", "-1", "1.5", "NaN", "Qty"])
def test_invalid_relevant_procurement_quantity_fails_closed(quantity):
    reader = InsoDuplicateHistoryReader(list_url="https://yingsuo.alperp.cn", procurement_history=True)
    with pytest.raises(InsoDuplicateHistoryError):
        reader._records_from_response({"rows": [row(1, quantity=quantity)]})


def test_window_does_not_require_quantity_from_irrelevant_old_records():
    reader = InsoDuplicateHistoryReader(list_url="https://yingsuo.alperp.cn", procurement_history=True)
    records = reader._records_from_response(
        {"rows": [row(1, quantity="", date="2025-01-01 00:00:00"), row(2)]},
        since=datetime(2026, 9, 25, tzinfo=UTC),
    )
    assert len(records) == 1
    assert records[0].bill_id == "2"


class LowerFrame:
    url = "https://yingsuo.alperp.cn/skins/etaoerp//InnerEnquiry/YeWuXJ/List.aspx"

    def __init__(self, pages, total):
        self.pages = pages
        self.total = total
        self.number = 0
        self.value = ""
        self.calls = []
        self.page = self

    def locator(self, selector):
        frame = self

        class Locator:
            def fill(self, value, **kwargs):
                frame.value = value
                frame.calls.append(("fill", selector))

            def input_value(self):
                return "PartNo" if selector == "#DetailField_FenLan" else (
                    "2" if selector == "select" else frame.value
                )

            def click(self, **kwargs):
                frame.calls.append(("click", selector))
                if selector in ("#select_btns_layout", "#tabs_b_panel_2 .layui-laypage-next:visible"):
                    frame.number += 1

            def inner_text(self):
                return f"共 {frame.total} 条"

            def locator(self, child):
                return frame.locator(child)

        return Locator()

    def evaluate(self, expression):
        return "4"

    def wait_for_function(self, expression, *, arg, timeout):
        assert len(arg) == len(self.pages[self.number - 1])

    def expect_response(self, predicate, *, timeout):
        frame = self

        class Pending:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                self.value = SimpleNamespace(
                    status=200,
                    url="https://yingsuo.alperp.cn/services/stock/select.ashx"
                    f"?action=Stock_VenQuote&para=MPN&pageindex={frame.number}",
                    json=lambda: {"rows": frame.pages[frame.number - 1], "total": -1},
                )
                assert predicate(self.value)

        return Pending()


def test_native_lower_query_reads_every_page_not_upper_query():
    frame = LowerFrame([[row(1), row(2)], [row(3)]], total=3)
    result = PlaywrightProcurementHistoryPage(frame).query_exact_response("MPN")
    assert len(result["rows"]) == 3
    assert ("click", "#tab_b_li2 > a") in frame.calls
    assert ("click", "#select_btns_layout") in frame.calls
    assert ("click", "#select_btns") not in frame.calls


def test_repeated_page_identity_is_not_a_complete_history():
    frame = LowerFrame([[row(1), row(2)], [row(2)]], total=3)
    with pytest.raises(InsoDuplicateHistoryError):
        PlaywrightProcurementHistoryPage(frame).query_exact_response("MPN")


def test_incomplete_page_is_not_a_negative_duplicate_result():
    frame = LowerFrame([[row(1)]], total=3)
    with pytest.raises(InsoDuplicateHistoryError):
        PlaywrightProcurementHistoryPage(frame).query_exact_response("MPN")
