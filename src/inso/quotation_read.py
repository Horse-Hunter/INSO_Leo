"""V1.3 raw quotation retrieval over the canonical settled lower-history query."""
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from src.core.mpn import inso_lookup_query, lookup_mpn_matches, lookup_mpn_prefix

from .duplicate_history import (
    DuplicateHistoryFailure,
    InsoDuplicateHistoryError,
    PlaywrightProcurementHistoryPage,
    canonical_history_mpn,
    parse_inso_timestamp,
)
from .session import InsoOperationAccess, SecurityViolation

try:
    SHANGHAI = ZoneInfo("Asia/Shanghai")
except ZoneInfoNotFoundError:
    # The verified contemporary ERP timestamp contract is UTC+08, also used by
    # parse_inso_timestamp. Windows may lack IANA data; never guess local time
    # or add a new dependency just to consume this existing INSO contract.
    SHANGHAI = timezone(timedelta(hours=8), "Asia/Shanghai")
QUOTATION_COLUMNS = (
    "日期", "型号", "品牌", "数量", "币种", "供方税点", "报价", "供方未税价",
    "平台数量", "批号", "货期", "备注", "备注2", "制单人",
)


@dataclass(frozen=True, slots=True)
class V13QuotationRow:
    """Display text is immutable; parsed time never replaces the date text."""
    quote_record_time: datetime
    payload: tuple[str, ...]

    def __post_init__(self):
        if self.quote_record_time.utcoffset() is None:
            raise ValueError("quotation time must be aware")
        if len(self.payload) != 14 or any(not isinstance(value, str) for value in self.payload):
            raise ValueError("quotation display must have fourteen text cells")


class QuotationPriceUnavailable(RuntimeError):
    """A closed comparison failure, never raw quotation/provider text."""
    def __init__(self, code):
        super().__init__(code)
        self.code = code


def select_recent_lowest(
    records: Iterable[V13QuotationRow], *, queried_mpn: str, now: datetime,
    currency_rate: Callable[[str], Decimal] | None = None,
) -> V13QuotationRow | None:
    """Owner prefix MPN, inclusive 72h; lowest RMB-equivalent supplier net price, newest on ties.

    Conversion only chooses a row; all fourteen display strings remain untouched.
    Blank/unparseable/nonfinite/negative net prices are skipped.
    Positive prices compete first; if only zero prices remain, newest zero wins.
    Unknown currencies or missing FX never silently compete as raw numeric prices.
    """
    if now.utcoffset() is None:
        raise ValueError("query clock must be aware")
    target = canonical_history_mpn(queried_mpn)
    if not target or not lookup_mpn_prefix(queried_mpn):
        raise ValueError("query MPN is required")
    end = now.astimezone(SHANGHAI)
    cutoff = end - timedelta(hours=72)
    eligible, zero_rows = [], []
    rates = {"RMB": Decimal(1)}
    currencies = {"RMB": "RMB", "CNY": "RMB", "人民币": "RMB", "CNY人民币": "RMB",
                  "USD": "USD", "美元": "USD", "HKD": "HKD", "港币": "HKD", "HKD港币": "HKD"}
    for row in records:
        if (not lookup_mpn_matches(queried_mpn, row.payload[1])
                or not cutoff <= row.quote_record_time.astimezone(SHANGHAI) <= end):
            continue
        try:
            price = Decimal(row.payload[7].strip().replace(",", ""))
        except InvalidOperation:
            continue
        if not price.is_finite() or price < 0:
            continue
        if price == 0:
            zero_rows.append(row)
            continue
        currency = currencies.get(row.payload[4].strip().upper())
        if currency is None:
            raise QuotationPriceUnavailable("QUOTE_CURRENCY_UNSUPPORTED")
        if currency not in rates:
            if currency_rate is None:
                raise QuotationPriceUnavailable("QUOTE_FX_REQUIRED")
            rate = currency_rate(currency)
            if not isinstance(rate, Decimal) or not rate.is_finite() or rate <= 0:
                raise QuotationPriceUnavailable("QUOTE_FX_INVALID")
            rates[currency] = rate
        eligible.append((price * rates[currency], row))
    if not eligible:
        return max(zero_rows, key=lambda row: row.quote_record_time, default=None)
    lowest = min(price for price, _ in eligible)
    return max((row for price, row in eligible if price == lowest),
               key=lambda row: row.quote_record_time)


