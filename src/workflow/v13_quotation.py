"""RFQ-004 serial read cycle; intentionally absent from the production scheduler."""
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol

from src.inso.duplicate_history import InsoDuplicateHistoryError
from src.inso.quotation_read import (
    InsoQuotationAuthenticationError,
    InsoQuotationReader,
    QuotationPriceUnavailable,
    V13QuotationRow,
    select_recent_lowest,
)
from src.inso.session import InsoOperationAccess
from src.sheets import (
    SheetRecordIdentity,
    WorksheetIdentity,
    WorksheetRowReader,
    query_quotation_candidates,
)
from src.sheets.brand_write import SheetRecordConflict
from src.sheets.quotation_candidates import (
    QuotationSourceAmbiguous,
    relocate_quotation_source,
)

from .inso_query import run_inso_query
from .models import WorkItem
from .v12_faults import FaultScope, V12Fault


class QuotationOutcome(StrEnum):
    UPDATED_INSERTED = "UPDATED_INSERTED"
    UPDATED_ALREADY_EXISTS = "UPDATED_ALREADY_EXISTS"
    QUOTE_FOUND = "QUOTE_FOUND"
    NO_RECENT_QUOTE = "NO_RECENT_QUOTE"
    ROW_FAILED = "ROW_FAILED"


class RowErrorReason(StrEnum):
    SOURCE_IDENTITY_UNRESOLVED = "SOURCE_IDENTITY_UNRESOLVED"
    SOURCE_IDENTITY_AMBIGUOUS = "SOURCE_IDENTITY_AMBIGUOUS"
    SOURCE_MPN_UNAVAILABLE = "SOURCE_MPN_UNAVAILABLE"
    SOURCE_CHANGED = "SOURCE_CHANGED"
    QUOTE_PRICE_UNCOMPARABLE = "QUOTE_PRICE_UNCOMPARABLE"
    QUOTE_INPUT_WRITE_FAILED = "QUOTE_INPUT_WRITE_FAILED"
    QUOTE_INPUT_READBACK_MISMATCH = "QUOTE_INPUT_READBACK_MISMATCH"
    UPDATE_RESULT_UNCONFIRMED = "UPDATE_RESULT_UNCONFIRMED"
    SOURCE_STATUS_NOT_UPDATED = "SOURCE_STATUS_NOT_UPDATED"


class V13SourceRowError(Exception):
    def __init__(self, reason: RowErrorReason):
        super().__init__(reason.value)
        self.reason = reason


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
    source_row_position: int | None = None


@dataclass(frozen=True, slots=True)
class V13QuotationResult:
    inquiry_id: str | None
    record_identity: SheetRecordIdentity | None
    queried_mpn: str | None
    outcome: QuotationOutcome
    quotation: V13QuotationRow | None
    row_error_reason: RowErrorReason | None = None
    source_worksheet: WorksheetIdentity | None = None
    source_row_position: int | None = None


def _read_source_rows(reader, worksheet):
    try:
        return tuple(reader.read_rows(worksheet))
    except V12Fault:
        raise
    except Exception:  # noqa: BLE001 - this boundary contains only the shared Sheets read
        raise V12Fault(FaultScope.GLOBAL_STOP, "SHEETS_READ_UNAVAILABLE") from None


def _ledger_items(store):
    try:
        return tuple(store.all_items())
    except V12Fault:
        raise
    except Exception:  # noqa: BLE001 - only the shared ledger read, not row validation
        raise V12Fault(FaultScope.GLOBAL_STOP, "WORKFLOW_LEDGER_UNAVAILABLE") from None


def _source_bindings(items, worksheet, source_rows):
    matches, ambiguous = {}, set()
    for item in items:
        if item.record_identity.worksheet != worksheet:
            continue
        try:
            row = relocate_quotation_source(
                item.record_identity, source_rows, expected_brand=_expected_brand(item),
            )
        except QuotationSourceAmbiguous as exc:
            ambiguous.update(exc.row_positions)
            continue
        except SheetRecordConflict:
            continue
        matches.setdefault(row.row_position, []).append(item)
    return matches, ambiguous


def read_v13_candidates(
    reader: WorksheetRowReader, worksheet: WorksheetIdentity, store: ExistingInquiryStore,
) -> tuple[V13Candidate | V13QuotationResult, ...]:
    """Ordered candidate-or-row-error; later bad rows cannot abort the batch."""
    source_rows = _read_source_rows(reader, worksheet)

    class SnapshotReader:
        def read_rows(self, requested):
            return source_rows

    try:
        observed = query_quotation_candidates(SnapshotReader(), worksheet)
    except Exception:  # noqa: BLE001 - schema/reader shape is a shared Sheets boundary
        raise V12Fault(FaultScope.GLOBAL_STOP, "SHEETS_SCHEMA_UNAVAILABLE") from None
    matches, ambiguous = _source_bindings(_ledger_items(store), worksheet, source_rows)
    result = []
    for record in sorted(observed, key=lambda row: row.row_position):
        items = matches.get(record.row_position, [])
        item = items[0] if len(items) == 1 and record.row_position not in ambiguous else None
        reason = None
        if not isinstance(record.model, str) or not record.model.strip():
            reason = RowErrorReason.SOURCE_MPN_UNAVAILABLE
        elif len(items) > 1 or record.row_position in ambiguous:
            reason = RowErrorReason.SOURCE_IDENTITY_AMBIGUOUS
        elif item is None:
            reason = RowErrorReason.SOURCE_IDENTITY_UNRESOLVED
        if reason is not None:
            result.append(V13QuotationResult(
                item.inquiry_id if item else None, item.record_identity if item else None,
                record.model if isinstance(record.model, str) else None,
                QuotationOutcome.ROW_FAILED, None, reason, worksheet, record.row_position,
            ))
        else:
            result.append(V13Candidate(item.inquiry_id, item.record_identity, record.model, record.row_position))
    return tuple(result)


