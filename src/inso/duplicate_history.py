"""Minimal read-only INSO duplicate-history adapter.

Reads the business-inquiry list (`YeWuXJ/List.aspx`) in exact model mode and
returns the matching historical records for the Workflow duplicate check. It is
read-only: it never saves, sends or mutates INSO data, and it owns no purchase,
notification or retry behaviour.

Only selectors verified during read-only discovery are used; see
`docs/modules/INSO.md`. :class:`PlaywrightDuplicateHistoryPage` sends the
verified exact `List_Detail` request from the authenticated shell and validates
the returned MPNs and unique BillIDs. It does not rely on the hidden `#nolike`
control or stale grid state. The 制单人 / INSO-quote fields remain optional and
unset until their response semantics are confirmed. An unverifiable response
fails closed with a typed error.

Business rules -- canonical MPN, the rolling inclusive 168h window, latest-record
selection and the equal-timestamp AMBIGUOUS rule -- are deliberately NOT
implemented here. This adapter returns raw records and the Workflow decision
layer applies those rules.
"""

from __future__ import annotations

import json
import re
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from enum import StrEnum
from typing import Protocol
from urllib.parse import parse_qs, urlsplit

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

# Exact, read-only request confirmed in the authenticated INSO shell.
EXACT_HISTORY_REQUEST_URL = (
    "/services/innerEnquiry/yewuxj.ashx"
    "?action=List_Detail&BillPage=YeWuXJ"
)

#: Result rows are scoped to the confirmed primary result table. Other
#: expandable panels on the list also contain rows whose ids end in ``_Main``.
RESULT_ROW_ID = re.compile(r"^\d+_Main$")
RESULT_ROW_SELECTOR = "#_id_dg tr[id$='_Main']"

#: Live header-to-cell mapping confirmed from the result table DOM.
RESULT_MODEL_CELL_SELECTOR = "td:nth-child(9)"
RESULT_QUANTITY_CELL_SELECTOR = "td:nth-child(11)"
RESULT_TIMESTAMP_CELL_SELECTOR = "td:nth-child(14)"

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


@dataclass(frozen=True, slots=True)
class DuplicateHistoryFieldSelectors:
    """Result-row cell selectors.

    The three required cells are live-verified. ``creator`` (制单人) and
    ``inso_quote`` are required by the duplicate notification contract but their
    live cell/field selector is still unconfirmed, so they default to ``None``:
    the adapter then never guesses a column and the record's optional fields come
    back as ``None``. Set them only from a confirmed live observation.
    """

    model: str = RESULT_MODEL_CELL_SELECTOR
    quantity: str = RESULT_QUANTITY_CELL_SELECTOR
    quoted_at: str = RESULT_TIMESTAMP_CELL_SELECTOR
    creator: str | None = None
    inso_quote: str | None = None


@dataclass(frozen=True, slots=True)
class DuplicateHistoryResponseFields:
    """Confirmed List_Detail JSON keys; optional business fields stay unset."""

    bill_id: str = "BillID"
    model: str = "PartNo"
    quantity: str = "Qty"
    quoted_at: str = "PEDate"
    creator: str | None = None
    inso_quote: str | None = None
    currency: str | None = None


