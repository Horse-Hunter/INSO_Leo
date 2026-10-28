"""Automatic customer-quoted age gate; all dates are explicit proxies, no I/O."""
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from src.sheets.tp_brief import bind_brief_source

SHANGHAI = ZoneInfo("Asia/Shanghai")


def age_reason(value, now):
    """Inclusive rolling timestamps or Shanghai calendar days; never guess a zone."""
    if not isinstance(now, datetime) or now.tzinfo is None:
        return "QUOTE_AGE_UNVERIFIED"
    local = now.astimezone(SHANGHAI)
    if isinstance(value, datetime):
        if value.tzinfo is None or value > now:
            return "QUOTE_AGE_UNVERIFIED"
        eligible = value.astimezone(UTC) >= now.astimezone(UTC) - timedelta(days=7)
    elif type(value) is date:
        if value > local.date():
            return "QUOTE_AGE_UNVERIFIED"
        eligible = value >= local.date() - timedelta(days=7)
    else:
        return "QUOTE_AGE_UNVERIFIED"
    return None if eligible else "QUOTE_AGE_EXPIRED"


def quotation_age_date(candidate, current_row, brief_lines, intake_at):
    """Only a unique canonical source binding can use a cached Brief inquiry day.

    No exact customer-send timestamp exists in the current event schema.
    Never use updated_at or supplier quote dates as a replacement.
    """
    matches = [line for line in brief_lines
               if line.get("sheet") == candidate.record_identity.worksheet.worksheet
               and line.get("sheet_row") == str(current_row.row_position)]
    if len(matches) == 1:
        try:
            bind_brief_source(matches[0], (current_row,))
        except ValueError:
            pass  # Not a verified Brief identity: only the exact local ID may fall back.
        else:
            try:
                return date.fromisoformat(matches[0].get("rfq_date")), "RFQ_DATE_PROXY"
            except (ValueError, TypeError):
                return None, "RFQ_DATE_PROXY"  # Malformed selected date cannot become recent.
    return intake_at(), "LOCAL_INTAKE_PROXY"
