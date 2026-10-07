"""V1.3 raw quotation retrieval over the canonical settled lower-history query."""
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

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
    "日期", "型号", "品牌", "数量", "币种", "供方返点", "报价", "供方未税价",
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


def select_recent_latest(
    records: Iterable[V13QuotationRow], *, queried_mpn: str, now: datetime,
) -> V13QuotationRow | None:
    """Inclusive rolling 72h in Shanghai; exact MPN, latest time only.

    Equal timestamps retain the first fully captured row: both are equally
    latest; no price/quantity/brand/creator tie-breaking business rule is added.
    """
    if now.utcoffset() is None:
        raise ValueError("query clock must be aware")
    target = canonical_history_mpn(queried_mpn)
    if not target:
        raise ValueError("query MPN is required")
    end = now.astimezone(SHANGHAI)
    cutoff = end - timedelta(hours=72)
    eligible = [row for row in records
                if canonical_history_mpn(row.payload[1]) == target
                and cutoff <= row.quote_record_time.astimezone(SHANGHAI) <= end]
    return max(eligible, key=lambda row: row.quote_record_time, default=None)


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
        if not target:
            raise InsoDuplicateHistoryError(DuplicateHistoryFailure.RECORD_FIELDS_INVALID)
        try:
            with access.operation_page() as operation:
                payload = self._page_factory(operation.shell_frame).query_exact_response(
                    target, capture_page=capture_quotation_page,
                )
            rows = payload.get("rows")
            if not isinstance(rows, list):
                raise TypeError
            result = []
            for row in rows:
                if not isinstance(row, dict):
                    raise TypeError
                # Fuzzy native matches never compete with exact queried MPN.
                if canonical_history_mpn(row.get("PartNo")) != target:
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
