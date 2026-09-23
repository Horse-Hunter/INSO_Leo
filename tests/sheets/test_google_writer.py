from typing import Any

import pytest

from src.sheets import WorksheetIdentity
from src.sheets.google_writer import GoogleSheetsBrandWriter, GoogleSheetsWriteError


class FakeRequest:
    def __init__(self, failure: Exception | None = None) -> None:
        self._failure = failure

    def execute(self) -> dict[str, Any]:
        if self._failure is not None:
            raise self._failure
        return {}


class FakeValuesResource:
    def __init__(self, failure: Exception | None = None) -> None:
        self._failure = failure
        self.update_calls: list[dict[str, Any]] = []

    def update(self, **kwargs: Any) -> FakeRequest:
        self.update_calls.append(kwargs)
        return FakeRequest(self._failure)


class FakeSpreadsheetsResource:
    def __init__(self, values_resource: FakeValuesResource) -> None:
        self._values_resource = values_resource

    def values(self) -> FakeValuesResource:
        return self._values_resource


class FakeSheetsService:
    def __init__(self, failure: Exception | None = None) -> None:
        self.values_resource = FakeValuesResource(failure)
        self.spreadsheets_resource = FakeSpreadsheetsResource(self.values_resource)

    def spreadsheets(self) -> FakeSpreadsheetsResource:
        return self.spreadsheets_resource


def worksheet() -> WorksheetIdentity:
    return WorksheetIdentity(spreadsheet="spreadsheet-id", worksheet="2026")


def test_google_writer_updates_only_target_brand_f_cell() -> None:
    service = FakeSheetsService()

    GoogleSheetsBrandWriter(service).write_brand(worksheet(), 12, "Resolved Brand")

    assert service.values_resource.update_calls == [
        {
            "spreadsheetId": "spreadsheet-id",
            "range": "'2026'!F12",
            "valueInputOption": "RAW",
            "body": {
                "majorDimension": "ROWS",
                "values": [["Resolved Brand"]],
            },
        }
    ]


def test_google_writer_updates_only_shahab_brand_e_cell() -> None:
    service = FakeSheetsService()
    target = WorksheetIdentity(spreadsheet="spreadsheet-id", worksheet="shahab")

    GoogleSheetsBrandWriter(service).write_brand(target, 13, "Resolved Brand")

    assert service.values_resource.update_calls == [
        {
            "spreadsheetId": "spreadsheet-id",
            "range": "'shahab'!E13",
            "valueInputOption": "RAW",
            "body": {
                "majorDimension": "ROWS",
                "values": [["Resolved Brand"]],
            },
        }
    ]


def test_google_write_failure_is_sheets_owned() -> None:
    writer = GoogleSheetsBrandWriter(
        FakeSheetsService(RuntimeError("simulated Google failure"))
    )

    with pytest.raises(GoogleSheetsWriteError) as raised:
        writer.write_brand(worksheet(), 12, "Resolved Brand")

    assert isinstance(raised.value.__cause__, RuntimeError)
