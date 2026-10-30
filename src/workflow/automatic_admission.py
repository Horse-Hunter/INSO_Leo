"""One calendar/identity admission contract for all automatic business paths."""
from calendar import monthrange
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from src.sheets.tp_brief import bind_brief_source

SHANGHAI = timezone(timedelta(hours=8))


def inquiry_day(value):
    if isinstance(value, datetime):
        return value.astimezone(SHANGHAI).date() if value.tzinfo else None
    if type(value) is date:
        return value
    if not isinstance(value, str) or not value.strip():
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(value.strip(), fmt).date()  # noqa: DTZ007 - calendar day only
        except ValueError:
            pass
    try:
        parsed = datetime.fromisoformat(value)
        return inquiry_day(parsed)
    except ValueError:
        return None


def age_reason(value, now, *, module="quotation"):
    if not isinstance(now, datetime) or now.tzinfo is None:
        return "QUOTE_AGE_UNVERIFIED"
    if isinstance(value, datetime) and (value.tzinfo is None or value > now):
        return "QUOTE_AGE_UNVERIFIED"
    today = now.astimezone(SHANGHAI).date()
    day = inquiry_day(value)
    if day is None or day > today:
        return "QUOTE_AGE_UNVERIFIED"
    if module in {"inquiry", "quotation"}:
        cutoff = today-timedelta(days=7)
    else:  # TP and every subsequent personalized requirement use this contract.
        year, month = (today.year-1, 12) if today.month == 1 else (today.year, today.month-1)
        cutoff = date(year, month, min(today.day, monthrange(year, month)[1]))
    return None if day >= cutoff else "QUOTE_AGE_EXPIRED"


def source_date(identity, row, brief_lines, intake_at=lambda: None):
    """No updated_at, guessed MPN or newly-created queue date fallback."""
    matches = [line for line in brief_lines
               if line.get("sheet") == identity.worksheet.worksheet
               and line.get("sheet_row").isdecimal()
               and int(line.get("sheet_row")) == row.row_position]
    if matches:
        if len(matches) != 1:
            return None, "SOURCE_DATE_CONFLICT"
        try:
            bind_brief_source(matches[0], (row,))
        except ValueError:
            return None, "SOURCE_DATE_CONFLICT"
        return inquiry_day(matches[0].get("rfq_date")), "RFQ_DATE"
    if identity.worksheet.worksheet.casefold() == "shahab":
        return inquiry_day(row.cells.get("A")), "SOURCE_RFQ_DATE"
    return intake_at(), "LOCAL_INTAKE_APPROXIMATION"


@dataclass(frozen=True)
class Admission:
    allowed: bool
    reason: str | None
    date_source: str


def admit(identity, row, brief_lines, intake_at, *, now, module, manual=False):
    from src.sheets.pending import identify_worksheet_row
    from src.sheets.worksheet_schema import worksheet_schema
    observed = identify_worksheet_row(identity.worksheet, row)
    before, after = identity.identifying_snapshot, observed.identifying_snapshot
    if any(getattr(before, field) != getattr(after, field) for field in ("model", "brand", "quantity")):
        return Admission(False, "SOURCE_IDENTITY_CONFLICT", "UNVERIFIED")
    status = row.cells.get(worksheet_schema(identity.worksheet.worksheet).status_column)
    if (module == "inquiry" and status != "未发" or
            module == "quotation" and status not in {"发给采购", "采购已报价", "已报价给客户"}):
        return Admission(False, "SOURCE_STATUS_EXCLUDED", "UNVERIFIED")
    if manual:
        return Admission(True, None, "OWNER_SINGLE_ORDER")
    value, origin = source_date(identity, row, brief_lines, intake_at)
    reason = age_reason(value, now, module=module)
    return Admission(reason is None, reason, origin)


def binding_key(identity):
    """Opaque binding for durable incident revalidation, never a new order ID."""
    import json
    from dataclasses import asdict
    from hashlib import sha256
    return sha256(json.dumps(asdict(identity), sort_keys=True, ensure_ascii=False).encode()).hexdigest()
