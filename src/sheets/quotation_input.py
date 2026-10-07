"""Narrow raw fourteen-cell quotation input adapter over the existing Sheets API."""
import re
from dataclasses import dataclass

from .google_oauth import GoogleSheetsAuthorizationError
from .pending import WorksheetIdentity


class QuotationInputUnavailable(RuntimeError):
    """Shared auth/sheet/schema/API failure; not a row write failure."""
    def __init__(self, reason="QUOTE_INPUT_INFRASTRUCTURE_UNAVAILABLE"):
        super().__init__(reason)
        self.reason = reason


class QuotationInputAttemptFailed(RuntimeError):
    """Targeted attempt failed; sanitized and retryable within this row."""


@dataclass(frozen=True, slots=True)
class QuotationInputLocation:
    worksheet: WorksheetIdentity
    header_row: int
    input_row: int
    first_column: int
    gid: str

    def __post_init__(self):
        if (not isinstance(self.worksheet, WorksheetIdentity) or self.worksheet.worksheet != "报价输入"
                or not isinstance(self.worksheet.spreadsheet, str)
                or not re.fullmatch(r"[A-Za-z0-9_-]+", self.worksheet.spreadsheet)
                or any(isinstance(value, bool) or not isinstance(value, int) or value < 1
                       for value in (self.header_row, self.input_row, self.first_column))
                or self.input_row <= self.header_row
                or not isinstance(self.gid, str) or not self.gid.isdecimal()):
            raise QuotationInputUnavailable("QUOTE_INPUT_LOCATION_INVALID")

    def range_at(self, row: int) -> str:
        return (f"'{self.worksheet.worksheet}'!{_column(self.first_column)}{row}:"
                f"{_column(self.first_column + 13)}{row}")

    @property
    def input_range(self):
        return self.range_at(self.input_row)

    @property
    def header_range(self):
        return self.range_at(self.header_row)

    @property
    def url(self):
        return f"https://docs.google.com/spreadsheets/d/{self.worksheet.spreadsheet}/edit#gid={self.gid}"


def _column(number):
    result = ""
    while number:
        number, remainder = divmod(number - 1, 26)
        result = chr(65 + remainder) + result
    return result


def _shared_error(error):
    return (isinstance(error, GoogleSheetsAuthorizationError)
            or type(error).__name__ in {"RefreshError", "DefaultCredentialsError"}
            or getattr(getattr(error, "resp", None), "status", None) in {400, 401, 403, 404, 429, 500, 502, 503, 504})


def _row_values(response):
    if not isinstance(response, dict):
        raise QuotationInputUnavailable("QUOTE_INPUT_RESPONSE_INVALID")
    rows = response.get("values", [])
    if not isinstance(rows, list) or len(rows) > 1 or any(not isinstance(row, list) for row in rows):
        raise QuotationInputUnavailable("QUOTE_INPUT_RESPONSE_INVALID")
    values = rows[0] if rows else []
    if len(values) > 14 or any(not isinstance(value, str) for value in values):
        # A RAW string must read as a string; never coerce numbers/dates back to text.
        raise QuotationInputAttemptFailed("QUOTE_INPUT_READBACK_MISMATCH")
    return tuple(values) + ("",) * (14 - len(values))


class GoogleQuotationInput:
    """Only this configured input row can be written; no source-status setter."""
    def __init__(self, service, location: QuotationInputLocation, *, expected_columns: tuple[str, ...]):
        if (not isinstance(location, QuotationInputLocation) or not isinstance(expected_columns, tuple)
                or len(expected_columns) != 14 or any(not isinstance(column, str) for column in expected_columns)
                or len(set(expected_columns)) != 14):
            raise QuotationInputUnavailable("QUOTE_INPUT_SCHEMA_CONTRACT_INVALID")
        self.location, self.worksheet = location, location.worksheet
        self._service, self._columns = service, expected_columns

    def validate_schema(self):
        self.validate_location_binding()
        try:
            values = self._get(self.location.header_range)
            if _row_values(values) != self._columns:
                raise QuotationInputUnavailable("QUOTE_INPUT_SCHEMA_MISMATCH")
        except QuotationInputUnavailable:
            raise
        except Exception:  # noqa: BLE001 - shared schema/read boundary
            raise QuotationInputUnavailable("QUOTE_INPUT_SCHEMA_UNAVAILABLE") from None

    def validate_location_binding(self):
        """Prove the API title and configured UI gid identify the same sheet."""
        try:
            response = self._service.spreadsheets().get(
                spreadsheetId=self.worksheet.spreadsheet,
                fields="sheets.properties(sheetId,title)", includeGridData=False,
            ).execute()
        except Exception:  # noqa: BLE001 - metadata is always a shared boundary
            raise QuotationInputUnavailable("QUOTE_INPUT_METADATA_UNAVAILABLE") from None
        if not isinstance(response, dict) or not isinstance(response.get("sheets"), list):
            raise QuotationInputUnavailable("QUOTE_INPUT_METADATA_INVALID")
        matches = []
        for sheet in response["sheets"]:
            properties = sheet.get("properties") if isinstance(sheet, dict) else None
            if not isinstance(properties, dict):
                raise QuotationInputUnavailable("QUOTE_INPUT_METADATA_INVALID")
            title, sheet_id = properties.get("title"), properties.get("sheetId")
            if (not isinstance(title, str) or isinstance(sheet_id, bool)
                    or not isinstance(sheet_id, int) or sheet_id < 0):
                raise QuotationInputUnavailable("QUOTE_INPUT_METADATA_INVALID")
            if title == self.worksheet.worksheet:
                matches.append(sheet_id)
        if len(matches) != 1 or str(matches[0]) != self.location.gid:
            raise QuotationInputUnavailable("QUOTE_INPUT_LOCATION_BINDING_MISMATCH")

    def write_payload(self, payload: tuple[str, ...]):
        if len(payload) != 14 or any(not isinstance(value, str) for value in payload):
            raise QuotationInputAttemptFailed("QUOTE_INPUT_WRITE_FAILED")
        self.validate_schema()
        try:
            self._service.spreadsheets().values().update(
                spreadsheetId=self.worksheet.spreadsheet, range=self.location.input_range,
                valueInputOption="RAW", body={"majorDimension": "ROWS", "values": [list(payload)]},
            ).execute()
        except Exception as exc:  # noqa: BLE001 - classify only targeted API operation
            if _shared_error(exc):
                raise QuotationInputUnavailable() from None
            raise QuotationInputAttemptFailed("QUOTE_INPUT_WRITE_FAILED") from None

    def read_payload(self):
        try:
            return _row_values(self._get(self.location.input_range))
        except (QuotationInputUnavailable, QuotationInputAttemptFailed):
            raise
        except Exception as exc:  # noqa: BLE001 - targeted range failure differs from shared API
            if _shared_error(exc):
                raise QuotationInputUnavailable() from None
            raise QuotationInputAttemptFailed("QUOTE_INPUT_READBACK_MISMATCH") from None

    def _get(self, range_name):
        return self._service.spreadsheets().values().get(
            spreadsheetId=self.worksheet.spreadsheet, range=range_name,
            majorDimension="ROWS", valueRenderOption="UNFORMATTED_VALUE",
        ).execute()
