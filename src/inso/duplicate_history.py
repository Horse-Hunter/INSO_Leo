"""Minimal read-only INSO duplicate-history adapter.

Reads the business-inquiry list (`YeWuXJ/List.aspx`) in exact model mode and
returns the matching historical records for the Workflow duplicate check. It is
read-only: it never saves, sends or mutates INSO data, and it owns no purchase,
notification or retry behaviour.

Only selectors verified during the 2026-09-26 read-only discovery are used; see
`docs/modules/INSO.md`. The result rows' field layout is still `UNKNOWN`, so the
per-record field extraction is an explicit injected seam
(:meth:`DuplicateHistoryPage.read_row_values`) instead of a guessed column
mapping. When a record cannot be opened or read safely, the adapter fails closed
with a typed error; it never guesses a value.

Business rules -- canonical MPN, the rolling inclusive 168h window, latest-record
selection and the equal-timestamp AMBIGUOUS rule -- are deliberately NOT
implemented here. This adapter returns raw records and the Workflow decision
layer applies those rules.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from enum import StrEnum
from typing import Protocol
from urllib.parse import urlsplit

from .session import InsoOperationAccess, SecurityViolation

# ---------------------------------------------------------------------------
# Verified read-only selectors (read-only discovery, 2026-09-26)
# ---------------------------------------------------------------------------

#: Business inquiry list path, observed live.
BUSINESS_INQUIRY_LIST_PATH = "/skins/etaoerp//InnerEnquiry/YeWuXJ/List.aspx"

#: Model query input; field selector ``#DetailField_text`` showed ``型号``.
MODEL_QUERY_INPUT = "#DetailFieldValue"
#: ``精确`` checkbox. The adapter only ever requests exact matching.
EXACT_MATCH_CHECKBOX = "#nolike"
#: ``查询`` button.
QUERY_BUTTON = "#select_btns"

#: Result row DOM ids are ``<digits>_Main``. The element tag is intentionally
#: not guessed; only the verified id suffix is used.
RESULT_ROW_ID = re.compile(r"^\d+_Main$")
RESULT_ROW_SELECTOR = "[id$='_Main']"

#: A detail link calls ``Bill_View_Open(<numeric>)``. The numeric argument is a
#: different identifier from the row DOM id and must never be substituted for it.
DETAIL_LINK_CALL = re.compile(r"Bill_View_Open\(\s*(\d+)\s*\)")
DETAIL_LINK_SELECTOR_TEMPLATE = "[onclick*='Bill_View_Open({argument})']"

#: ``BillID`` is the documented detail field name. ``#<FieldName>`` matches the
#: verified inputs on this page; confirm the selector on the live page before
#: enabling a live read, and override it through the constructor if it differs.
DETAIL_BILL_ID_SELECTOR = "#BillID"

#: INSO serves Asia/Shanghai timestamps without an offset.
_INSO_TIMEZONE = timezone(timedelta(hours=8))
_INSO_TIMESTAMP_PATTERNS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y/%m/%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y/%m/%d %H:%M",
    "%Y-%m-%d",
)


class DuplicateHistoryFailure(StrEnum):
    """Closed failure codes; a read failure is never a "not a duplicate"."""

    SESSION_LEASE_REQUIRED = "SESSION_LEASE_REQUIRED"
    HISTORY_LIST_UNAVAILABLE = "HISTORY_LIST_UNAVAILABLE"
    RESULT_ROW_UNREADABLE = "RESULT_ROW_UNREADABLE"
    RESULT_IDENTIFIER_AMBIGUOUS = "RESULT_IDENTIFIER_AMBIGUOUS"
    RECORD_FIELDS_UNAVAILABLE = "RECORD_FIELDS_UNAVAILABLE"
    RECORD_FIELDS_INVALID = "RECORD_FIELDS_INVALID"
    DETAIL_IDENTITY_MISMATCH = "DETAIL_IDENTITY_MISMATCH"


class InsoDuplicateHistoryError(RuntimeError):
    """Typed, sanitized read failure. It carries no page or provider text."""

    def __init__(self, code: DuplicateHistoryFailure, url: str | None = None) -> None:
        super().__init__(code.value)
        self.code = code
        self.url = url


# ---------------------------------------------------------------------------
# Values exchanged with the injected page capability
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class DuplicateHistoryRowValues:
    """Raw values displayed for one result row, exactly as they appear.

    The page implementation must NOT canonicalize or reinterpret them.
    """

    model: str
    quantity_text: str
    quoted_at_text: str


@dataclass(frozen=True, slots=True)
class DuplicateHistoryRecord:
    """One historical inquiry record read from INSO, with verified identity."""

    bill_id: str
    mpn: str
    quantity: int
    quoted_at: datetime
    creator: str | None = None
    inso_quote: Decimal | None = None
    currency: str | None = None

    def __post_init__(self) -> None:
        if not self.bill_id or not self.mpn:
            raise ValueError("record identity and model are required")
        if isinstance(self.quantity, bool) or not isinstance(self.quantity, int):
            raise TypeError("quantity must be an integer")
        if self.quantity <= 0:
            raise ValueError("quantity must be positive")
        if self.quoted_at.tzinfo is None:
            raise ValueError("quoted_at must be timezone-aware")


@dataclass(frozen=True, slots=True)
class DuplicateHistoryCapture:
    target_mpn: str
    records: tuple[DuplicateHistoryRecord, ...]
    url: str
    captured_at: datetime


@dataclass(frozen=True, slots=True)
class _ResultRow:
    """One result row: verified-shape identity plus its displayed values."""

    row_id: str
    bill_argument: str
    values: DuplicateHistoryRowValues


class DuplicateHistoryPage(Protocol):
    """Narrow read-only page capability.

    It exposes navigation and reading only. There is deliberately no save, send,
    submit or write method.
    """

    def goto(self, url: str) -> None: ...

    def set_text(self, selector: str, value: str) -> None: ...

    def ensure_checked(self, selector: str) -> None: ...

    def click(self, selector: str) -> None: ...

    def wait_for_query_settled(self, *, timeout_ms: int) -> None:
        """Block until the submitted search has finished.

        The grid's settled/no-row indicator is not yet verified
        (`docs/modules/INSO.md`), so the implementation owns that decision. It
        MUST raise when it cannot establish that the search finished; an empty
        result is only meaningful once this returns.
        """
        ...

    def wait_for(self, selector: str, *, timeout_ms: int) -> None: ...

    def attributes(self, selector: str, name: str) -> tuple[str | None, ...]: ...

    def html(self, selector: str) -> str | None: ...

    def read_row_values(self, row_id: str) -> DuplicateHistoryRowValues | None:
        """Return one row's displayed model/quantity/time, or ``None``.

        The concrete selectors for these three fields are not yet verified
        (`docs/modules/INSO.md`), so they are supplied by the composition root
        rather than guessed by this adapter. Keys, order and values must not be
        reinterpreted here.
        """
        ...


class InsoDuplicateHistoryReader:
    """Read the exact-model history for one MPN through a leased child page."""

    def __init__(
        self,
        *,
        list_url: str,
        operation_access: InsoOperationAccess
        | Callable[[], InsoOperationAccess]
        | None = None,
        timeout_ms: int = 45_000,
        detail_bill_id_selector: str = DETAIL_BILL_ID_SELECTOR,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        parsed = urlsplit(list_url)
        if parsed.scheme != "https" or not parsed.hostname:
            raise ValueError("INSO list_url must be HTTPS")
        self._list_url = list_url.rstrip("/")
        self._operation_access = operation_access
        self._timeout_ms = timeout_ms
        self._detail_bill_id_selector = detail_bill_id_selector
        self._clock = clock or (lambda: datetime.now(UTC))

    @property
    def list_url(self) -> str:
        return f"{self._list_url}{BUSINESS_INQUIRY_LIST_PATH}"

    def read(self, search_value: str) -> DuplicateHistoryCapture:
        """Search one exact model value and return its verified records.

        ``search_value`` is searched verbatim; the caller supplies the canonical
        MPN when it wants deterministic matching. An empty result returns an
        empty capture -- it is not by itself proof of "not a duplicate" for the
        Workflow layer, which owns that decision.
        """

        if not isinstance(search_value, str) or not search_value.strip():
            raise InsoDuplicateHistoryError(DuplicateHistoryFailure.RECORD_FIELDS_INVALID)
        target = search_value.strip()
        url = self.list_url
        access = self._resolve_access()
        try:
            with access.open_operation_page() as operation_page:
                page: DuplicateHistoryPage = operation_page.page  # type: ignore[assignment]
                rows = self._read_rows(page, target)
                records = tuple(
                    self._verify_and_build(page, target, row) for row in rows
                )
        except InsoDuplicateHistoryError:
            raise
        except SecurityViolation as exc:
            raise InsoDuplicateHistoryError(
                DuplicateHistoryFailure.SESSION_LEASE_REQUIRED, url
            ) from exc
        except Exception as exc:
            raise InsoDuplicateHistoryError(
                DuplicateHistoryFailure.HISTORY_LIST_UNAVAILABLE, url
            ) from exc
        return DuplicateHistoryCapture(target, records, url, self._clock())

    # -- internals ---------------------------------------------------------

    def _resolve_access(self) -> InsoOperationAccess:
        access = (
            self._operation_access()
            if callable(self._operation_access)
            else self._operation_access
        )
        if access is None:
            raise InsoDuplicateHistoryError(
                DuplicateHistoryFailure.SESSION_LEASE_REQUIRED, self.list_url
            )
        return access

    def _run_exact_query(self, page: DuplicateHistoryPage, target: str) -> None:
        page.goto(self.list_url)
        page.set_text(MODEL_QUERY_INPUT, target)
        page.ensure_checked(EXACT_MATCH_CHECKBOX)
        page.click(QUERY_BUTTON)
        page.wait_for_query_settled(timeout_ms=self._timeout_ms)

    def _read_rows(self, page: DuplicateHistoryPage, target: str) -> tuple[_ResultRow, ...]:
        self._run_exact_query(page, target)
        raw_ids = page.attributes(RESULT_ROW_SELECTOR, "id")
        row_ids = [
            value
            for value in raw_ids
            if isinstance(value, str) and RESULT_ROW_ID.match(value)
        ]
        if len(set(row_ids)) != len(row_ids):
            # Two rows cannot be told apart, so neither result is reliable.
            raise InsoDuplicateHistoryError(
                DuplicateHistoryFailure.RESULT_IDENTIFIER_AMBIGUOUS, self.list_url
            )
        rows: list[_ResultRow] = []
        for row_id in row_ids:
            row_html = page.html(f"#{row_id}")
            arguments = set(DETAIL_LINK_CALL.findall(row_html or ""))
            if not arguments:
                raise InsoDuplicateHistoryError(
                    DuplicateHistoryFailure.RESULT_ROW_UNREADABLE, self.list_url
                )
            if len(arguments) != 1:
                raise InsoDuplicateHistoryError(
                    DuplicateHistoryFailure.RESULT_IDENTIFIER_AMBIGUOUS, self.list_url
                )
            values = page.read_row_values(row_id)
            if values is None:
                raise InsoDuplicateHistoryError(
                    DuplicateHistoryFailure.RECORD_FIELDS_UNAVAILABLE, self.list_url
                )
            rows.append(_ResultRow(row_id, arguments.pop(), values))
        return tuple(rows)

    def _verify_and_build(
        self,
        page: DuplicateHistoryPage,
        target: str,
        row: _ResultRow,
    ) -> DuplicateHistoryRecord:
        """Confirm in this runtime that the opened detail is the linked record."""

        if not row.values.model.strip():
            raise InsoDuplicateHistoryError(
                DuplicateHistoryFailure.RECORD_FIELDS_INVALID, self.list_url
            )
        self._run_exact_query(page, target)
        page.click(DETAIL_LINK_SELECTOR_TEMPLATE.format(argument=row.bill_argument))
        page.wait_for(self._detail_bill_id_selector, timeout_ms=self._timeout_ms)
        read_back = page.attributes(self._detail_bill_id_selector, "value")
        bill_id = read_back[0].strip() if read_back and read_back[0] else ""
        if bill_id != row.bill_argument:
            # The opened record is not the record the row pointed at.
            raise InsoDuplicateHistoryError(
                DuplicateHistoryFailure.DETAIL_IDENTITY_MISMATCH, self.list_url
            )
        return DuplicateHistoryRecord(
            bill_id=bill_id,
            mpn=row.values.model,
            quantity=_parse_quantity(row.values.quantity_text),
            quoted_at=_parse_inso_timestamp(row.values.quoted_at_text),
        )


def _parse_quantity(value: str) -> int:
    text = value.strip().replace(",", "")
    if not text.isdecimal():
        raise InsoDuplicateHistoryError(DuplicateHistoryFailure.RECORD_FIELDS_INVALID)
    parsed = int(text)
    if parsed <= 0:
        raise InsoDuplicateHistoryError(DuplicateHistoryFailure.RECORD_FIELDS_INVALID)
    return parsed


def _parse_inso_timestamp(value: str) -> datetime:
    text = value.strip()
    for pattern in _INSO_TIMESTAMP_PATTERNS:
        try:
            # INSO serves offset-less Asia/Shanghai timestamps.
            return datetime.strptime(text, pattern).replace(
                tzinfo=_INSO_TIMEZONE
            ).astimezone(UTC)
        except ValueError:
            continue
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise InsoDuplicateHistoryError(
            DuplicateHistoryFailure.RECORD_FIELDS_INVALID
        ) from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=_INSO_TIMEZONE)
    return parsed.astimezone(UTC)


__all__ = [
    "BUSINESS_INQUIRY_LIST_PATH",
    "DETAIL_BILL_ID_SELECTOR",
    "DETAIL_LINK_CALL",
    "DETAIL_LINK_SELECTOR_TEMPLATE",
    "EXACT_MATCH_CHECKBOX",
    "MODEL_QUERY_INPUT",
    "QUERY_BUTTON",
    "RESULT_ROW_ID",
    "RESULT_ROW_SELECTOR",
    "DuplicateHistoryCapture",
    "DuplicateHistoryFailure",
    "DuplicateHistoryPage",
    "DuplicateHistoryRecord",
    "DuplicateHistoryRowValues",
    "InsoDuplicateHistoryError",
    "InsoDuplicateHistoryReader",
]
