"""RFQ-004 serial read cycle; intentionally absent from the production scheduler."""
import sqlite3
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol

from src.inso.duplicate_history import InsoDuplicateHistoryError
from src.inso.quotation_read import (
    InsoQuotationAuthenticationError,
    InsoQuotationReader,
    V13QuotationRow,
    select_recent_latest,
)
from src.inso.session import InsoOperationAccess
from src.sheets import (
    SheetRecordIdentity,
    WorksheetIdentity,
    WorksheetRowReader,
    query_quotation_candidates,
)
from src.sheets.brand_write import SheetRecordConflict
from src.sheets.quotation_candidates import relocate_quotation_source

from .inso_query import run_inso_query
from .models import WorkItem
from .v12_faults import FaultScope, V12Fault


class QuotationOutcome(StrEnum):
    QUOTE_FOUND = "QUOTE_FOUND"
    NO_RECENT_QUOTE = "NO_RECENT_QUOTE"


class V13Stopped(RuntimeError):
    """Shutdown interrupted the read cycle; no fabricated quotation result."""


class ExistingInquiryStore(Protocol):
    def all_items(self) -> Iterable[WorkItem]: ...
    def get_by_inquiry_id(self, inquiry_id: str) -> WorkItem: ...


class QuotationOperations(Protocol):
    """Launcher supplies a NEW owned tab for every open; protect auth failures."""
    def open(self, inquiry_id: str) -> InsoOperationAccess: ...
    def close(self) -> None: ...
    def preserve(self) -> None: ...


@dataclass(frozen=True, slots=True)
class V13Candidate:
    inquiry_id: str
    record_identity: SheetRecordIdentity
    queried_mpn: str


@dataclass(frozen=True, slots=True)
class V13QuotationResult:
    inquiry_id: str
    record_identity: SheetRecordIdentity
    queried_mpn: str
    outcome: QuotationOutcome
    quotation: V13QuotationRow | None


def read_v13_candidates(
    reader: WorksheetRowReader, worksheet: WorksheetIdentity, store: ExistingInquiryStore,
) -> tuple[V13Candidate, ...]:
    """Bind source candidates ONLY to uniquely relocated original ledger IDs.

    There is deliberately no enqueue, inquiry_id_for(current row), or new ID.
    An orphan or ambiguous source cannot become a different business order.
    """
    source_rows = tuple(reader.read_rows(worksheet))

    class SnapshotReader:
        def read_rows(self, requested):
            return source_rows

    observed = query_quotation_candidates(SnapshotReader(), worksheet)
    matches: dict[int, list[WorkItem]] = {row.row_position: [] for row in observed}
    for item in store.all_items():
        if item.record_identity.worksheet != worksheet:
            continue
        try:
            row = relocate_quotation_source(
                item.record_identity, source_rows, expected_brand=_expected_brand(item),
            )
        except SheetRecordConflict:
            continue
        matches[row.row_position].append(item)
    result = []
    for record in sorted(observed, key=lambda row: row.row_position):
        items = matches[record.row_position]
        if len(items) != 1:
            raise V12Fault(FaultScope.GLOBAL_STOP, "SOURCE_IDENTITY_UNRESOLVED")
        item = items[0]
        if not isinstance(record.model, str) or not record.model.strip():
            raise V12Fault(FaultScope.GLOBAL_STOP, "SOURCE_MPN_UNAVAILABLE")
        result.append(V13Candidate(item.inquiry_id, item.record_identity, record.model))
    return tuple(result)


class V13QuotationCycle:
    def __init__(self, *, reader: WorksheetRowReader, store: ExistingInquiryStore,
                 operations: QuotationOperations, clock: Callable[[], datetime],
                 wait: Callable[[int], bool], stop_requested: Callable[[], bool] = lambda: False,
                 quote_reader: InsoQuotationReader | None = None):
        self._reader, self._store, self._operations = reader, store, operations
        self._clock, self._wait, self._stop = clock, wait, stop_requested
        self._quotes = quote_reader or InsoQuotationReader()

    def run(self, worksheet: WorksheetIdentity) -> tuple[V13QuotationResult, ...]:
        try:
            candidates = read_v13_candidates(self._reader, worksheet, self._store)
        except V12Fault:
            raise
        except sqlite3.Error:
            raise V12Fault(FaultScope.GLOBAL_STOP, "WORKFLOW_LEDGER_UNAVAILABLE") from None
        except Exception:  # noqa: BLE001 - source read failure must stop, never empty
            raise V12Fault(FaultScope.GLOBAL_STOP, "SHEETS_READ_UNAVAILABLE") from None
        results = []
        for candidate in candidates:
            if self._stop():
                raise V13Stopped("STOP_REQUESTED")

            def operation(candidate=candidate):
                if self._stop():
                    raise V13Stopped("STOP_REQUESTED")
                item = self._store.get_by_inquiry_id(candidate.inquiry_id)
                if item.record_identity != candidate.record_identity:
                    raise SheetRecordConflict("ledger source identity changed")
                relocate_quotation_source(
                    item.record_identity, self._reader.read_rows(worksheet),
                    expected_brand=_expected_brand(item),
                )
                access = self._operations.open(candidate.inquiry_id)
                try:
                    rows = self._quotes.read(access, candidate.queried_mpn)
                    # Query-time clock sampled after this attempt completes, not batch start.
                    return select_recent_latest(rows, queried_mpn=candidate.queried_mpn, now=self._clock()), True
                except InsoQuotationAuthenticationError:
                    self._operations.preserve()
                    raise V12Fault(FaultScope.GLOBAL_STOP, "INSO_AUTHENTICATION_REQUIRED") from None
                except InsoDuplicateHistoryError:
                    return None, False

            try:
                quote, _ = run_inso_query(
                    operation, succeeded=lambda result: result[1],
                    reset=self._operations.close, wait=self._wait,
                    stop_fault=lambda: V13Stopped("STOP_REQUESTED"),
                )
            except V12Fault:
                # Engine closes failed query tabs before exhaustion; auth tabs protected.
                raise
            except V13Stopped:
                self._operations.close()
                raise
            except Exception:  # noqa: BLE001 - identity/read/clock faults never become no quote
                self._operations.close()
                raise V12Fault(FaultScope.GLOBAL_STOP, "V13_READ_UNAVAILABLE") from None
            self._operations.close()
            results.append(V13QuotationResult(
                candidate.inquiry_id, candidate.record_identity, candidate.queried_mpn,
                QuotationOutcome.QUOTE_FOUND if quote is not None else QuotationOutcome.NO_RECENT_QUOTE,
                quote,
            ))
        return tuple(results)


def _expected_brand(item: WorkItem) -> object:
    return (item.resolved_brand if item.brand_update_status == "UPDATED"
            else item.record_identity.identifying_snapshot.brand)