class InsoQuotationAuthenticationError(SecurityViolation):
    """Immediate shared stop; caller must retain the human-needed tab."""


def capture_quotation_page(frame: object, rows: list[dict]) -> list[dict]:
    """Read exact labelled contiguous display cells on this settled page.

    Map observed headers to their data-field cells; do not guess unverified JSON
    keys or substitute API numbers for the displayed text. Missing structure
    differs from a present empty cell. No business content is validated.
    """
    captured = frame.evaluate(
        """expected => {
            const panel = document.querySelector('#tabs_b_panel_2');
            const headers = panel ? [...panel.querySelectorAll('th[data-field]')] : [];
            const labels = headers.map(h => h.innerText.trim());
            const start = labels.indexOf(expected.columns[0]);
            if (start < 0 || expected.columns.some((label, i) =>
                labels[start + i] !== label || labels.filter(x => x === label).length !== 1))
                return null;
            const fields = headers.slice(start, start + expected.columns.length)
                .map(h => h.getAttribute('data-field'));
            if (new Set(fields).size !== fields.length || fields.some(f => !f)) return null;
            const grid = panel.querySelector('#_id_tabs_b_2');
            const result = grid ? [...grid.querySelectorAll('tr[id$="_Main"]')] : [];
            if (result.length !== expected.ids.length) return null;
            return result.map((row, i) => {
                if (row.id !== expected.ids[i] + '_Main') return null;
                return fields.map(field => {
                    const cells = [...row.querySelectorAll('td[data-field]')]
                        .filter(td => td.getAttribute('data-field') === field);
                    if (cells.length !== 1) return null;
                    const display = cells[0].querySelector('.layui-table-cell') || cells[0];
                    return display.textContent;
                });
            });
        }""",
        {"columns": list(QUOTATION_COLUMNS), "ids": [str(row["id"]) for row in rows]},
    )
    if not isinstance(captured, list) or len(captured) != len(rows):
        raise InsoDuplicateHistoryError(DuplicateHistoryFailure.RESULT_ROW_UNREADABLE)
    result = []
    for row, values in zip(rows, captured, strict=True):
        if (not isinstance(values, list) or len(values) != 14
                or any(not isinstance(value, str) for value in values)
                or canonical_history_mpn(values[1]) != canonical_history_mpn(row.get("PartNo"))):
            raise InsoDuplicateHistoryError(DuplicateHistoryFailure.RESULT_ROW_UNREADABLE)
        result.append({**row, "quotation_display": tuple(values)})
    return result


class InsoQuotationReader:
    """No quantity/brand/price validation; no Save/Send capability."""
    def __init__(self, *, page_factory: Callable = PlaywrightProcurementHistoryPage):
        self._page_factory = page_factory

    def read(self, access: InsoOperationAccess, mpn: str) -> tuple[V13QuotationRow, ...]:
        target = canonical_history_mpn(mpn)
        if not target or not lookup_mpn_prefix(mpn):
            raise InsoDuplicateHistoryError(DuplicateHistoryFailure.RECORD_FIELDS_INVALID)
        try:
            with access.operation_page() as operation:
                payload = self._page_factory(operation.shell_frame).query_exact_response(
                    inso_lookup_query(mpn), capture_page=capture_quotation_page,
                )
            rows = payload.get("rows")
            if not isinstance(rows, list):
                raise TypeError
            result = []
            for row in rows:
                if not isinstance(row, dict):
                    raise TypeError
                # Apply the same Owner rule before reading and before price selection.
                if not lookup_mpn_matches(mpn, row.get("PartNo")):
                    continue
                raw = row.get("quotation_display")
                if not isinstance(raw, tuple):
                    raise TypeError
                result.append(V13QuotationRow(parse_inso_timestamp(raw[0]), raw))
            return tuple(result)
        except SecurityViolation:
            raise InsoQuotationAuthenticationError("INSO_AUTHENTICATION_REQUIRED") from None
        except InsoDuplicateHistoryError:
            raise
        except Exception:  # noqa: BLE001 - sanitized incomplete query, never empty
            raise InsoDuplicateHistoryError(DuplicateHistoryFailure.RESULT_ROW_UNREADABLE) from None
