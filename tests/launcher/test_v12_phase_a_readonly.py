from __future__ import annotations

import inspect
import json

from src.launcher.v12_phase_a_readonly import (
    _SAFE_BLANK_FORM_BACK,
    _ai_dialog_frame,
    _classify_duplicate_fields,
    _confirmed_duplicate_fields,
    _decimal_is_readable,
    _empty_report,
    _inspect_blank_form,
    _schema_summary,
    _top_level_login_redirect,
)


def test_schema_summary_keeps_keys_but_never_values() -> None:
    payload = {
        "rows": [
            {
                "BillID": "101",
                "OfferPrice": "23.50",
                "Creator": "SECRET_CANARY_private_customer",
            }
        ],
        "token": "SECRET_CANARY_auth_token",
    }

    top_level, row_shapes = _schema_summary(payload)
    report = json.dumps({"top": top_level, "rows": row_shapes})

    assert top_level == ["rows"]
    assert row_shapes == [
        {"path": "rows", "fields": ["BillID", "Creator", "OfferPrice"]}
    ]
    assert "SECRET_CANARY" not in report
    assert "token" not in report


def test_creator_requires_schema_grid_and_detail_agreement() -> None:
    row_fields = {"BillID", "Creator", "UserName", "OwnerID"}
    columns = [{"field": "Creator", "label": "制单人"}]
    details = [{"field": "Creator", "label": "制单人", "creator_nonempty": True}]

    creator, quote, currency = _confirmed_duplicate_fields(row_fields, columns, details)

    assert creator == "Creator"
    assert quote is None
    assert currency is None


def test_purchaser_and_salesperson_never_count_as_creator() -> None:
    row_fields = {"BillID", "UserName", "OwnerID"}
    columns = [
        {"field": "UserName", "label": "采购人员"},
        {"field": "OwnerID", "label": "业务员"},
    ]
    details = columns.copy()

    assert _confirmed_duplicate_fields(row_fields, columns, details) == (
        None,
        None,
        None,
    )


def test_quote_requires_response_grid_and_detail_mapping() -> None:
    row_fields = {"BillID", "OfferPrice", "OfferCurrencyID"}
    columns = [{"field": "OfferPrice", "label": "报价"}]
    details = [
        {"field": "OfferPrice", "label": "报价", "value": "23.50"},
        {
            "field": "OfferCurrencyID",
            "label": "报价币种",
            "value": "1",
            "currency_display_readable": True,
        },
    ]

    assert _confirmed_duplicate_fields(row_fields, columns, details) == (
        None,
        "OfferPrice",
        "OfferCurrencyID",
    )
    assert _confirmed_duplicate_fields(row_fields, [], details) == (
        None,
        None,
        "OfferCurrencyID",
    )


def test_quote_needs_matching_detail_currency_and_decimal() -> None:
    report = _empty_report()
    fields = [
        {"field": "OfferPrice", "label": "报价", "value": "23.50"},
        {
            "field": "OfferCurrencyID",
            "label": "报价币种",
            "value": "1",
            "currency_display_readable": True,
        },
    ]
    _classify_duplicate_fields(
        report,
        fields,
        row_fields={"BillID", "OfferPrice", "OfferCurrencyID"},
        columns=[{"field": "OfferPrice", "label": "报价"}],
        bill_id="101",
        rows=[{"BillID": "101", "OfferPrice": "23.50", "OfferCurrencyID": "1"}],
    )
    assert report["inso_quote"]["status"] == "CONFIRMED"
    assert report["inso_quote"]["row_detail_values_match"] is True
    assert "23.50" not in json.dumps(report)

    mismatch = _empty_report()
    _classify_duplicate_fields(
        mismatch,
        fields,
        row_fields={"BillID", "OfferPrice", "OfferCurrencyID"},
        columns=[{"field": "OfferPrice", "label": "报价"}],
        bill_id="101",
        rows=[{"BillID": "101", "OfferPrice": "23.50", "OfferCurrencyID": "2"}],
    )
    assert mismatch["inso_quote"]["status"] == "UNKNOWN"


def test_decimal_probe_does_not_return_or_log_quote_value() -> None:
    assert _decimal_is_readable("1,234.50")
    assert not _decimal_is_readable("SECRET_CANARY")
    report = json.dumps(_empty_report())
    assert "SECRET_CANARY" not in report


def test_read_only_inspector_has_no_recognition_import_or_save_click() -> None:
    source = inspect.getsource(_inspect_blank_form)

    assert "ai_entry.click" in source  # opening the inspected panel only
    assert "ai_frames = [" not in source
    assert "dialog_result = _ai_dialog_frame(frame)" in source
    assert "details-dialog._dialog1" in source
    assert "iframe[src*='/product/Import_ai.aspx']" in source
    assert "recognize.click" not in source
    assert "pasteImport" in source  # function source is inspected, not invoked
    assert "doImport" in source
    assert "save_button.click" not in source
    assert "save_send.click" not in source
    assert "send.click" not in source
    assert "win_btn__dialog11" not in source