class DuplicateHistoryFailure(StrEnum):
    """Closed failure codes; a read failure is never a "not a duplicate"."""

    SESSION_LEASE_REQUIRED = "SESSION_LEASE_REQUIRED"
    HISTORY_LIST_UNAVAILABLE = "HISTORY_LIST_UNAVAILABLE"
    QUERY_SETTLEMENT_UNCONFIRMED = "QUERY_SETTLEMENT_UNCONFIRMED"
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
    ``creator`` and ``inso_quote_text`` are ``None`` while their live selector is
    unconfirmed; they must never be filled from a guessed column.
    """

    model: str
    quantity_text: str
    quoted_at_text: str
    creator: str | None = None
    inso_quote_text: str | None = None


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

    def wait_for_query_settled(self, *, timeout_ms: int) -> dict[str, object]:
        """Block until the submitted search has finished.

        The live adapter requires a matching exact-MPN response, advanced grid
        sequence, idle state, re-enabled query control, and matching response,
        cache, and DOM BillIDs. It MUST raise when any part cannot be established;
        an empty result is only meaningful once this returns.
        """
        ...

    def wait_for(self, selector: str, *, timeout_ms: int) -> None: ...

    def attributes(self, selector: str, name: str) -> tuple[str | None, ...]: ...

    def html(self, selector: str) -> str | None: ...

    def read_row_values(self, row_id: str) -> DuplicateHistoryRowValues | None:
        """Return one row's displayed model/quantity/time, or ``None``.

        The verified cells are `td:nth-child(9)`, `td:nth-child(11)`, and
        `td:nth-child(14)` within the row. Query settlement is still unresolved;
        implementations must not return rows until they can prove it settled.
        """
        ...


class InsoDuplicateHistoryReader:
    """Read exact-model history through the leased authenticated shell page."""

    def __init__(
        self,
        *,
        list_url: str,
        operation_access: InsoOperationAccess
        | Callable[[], InsoOperationAccess]
        | None = None,
        timeout_ms: int = 45_000,
        detail_bill_id_selector: str = DETAIL_BILL_ID_SELECTOR,
        response_fields: DuplicateHistoryResponseFields | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        parsed = urlsplit(list_url)
        if parsed.scheme != "https" or not parsed.hostname:
            raise ValueError("INSO list_url must be HTTPS")
        self._list_url = list_url.rstrip("/")
        self._operation_access = operation_access
        self._timeout_ms = timeout_ms
        self._detail_bill_id_selector = detail_bill_id_selector
        self._response_fields = response_fields or DuplicateHistoryResponseFields()
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
            with access.operation_page() as operation_page:
                if hasattr(operation_page, "shell_frame"):
                    live_page = PlaywrightDuplicateHistoryPage(
                        operation_page.shell_frame, timeout_ms=self._timeout_ms
                    )
                    payload = live_page.query_exact_response(target)
                    records = self._records_from_response(payload)
                else:
                    # Deterministic fake/page adapters can keep the narrow
                    # DuplicateHistoryPage test seam.
                    page: DuplicateHistoryPage = operation_page.page  # type: ignore[assignment]
                    rows = self._read_rows(page, target)
                    records = tuple(
                        self._verify_and_build(page, target, row) for row in rows
                    )
        except InsoDuplicateHistoryError:
            raise
        except SecurityViolation:
            # `from None`: the wrapped message must never surface raw page or
            # provider text through a chained traceback.
            raise InsoDuplicateHistoryError(
                DuplicateHistoryFailure.SESSION_LEASE_REQUIRED, url
            ) from None
        except Exception:  # noqa: BLE001 - raw page/provider failures are sanitized
            raise InsoDuplicateHistoryError(
                DuplicateHistoryFailure.HISTORY_LIST_UNAVAILABLE, url
            ) from None
        return DuplicateHistoryCapture(target, records, url, self._clock())

    def _records_from_response(
        self, payload: dict[str, object]
    ) -> tuple[DuplicateHistoryRecord, ...]:
        rows = payload.get("rows")
        fields = self._response_fields
        if not isinstance(rows, list):
            raise InsoDuplicateHistoryError(
                DuplicateHistoryFailure.QUERY_SETTLEMENT_UNCONFIRMED
            )
        records: list[DuplicateHistoryRecord] = []
        seen_bill_ids: set[str] = set()
        try:
            for row in rows:
                if not isinstance(row, dict):
                    raise TypeError
                bill_id = str(row.get(fields.bill_id, "")).strip()
                mpn = row.get(fields.model)
                if (
                    not bill_id.isdecimal()
                    or bill_id in seen_bill_ids
                    or not isinstance(mpn, str)
                    or not mpn.strip()
                ):
                    raise ValueError
                seen_bill_ids.add(bill_id)
                quantity_text = str(row.get(fields.quantity, ""))
                quoted_at_text = str(row.get(fields.quoted_at, ""))
                quote_raw = row.get(fields.inso_quote) if fields.inso_quote else None
                currency_raw = row.get(fields.currency) if fields.currency else None
                creator_raw = row.get(fields.creator) if fields.creator else None
                records.append(
                    DuplicateHistoryRecord(
                        bill_id=bill_id,
                        mpn=mpn,
                        quantity=_parse_quantity(quantity_text),
                        quoted_at=_parse_inso_timestamp(quoted_at_text),
                        creator=_optional_text(
                            creator_raw if isinstance(creator_raw, str) else None
                        ),
                        inso_quote=_parse_optional_quote(
                            str(quote_raw) if quote_raw is not None else None
                        ),
                        currency=_optional_text(
                            str(currency_raw) if currency_raw is not None else None
                        ),
                    )
                )
        except InsoDuplicateHistoryError:
            raise
        except (TypeError, ValueError):
            raise InsoDuplicateHistoryError(
                DuplicateHistoryFailure.RECORD_FIELDS_INVALID
            ) from None
        return tuple(records)

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

        if _dup_mpn_key(row.values.model) != _dup_mpn_key(target):
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
            creator=_optional_text(row.values.creator),
            inso_quote=_parse_optional_quote(row.values.inso_quote_text),
        )


def _optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    return text or None


def _parse_optional_quote(value: str | None) -> Decimal | None:
    """Parse an optional displayed INSO quote.

    Absent/blank means the row showed no quote. A present value that is not a
    plain non-negative decimal is a data error, not an invented amount.
    """

    text = _optional_text(value)
    if text is None:
        return None
    try:
        parsed = Decimal(text.replace(",", ""))
    except ArithmeticError:
        raise InsoDuplicateHistoryError(
            DuplicateHistoryFailure.RECORD_FIELDS_INVALID
        ) from None
    if not parsed.is_finite() or parsed < 0:
        raise InsoDuplicateHistoryError(
            DuplicateHistoryFailure.RECORD_FIELDS_INVALID
        ) from None
    return parsed


class PlaywrightDuplicateHistoryPage:
    """Live read-only adapter over the INSO business-inquiry list frame.

    The exact query uses the list page's native search handler and serializer in
    the already authenticated shell. It does not hand-build a request or click
    the hidden exact checkbox. A valid response must contain only the requested
    MPN and unique numeric BillIDs; missing or non-JSON response data fails closed.

    It navigates and reads only: there is no save, send or submit call, and no
    such selector is registered.
    """

    def __init__(
        self,
        page: object,
        *,
        selectors: DuplicateHistoryFieldSelectors | None = None,
        timeout_ms: int = 45_000,
    ) -> None:
        self._page = page
        self._selectors = selectors or DuplicateHistoryFieldSelectors()
        self._timeout_ms = timeout_ms
        self._target_mpn: str | None = None
        self._sequence_before_query: int | None = None
        self._sequence_after_dispatch: int | None = None
        self._settled_response: object | None = None
        self._response_listener: Callable[[object], None] | None = None
        self._owner_page: object | None = None
        self._settled_request: object | None = None

    @property
    def last_exact_request_shape(self) -> str:
        """Return safe request field shape only; never include posted values."""

        return _exact_history_request_shape(self._settled_request)

    @property
    def last_exact_request_matched(self) -> bool:
        """Whether the observed response belongs to this operation's exact query."""

        return bool(
            self._settled_request is not None
            and self._target_mpn
            and _is_exact_history_request(self._settled_request, self._target_mpn)
        )

    def query_exact_response(self, target_mpn: str) -> dict[str, object]:
        """Run the verified native search and return its settled response."""

        if not isinstance(target_mpn, str) or not target_mpn.strip():
            raise InsoDuplicateHistoryError(
                DuplicateHistoryFailure.QUERY_SETTLEMENT_UNCONFIRMED
            )
        target = target_mpn.strip()
        self._verify_list_identity()
        self.set_text(MODEL_QUERY_INPUT, target)
        self.ensure_checked(EXACT_MATCH_CHECKBOX)
        self.click(QUERY_BUTTON)
        return self.wait_for_query_settled(timeout_ms=self._timeout_ms)

    # -- DuplicateHistoryPage ----------------------------------------------

    def goto(self, url: str) -> None:
        parsed = urlsplit(url)
        if (
            parsed.scheme != "https"
            or parsed.hostname != "yingsuo.alperp.cn"
            or not parsed.path.casefold().endswith("/innerenquiry/yewuxj/list.aspx")
            or parsed.username
            or parsed.password
        ):
            raise InsoDuplicateHistoryError(
                DuplicateHistoryFailure.HISTORY_LIST_UNAVAILABLE, url
            )
        self._page.goto(url, wait_until="domcontentloaded", timeout=self._timeout_ms)
        self._verify_list_identity(url)

    def set_text(self, selector: str, value: str) -> None:
        if selector != MODEL_QUERY_INPUT or not isinstance(value, str) or not value.strip():
            raise InsoDuplicateHistoryError(
                DuplicateHistoryFailure.QUERY_SETTLEMENT_UNCONFIRMED
            )
        locator = self._unique_locator(selector)
        if not locator.is_visible() or not locator.is_enabled():
            raise InsoDuplicateHistoryError(
                DuplicateHistoryFailure.QUERY_SETTLEMENT_UNCONFIRMED
            )
        locator.fill(value, timeout=self._timeout_ms)
        if locator.input_value() != value:
            raise InsoDuplicateHistoryError(
                DuplicateHistoryFailure.QUERY_SETTLEMENT_UNCONFIRMED
            )
        self._target_mpn = value

    def ensure_checked(self, selector: str) -> None:
        if selector != EXACT_MATCH_CHECKBOX:
            raise InsoDuplicateHistoryError(
                DuplicateHistoryFailure.QUERY_SETTLEMENT_UNCONFIRMED
            )
        try:
            self._unique_locator(selector)
            # The site hides these form checkboxes. Set their state without a
            # synthetic click, then let the visible query button call native
            # search() and its own form-data serializer.
            state = self._page.evaluate(
                """() => {
                    const forms = document.querySelectorAll('form#search_form');
                    const exacts = document.querySelectorAll('#nolike');
                    const leftLikes = document.querySelectorAll('#leftlike');
                    if (forms.length !== 1 || exacts.length !== 1 || leftLikes.length !== 1) return null;
                    const form = forms[0];
                    const exact = exacts[0];
                    const leftLike = leftLikes[0];
                    if (exact.form !== form || leftLike.form !== form ||
                        exact.type !== 'checkbox' || leftLike.type !== 'checkbox' ||
                        exact.name !== 'nolike' || leftLike.name !== 'leftlike' ||
                        exact.disabled || leftLike.disabled) return null;
                    exact.checked = true;
                    leftLike.checked = false;
                    return {exact: exact.checked, leftLike: leftLike.checked};
                }"""
            )
            if not isinstance(state, dict) or state.get("exact") is not True or state.get("leftLike") is not False:
                raise InsoDuplicateHistoryError(
                    DuplicateHistoryFailure.QUERY_SETTLEMENT_UNCONFIRMED
                )
        except InsoDuplicateHistoryError:
            raise
        except Exception:  # noqa: BLE001 - selector failures are sanitized
            raise InsoDuplicateHistoryError(
                DuplicateHistoryFailure.QUERY_SETTLEMENT_UNCONFIRMED
            ) from None

    def click(self, selector: str) -> None:
        detail_match = re.fullmatch(
            r"\[onclick\*='Bill_View_Open\((\d+)\)'\]", selector
        )
        if detail_match is not None:
            locator = self._unique_locator(selector)
            if not locator.is_visible() or not locator.is_enabled():
                raise InsoDuplicateHistoryError(
                    DuplicateHistoryFailure.RESULT_IDENTIFIER_AMBIGUOUS
                )
            locator.click(timeout=self._timeout_ms)
            return
        if selector != QUERY_BUTTON or not self._target_mpn:
            raise InsoDuplicateHistoryError(
                DuplicateHistoryFailure.QUERY_SETTLEMENT_UNCONFIRMED
            )
        button = self._unique_locator(selector)
        if (
            not button.is_visible()
            or not button.is_enabled()
            or button.inner_text().strip() != "查询"
        ):
            raise InsoDuplicateHistoryError(
                DuplicateHistoryFailure.QUERY_SETTLEMENT_UNCONFIRMED
            )
        state = self._query_state()
        if (
            state is None
            or not state["exact_checked"]
            or state.get("left_like_checked") is not False
            or state.get("pending") is not False
        ):
            raise InsoDuplicateHistoryError(
                DuplicateHistoryFailure.QUERY_SETTLEMENT_UNCONFIRMED
            )
        self._clear_query_listeners()
        self._settled_response = None
        self._settled_request = None
        self._sequence_before_query = state["sequence"]
        owner = self._owner_page_for_events()
        target = self._target_mpn

        def matches_request(request: object) -> bool:
            return _is_exact_history_request(request, target)

        def on_response(response: object) -> None:
            request = getattr(response, "request", None)
            if request is not None and matches_request(request):
                self._settled_request = request
                self._settled_response = response

        self._owner_page = owner
        self._response_listener = on_response
        owner.on("response", on_response)
        try:
            button.click(timeout=self._timeout_ms)
            after = self._query_state()
            if after is None or after["sequence"] <= self._sequence_before_query:
                raise InsoDuplicateHistoryError(
                    DuplicateHistoryFailure.QUERY_SETTLEMENT_UNCONFIRMED
                )
            self._sequence_after_dispatch = after["sequence"]
        except InsoDuplicateHistoryError:
            self._clear_query_listeners()
            raise
        except Exception:  # noqa: BLE001 - browser details are not persisted
            self._clear_query_listeners()
            raise InsoDuplicateHistoryError(
                DuplicateHistoryFailure.QUERY_SETTLEMENT_UNCONFIRMED
            ) from None

    def wait_for_query_settled(self, *, timeout_ms: int) -> dict[str, object]:
        """Wait for the native exact-MPN response and prove its rows reached this grid."""

        response = self._settled_response
        owner = self._owner_page
        target = self._target_mpn
        sequence = self._sequence_after_dispatch
        if owner is None or not target or sequence is None:
            self._clear_query_listeners()
            raise InsoDuplicateHistoryError(
                DuplicateHistoryFailure.QUERY_SETTLEMENT_UNCONFIRMED
            )
        try:
            if response is None:
                response = owner.wait_for_event(
                    "response",
                    predicate=lambda candidate: _is_exact_history_request(
                        getattr(candidate, "request", None), target
                    ),
                    timeout=timeout_ms,
                )
            status = getattr(response, "status", None)
            if not isinstance(status, int) or not 200 <= status < 300:
                raise ValueError
            payload = response.json()
            rows = payload.get("rows") if isinstance(payload, dict) else None
            if not isinstance(rows, list):
                raise TypeError("unexpected response shape")
            _validate_exact_response_rows(rows, target)
            bill_ids = [str(row.get("BillID", "")).strip() for row in rows]
            if any(not bill_id.isdecimal() or int(bill_id) <= 0 for bill_id in bill_ids):
                raise ValueError
            if len(set(bill_ids)) != len(bill_ids):
                raise ValueError
            observation = {
                "sequence": sequence,
                "bill_ids": bill_ids,
                "empty": not bill_ids,
            }
            self._page.wait_for_function(
                """expected => {
                    const button = document.querySelector('#select_btns');
                    const cache = window.table && window.table.cache
                        && window.table.cache.dg;
                    const domRows = [...document.querySelectorAll(
                        '#_id_dg tr[id$=\"_Main\"]')];
                    const cacheIds = Array.isArray(cache)
                        ? cache.map(row => String(row.BillID || '')) : null;
                    const domIds = domRows.map(row => {
                        const calls = [...row.querySelectorAll('[onclick]')]
                            .map(el => (el.getAttribute('onclick') || '').match(
                                /Bill_View_Open\\(\\s*(\\d+)/))
                            .filter(Boolean).map(match => match[1]);
                        return calls.length === 1 ? calls[0] : '';
                    });
                    return window._select_pending === false
                        && (window._select_request_seq || {}).dg === expected.sequence
                        && button && !button.disabled
                        && cacheIds !== null
                        && JSON.stringify(cacheIds) === JSON.stringify(expected.bill_ids)
                        && JSON.stringify(domIds) === JSON.stringify(expected.bill_ids)
                        && (expected.empty
                            ? document.querySelectorAll('.layui-table-none').length > 0
                            : domRows.length > 0);
                }""",
                arg=observation,
                timeout=timeout_ms,
            )
        except Exception:  # noqa: BLE001 - raw network/page details never escape
            self._clear_query_listeners()
            raise InsoDuplicateHistoryError(
                DuplicateHistoryFailure.QUERY_SETTLEMENT_UNCONFIRMED
            ) from None
        self._clear_query_listeners()
        if not isinstance(payload, dict):
            raise InsoDuplicateHistoryError(
                DuplicateHistoryFailure.QUERY_SETTLEMENT_UNCONFIRMED
            )
        return payload

    def wait_for(self, selector: str, *, timeout_ms: int) -> None:
        self._page.wait_for_selector(selector, state="visible", timeout=timeout_ms)

    def attributes(self, selector: str, name: str) -> tuple[str | None, ...]:
        values = self._page.eval_on_selector_all(
            selector,
            "(els, attr) => els.map((el) => el.getAttribute(attr))",
            name,
        )
        if not isinstance(values, list):
            return ()
        return tuple(value if isinstance(value, str) else None for value in values)

    def html(self, selector: str) -> str | None:
        return self._element_text(selector, "el => el.outerHTML")

    def read_row_values(self, row_id: str) -> DuplicateHistoryRowValues | None:
        """Read the verified model/quantity/time cells, plus any confirmed extras."""

        model = self._cell_text(row_id, self._selectors.model)
        quantity_text = self._cell_text(row_id, self._selectors.quantity)
        quoted_at_text = self._cell_text(row_id, self._selectors.quoted_at)
        if model is None or quantity_text is None or quoted_at_text is None:
            return None
        return DuplicateHistoryRowValues(
            model=model,
            quantity_text=quantity_text,
            quoted_at_text=quoted_at_text,
            creator=self._cell_text(row_id, self._selectors.creator),
            inso_quote_text=self._cell_text(row_id, self._selectors.inso_quote),
        )

    def _unique_locator(self, selector: str) -> object:
        locator = self._page.locator(selector)
        if locator.count() != 1:
            raise InsoDuplicateHistoryError(
                DuplicateHistoryFailure.QUERY_SETTLEMENT_UNCONFIRMED
            )
        return locator

    def _owner_page_for_events(self) -> object:
        page = getattr(self._page, "page", None) or self._page
        self._verify_list_identity()
        return page

    def _verify_list_identity(self, expected_url: str | None = None) -> None:
        current_url = str(getattr(self._page, "url", ""))
        current = urlsplit(current_url)
        path_ok = current.path.casefold().endswith(
            "/innerenquiry/yewuxj/list.aspx"
        )
        if (
            current.scheme != "https"
            or current.hostname != "yingsuo.alperp.cn"
            or not path_ok
            or current.username
            or current.password
        ):
            raise InsoDuplicateHistoryError(
                DuplicateHistoryFailure.HISTORY_LIST_UNAVAILABLE,
                expected_url or current_url,
            )
        page = getattr(self._page, "page", None)
        if page is None:
            frames = getattr(self._page, "frames", None)
            main_frame = getattr(self._page, "main_frame", None)
            if frames is not None and (
                len(frames) != 1 or not frames or frames[0] is not main_frame
            ):
                raise InsoDuplicateHistoryError(
                    DuplicateHistoryFailure.HISTORY_LIST_UNAVAILABLE,
                    expected_url or current_url,
                )
        else:
            matches = [
                frame
                for frame in page.frames
                if urlsplit(frame.url).path.casefold().endswith(
                    "/innerenquiry/yewuxj/list.aspx"
                )
            ]
            if len(matches) != 1 or matches[0] is not self._page:
                raise InsoDuplicateHistoryError(
                    DuplicateHistoryFailure.HISTORY_LIST_UNAVAILABLE,
                    expected_url or current_url,
                )

    def _query_state(self) -> dict[str, object] | None:
        try:
            state = self._page.evaluate(
                """() => {
                    const exact = document.querySelector('#nolike');
                    const leftLike = document.querySelector('#leftlike');
                    const button = document.querySelector('#select_btns');
                    const sequence = (window._select_request_seq || {}).dg;
                    if (!exact || !leftLike || !button || !Number.isInteger(sequence)) return null;
                    return {
                        exact_checked: exact.checked === true,
                        left_like_checked: leftLike.checked === true,
                        // Missing state is not evidence that the request is idle.
                        pending: window._select_pending !== false,
                        sequence,
                    };
                }"""
            )
            if not isinstance(state, dict):
                return None
            if not isinstance(state.get("sequence"), int):
                return None
            return state
        except Exception:  # noqa: BLE001 - state reads fail closed
            return None

    def _clear_query_listeners(self) -> None:
        owner, response_listener = self._owner_page, self._response_listener
        if owner is not None and response_listener is not None:
            owner.remove_listener("response", response_listener)
        self._owner_page = None
        self._response_listener = None

    # -- internals ---------------------------------------------------------

    def _cell_text(self, row_id: str, cell_selector: str | None) -> str | None:
        if not cell_selector:
            # The selector is still unconfirmed, so nothing is read or guessed.
            return None
        return self._element_text(f"#{row_id} {cell_selector}", "el => el.textContent")

    def _element_text(self, selector: str, expression: str) -> str | None:
        if int(self._page.locator(selector).count()) != 1:
            return None
        value = self._page.eval_on_selector(selector, expression)
        return value if isinstance(value, str) else None


