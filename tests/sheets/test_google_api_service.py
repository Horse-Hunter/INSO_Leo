"""Service-Account Sheets API transport behind the existing adapters (offline).

The fake API below answers with the shapes the real endpoint returns: JSON numbers
for numeric cells, display strings for dates, blanks as trimmed rows, and an
`updatedRange`/`updatedCells` receipt. Nothing is pre-stringified for convenience.
"""

import json

import pytest

from src.core.protected_local_store import protect_bytes
from src.sheets.google_api_service import (
    GoogleApiSheetsService,
    GoogleSheetsWriteUnconfirmed,
    build_service_account_sheets_service,
    load_service_account_info,
)
from src.sheets.google_oauth import (
    READ_ONLY_SCOPE,
    GoogleSheetsAuthorizationError,
)
from src.sheets.google_reader import GoogleSheetsRowReader
from src.sheets.pending import WorksheetIdentity

SHEET = "1AbCdEfGhIjKlMnOpQrStUvWxYz0123456789abcd"
WIDTH_2026 = 23


class _Exec:
    def __init__(self, value):
        self.value = value

    def execute(self):
        if isinstance(self.value, Exception):
            raise self.value
        return self.value


class _Values:
    def __init__(self, owner):
        self.owner = owner

    def get(self, **kwargs):
        self.owner.calls.append(("get", kwargs))
        return _Exec(self.owner.responses.pop(0))

    def update(self, **kwargs):
        self.owner.calls.append(("update", kwargs))
        return _Exec(self.owner.responses.pop(0))


class _Spreadsheets:
    def __init__(self, owner):
        self.owner = owner

    def values(self):
        return _Values(self.owner)

    def get(self, **kwargs):
        self.owner.calls.append(("metadata", kwargs))
        return _Exec(self.owner.responses.pop(0))


