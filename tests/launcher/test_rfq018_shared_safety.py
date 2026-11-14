"""RFQ-018 negative regressions for shared page/document admission."""

from types import SimpleNamespace

import pytest

from src.launcher import sales_header
from src.launcher.backend import ProductionBackend
from src.launcher.google_quote_update import GoogleQuotationUpdateActions
from src.order_mail.contracts import OrderError
from src.research.cdp_pages import (
    PageResourceAdmission,
    PageTargetCleanupError,
)
from src.sheets.quotation_input import QuotationInputBusy
from src.workflow.v12_faults import V12Fault
from tests.launcher.test_google_quote_update import Browser, adapter, location


def _quote_with_admission():
    writer, browser = adapter()
    admission = PageResourceAdmission()
    browser._inso_page_admission = admission
    return writer, browser, admission


def test_unconfirmed_quote_write_blocks_new_client_after_close():
    writer, browser, _admission = _quote_with_admission()
    writer.open_sheet(select_worksheet=True, worksheet="2026")
    writer._script_pending = True
    writer.close()

    other = GoogleQuotationUpdateActions(
        browser_handle=SimpleNamespace(owned=False, browser=browser),
        location=location(),
    )
    with pytest.raises((QuotationInputBusy, V12Fault)):
        other.open_sheet(select_worksheet=True, worksheet="2026")


def test_unconfirmed_quote_write_blocks_another_sheet_in_same_document():
    writer, browser, _admission = _quote_with_admission()
    writer.open_sheet(select_worksheet=True, worksheet="2026")
    writer._protected = True
    writer.close()

    other = GoogleQuotationUpdateActions(
        browser_handle=SimpleNamespace(owned=False, browser=browser),
        location=location(),
    )
    with pytest.raises((QuotationInputBusy, V12Fault)):
        other.open_sheet(select_worksheet=True, worksheet="SHAHAB")


def test_quote_write_without_shared_admission_fails_closed():
    browser = Browser()
    actions = GoogleQuotationUpdateActions(
        browser_handle=SimpleNamespace(owned=False, browser=browser),
        location=location(),
    )

    with pytest.raises(V12Fault, match="CDP_PAGE_ADMISSION_UNCONFIRMED"):
        actions.open_sheet(select_worksheet=True, worksheet="2026")


def _sales_config():
    return SimpleNamespace(cdp=SimpleNamespace(cdp_url="http://127.0.0.1:9222"))


def test_sales_preflight_without_admission_stops_before_browser(monkeypatch):
    monkeypatch.setattr(sales_header, "sales_config", lambda *_: (_sales_config(), {}))
    monkeypatch.setattr(
        sales_header,
        "acquire_cdp_browser",
        lambda *_: pytest.fail("unexpected browser acquisition"),
    )

    stage, _text = sales_header.run_sales_header_check(
        config_path="unused", production_path="unused", root="unused",
    )

    assert stage == "STOPPED"


def test_sales_preflight_with_invalid_admission_stops_before_browser(monkeypatch):
    monkeypatch.setattr(sales_header, "sales_config", lambda *_: (_sales_config(), {}))
    monkeypatch.setattr(
        sales_header,
        "acquire_cdp_browser",
        lambda *_: pytest.fail("unexpected browser acquisition"),
    )
    admission = PageResourceAdmission()
    admission.invalidate(PageTargetCleanupError((ValueError("synthetic"),)))

    stage, _text = sales_header.run_sales_header_check(
        config_path="unused", production_path="unused", root="unused",
        page_admission=admission,
    )

    assert stage == "STOPPED"


def test_sales_preflight_binds_admission_before_creating_page(monkeypatch):
    monkeypatch.setattr(sales_header, "sales_config", lambda *_: (_sales_config(), {}))
    admission = PageResourceAdmission()
    browser = SimpleNamespace(contexts=[SimpleNamespace(pages=[])])
    handle = SimpleNamespace(owned=False, browser=browser, disconnect=lambda: None)
    monkeypatch.setattr(sales_header, "acquire_cdp_browser", lambda *_: handle)
    observed = []

    def stop_at_new_page(actual, *_args, **_kwargs):
        observed.append(getattr(actual, "_inso_page_admission", None) is admission)
        raise OrderError("INSO")

    monkeypatch.setattr(sales_header, "new_background_page", stop_at_new_page)

    stage, _text = sales_header.run_sales_header_check(
        config_path="unused", production_path="unused", root="unused",
        page_admission=admission,
    )

    assert stage == "STOPPED" and observed == [True]


def test_backend_order_mail_passes_the_same_admission(tmp_path, monkeypatch):
    observed = []
    backend = ProductionBackend(root=tmp_path)

    def check(**kwargs):
        observed.append(kwargs.get("page_admission") is backend._page_admission)
        return "NO_ORDER", "synthetic"

    monkeypatch.setattr(sales_header, "run_sales_header_check", check)
    try:
        assert backend.start_order_mail_check()
        backend._order_mail_thread.join(5)
        assert observed == [True]
    finally:
        backend.shutdown()