def _is_exact_history_request(request: object, target: str) -> bool:
    """Match only the current exact-MPN List_Detail request, without logging it."""

    try:
        url = urlsplit(str(request.url))
        query = parse_qs(url.query, keep_blank_values=True)
        if (
            url.scheme != "https"
            or url.hostname != "yingsuo.alperp.cn"
            or str(request.method).upper() != "POST"
            or not url.path.casefold().endswith("/innerenquiry/yewuxj.ashx")
            or query.get("action", [""])[0] != "List_Detail"
            or query.get("BillPage", [""])[0] != "YeWuXJ"
        ):
            return False
        body = str(getattr(request, "post_data", "") or "")
        fields = parse_qs(body, keep_blank_values=True)
        search_data: dict[str, object] = {}
        raw_search_data = fields.get("searchData", [""])[0]
        if raw_search_data:
            # parse_qs already form-decodes the value. A second unquote would
            # turn a literal MPN '+' into a space and misclassify the request.
            parsed = json.loads(raw_search_data)
            if isinstance(parsed, dict):
                search_data.update(parsed)
        for key, values in fields.items():
            if key.startswith("searchData[") and key.endswith("]") and values:
                search_data[key[len("searchData["):-1]] = values[0]
        target_key = _dup_mpn_key(target)
        return (
            target_key is not None
            and search_data.get("DetailField") == "PartNo"
            and _dup_mpn_key(search_data.get("DetailFieldValue"))
            == target_key
            and search_data.get("nolike") == "on"
            and search_data.get("leftlike") != "on"
        )
    except Exception:  # noqa: BLE001 - malformed/unexpected request is not a match
        return False


