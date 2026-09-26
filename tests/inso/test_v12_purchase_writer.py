from __future__ import annotations

import pytest

from src.inso.purchase_writer import InsoPurchaseWriter, PlaywrightAiResultReader
from src.inso.session import SecurityViolation
from src.inso.write_safety import FakeWriteGate


class _OperationPage:
    def __init__(self, page):
        self.page = page


class _Locator:
    def __init__(self, page, selector: str, *, text: str = "", value: str = ""):
        self.page = page
        self.selector = selector
        self.text = text
        self.value = value

    def count(self):
        if self.selector == "input#ImpValueF":
            return 1
        if self.selector == "button#ai-recognize":
            return 1
        if self.selector.startswith('input[data-f="'):
            return 1
        if self.selector == ".select-menu-modal .select-menu-item":
            return len(self.page.options) if self.page.menu_open else 0
        return 0

    def evaluate_all(self, _script):
        if self.selector != "input#ImpValueF":
            return []
        return [
            {
                "role": "textbox",
                "accessibleName": "",
                "visibleText": "",
                "id": "ImpValueF",
                "type": "text",
                "enabled": True,
                "visible": True,
            }
        ]

    def click(self):
        if self.selector == "input#ImpValueF":
            self.page.menu_open = True
        elif self.selector == ".select-menu-modal .select-menu-item":
            self.page.value = self.text
            self.page.menu_open = False

    def input_value(self):
        if self.selector.startswith('input[data-f="'):
            return self.value
        return self.page.value

    def inner_text(self):
        return self.text

    def all(self):
        return [
            _Locator(self.page, self.selector, text=option)
            for option in self.page.options
        ]


class _Frame:
    def __init__(self, page):
        self.page = page

    def locator(self, selector: str):
        return _Locator(self.page, selector)


class _FakeFormPage:
    url = "https://yingsuo.alperp.cn/"
    options = ("需要问全价格", "普通询价")

    def __init__(self):
        self.value = ""
        self.menu_open = False

    def frame_locator(self, _selector: str):
        return _Frame(self)


class _FakeAiPage:
    url = "https://yingsuo.alperp.cn/skins/etaoerp/product/Import_ai.aspx?BillPage=Enquiry&VendorID=&h=510"

    def __init__(self, *, ready: bool = True, values=None):
        self.ready = ready
        self.values = values or {"PartNo": "LM358", "Brand": "Texas Instruments", "Qty": "123"}

    def locator(self, selector: str):
        if selector == "button#ai-recognize":
            text = "重新识别" if self.ready else "AI 智能识别"
            return _Locator(self, selector, text=text)
        if selector == "#preview-body > tr":
            return _Rows(self)
        return _Locator(self, selector)


class _Rows:
    def __init__(self, page):
        self.page = page

    def count(self):
        return 1

    def nth(self, _index: int):
        return _Row(self.page)


class _Row:
    def __init__(self, page):
        self.page = page

    def locator(self, selector: str):
        field = selector.split('data-f="', 1)[1].split('"', 1)[0]
        return _Locator(self.page, selector, value=self.page.values[field])


@pytest.mark.parametrize("value", ["需要问全价格", "普通询价"])
def test_quotation_type_maps_to_exact_importance_control(value: str) -> None:
    form_page = _FakeFormPage()
    writer = InsoPurchaseWriter(
        form_page=_OperationPage(form_page),
        ai_page=_OperationPage(_FakeAiPage()),
        gate=FakeWriteGate(enabled=True),
    )

    writer.set_quotation_type(value)

    assert form_page.value == value


def test_quotation_type_rejects_values_outside_the_two_business_routes() -> None:
    writer = InsoPurchaseWriter(
        form_page=_OperationPage(_FakeFormPage()),
        ai_page=_OperationPage(_FakeAiPage()),
        gate=FakeWriteGate(enabled=True),
    )

    with pytest.raises(SecurityViolation):
        writer.set_quotation_type("意向单询价")


def test_production_gate_is_closed_and_writer_has_no_save_or_send_method() -> None:
    form_page = _FakeFormPage()
    writer = InsoPurchaseWriter(
        form_page=_OperationPage(form_page),
        ai_page=_OperationPage(_FakeAiPage()),
    )

    assert not {"save_data", "save_and_send", "send", "submit"} & set(dir(writer))
    with pytest.raises(SecurityViolation):
        writer.set_quotation_type("普通询价")
    assert form_page.value == ""


def test_ai_reader_returns_only_ready_single_row_result() -> None:
    reader = PlaywrightAiResultReader(_OperationPage(_FakeAiPage()))

    result = reader.read()
    assert result is not None
    assert (result.model, result.brand, result.quantity, result.ready) == (
        "LM358",
        "Texas Instruments",
        123,
        True,
    )


def test_ai_reader_fails_closed_until_ready_state() -> None:
    reader = PlaywrightAiResultReader(
        _OperationPage(_FakeAiPage(ready=False))
    )

    assert reader.read() is None
