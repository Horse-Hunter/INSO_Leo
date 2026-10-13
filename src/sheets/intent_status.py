"""Guarded per-line quoted-to-customer -> intent order single-cell updates."""
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from .worksheet_schema import worksheet_schema

INTENT_STATUS = "意向订单"
QUOTED_STATUS = "已报价给客户"


@dataclass(frozen=True)
class IntentLine:
    model: str
    quantity: int


@dataclass(frozen=True)
class IntentResult:
    line: IntentLine
    success: bool
    reason: str


def _quantity(value):
    if isinstance(value, bool):
        return None
    try:
        number = Decimal(str(value).strip())
        return number if number.is_finite() and number > 0 else None
    except InvalidOperation:
        return None


def _matches(reader, worksheets, line):
    matches = []
    for worksheet in worksheets:
        schema = worksheet_schema(worksheet.worksheet)
        for row in reader.read_rows(worksheet):
            model = row.cells.get(schema.model_column)
            if (row.cells.get(schema.status_column) in {QUOTED_STATUS, INTENT_STATUS}
                    and isinstance(model, str) and model.strip() == line.model
                    and _quantity(row.cells.get(schema.quantity_column)) == line.quantity):
                matches.append((worksheet, row))
    return matches


def update_intent_statuses(reader, writer, worksheets, lines):
    """No guessing/retry: re-read both sheets before each write and verify it."""
    worksheets = tuple(worksheets)
    lines = tuple(dict.fromkeys(lines))
    results = []
    if len(worksheets) != 2 or len(set(worksheets)) != 2:
        return tuple(IntentResult(line, False, "CONFIGURATION_UNCONFIRMED") for line in lines)
    for line in lines:
        try:
            if not line.model or _quantity(line.quantity) is None:
                results.append(IntentResult(line, False, "LINE_UNCONFIRMED"))
                continue
            matches = _matches(reader, worksheets, line)
            if len(matches) != 1:
                results.append(IntentResult(line, False, "MATCH_NOT_UNIQUE"))
                continue
            worksheet, original = matches[0]
            fresh = _matches(reader, worksheets, line)
            if (len(fresh) != 1 or fresh[0][0] != worksheet
                    or fresh[0][1].row_position != original.row_position
                    or dict(fresh[0][1].cells) != dict(original.cells)):
                results.append(IntentResult(line, False, "SOURCE_CHANGED"))
                continue
            schema = worksheet_schema(worksheet.worksheet)
            if original.cells[schema.status_column] == INTENT_STATUS:
                results.append(IntentResult(line, True, "ALREADY_INTENT"))
                continue
            writer.write_intent_status(worksheet, original.row_position)
            confirmed = _matches(reader, worksheets, line)
            if (len(confirmed) != 1 or confirmed[0][0] != worksheet
                    or confirmed[0][1].row_position != original.row_position
                    or dict(confirmed[0][1].cells) != {**original.cells, schema.status_column: INTENT_STATUS}):
                results.append(IntentResult(line, False, "WRITE_UNCONFIRMED"))
                continue
            results.append(IntentResult(line, True, "UPDATED"))
        except Exception:  # noqa: BLE001 - no provider/customer data or blind write retry
            results.append(IntentResult(line, False, "SHEETS_UNAVAILABLE"))
    return tuple(results)
