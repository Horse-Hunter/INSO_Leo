import pytest

from src.quotation.update_result import UpdatePopupOutcome, parse_update_popup


@pytest.mark.parametrize("display,expected", [
    ("报价更新完成\n成功填入：1行", "INSERTED"),
    (" 报价更新完成 \n 成功填入 : 1 行 \n已有报价：0行", "INSERTED"),
    ("报价更新完成\n成功填入：0行\n已有报价：1行", "ALREADY_EXISTS"),
    ("报价更新完成\n已有报价：1行", "ALREADY_EXISTS"),
    ("报价更新完成 成功填入：0行 已有报价：0行", "UNCONFIRMED"),
    ("报价更新完成 成功填入：2行", "UNCONFIRMED"),
    ("报价更新完成 成功填入：1行 已有报价：1行", "UNCONFIRMED"),
    ("报价更新完成 成功填入：1行 已有报价：-1行", "UNCONFIRMED"),
    ("成功！", "UNCONFIRMED"), ("错误：报价更新完成 成功填入：1行", "UNCONFIRMED"),
    ("报价更新完成 成功填入：1行 成功填入：1行", "UNCONFIRMED"),
    ("报价更新完成 成功填入：-1行", "UNCONFIRMED"),
    (None, "UNCONFIRMED"), ("", "UNCONFIRMED"),
])
def test_strict_single_row_popup_counts(display, expected):
    assert parse_update_popup(display) is UpdatePopupOutcome(expected)


@pytest.mark.parametrize("display,expected", [
    ("更新完成成功填入：0 行已有价跳过：1 行确定", "ALREADY_EXISTS"),
    ("更新完成\n成功填入：1 行\n已有价跳过：0 行", "INSERTED"),
    ("更新完成成功填入：0行已有价跳过：0行", "UNCONFIRMED"),
    ("更新完成成功填入：1行已有价跳过：1行", "UNCONFIRMED"),
    ("更新完成成功填入：0行已有价跳过：2行", "UNCONFIRMED"),
    ("更新完成成功填入：0行已有价跳过：-1行", "UNCONFIRMED"),
    ("更新完成成功填入：0行已有价跳过：1行已有报价：1行", "UNCONFIRMED"),
    ("更新完成成功填入：0行已有价跳过：1行已有价跳过：1行", "UNCONFIRMED"),
])
def test_observed_live_popup_keeps_strict_single_row_counts(display, expected):
    assert parse_update_popup(display) is UpdatePopupOutcome(expected)
