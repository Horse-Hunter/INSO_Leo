"""Service-Account Sheets API transport behind the existing adapters (offline)."""

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

HEADER = ["2026/10/07", "本原厂", "MPN", "示例客户", "", "TI", "100", "备注"]
EXTRA = [""] * 15


class _Exec:
    def __init__(self, value):
        self.value = value

    def execute(self):
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


def service(responses, **kwargs):
    return GoogleApiSheetsService(FakeApi(responses), **kwargs)


def _row(e, f, g, w):
    return [*HEADER[:4], e, f, g, *EXTRA, w]


def test_source_read_widens_to_quote_date_and_returns_seven_columns():
    api = FakeApi([{"values": [
        [*HEADER[:7], *EXTRA, "quote_date"],
        _row("E1", "TI", "100", "2026/10/01"),
        _row("", "TI", "200", "2026/10/02"),
    ]}])
    response = GoogleApiSheetsService(api).get(
        spreadsheetId=SHEET, range="'2026'!A1:G", majorDimension="ROWS",
        valueRenderOption="UNFORMATTED_VALUE").execute()

    assert api.calls[0][1]["range"] == "'2026'!A1:W"
    assert all(len(row) == 7 for row in response["values"])
    evidence = response["source_order_dates"]
    assert evidence["column"] == "W" and evidence["header"] == "quote_date"
    # Only rows with an actual E (model) value carry a proof, like the CDP read.
    assert evidence["rows"] == [(2, "E1", "TI", "100", "2026/10/01")]


def test_source_read_without_quote_date_header_reports_no_evidence():
    api = FakeApi([{"values": [[*HEADER[:7], *EXTRA, "别的列"]]}])
    response = GoogleApiSheetsService(api).get(spreadsheetId=SHEET, range="'2026'!A1:G").execute()
    assert "source_order_dates" not in response


def test_ambiguous_quote_date_header_is_rejected():
    header = [*HEADER[:7], *EXTRA, "别的列"]
    header[3] = "quote_date"
    with pytest.raises(ValueError, match="GOOGLE_ORDER_DATE_HEADER_AMBIGUOUS"):
        GoogleApiSheetsService(FakeApi([{"values": [header]}])).get(
            spreadsheetId=SHEET, range="'2026'!A1:G").execute()


def test_other_sheets_are_read_exactly_as_asked_and_padded():
    api = FakeApi([{"values": [["2026/10/07", "本原厂", "MPN"]]}])
    response = GoogleApiSheetsService(api).get(
        spreadsheetId=SHEET, range="'SHAHAB'!A1:G").execute()
    assert api.calls[0][1]["range"] == "'SHAHAB'!A1:G"
    assert response["values"] == [["2026/10/07", "本原厂", "MPN", "", "", "", ""]]


def test_reader_reuses_the_existing_adapter_unchanged():
    api = FakeApi([{"values": [
        [*HEADER[:7], *EXTRA, "quote_date"],
        _row("E1", "TI", "100", "2026/10/01"),
    ]}])
    observed = []
    reader = GoogleSheetsRowReader(GoogleApiSheetsService(api), first_row=1,
                                   on_observation=lambda ws, rows, failed: observed.append((rows, failed)))
    rows = reader.read_rows(WorksheetIdentity(SHEET, "2026"))

    assert [row.row_position for row in rows] == [1, 2]
    assert rows[1].cells["E"] == "E1" and rows[1].cells["G"] == "100"
    assert rows[1].source_order_date == "2026/10/01"
    assert rows[0].cells["G"] == "100" and rows[0].source_order_date is None
    assert observed and observed[-1][1] is False


def test_write_requires_raw_single_row_and_reports_confirmation():
    api = FakeApi([{"updatedRange": "'报价输入'!B5:O5", "updatedRows": 1, "updatedCells": 14}])
    payload = [f"v{index}" for index in range(14)]
    response = GoogleApiSheetsService(api).update(
        spreadsheetId=SHEET, range="'报价输入'!B5:O5", valueInputOption="RAW",
        body={"majorDimension": "ROWS", "values": [payload]}).execute()
    assert response["updatedCells"] == 14
    assert api.calls[0][1]["body"]["values"] == [payload]


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


def test_write_without_server_confirmation_is_not_success():
    api = FakeApi([{"spreadsheetId": SHEET}])
    with pytest.raises(GoogleSheetsWriteUnconfirmed):
        GoogleApiSheetsService(api).update(
            spreadsheetId=SHEET, range="'2026'!F9", valueInputOption="RAW",
            body={"values": [["TI"]]}).execute()