class FakeApi:
    """Minimal API surface; every call is recorded, nothing leaves the process."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def spreadsheets(self):
        return _Spreadsheets(self)


def header_2026():
    """A real 2026 header row: the exact labels the CDP transport required."""
    row = ["STATUS", "", "CLASS", "", "MPN", "MFR", "Qty"]
    row += [None] * (WIDTH_2026 - len(row) - 1)
    row.append("quote_date")
    return row


def row_2026(date, importance, customer, mpn, brand, qty, quote_date):
    """A real source row: numbers stay numbers, dates are display strings."""
    row = [date, importance, customer, "", mpn, brand, qty]
    row += [None] * (WIDTH_2026 - len(row) - 1)
    row.append(quote_date)
    return row


def read(response, range_name="'2026'!A1:G"):
    return GoogleApiSheetsService(FakeApi([response])).get(
        spreadsheetId=SHEET, range=range_name, majorDimension="ROWS",
        valueRenderOption="UNFORMATTED_VALUE").execute()


# --- reads: display parity and identity --------------------------------------
def test_source_read_is_formatted_and_widened_to_the_quote_date_column():
    api = FakeApi([{"values": [header_2026(),
                               row_2026("2026/10/07", "高", "客户A", "000123", "TI", 100, "2026/10/01")]}])
    response = GoogleApiSheetsService(api).get(
        spreadsheetId=SHEET, range="'2026'!A1:G", valueRenderOption="UNFORMATTED_VALUE").execute()

    # The caller asked for unformatted, but display parity is the transport contract.
    assert api.calls[0][1]["range"] == "'2026'!A1:W"
    assert api.calls[0][1]["valueRenderOption"] == "FORMATTED_VALUE"
    assert all(len(row) == 7 for row in response["values"])
    assert response["values"][1] == ["2026/10/07", "高", "客户A", "", "000123", "TI", 100]


def test_quote_date_evidence_uses_the_same_values_as_the_row():
    """E/F/G in the W proof must be literally the cells the reader compares."""
    response = read({"values": [header_2026(),
                                row_2026("2026/10/07", "高", "客户A", 123, "TI", 100, "2026/10/01")]})
    evidence = response["source_order_dates"]
    assert evidence["column"] == "W" and evidence["header"] == "quote_date"
    assert evidence["rows"] == [(2, "123", "TI", 100, "2026/10/01")]
    # A JSON number in the model cell displays exactly like the TSV download.
    assert response["values"][1][4] == "123"
    assert tuple(response["values"][1][index] for index in (4, 5, 6)) == evidence["rows"][0][1:4]


def test_reader_binds_the_same_row_without_any_identity_mismatch():
    api = FakeApi([{"values": [header_2026(),
                               row_2026("2026/10/07", "高", "客户A", 123, "TI", 100, "2026/10/01"),
                               row_2026("2026/10/07", "低", "客户B", "000123", "TI", 5.5, "2026/10/02")]}])
    observed = []
    reader = GoogleSheetsRowReader(GoogleApiSheetsService(api), first_row=1,
                                   on_observation=lambda ws, rows, failed: observed.append((rows, failed)))
    rows = reader.read_rows(WorksheetIdentity(SHEET, "2026"))

    assert [row.row_position for row in rows] == [1, 2, 3]
    assert rows[1].cells["E"] == "123" and rows[2].cells["E"] == "000123"
    assert rows[1].source_order_date == "2026/10/01" and rows[2].source_order_date == "2026/10/02"
    assert rows[1].cells["G"] == 100 and rows[2].cells["G"] == 5.5
    assert observed and observed[-1][1] is False


def test_blank_and_quoted_source_cells_keep_their_meaning():
    row = row_2026("2026/10/07", "", "", "", "TI", "", "")
    row[3] = "'000456"  # A user-typed leading apostrophe is display text, not a number.
    response = read({"values": [header_2026(), row]})
    values = response["values"][1]
    assert values[1] == "" and values[3] == "'000456"
    assert values[6] is None  # Blank quantity keeps the old TSV→None contract.
    assert response["source_order_dates"]["rows"] == []


def test_source_read_without_a_quote_date_column_carries_no_evidence():
    header = header_2026()
    header[WIDTH_2026 - 1] = "别的列"
    assert "source_order_dates" not in read({"values": [header]})


def test_duplicate_quote_date_header_is_still_refused():
    header = header_2026()
    header[3] = "quote_date"
    with pytest.raises(ValueError, match="GOOGLE_ORDER_DATE_HEADER_AMBIGUOUS"):
        read({"values": [header]})

    header = header_2026()
    header[WIDTH_2026 - 1] = "quote_date_extra"
    assert "source_order_dates" not in read({"values": [header]})


def test_shahab_keeps_the_native_column_contract():
    header = ["", "STATUS", "", "Part Number", "Brand", "QTY", ""]
    data = ["2026/10/07", "发给采购", "", "MPN1", "TI", 1000]
    api = FakeApi([{"values": [["stale pre-header row"], header, data]}])
    response = GoogleApiSheetsService(api).get(
        spreadsheetId=SHEET, range="'SHAHAB'!A1:G").execute()
    # Read from row 1 like the native download; the requested slice starts at row 1.
    assert api.calls[0][1]["range"] == "'SHAHAB'!A1:G"
    assert api.calls[0][1]["valueRenderOption"] == "FORMATTED_VALUE"
    assert response["values"][2] == ["2026/10/07", "发给采购", "", "MPN1", "TI", 1000, ""]


def test_source_header_mismatch_fails_closed_like_the_native_download():
    """The 21:50 production stop class: worksheet identity is never assumed."""
    from src.workflow.v12_faults import FaultScope, V12Fault

    for bad in ([["STATUS", "", "CLASS", "", "PART", "MFR", "Qty"]],
                [["STATUS", "", "", "", "MPN", "MFR", "Qty"]],
                []):
        with pytest.raises(V12Fault) as caught:
            read({"values": bad})
        assert caught.value.reason == "SHEETS_SCHEMA_UNAVAILABLE"
        assert caught.value.scope is FaultScope.GLOBAL_STOP


def test_shahab_header_must_be_on_the_second_row():
    from src.workflow.v12_faults import V12Fault

    with pytest.raises(V12Fault) as caught:
        GoogleApiSheetsService(FakeApi([{"values": [
            ["", "STATUS", "", "Part Number", "Brand", "QTY"]]}])).get(
            spreadsheetId=SHEET, range="'SHAHAB'!A1:G").execute()
    assert caught.value.reason == "SHEETS_SCHEMA_UNAVAILABLE"


def test_quotation_input_row_is_text_only():
    payload = [2026, 5, "MPN", "", "USD", "", 12.5, "", "", "", "", "", "", ""]
    api = FakeApi([{"values": [payload]}])
    values = GoogleApiSheetsService(api).get(
        spreadsheetId=SHEET, range="'报价输入'!B1:O1").execute()["values"]
    assert values == [["2026", "5", "MPN", "", "USD", "", "12.5", "", "", "", "", "", "", ""]]


def test_brief_read_makes_every_cell_text_like_the_native_read():
    brief = [["rfq_line_id", "sheet", "sheet_row", "rfq_date", "mpn", "mfr", "qty"],
             [12345, "2026", 42, "2026/10/07", 100123, "TI", 1000]]
    api = FakeApi([{"values": brief}])
    transport = GoogleApiSheetsService(api)
    values = transport.read_brief(SHEET)["values"]

    assert api.calls[0][1]["range"].endswith("RFQ_BRIEF!A1:Q")
    assert api.calls[0][1]["valueRenderOption"] == "FORMATTED_VALUE"
    assert values[1][:7] == ["12345", "2026", "42", "2026/10/07", "100123", "TI", "1000"]
    assert all(isinstance(cell, str) for row in values for cell in row)
    assert all(len(row) == 17 for row in values)


def test_brief_snapshot_caches_for_a_minute_and_write_invalidates():
    clock = [0.0]
    api = FakeApi([{"values": [["rfq_line_id"], ["x", "2026"]]},
                   {"updatedRange": "'2026'!F9", "updatedCells": 1}])
    transport = GoogleApiSheetsService(api, timer=lambda: clock[0])
    transport.read_brief(SHEET)
    revision, entry = transport.peek_brief_token(SHEET)
    assert revision == 1 and entry is not None
    clock[0] = 59.0
    assert transport.read_brief_discovery(SHEET)["values"][0][0] == "rfq_line_id"
    assert len(api.calls) == 1
    clock[0] = 61.0
    assert transport.peek_brief_snapshot(SHEET) is None
    transport.update(spreadsheetId=SHEET, range="'2026'!F9", valueInputOption="RAW",
                     body={"values": [["TI"]]}).execute()
    assert transport.peek_brief_snapshot(SHEET) is None


# --- writes: target whitelist and receipt proof ------------------------------
def test_raw14_write_is_confirmed_by_its_exact_receipt():
    api = FakeApi([{"updatedRange": "'报价输入'!B5:O5", "updatedRows": 1, "updatedCells": 14}])
    payload = [f"v{index}" for index in range(14)]
    response = GoogleApiSheetsService(api).update(
        spreadsheetId=SHEET, range="'报价输入'!B5:O5", valueInputOption="RAW",
        body={"majorDimension": "ROWS", "values": [payload]}).execute()
    assert response["updatedCells"] == 14
    assert api.calls[0][1]["valueInputOption"] == "RAW"


def test_single_cell_write_accepts_quoted_or_bare_receipts():
    for receipt_range in ("'2026'!F9", "2026!F9", "'2026'!F9:F9"):
        api = FakeApi([{"updatedRange": receipt_range, "updatedCells": 1}])
        GoogleApiSheetsService(api).update(
            spreadsheetId=SHEET, range="'2026'!F9", valueInputOption="RAW",
            body={"values": [["TI"]]}).execute()


@pytest.mark.parametrize("receipt", [
    {"updatedRange": "'2026'!F9", "updatedCells": 0},
    {"updatedRange": "'2026'!F9:G9", "updatedCells": 2},
    {"updatedRange": "'2026'!G9", "updatedCells": 1},
    {"updatedRange": "'2026'!F10", "updatedCells": 1},
    {"updatedRange": "'SHAHAB'!F9", "updatedCells": 1},
    {"updatedRange": "not-a-range", "updatedCells": 1},
    {"updatedCells": 1},
    {"updatedRange": "'2026'!F9"},
])
def test_write_receipt_must_prove_the_exact_target_and_count(receipt):
    api = FakeApi([receipt])
    with pytest.raises(GoogleSheetsWriteUnconfirmed):
        GoogleApiSheetsService(api).update(
            spreadsheetId=SHEET, range="'2026'!F9", valueInputOption="RAW",
            body={"values": [["TI"]]}).execute()


def test_write_receipt_rejects_a_different_spreadsheet():
    api = FakeApi([{"spreadsheetId": "other", "updatedRange": "'2026'!F9", "updatedCells": 1}])
    with pytest.raises(GoogleSheetsWriteUnconfirmed):
        GoogleApiSheetsService(api).update(
            spreadsheetId=SHEET, range="'2026'!F9", valueInputOption="RAW",
            body={"values": [["TI"]]}).execute()


def test_missing_receipt_is_not_success():
    api = FakeApi([{"spreadsheetId": SHEET}])
    with pytest.raises(GoogleSheetsWriteUnconfirmed):
        GoogleApiSheetsService(api).update(
            spreadsheetId=SHEET, range="'2026'!F9", valueInputOption="RAW",
            body={"values": [["TI"]]}).execute()


@pytest.mark.parametrize("options", [
    {"range": "'报价输入'!B5:O5", "valueInputOption": "USER_ENTERED",
     "body": {"values": [["x"] * 14]}},
    {"range": "'报价输入'!B5:O5", "valueInputOption": "RAW",
     "body": {"values": [["x"] * 13]}},
    {"range": "'报价输入'!B5:O5", "valueInputOption": "RAW",
     "body": {"values": [["x"] * 14, ["y"] * 14]}},
    {"range": "'报价输入'!B5:O5", "valueInputOption": "RAW",
     "body": {"values": [[True] * 14]}},
])
def test_write_rejects_anything_outside_the_existing_contract(options):
    with pytest.raises(ValueError, match="GOOGLE_WRITE_UNCONFIRMED"):
        GoogleApiSheetsService(FakeApi([])).update(spreadsheetId=SHEET, **options).execute()


@pytest.mark.parametrize("range_name, width", [
    ("'2026'!B9", 1),        # a column the schema never writes
    ("'2026'!B9:F9", 5),     # a multi-cell source block
    ("'RFQ_BRIEF'!B2", 1),   # never writable through this transport
    ("'Unknown'!F9", 1),     # unknown worksheet
    ("'报价输入'!B5:M5", 13),  # 13 of the 14 input cells
])
def test_forbidden_write_targets_are_refused_before_any_call(range_name, width):
    api = FakeApi([])
    with pytest.raises(ValueError):
        GoogleApiSheetsService(api).update(
            spreadsheetId=SHEET, range=range_name, valueInputOption="RAW",
            body={"values": [["x"] * width]}).execute()
    assert api.calls == []


@pytest.mark.parametrize("range_name", [
    "'2026'!A1:H",       # beyond the source A:G contract
    "'2026'!B1:G",       # missing the status column
    "'Unknown'!A1:G",
    "'报价输入'!B5:N5",    # 13 cells
])
def test_forbidden_read_targets_are_refused_before_any_call(range_name):
    api = FakeApi([])
    with pytest.raises(ValueError):
        GoogleApiSheetsService(api).get(spreadsheetId=SHEET, range=range_name).execute()
    assert api.calls == []


def test_read_only_lifecycle_ports_are_inert():
    transport = GoogleApiSheetsService(FakeApi([]))
    with transport.poll_scope(), transport.suspend_idle_poll():
        assert transport.operations_idle() is True
    assert transport.release_retained_pages(browser_handle=object()) is None
    assert transport.close() is None
    assert transport.external_write is True
    assert transport.live_read_revision == 0


# --- credential loading ------------------------------------------------------
def test_key_file_is_read_from_plain_json(tmp_path):
    path = tmp_path / "sa.json"
    path.write_text(json.dumps({"client_email": "sa@example.com",
                                'private_key': "synthetic-placeholder-body",
                                "token_uri": "https://oauth2.googleapis.com/token"}),
                    encoding="utf-8")
    info = load_service_account_info(path)
    assert info["client_email"] == "sa@example.com"


def test_key_file_is_read_from_a_dpapi_protected_copy(tmp_path):
    payload = json.dumps({"client_email": "sa@example.com",
                          'private_key': "synthetic-placeholder-body",
                          "token_uri": "https://oauth2.googleapis.com/token"}).encode()
    try:
        protected = protect_bytes(payload)
    except Exception:  # noqa: BLE001 - DPAPI is Windows-only in this repository
        pytest.skip("CurrentUser DPAPI unavailable on this host")
    path = tmp_path / "sa.key"
    path.write_bytes(protected)
    assert b"synthetic-placeholder-body" not in protected
    assert load_service_account_info(path)["client_email"] == "sa@example.com"


def test_incomplete_or_unreadable_key_is_rejected(tmp_path):
    incomplete = tmp_path / "sa.json"
    incomplete.write_text(json.dumps({"client_email": "sa@example.com"}), encoding="utf-8")
    with pytest.raises(GoogleSheetsAuthorizationError):
        load_service_account_info(incomplete)

    garbage = tmp_path / "sa.bin"
    garbage.write_bytes(b"not a key")
    with pytest.raises(GoogleSheetsAuthorizationError):
        load_service_account_info(garbage)


def test_unsupported_scope_is_refused_before_any_client_is_built(tmp_path):
    with pytest.raises(ValueError, match="GOOGLE_API_SCOPE_UNSUPPORTED"):
        build_service_account_sheets_service(tmp_path / "missing.json", scope="drive")
    assert READ_ONLY_SCOPE != "drive"
