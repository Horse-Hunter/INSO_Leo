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


def test_fuzzy_other_model_quantity_is_not_current_order_validation():
    reader = InsoDuplicateHistoryReader(list_url="https://yingsuo.alperp.cn", procurement_history=True)
    unrelated = row(1, quantity="0")
    unrelated["PartNo"] = "XMPN suffix"
    assert reader._records_from_response({"rows": [unrelated]}, target_mpn="MPN") == ()
    with pytest.raises(InsoDuplicateHistoryError):
        reader._records_from_response({"rows": [row(2, quantity="0")]}, target_mpn="MPN")


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
        assert arg["ids"] == [r["id"] for r in self.pages[self.number - 1]]
        assert arg["models"] == [" ".join(r["PartNo"].split()) for r in self.pages[self.number - 1]]
        assert arg["page"] == self.number
        assert 'ids.every' in expression and 'expected.page' in expression

    def expect_response(self, predicate, *, timeout):
        frame = self

        class Pending:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                self.value = SimpleNamespace(
                    status=200,
                    url="https://yingsuo.alperp.cn/services/stock/select.ashx"
                    f"?action=Stock_VenQuote&para={frame.value}&pageindex={frame.number}",
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


def test_lower_render_uses_display_whitespace_without_altering_raw_model():
    record = row(1)
    record["PartNo"] = "MPN  suffix\u00a0TRAY"
    frame = LowerFrame([[record]], total=1)
    assert PlaywrightProcurementHistoryPage(frame).query_exact_response("MPN")["rows"][0]["PartNo"] == record["PartNo"]


def test_new_lower_page_waits_for_native_field_initialization():
    class InitializingFrame(LowerFrame):
        ready = False

        def locator(self, selector):
            locator = super().locator(selector)
            if selector == "#DetailField_FenLan" and not self.ready:
                locator.input_value = lambda: ""
            return locator

        def wait_for_function(self, expression, **kwargs):
            if "arg" not in kwargs:
                assert "DetailField_FenLan" in expression
                self.ready = True
            else:
                super().wait_for_function(expression, **kwargs)

    frame = InitializingFrame([[row(1)]], total=1)
    assert PlaywrightProcurementHistoryPage(frame).query_exact_response("MPN")["rows"] == [row(1)]
    assert frame.ready


def test_repeated_page_identity_is_not_a_complete_history():
    frame = LowerFrame([[row(1), row(2)], [row(2)]], total=3)
    with pytest.raises(InsoDuplicateHistoryError):
        PlaywrightProcurementHistoryPage(frame).query_exact_response("MPN")


def test_incomplete_page_is_not_a_negative_duplicate_result():
    frame = LowerFrame([[row(1)]], total=3)
    with pytest.raises(InsoDuplicateHistoryError):
        PlaywrightProcurementHistoryPage(frame).query_exact_response("MPN")


def test_lower_query_checks_row_identity_and_page_not_just_repeated_models():
    frame = LowerFrame([[row(1), row(2)], [row(3)]], total=3)
    observations = []
    original = frame.wait_for_function
    def wait(expression, *, arg, timeout):
        observations.append(arg)
        original(expression, arg=arg, timeout=timeout)
    frame.wait_for_function = wait
    PlaywrightProcurementHistoryPage(frame).query_exact_response("MPN")
    assert [o["ids"] for o in observations] == [["1", "2"], ["3"]]
    assert [o["page"] for o in observations] == [1, 2]


def test_lower_query_has_one_overall_deadline(monkeypatch):
    import src.inso.duplicate_history as history
    clock = iter([0, 0, 0, 6])
    monkeypatch.setattr(history, "monotonic", lambda: next(clock))
    frame = LowerFrame([[row(1), row(2)], [row(3)]], total=3)
    with pytest.raises(InsoDuplicateHistoryError):
        PlaywrightProcurementHistoryPage(frame, timeout_ms=5000).query_exact_response("MPN")


def test_owner_suffix_duplicate_keeps_zero_price_and_relevant_quantity_guard():
    reader = InsoDuplicateHistoryReader(list_url="https://yingsuo.alperp.cn", procurement_history=True)
    matched, wrong = row(1), row(2, quantity="bad")
    matched["PartNo"], wrong["PartNo"] = "WGI210IT S LJXS", "WGI211IT"
    records = reader._records_from_response({"rows": [matched, wrong]}, target_mpn="WGI210IT")
    assert len(records) == 1
    assert records[0].mpn == matched["PartNo"] and records[0].inso_quote == 0
    matched["Qty"] = "bad"
    with pytest.raises(InsoDuplicateHistoryError):
        reader._records_from_response({"rows": [matched]}, target_mpn="WGI210IT")


def test_procurement_reader_queries_prefix_once_and_filters_full_original_target():
    from contextlib import nullcontext
    matched, too_long = row(1), row(2, quantity="bad")
    matched["PartNo"] = "WGI210IT S LJXS"
    too_long["PartNo"] = "WGI210" + "A" * 11
    frame = LowerFrame([[matched, too_long]], total=2)
    access = SimpleNamespace(operation_page=lambda: nullcontext(SimpleNamespace(shell_frame=frame)))
    reader = InsoDuplicateHistoryReader(list_url="https://yingsuo.alperp.cn",
        procurement_history=True, operation_access=access)
    capture = reader.read("WGI210IT")
    assert frame.value == "WGI210IT"
    assert len(capture.records) == 1
    assert capture.records[0].mpn == matched["PartNo"]


def test_separated_model_query_keeps_duplicate_matching_and_rejects_other_models():
    from contextlib import nullcontext
    matched, other = row(1), row(2)
    matched["PartNo"], other["PartNo"] = "RM342-059-581-7200", "RM342-999-581-7200"
    frame = LowerFrame([[matched, other]], total=2)
    access = SimpleNamespace(operation_page=lambda: nullcontext(SimpleNamespace(shell_frame=frame)))
    reader = InsoDuplicateHistoryReader(list_url="https://yingsuo.alperp.cn",
        procurement_history=True, operation_access=access)
    capture = reader.read("RM342-059-581-7200")
    assert frame.value == "RM342-059-581-7200"
    assert [record.mpn for record in capture.records] == [matched["PartNo"]]
