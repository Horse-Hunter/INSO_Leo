"""RFQ-016 phase 1: one fully wired API chain over the real adapters and ledger.

Google API read → row identity → single-cell brand/status write → quotation
input write → (button) → durable hold. Only the external Sheets endpoint and the
browser are simulated; every repository component in between is the production
one, and the hold lives in a real SQLite file.
"""

from dataclasses import replace

import pytest

from src.research.cdp_pages import PageResourceAdmission
from src.sheets.google_api_service import GoogleApiSheetsService
from src.sheets.google_reader import GoogleSheetsRowReader
from src.sheets.google_writer import (
    GoogleSheetsBrandWriter,
    GoogleSheetsPurchaseStatusWriter,
)
from src.sheets.pending import WorksheetIdentity
from src.sheets.quotation_input import (
    GoogleQuotationInput,
)
from src.workflow.v12_faults import V12Fault
from src.workflow.v13_integration import V13HoldStore, hold_payload_is_effect_uncertain
from src.workflow.v13_quotation import QuotationOutcome, RowErrorReason
from src.workflow.v13_quote_update import V13QuotationUpdater
from tests.inso.test_v13_quotation_read import quote
from tests.sheets.test_quotation_input import RAW, location
from tests.workflow.test_rfq006_integration import fixture as hold_fixture
from tests.workflow.test_v13_quote_update import POPUP, found

SPREADSHEET = "fake-sheet"
SOURCE_HEADER = ["STATUS", "", "CLASS", "", "MPN", "MFR", "Qty"] + [""] * 15 + ["quote_date"]
SOURCE_ROW = ["2026/10/07", "高", "客户A", "", "000123", "TI", 1000] + [""] * 15 + ["2026/10/01"]


class _Exec:
    def __init__(self, value):
        self.value = value

    def execute(self):
        if isinstance(self.value, Exception):
            raise self.value
        return self.value


class FakeSheetsApi:
    """Records every request; returns receipts shaped like the real endpoint."""

    def __init__(self, *, update_error=None):
        self.calls, self.update_calls = [], []
        self.update_error = update_error

    def spreadsheets(self):
        return self

    def values(self):
        return self

    def get(self, **kwargs):
        self.calls.append(("get", kwargs))
        if "range" in kwargs:
            return _Exec({"values": [SOURCE_HEADER, SOURCE_ROW]})
        return _Exec({"sheets": [{"properties": {"title": "报价输入", "sheetId": 489913321}}]})

    def update(self, **kwargs):
        self.calls.append(("update", kwargs))
        self.update_calls.append(kwargs)
        if self.update_error is not None:
            raise self.update_error
        return _Exec({"spreadsheetId": kwargs["spreadsheetId"],
                      "updatedRange": kwargs["range"], "updatedCells": _cells(kwargs["range"])})


def _service(api, **kwargs):
    """Controlled test construction: every writable API client gets a shared admission."""
    kwargs.setdefault("page_admission", PageResourceAdmission())
    return GoogleApiSheetsService(api, **kwargs)


def _cells(range_name):
    _sheet, cells = range_name.split("!")
    first, _, last = cells.partition(":")
    return _column(last or first) - _column(first) + 1


def _column(cell):
    number = 0
    for char in cell.rstrip("0123456789"):
        number = number * 26 + ord(char) - 64
    return number


class Actions:
    """The CDP side of the handoff: no page, only the ordering is recorded."""

    def __init__(self):
        self.order, self.clicks = [], 0
        self.popups = [POPUP]

    def prepare_price_refresh(self):
        pass

    def open_quote_input(self):
        self.order.append("open")

    def refresh_after_external_write(self):
        self.order.append("refresh")

    def click_update_quote(self):
        self.order.append("click")
        self.clicks += 1
        self.quoted = True  # the bound script changes the source status

    def read_update_result(self):
        return self.popups[0]

    def dismiss_result(self):
        self.order.append("dismiss")

    def close(self):
        self.order.append("close")


class Source:
    def __init__(self, actions):
        self.model, self.actions = "000123", actions

    def read_state(self, _result):
        return ("采购已报价" if getattr(self.actions, "quoted", False) else "发给采购"), self.model


def updater(service, holds, *, identity):
    actions = Actions()
    return V13QuotationUpdater(
        source=Source(actions),
        quotation_input=GoogleQuotationInput(service, location(), expected_columns=_columns()),
        actions=actions,
        wait=lambda _seconds: False,
        persist_uncertain=lambda result: holds.hold(result, identity),
    )


def _columns():
    from src.inso.quotation_read import QUOTATION_COLUMNS

    return QUOTATION_COLUMNS


def read_chain(service):
    reader = GoogleSheetsRowReader(service)
    rows = reader.read_rows(WorksheetIdentity(SPREADSHEET, "2026"))
    return rows