class V13QuotationCycle:
    def __init__(self, *, reader: WorksheetRowReader, store: ExistingInquiryStore,
                 operations: QuotationOperations, clock: Callable[[], datetime],
                 wait: Callable[[int], bool], stop_requested: Callable[[], bool] = lambda: False,
                 quote_reader: InsoQuotationReader | None = None, fx_provider=None):
        self._reader, self._store, self._operations = reader, store, operations
        self._clock, self._wait, self._stop = clock, wait, stop_requested
        self._quotes = quote_reader or InsoQuotationReader()
        self._fx = fx_provider

    def _currency_rate(self, currency):
        if self._fx is None:
            raise V12Fault(FaultScope.GLOBAL_STOP, "V13_FX_UNAVAILABLE")
        from src.research.ecb_fx import EcbFxError
        try:
            quote = self._fx.get_quote()
            return quote.rate if currency == "USD" else self._fx.get_hkd_rmb_rate()
        except (EcbFxError, OSError):
            raise V12Fault(FaultScope.GLOBAL_STOP, "V13_FX_UNAVAILABLE") from None

    def run(self, worksheet: WorksheetIdentity, *, skip=lambda _: False, on_result=lambda result: result) -> tuple[V13QuotationResult, ...]:
        try:
            return self._run(worksheet, skip=skip, on_result=on_result)
        except (V12Fault, V13Stopped):
            raise
        except Exception:  # noqa: BLE001 - includes close/result adapter contract failures
            raise V12Fault(FaultScope.GLOBAL_STOP, "V13_INTERNAL_FAILURE") from None

    def _run(self, worksheet, *, skip, on_result):
        candidates = read_v13_candidates(self._reader, worksheet, self._store)
        results = []
        for candidate in candidates:
            if self._stop():
                raise V13Stopped("STOP_REQUESTED")

            if skip(candidate):
                continue

            if isinstance(candidate, V13QuotationResult):
                results.append(on_result(candidate))
                continue

            def operation(candidate=candidate):
                if self._stop():
                    raise V13Stopped("STOP_REQUESTED")
                try:
                    item = self._store.get_by_inquiry_id(candidate.inquiry_id)
                except KeyError:
                    raise V13SourceRowError(RowErrorReason.SOURCE_IDENTITY_UNRESOLVED) from None
                except V12Fault:
                    raise
                except Exception:  # noqa: BLE001 - only shared ledger access
                    raise V12Fault(FaultScope.GLOBAL_STOP, "WORKFLOW_LEDGER_UNAVAILABLE") from None
                if item.record_identity != candidate.record_identity:
                    raise V13SourceRowError(RowErrorReason.SOURCE_CHANGED)
                fresh_rows = _read_source_rows(self._reader, worksheet)
                try:
                    row = relocate_quotation_source(
                        item.record_identity, fresh_rows, expected_brand=_expected_brand(item),
                    )
                except QuotationSourceAmbiguous:
                    raise V13SourceRowError(RowErrorReason.SOURCE_IDENTITY_AMBIGUOUS) from None
                except SheetRecordConflict:
                    raise V13SourceRowError(RowErrorReason.SOURCE_CHANGED) from None
                bindings, ambiguous = _source_bindings(_ledger_items(self._store), worksheet, fresh_rows)
                bound = bindings.get(row.row_position, [])
                if row.row_position in ambiguous or len(bound) != 1:
                    raise V13SourceRowError(RowErrorReason.SOURCE_IDENTITY_AMBIGUOUS)
                if bound[0].inquiry_id != candidate.inquiry_id:
                    raise V13SourceRowError(RowErrorReason.SOURCE_CHANGED)
                access = self._operations.open(candidate.inquiry_id)
                try:
                    rows = self._quotes.read(access, candidate.queried_mpn)
                    # Query-time clock sampled after this attempt completes, not batch start.
                    try:
                        return select_recent_lowest(rows, queried_mpn=candidate.queried_mpn,
                                                    now=self._clock(), currency_rate=self._currency_rate), True
                    except QuotationPriceUnavailable as exc:
                        if exc.code.startswith("QUOTE_FX"):
                            raise V12Fault(FaultScope.GLOBAL_STOP, "V13_FX_UNAVAILABLE") from None
                        raise V13SourceRowError(RowErrorReason.QUOTE_PRICE_UNCOMPARABLE) from None
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
            except V13SourceRowError as exc:
                self._operations.close()
                results.append(on_result(V13QuotationResult(
                    candidate.inquiry_id, candidate.record_identity, candidate.queried_mpn,
                    QuotationOutcome.ROW_FAILED, None, exc.reason, worksheet, candidate.source_row_position,
                )))
                continue
            except V12Fault:
                # Engine closes failed query tabs before exhaustion; auth tabs protected.
                raise
            except V13Stopped:
                self._operations.close()
                raise
            except Exception:  # noqa: BLE001 - unknown adapter failures stop shared business
                self._operations.close()
                raise V12Fault(FaultScope.GLOBAL_STOP, "V13_INTERNAL_FAILURE") from None
            self._operations.close()
            results.append(on_result(V13QuotationResult(
                candidate.inquiry_id, candidate.record_identity, candidate.queried_mpn,
                QuotationOutcome.QUOTE_FOUND if quote is not None else QuotationOutcome.NO_RECENT_QUOTE,
                quote, source_worksheet=worksheet, source_row_position=candidate.source_row_position,
            )))
        return tuple(results)


def _expected_brand(item: WorkItem) -> object:
    return (item.resolved_brand if item.brand_update_status == "UPDATED"
            else item.record_identity.identifying_snapshot.brand)
