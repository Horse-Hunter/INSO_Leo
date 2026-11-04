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


def source_date(identity, row, brief_lines, intake_at=lambda: None, *, recorded_source_date=None, as_of=None, conservative_intake=True):
    """Bind existing original dates; never mint today's date for an old row."""
    matches = [line for line in brief_lines
               if line.get("sheet") == identity.worksheet.worksheet
               and line.get("sheet_row").isdecimal()
               and int(line.get("sheet_row")) == row.row_position]
    source = None
    origin = None
    if matches:
        if len(matches) != 1:
            return None, "SOURCE_DATE_CONFLICT"
        try:
            bind_brief_source(matches[0], (row,))
        except ValueError:
            return None, "SOURCE_DATE_CONFLICT"
        raw = matches[0].get("rfq_date")
        if raw not in (None, ""):
            source, origin = raw, "RFQ_DATE"
        else:
            origin = "RFQ_DATE"  # Blank is missing, malformed is never missing.
    elif identity.worksheet.worksheet.casefold() == "shahab":
        source, origin = row.cells.get("A"), "SOURCE_RFQ_DATE"
        if source in (None, ""):
            return None, origin
    if source is None and identity.worksheet.worksheet == "2026":
        value = getattr(row, "source_order_date", None)
        if (row.cells.get("A") == "未发" or recorded_source_date is not None) and value not in (None, ""):
            source, origin = value, "SOURCE_ORDER_DATE"
    if matches and source is None and recorded_source_date is None:
        return None, "RFQ_DATE"
    # Existing explicit RFQ dates remain authoritative over a local intake
    # approximation. Preserve their parsed value so the original age gate rejects
    # malformed/future dates rather than replacing them with a recent intake.
    if source is not None and origin in {"RFQ_DATE", "SOURCE_RFQ_DATE"}:
        if recorded_source_date is None:
            return inquiry_day(source), origin
        day = inquiry_day(source)
        original_day = inquiry_day(recorded_source_date)
        if day is None or as_of is not None and day > as_of.astimezone(SHANGHAI).date():
            return inquiry_day(source), origin
        if original_day is None:
            return None, "SOURCE_DATE_CONFLICT"
        return (original_day, "SOURCE_ORDER_DATE") if original_day < day else (day, origin)
    candidates = []
    for raw, kind in ((source, origin), (recorded_source_date, "SOURCE_ORDER_DATE")):
        if raw is None or raw == "":
            continue
        day = inquiry_day(raw)
        if day is None or as_of is not None and day > as_of.astimezone(SHANGHAI).date():
            return None, "SOURCE_DATE_CONFLICT"
        candidates.append((day, kind, day))
    intake = intake_at()
    local_day = inquiry_day(intake)
    if local_day is not None and as_of is not None and local_day > as_of.astimezone(SHANGHAI).date():
        return None, "SOURCE_DATE_CONFLICT"
    if local_day is not None:
        candidates.append((local_day, "LOCAL_INTAKE_APPROXIMATION", intake))
    if candidates:
        _, kind, value = (min(candidates, key=lambda candidate: candidate[0])
                          if conservative_intake else candidates[0])
        return value, kind
    return None, origin or "LOCAL_INTAKE_APPROXIMATION"


@dataclass(frozen=True)
class Admission:
    allowed: bool
    reason: str | None
    date_source: str
    order_date: date | None = None


def admit(identity, row, brief_lines, intake_at, *, now, module, manual=False, recorded_source_date=None):
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
    value, origin = source_date(identity, row, brief_lines, intake_at, recorded_source_date=recorded_source_date, as_of=now)
    reason = age_reason(value, now, module=module)
    return Admission(reason is None, reason, origin, inquiry_day(value) if reason is None and origin == "SOURCE_ORDER_DATE" else None)


def binding_key(identity):
    """Opaque binding for durable incident revalidation, never a new order ID."""
    import json
    from dataclasses import asdict
    from hashlib import sha256
    return sha256(json.dumps(asdict(identity), sort_keys=True, ensure_ascii=False).encode()).hexdigest()