def test_api_read_then_single_cell_writes_keep_the_old_contract():
    api = FakeSheetsApi()
    service = _service(api)

    rows = read_chain(service)
    assert rows[1].cells["E"] == "000123"  # leading zeros preserved
    assert rows[1].cells["G"] == 1000
    assert rows[1].cells["D"] is None  # blank source cell
    assert rows[1].source_order_date == "2026/10/01"

    GoogleSheetsBrandWriter(service).write_brand(WorksheetIdentity(SPREADSHEET, "2026"), 2, "TI")
    GoogleSheetsPurchaseStatusWriter(service).write_purchase_status(
        WorksheetIdentity(SPREADSHEET, "2026"), 2)
    assert [call["range"] for call in api.update_calls] == ["'2026'!F2", "'2026'!A2"]
    assert [call["valueInputOption"] for call in api.update_calls] == ["RAW", "RAW"]
    assert api.update_calls[1]["body"]["values"] == [["发给采购"]]


def test_unknown_api_write_holds_the_order_and_never_clicks(tmp_path):
    api = FakeSheetsApi(update_error=RuntimeError("response lost after the server applied it"))
    service = _service(api)
    _db, _store, _sheets, holds, _ledger, _quotes, _make, _observed = hold_fixture(tmp_path, [()])
    identity = found().record_identity
    cycle = updater(service, holds, identity=identity)

    result = cycle.update_one(found())

    assert result.outcome is QuotationOutcome.ROW_FAILED and result.effect_uncertain is True
    assert result.row_error_reason is RowErrorReason.QUOTE_INPUT_WRITE_FAILED
    assert len(api.update_calls) == 1  # exactly one attempt, no retry
    assert cycle._actions.clicks == 0
    assert cycle._actions.order[0] == "open" and "click" not in cycle._actions.order

    active = holds.active()
    assert len(active) == 1
    assert active[0][0] == found().inquiry_id
    assert active[0][3] == "QUOTE_INPUT_WRITE_FAILED"
    assert hold_payload_is_effect_uncertain(active[0][1]) is True

    # Restart: the same file still refuses to release or overwrite the evidence.
    reopened = V13HoldStore(holds.path)
    reopened.migrate()
    assert reopened.active() == active
    reopened.close(active[0][0])
    assert reopened.active() == active
    with pytest.raises(V12Fault):
        reopened.hold(replace(found(), outcome=QuotationOutcome.ROW_FAILED,
                              row_error_reason=RowErrorReason.SOURCE_CHANGED,
                              effect_uncertain=False), identity)


def test_confirmed_api_write_reloads_once_then_clicks_once(tmp_path):
    api = FakeSheetsApi()
    service = _service(api)
    _db, _store, _sheets, holds, _ledger, _quotes, _make, _observed = hold_fixture(tmp_path, [()])
    cycle = updater(service, holds, identity=found().record_identity)

    result = cycle.update_one(found())

    assert result.outcome is QuotationOutcome.UPDATED_INSERTED
    assert holds.active() == ()
    assert cycle._actions.order == ["open", "refresh", "click", "dismiss", "close"]
    assert cycle._actions.clicks == 1
    update = api.update_calls[0]
    assert update["range"] == "'报价输入'!A1:N1" and len(update["body"]["values"][0]) == 14
    assert update["body"]["values"][0][1] == "000123"  # the source model, not the quote's


def test_unconfirmed_receipt_stops_before_the_button(tmp_path):
    class ShortReceipt(FakeSheetsApi):
        def update(self, **kwargs):
            self.update_calls.append(kwargs)
            return _Exec({"spreadsheetId": kwargs["spreadsheetId"],
                          "updatedRange": kwargs["range"], "updatedCells": 1})

    service = _service(ShortReceipt())
    _db, _store, _sheets, holds, _ledger, _quotes, _make, _observed = hold_fixture(tmp_path, [()])
    cycle = updater(service, holds, identity=found().record_identity)

    result = cycle.update_one(found())

    assert result.effect_uncertain is True and cycle._actions.clicks == 0
    assert len(holds.active()) == 1


def test_a_15_cell_input_range_is_refused_before_any_call(tmp_path):
    from src.sheets.quotation_input import QuotationInputUnavailable

    api = FakeSheetsApi()
    service = _service(api)
    with pytest.raises(QuotationInputUnavailable):
        # first_column 1 with a 15-wide location is rejected by the transport.
        GoogleQuotationInput(service, location(first_column=0),
                             expected_columns=_columns()).write_payload(RAW)
    assert api.update_calls == []


def test_quote_payload_keeps_the_raw14_contract_through_the_api(tmp_path):
    api = FakeSheetsApi()
    service = _service(api)
    writer = GoogleQuotationInput(service, location(), expected_columns=_columns())
    writer.write_payload(RAW)
    assert api.update_calls[0]["body"]["values"] == [list(RAW)]
    assert api.update_calls[0]["valueInputOption"] == "RAW"


def test_actual_quote_payload_from_the_workflow_is_unchanged():
    """The same payload the CDP transport used must reach the API unchanged."""
    payload = found().quotation.payload
    assert isinstance(payload, tuple) and len(payload) == 14
    assert all(isinstance(cell, str) for cell in payload)
    assert payload == quote().payload