def test_write_invalidates_the_brief_snapshot():
    brief = [["RFQ_BRIEF"]]
    api = FakeApi([{"values": brief},
                   {"updatedRange": "'2026'!F9", "updatedRows": 1, "updatedCells": 1}])
    transport = GoogleApiSheetsService(api)
    transport.read_brief(SHEET)
    assert transport.peek_brief_snapshot(SHEET) is not None
    transport.update(spreadsheetId=SHEET, range="'2026'!F9", valueInputOption="RAW",
                     body={"values": [["TI"]]}).execute()
    assert transport.peek_brief_snapshot(SHEET) is None


def test_brief_read_pads_to_seventeen_columns_and_caches_for_a_minute():
    clock = [0.0]
    api = FakeApi([{"values": [["rfq_line_id"], ["x", "2026"]]}])
    transport = GoogleApiSheetsService(api, timer=lambda: clock[0])
    response = transport.read_brief(SHEET)

    assert api.calls[0][1]["range"].endswith("RFQ_BRIEF!A1:Q")
    assert len(response["values"][0]) == 17 and len(response["values"][1]) == 17
    revision, entry = transport.peek_brief_token(SHEET)
    assert revision == 1 and entry is not None and entry[1][0][0] == "rfq_line_id"

    clock[0] = 59.0
    assert transport.read_brief_discovery(SHEET)["values"][0][0] == "rfq_line_id"
    assert len(api.calls) == 1  # Discovery used the unexpired snapshot.

    clock[0] = 61.0
    assert transport.peek_brief_snapshot(SHEET) is None


def test_read_only_lifecycle_ports_are_inert():
    transport = GoogleApiSheetsService(FakeApi([]))
    with transport.poll_scope(), transport.suspend_idle_poll():
        assert transport.operations_idle() is True
    assert transport.release_retained_pages(browser_handle=object()) is None
    assert transport.close() is None
    assert transport.external_write is True
    assert transport.live_read_revision == 0


def test_key_file_is_read_from_plain_json(tmp_path):
    path = tmp_path / "sa.json"
    path.write_text(json.dumps({"client_email": "sa@example.com",
                                'private_key': 'synthetic-placeholder-body',
                                "token_uri": "https://oauth2.googleapis.com/token"}),
                    encoding="utf-8")
    info = load_service_account_info(path)
    assert info["client_email"] == "sa@example.com"


def test_key_file_is_read_from_a_dpapi_protected_copy(tmp_path):
    payload = json.dumps({"client_email": "sa@example.com",
                          'private_key': 'synthetic-placeholder-body',
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


def test_model_identity_is_text_only_and_never_repadded():
    """A numeric cell is the same number the native download would have shown."""
    api = FakeApi([{"values": [
        [*HEADER[:7], *EXTRA, "quote_date"],
        _row(123, "TI", 100, "2026/10/01"),
        _row(123.0, "TI", 100, "2026/10/01"),
        _row("000123", "TI", 100, "2026/10/01"),
        _row("1.5", "TI", 100, "2026/10/01"),
    ]}])
    rows = GoogleApiSheetsService(api).get(
        spreadsheetId=SHEET, range="'2026'!A1:G").execute()["values"]

    assert rows[1][4] == "123"      # Exact integer: same display, no padding added.
    assert rows[2][4] == "123"      # 123.0 is the same integer.
    assert rows[3][4] == "000123"   # Stored text keeps its leading zeros untouched.
    assert rows[4][4] == "1.5"      # Ordinary text is never reinterpreted.
    # Quantity stays numeric exactly as the native A:G read produced it.
    assert rows[1][6] == 100


def test_non_integral_numeric_identity_is_left_for_the_row_checks():
    api = FakeApi([{"values": [
        [*HEADER[:7], *EXTRA, "quote_date"],
        _row(1.5, "TI", 100, "2026/10/01"),
    ]}])
    rows = GoogleApiSheetsService(api).get(
        spreadsheetId=SHEET, range="'2026'!A1:G").execute()["values"]
    assert rows[1][4] == 1.5  # The transport never invents a model name.


def test_quotation_input_row_is_never_reinterpreted():
    """The 14-cell payload stays exactly what Sheets returns: no identity rules."""
    payload = [2026, 5, "MPN", "", "USD", "", 12.5, "", "", "", "", "", "", ""]
    api = FakeApi([{"values": [payload]}])
    values = GoogleApiSheetsService(api).get(
        spreadsheetId=SHEET, range="'报价输入'!B5:O5").execute()["values"]
    assert values == [payload]
