from typing import Any

from src.sheets import WorksheetIdentity, query_pending_records
from src.sheets.google_oauth import READ_ONLY_SCOPE
from src.sheets.google_reader import GoogleSheetsReadError, GoogleSheetsRowReader


class FakeRequest:
    def __init__(
        self,
        response: dict[str, Any] | None = None,
        failure: Exception | None = None,
    ) -> None:
        self._response = response if response is not None else {}
        self._failure = failure

    def execute(self) -> dict[str, Any]:
        if self._failure is not None:
            raise self._failure
        return self._response


class FakeValuesResource:
    def __init__(self, request: FakeRequest) -> None:
        self._request = request
        self.get_calls: list[dict[str, Any]] = []

    def get(self, **kwargs: Any) -> FakeRequest:
        self.get_calls.append(kwargs)
        return self._request


class FakeSpreadsheetsResource:
    def __init__(self, values_resource: FakeValuesResource) -> None:
        self._values_resource = values_resource

    def values(self) -> FakeValuesResource:
        return self._values_resource


class FakeSheetsService:
    def __init__(
        self,
        response: dict[str, Any] | None = None,
        failure: Exception | None = None,
    ) -> None:
        self.values_resource = FakeValuesResource(FakeRequest(response, failure))
        self.spreadsheets_resource = FakeSpreadsheetsResource(self.values_resource)

    def spreadsheets(self) -> FakeSpreadsheetsResource:
        return self.spreadsheets_resource


def worksheet() -> WorksheetIdentity:
    return WorksheetIdentity(spreadsheet="spreadsheet-id", worksheet="2026")


def test_api_rows_preserve_physical_positions_from_non_first_start() -> None:
    service = FakeSheetsService(
        {
            "values": [
                ["未发", "ignored", "A", "ignored", "MPN-1", "Brand", 10],
                ["sent", "ignored", "B", "ignored", "MPN-2", "", 20],
            ]
        }
    )
    reader = GoogleSheetsRowReader(service, first_row=5)

    rows = reader.read_rows(worksheet())

    assert [item.row_position for item in rows] == [5, 6]
    assert rows[0].cells == {
        "A": "未发",
        "B": "ignored",
        "C": "A",
        "D": "ignored",
        "E": "MPN-1",
        "F": "Brand",
        "G": 10,
    }
    assert service.values_resource.get_calls == [
        {
            "spreadsheetId": "spreadsheet-id",
            "range": "'2026'!A5:G",
            "majorDimension": "ROWS",
            "valueRenderOption": "UNFORMATTED_VALUE",
        }
    ]


def test_short_rows_fill_trailing_cells_without_shifting_columns() -> None:
    service = FakeSheetsService({"values": [["未发"], ["sent", "", "B", "", "MPN"]]})

    rows = GoogleSheetsRowReader(service).read_rows(worksheet())

    assert rows[0].cells == {
        "A": "未发",
        "B": None,
        "C": None,
        "D": None,
        "E": None,
        "F": None,
        "G": None,
    }
    assert rows[1].cells["A"] == "sent"
    assert rows[1].cells["C"] == "B"
    assert rows[1].cells["E"] == "MPN"
    assert rows[1].cells["F"] is None
    assert rows[1].cells["G"] is None


def test_empty_worksheet_returns_empty_collection() -> None:
    assert GoogleSheetsRowReader(FakeSheetsService()).read_rows(worksheet()) == ()
    assert (
        GoogleSheetsRowReader(FakeSheetsService({"values": []})).read_rows(worksheet())
        == ()
    )


def test_null_values_response_is_a_read_error_not_an_empty_worksheet() -> None:
    reader = GoogleSheetsRowReader(FakeSheetsService({"values": None}))

    try:
        reader.read_rows(worksheet())
    except GoogleSheetsReadError as exc:
        assert str(exc) == "Google Sheets values response is null"
    else:
        raise AssertionError("Expected GoogleSheetsReadError")


def test_adapter_returns_all_rows_and_existing_query_owns_pending_rule() -> None:
    service = FakeSheetsService(
        {
            "values": [
                [" 未发", "", "A", "", "NOT-PENDING", "", 1],
                ["未发", "", " B ", "", "PENDING", "Brand", 2],
                ["sent", "", "C", "", "NOT-PENDING-2", "", 3],
            ]
        }
    )
    reader = GoogleSheetsRowReader(service)

    rows = reader.read_rows(worksheet())
    pending = query_pending_records(reader, worksheet())

    assert len(rows) == 3
    assert [record.model for record in pending] == ["PENDING"]
    assert pending[0].importance_raw == " B "
    assert pending[0].brand == "Brand"
    assert pending[0].quantity == 2


def test_api_failure_is_raised_as_sheets_read_error_not_empty_rows() -> None:
    reader = GoogleSheetsRowReader(
        FakeSheetsService(failure=RuntimeError("simulated API failure"))
    )

    try:
        reader.read_rows(worksheet())
    except GoogleSheetsReadError as exc:
        assert isinstance(exc.__cause__, RuntimeError)
    else:
        raise AssertionError("Expected GoogleSheetsReadError")


def test_oauth_scope_is_read_only() -> None:
    assert READ_ONLY_SCOPE == "https://www.googleapis.com/auth/spreadsheets.readonly"