def _dup_mpn_key(value: object) -> str | None:
    """Apply the exact ``dup-mpn-v1`` normalization for adapter consistency."""

    if not isinstance(value, str):
        return None
    normalized = unicodedata.normalize("NFKC", value).strip()
    if not normalized:
        return None
    return "".join(
        chr(ord(char) - 32) if "a" <= char <= "z" else char
        for char in normalized
    )


def _validate_exact_response_rows(rows: list[object], target: str) -> None:
    """Reject stale, fuzzy, malformed or duplicate-id rows from this response."""

    seen_bill_ids: set[str] = set()
    target_key = _dup_mpn_key(target)
    if target_key is None:
        raise ValueError("invalid query model")
    for row in rows:
        if not isinstance(row, dict):
            raise TypeError("invalid response row")
        bill_id = str(row.get("BillID", "")).strip()
        if (
            _dup_mpn_key(row.get("PartNo")) != target_key
            or not bill_id.isdecimal()
            or int(bill_id) <= 0
            or bill_id in seen_bill_ids
        ):
            raise ValueError("response row does not match exact query")
        seen_bill_ids.add(bill_id)


def _exact_history_request_shape(request: object | None) -> str:
    """Describe only the serialized search keys, never their values."""

    if request is None:
        return "UNKNOWN"
    try:
        fields = parse_qs(
            str(getattr(request, "post_data", "") or ""), keep_blank_values=True
        )
        raw_search_data = fields.get("searchData", [""])[0]
        if raw_search_data:
            parsed = json.loads(raw_search_data)
            if isinstance(parsed, dict):
                keys = sorted(
                    key
                    for key in parsed
                    if key in {"DetailField", "DetailFieldValue", "nolike", "leftlike"}
                )
                return "searchData=JSON{" + ",".join(keys) + "}"
        keys = sorted(
            key[len("searchData[") : -1]
            for key in fields
            if key.startswith("searchData[") and key.endswith("]")
        )
        return "searchData[fields]{" + ",".join(keys) + "}" if keys else "UNKNOWN"
    except Exception:  # noqa: BLE001 - diagnostics never expose request content
        return "UNKNOWN"


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
    except ValueError:
        raise InsoDuplicateHistoryError(
            DuplicateHistoryFailure.RECORD_FIELDS_INVALID
        ) from None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=_INSO_TIMEZONE)
    return parsed.astimezone(UTC)


__all__ = [
    "BUSINESS_INQUIRY_LIST_PATH",
    "DETAIL_BILL_ID_SELECTOR",
    "DETAIL_LINK_CALL",
    "DETAIL_LINK_SELECTOR_TEMPLATE",
    "EXACT_HISTORY_REQUEST_URL",
    "EXACT_MATCH_CHECKBOX",
    "MODEL_QUERY_INPUT",
    "QUERY_BUTTON",
    "RESULT_MODEL_CELL_SELECTOR",
    "RESULT_QUANTITY_CELL_SELECTOR",
    "RESULT_ROW_ID",
    "RESULT_ROW_SELECTOR",
    "RESULT_TIMESTAMP_CELL_SELECTOR",
    "DuplicateHistoryCapture",
    "DuplicateHistoryFailure",
    "DuplicateHistoryFieldSelectors",
    "DuplicateHistoryPage",
    "DuplicateHistoryRecord",
    "DuplicateHistoryResponseFields",
    "DuplicateHistoryRowValues",
    "InsoDuplicateHistoryError",
    "InsoDuplicateHistoryReader",
    "PlaywrightDuplicateHistoryPage",
]