def test_ai_iframe_is_resolved_through_the_confirmed_dialog_container() -> None:
    class Frame:
        url = "https://yingsuo.alperp.cn/skins/etaoerp/product/Import_ai.aspx"

    class ElementHandle:
        def content_frame(self):
            return Frame()

    class Iframe:
        def __init__(self, src: str) -> None:
            self.src = src

        def count(self) -> int:
            return 1

        def is_visible(self) -> bool:
            return True

        def wait_for(self, **_: object) -> None:
            return None

        def get_attribute(self, name: str) -> str | None:
            return self.src if name == "src" else None

        def element_handle(self) -> ElementHandle:
            return ElementHandle()

    class Dialog:
        def __init__(self, iframe: Iframe, count: int = 1) -> None:
            self.iframe = iframe
            self._count = count
            self.selectors: list[str] = []

        def count(self) -> int:
            return self._count

        def is_visible(self) -> bool:
            return True

        def wait_for(self, **_: object) -> None:
            return None

        def locator(self, selector: str) -> Iframe:
            self.selectors.append(selector)
            return self.iframe

    class ShellFrame:
        url = "https://yingsuo.alperp.cn/skins/etaoerp/InnerEnquiry/YeWuXJ/List.aspx"

        def __init__(self, dialog: Dialog) -> None:
            self.dialog = dialog
            self.selectors: list[str] = []

        def locator(self, selector: str) -> Dialog:
            self.selectors.append(selector)
            return self.dialog

    iframe = Iframe("/skins/etaoerp/product/Import_ai.aspx?BillPage=YeWuXJ")
    dialog = Dialog(iframe)
    shell = ShellFrame(dialog)

    result = _ai_dialog_frame(shell)

    assert result is not None
    assert result[0] is dialog
    assert result[1] is iframe
    assert isinstance(result[2], Frame)
    assert shell.selectors == ["details-dialog._dialog1"]
    assert dialog.selectors == [
        "iframe[src*='/product/Import_ai.aspx']"
    ]


def test_ai_iframe_resolution_fails_closed_on_ambiguous_or_wrong_target() -> None:
    class ElementHandle:
        def content_frame(self):
            return type(
                "Frame",
                (),
                {"url": "https://yingsuo.alperp.cn/skins/etaoerp/login.aspx"},
            )()

    class Iframe:
        def count(self) -> int:
            return 1

        def is_visible(self) -> bool:
            return True

        def wait_for(self, **_: object) -> None:
            return None

        def get_attribute(self, name: str) -> str | None:
            return "/skins/etaoerp/product/Import_ai.aspx" if name == "src" else None

        def element_handle(self) -> ElementHandle:
            return ElementHandle()

    class Dialog:
        def __init__(self, count: int) -> None:
            self.count_value = count

        def count(self) -> int:
            return self.count_value

        def is_visible(self) -> bool:
            return True

        def wait_for(self, **_: object) -> None:
            return None

        def locator(self, _selector: str) -> Iframe:
            return Iframe()

    class ShellFrame:
        url = "https://yingsuo.alperp.cn/skins/etaoerp/InnerEnquiry/YeWuXJ/List.aspx"

        def __init__(self, dialog: Dialog) -> None:
            self.dialog = dialog

        def locator(self, _selector: str) -> Dialog:
            return self.dialog

    assert _ai_dialog_frame(ShellFrame(Dialog(count=2))) is None
    assert _ai_dialog_frame(ShellFrame(Dialog(count=1))) is None


def test_embedded_login_frame_does_not_mark_top_level_session_logged_out() -> None:
    class Page:
        class Frame:
            url = "https://yingsuo.alperp.cn/"

        def __init__(self) -> None:
            self.main_frame = self.Frame()
            login_frame = type(
                "LoginFrame", (), {"url": "https://yingsuo.alperp.cn/login.aspx"}
            )()
            self.frames = [self.main_frame, login_frame]

    assert _top_level_login_redirect(Page()) is False


def test_top_level_login_redirect_is_reported() -> None:
    class Page:
        class Frame:
            url = "https://yingsuo.alperp.cn/login.aspx"

        main_frame = Frame()

    assert _top_level_login_redirect(Page()) is True


def test_blank_form_back_handler_allows_only_the_observed_close_callback() -> None:
    assert _SAFE_BLANK_FORM_BACK.fullmatch(
        "function goback() {\n parent.main_alertbox_close('alert_enquiry');\n}"
    )
    assert not _SAFE_BLANK_FORM_BACK.fullmatch(
        "function goback() { parent.main_alertbox_close('alert_enquiry'); "
        "bill_save(); }"
    )
