"""Read-only RFQ_BRIEF contract; explicit source anchor, never a V1 inquiry ID."""
import re
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal

from .google_reader import execute_google_read
from .pending import WorksheetIdentity, usable_brand
from .worksheet_schema import worksheet_schema

BRIEF_TITLE = "RFQ_BRIEF"
BRIEF_HEADERS = (
    "rfq_line_id", "sheet", "sheet_row", "rfq_date", "mpn", "mfr", "qty",
    "target_price", "target_price_source", "status", "suggested_sourcing_mode",
    "customer_type", "decision_window", "min_datecode", "full_package",
    "customer_default_requirements", "updated_at",
)


class TpLocalError(ValueError):
    """An explicitly identified TP-only failure; never a shared safety fault."""


def quantity_value(value):
    if isinstance(value, bool):
        raise ValueError("TP_QUANTITY_INVALID")  # noqa: TRY004 - row-level invalid input
    text = str(value).strip()
    if not re.fullmatch(r"(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.0+)?", text):
        raise ValueError("TP_QUANTITY_INVALID")
    number = int(Decimal(text.replace(",", "")))
    if number <= 0:
        raise ValueError("TP_QUANTITY_INVALID")
    return number


def parse_target_price(value):
    """Explicit USD/RMB currency required; never infer missing currency or zero."""
    if not isinstance(value, str) or not value.strip():
        return None
    number = r"((?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d+)?)"
    currency = r"(USD|US\$|\$|RMB|CNY|¥|￥)"
    text = value.strip().upper()
    match = re.fullmatch(number + r"\s*" + currency, text)
    if match:
        raw, unit = match.groups()
    else:
        match = re.fullmatch(currency + r"\s*" + number, text)
        if not match:
            raise ValueError("TP_PRICE_INVALID")
        unit, raw = match.groups()
    price = Decimal(raw.replace(",", ""))
    if not price.is_finite() or price <= 0:
        raise ValueError("TP_PRICE_INVALID")
    return price, "USD" if unit in {"USD", "US$", "$"} else "RMB"


@dataclass(frozen=True)
class BriefLine:
    brief_row: int
    values: tuple[str, ...]

    def get(self, key):
        return self.values[BRIEF_HEADERS.index(key)]


@dataclass(frozen=True)
class TpOrder:
    spreadsheet: str
    sheet: str
    row: int
    mpn: str
    brand: str | None
    quantity: int
    customer: str | None
    rfq_date: str
    target_raw: str
    target_price: Decimal
    currency: str


class BriefReader:
    def __init__(self, service, *, retry_wait=lambda _seconds: False):
        self.service, self.retry_wait = service, retry_wait

    def read_discovery(self, spreadsheet):
        return self._read(spreadsheet, discovery=True)

    def read(self, spreadsheet):
        return self._read(spreadsheet, discovery=False)

    def _read(self, spreadsheet, *, discovery):
        read = getattr(self.service, "read_brief_discovery", self.service.read_brief) if discovery else self.service.read_brief
        response = execute_google_read(lambda: read(spreadsheet),
                                       retry_wait=self.retry_wait)
        rows = response.get("values", []) if isinstance(response, Mapping) else None
        if (not isinstance(rows, (list, tuple)) or not rows
                or not isinstance(rows[0], (list, tuple)) or tuple(rows[0]) != BRIEF_HEADERS):
            raise TpLocalError("TP_BRIEF_SCHEMA_UNAVAILABLE")
        result = []
        for position, row in enumerate(rows[1:], 2):
            if not isinstance(row, (list, tuple)) or len(row) > 17 or any(not isinstance(v, str) for v in row):
                raise TpLocalError("TP_BRIEF_SCHEMA_UNAVAILABLE")
            if any(v.strip() for v in row):
                result.append(BriefLine(position, tuple(row) + ("",) * (17-len(row))))
        return tuple(result)


def bind_tp_order(line, spreadsheet, source_rows):
    """Fixed physical anchor plus key corroboration; no global MPN guessing."""
    sheet, pointer = line.get("sheet"), line.get("sheet_row")
    if sheet not in {"2026", "SHAHAB"} or not pointer.isdecimal() or int(pointer) < 1:
        raise ValueError("TP_SOURCE_UNMATCHED")
    candidates = [r for r in source_rows if r.row_position == int(pointer)]
    if len(candidates) != 1:
        raise ValueError("TP_SOURCE_AMBIGUOUS" if candidates else "TP_SOURCE_UNMATCHED")
    schema = worksheet_schema(sheet)
    row = candidates[0].cells
    if not line.get("mpn").strip() or row.get(schema.model_column) != line.get("mpn"):
        raise ValueError("TP_SOURCE_MODEL_CONFLICT")
    quantity = quantity_value(line.get("qty"))
    if quantity_value(row.get(schema.quantity_column)) != quantity:
        raise ValueError("TP_SOURCE_QUANTITY_CONFLICT")
    brief_brand, source_brand = usable_brand(line.get("mfr")), usable_brand(row.get(schema.brand_column))
    if brief_brand and brief_brand != source_brand:
        raise ValueError("TP_SOURCE_BRAND_CONFLICT")
    if sheet == "SHAHAB":
        from datetime import datetime
        def day(text):
            for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y-%m-%d %H:%M:%S"):
                try:
                    return datetime.strptime(str(text).strip(), fmt).date()  # noqa: DTZ007 - calendar day, not instant
                except ValueError:
                    pass
            raise ValueError("TP_SOURCE_DATE_UNCONFIRMED")
        if day(row.get("A")) != day(line.get("rfq_date")):
            raise ValueError("TP_SOURCE_DATE_CONFLICT")
    target = parse_target_price(line.get("target_price"))
    if target is None:
        raise ValueError("TP_PRICE_EMPTY")
    customer = schema.fixed_customer_name
    if schema.customer_name_column:
        customer = row.get(schema.customer_name_column)
    return TpOrder(spreadsheet, sheet, int(pointer), line.get("mpn"), source_brand,
                   quantity, customer, line.get("rfq_date"), line.get("target_price"), *target)


def source_worksheet(spreadsheet, line):
    return WorksheetIdentity(spreadsheet, line.get("sheet"))
