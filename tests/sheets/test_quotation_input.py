from types import SimpleNamespace

import pytest

from src.inso.quotation_read import QUOTATION_COLUMNS
from src.sheets import WorksheetIdentity
from src.sheets.quotation_input import (
    GoogleQuotationInput,
    QuotationInputAttemptFailed,
    QuotationInputLocation,
    QuotationInputUnavailable,
)

RAW = ("2026/10/07 01:00", "000MPN", "", "001.2300", "奇币", "", "000.1000", "",
       "0009", "000批号", "2周", "  原文\n备注  ", "备注2\t", "")


def location(**changes):
    values = {"worksheet": WorksheetIdentity("fake-sheet", "报价输入"), "header_row": 4,
              "input_row": 7, "first_column": 3, "gid": "27"}
    return QuotationInputLocation(**{**values, **changes})


class Values:
    def __init__(self):
        self.payload = ["old"]*14
        self.headers = list(QUOTATION_COLUMNS)
        self.calls = []
        self.metadata = {"sheets": [{"properties": {"title": "报价输入", "sheetId": 27}}]}
        self.metadata_error = None
        self.write_error = None
        self.read_error = None
    def metadata_get(self, **kwargs):
        self.calls.append(("metadata", kwargs))
        def run():
            if self.metadata_error:
                raise self.metadata_error
            return self.metadata
        return SimpleNamespace(execute=run)
    def get(self, **kwargs):
        self.calls.append(("get", kwargs))
        def run():
            if self.read_error:
                raise self.read_error
            return {"values": [self.headers if kwargs["range"].endswith("C4:P4") else self.payload]}
        return SimpleNamespace(execute=run)
    def update(self, **kwargs):
        self.calls.append(("update", kwargs))
        def run():
            if self.write_error:
                raise self.write_error
            self.payload = kwargs["body"]["values"][0].copy()
            return {}
        return SimpleNamespace(execute=run)


def adapter(**changes):
    values = Values()
    service = SimpleNamespace(spreadsheets=lambda: SimpleNamespace(values=lambda: values, get=values.metadata_get))
    return GoogleQuotationInput(service, location(**changes), expected_columns=QUOTATION_COLUMNS), values


def test_full_raw14_exact_order_blanks_and_special_text_overwrite_old_row():
    writer, values = adapter()
    writer.validate_schema()
    writer.write_payload(RAW)
    assert writer.read_payload() == RAW
    update = next(call[1] for call in values.calls if call[0] == "update")
    assert update == {"spreadsheetId": "fake-sheet", "range": "'报价输入'!C7:P7",
                      "valueInputOption": "RAW", "body": {"majorDimension": "ROWS", "values": [list(RAW)]}}
    assert values.payload[2] == values.payload[5] == values.payload[13] == ""
    assert values.payload[3] == "001.2300" and values.payload[11] == "  原文\n备注  "
    assert all(call[1]["range"].startswith("'报价输入'!") for call in values.calls if call[0] != "metadata")


def test_readback_missing_trailing_cells_only_pads_empty_without_trim():
    writer, values = adapter()
    values.payload = list(RAW[:-1])
    assert writer.read_payload() == RAW
    values.payload = []
    assert writer.read_payload() == ("",)*14


@pytest.mark.parametrize("bad", [["wrong"]*14, list(reversed(QUOTATION_COLUMNS)), []])
def test_missing_or_shifted_schema_is_shared_failure_before_write(bad):
    writer, values = adapter()
    values.headers = bad
    with pytest.raises(QuotationInputUnavailable):
        writer.validate_schema()
    assert not any(kind == "update" for kind, _ in values.calls)


@pytest.mark.parametrize("status", [400, 401, 403, 404, 429, 500, 503])
def test_actual_api_status_classification_distinguishes_shared_failure(status):
    writer, values = adapter()
    error = RuntimeError("private provider text")
    error.resp = SimpleNamespace(status=status)
    values.write_error = error
    with pytest.raises(QuotationInputUnavailable) as raised:
        writer.write_payload(RAW)
    assert "private" not in str(raised.value)


def test_targeted_write_and_readback_failures_are_row_attempts():
    writer, values = adapter()
    values.write_error = TimeoutError("private details")
    with pytest.raises(QuotationInputAttemptFailed, match="QUOTE_INPUT_WRITE_FAILED"):
        writer.write_payload(RAW)
    values.payload = [123] + [""]*13
    with pytest.raises(QuotationInputAttemptFailed, match="QUOTE_INPUT_READBACK_MISMATCH"):
        writer.read_payload()


@pytest.mark.parametrize("changes", [{"input_row": 4}, {"first_column": 0}, {"gid": "unknown"},
                                     {"worksheet": WorksheetIdentity("fake-sheet", "wrong")}, {"input_row": True}])
def test_geometry_is_explicit_and_never_guessed(changes):
    with pytest.raises(QuotationInputUnavailable):
        location(**changes)


def test_configured_column_range_crosses_z_correctly_without_magic_a1():
    target = location(first_column=26)
    assert target.input_range == "'报价输入'!Z7:AM7"
    assert target.url == "https://docs.google.com/spreadsheets/d/fake-sheet/edit#gid=27"


def test_correct_title_only_and_old_name_is_rejected():
    assert location().worksheet.worksheet == "报价输入"
    with pytest.raises(QuotationInputUnavailable, match="QUOTE_INPUT_LOCATION_INVALID"):
        location(worksheet=WorksheetIdentity("fake-sheet", "报价输入子表"))


def test_direct_write_validates_minimal_metadata_then_headers_before_raw_update():
    writer, values = adapter()
    writer.write_payload(RAW)
    assert [kind for kind, _ in values.calls] == ["metadata", "get", "update"]
    assert values.calls[0][1] == {
        "spreadsheetId": "fake-sheet", "fields": "sheets.properties(sheetId,title)",
        "includeGridData": False,
    }
    assert values.calls[1][1]["range"] == "'报价输入'!C4:P4"
    values.metadata["sheets"][0]["properties"]["sheetId"] = 99
    with pytest.raises(QuotationInputUnavailable):
        writer.write_payload(RAW)
    assert sum(kind == "update" for kind, _ in values.calls) == 1


def test_zero_is_a_valid_sheet_id_and_requires_exact_gid_text():
    writer, values = adapter(gid="0")
    values.metadata["sheets"][0]["properties"]["sheetId"] = 0
    writer.validate_schema()
    writer, values = adapter(gid="027")
    with pytest.raises(QuotationInputUnavailable):
        writer.validate_schema()
