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


def test_transient_read_retries_once_and_recovers():
    service = FakeSheetsService()
    calls = []
    def execute():
        calls.append(True)
        if len(calls) == 1:
            raise TimeoutError("synthetic read timeout")
        return {"values": [["未发"]]}
    service.values_resource._request.execute = execute
    assert len(GoogleSheetsRowReader(service).read_rows(worksheet())) == 1
    assert len(calls) == 2


def test_transient_read_exhaustion_is_distinct_from_invalid_response():
    import pytest

    from src.sheets.google_reader import GoogleSheetsReadUnavailable

    service = FakeSheetsService(failure=TimeoutError("synthetic timeout"))
    with pytest.raises(GoogleSheetsReadUnavailable):
        GoogleSheetsRowReader(service).read_rows(worksheet())
    assert len(service.values_resource.get_calls) == 5
    broken = FakeSheetsService(response={"values": None})
    with pytest.raises(GoogleSheetsReadError) as error:
        GoogleSheetsRowReader(broken).read_rows(worksheet())
    assert not isinstance(error.value, GoogleSheetsReadUnavailable)
    assert len(broken.values_resource.get_calls) == 1


def test_permission_denied_is_not_transient_or_retried():
    import pytest
    class Denied(Exception):
        resp = type("Response", (), {"status": 403})()
    service = FakeSheetsService(failure=Denied("synthetic permission denied"))
    with pytest.raises(GoogleSheetsReadError):
        GoogleSheetsRowReader(service).read_rows(worksheet())
    assert len(service.values_resource.get_calls) == 1


def test_fifth_read_can_recover_and_backoff_is_bounded():
    calls, waits = [], []
    service = FakeSheetsService()
    def execute():
        calls.append(True)
        if len(calls) < 5:
            raise TimeoutError("synthetic")
        return {"values": [["未发"]]}
    service.values_resource._request.execute = execute
    reader = GoogleSheetsRowReader(service, retry_wait=lambda seconds: waits.append(seconds))
    assert reader.read_rows(worksheet())[0].cells['A'] == '未发'
    assert len(calls) == 5 and waits == [2, 4, 6, 8]


def test_discovery_is_bounded_immutable_and_fresh_checks_never_use_it():
    import pytest
    response = {"values": [["未发", "", "A", "", "TEST", "brand", 2]]}
    service = FakeSheetsService(response)
    reader = GoogleSheetsRowReader(service)
    with reader.discovery_scope():
        first = reader.read_discovery_rows(worksheet())
        assert reader.read_discovery_rows(worksheet()) is first
        with pytest.raises(TypeError):
            first[0].cells['A'] = 'wrong'
        response['values'][0][0] = '发给采购'
        assert reader.read_discovery_rows(worksheet())[0].cells['A'] == '未发'
        assert reader.read_rows(worksheet())[0].cells['A'] == '发给采购'
        assert reader.read_discovery_rows(worksheet())[0].cells['A'] == '发给采购'
        reader.clear_discovery_snapshot()
        reader.read_discovery_rows(worksheet())
        assert len(service.values_resource.get_calls) == 3
    reader.read_discovery_rows(worksheet())
    with reader.discovery_scope():
        reader.read_discovery_rows(worksheet())
    assert len(service.values_resource.get_calls) == 5


def test_discovery_does_not_cross_threads_or_survive_a_failed_live_check():
    from concurrent.futures import ThreadPoolExecutor

    import pytest
    service = FakeSheetsService({"values": [["未发"]]})
    reader = GoogleSheetsRowReader(service)
    with reader.discovery_scope():
        reader.read_discovery_rows(worksheet())
        with ThreadPoolExecutor(max_workers=1) as executor:
            executor.submit(reader.read_discovery_rows, worksheet()).result()
        assert len(service.values_resource.get_calls) == 2
        service.values_resource._request._failure = RuntimeError('synthetic unknown')
        with pytest.raises(GoogleSheetsReadError):
            reader.read_rows(worksheet())
        with pytest.raises(GoogleSheetsReadError):
            reader.read_discovery_rows(worksheet())
        service.values_resource._request._failure = None
        reader.read_discovery_rows(worksheet())
        assert len(service.values_resource.get_calls) == 5


def test_stop_during_backoff_does_not_continue_reading():
    import pytest

    from src.sheets.google_reader import GoogleSheetsReadUnavailable
    service = FakeSheetsService(failure=TimeoutError('synthetic'))
    with pytest.raises(GoogleSheetsReadUnavailable):
        GoogleSheetsRowReader(service, retry_wait=lambda _: True).read_rows(worksheet())
    assert len(service.values_resource.get_calls) == 1
