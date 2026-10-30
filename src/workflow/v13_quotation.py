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
    BASELINE_RECORDED = "BASELINE_RECORDED"
    PRICE_UNCHANGED = "PRICE_UNCHANGED"
    UPDATED_INSERTED = "UPDATED_INSERTED"
    UPDATED_ALREADY_EXISTS = "UPDATED_ALREADY_EXISTS"
    QUOTE_FOUND = "QUOTE_FOUND"
    NO_RECENT_QUOTE = "NO_RECENT_QUOTE"
    ROW_FAILED = "ROW_FAILED"
    QUOTE_AGE_EXPIRED = "QUOTE_AGE_EXPIRED"
    QUOTE_AGE_UNVERIFIED = "QUOTE_AGE_UNVERIFIED"


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


class _QuotationAgeSkip(Exception):
    def __init__(self, reason):
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
    source_status: str = "发给采购"


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
    source_status: str = "发给采购"
    effect_uncertain: bool = False


def _read_source_rows(reader, worksheet, *, discovery=False):
    try:
        read = getattr(reader, "read_discovery_rows", reader.read_rows) if discovery else reader.read_rows
        return tuple(read(worksheet))
    except V12Fault:
        raise
    except Exception as exc:
        raise V12Fault(FaultScope.GLOBAL_STOP, "SHEETS_READ_UNAVAILABLE") from exc


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
    *, discovery=False, on_unverified_customer=lambda: None,
) -> tuple[V13Candidate | V13QuotationResult, ...]:
    """Ordered candidate-or-row-error; later bad rows cannot abort the batch."""
    source_rows = _read_source_rows(reader, worksheet, discovery=discovery)

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
        # Refreshes require an EXISTING unique internal ID for their baseline.
        # Historical/unbound quoted rows must not create IDs or a mailbox flood.
        # Initial sent-to-procurement rows retain their reviewed failure handling.
        if record.status != "发给采购" and item is None:
            if record.status == "已报价给客户":
                on_unverified_customer()  # No ID, hold, notification or INSO query.
            continue
        if reason is not None:
            result.append(V13QuotationResult(
                item.inquiry_id if item else None, item.record_identity if item else None,
                record.model if isinstance(record.model, str) else None,
                QuotationOutcome.ROW_FAILED, None, reason, worksheet, record.row_position, str(record.status),
            ))
        else:
            result.append(V13Candidate(item.inquiry_id, item.record_identity, record.model, record.row_position, str(record.status)))
    return tuple(result)


class V13QuotationCycle:
    def __init__(self, *, reader: WorksheetRowReader, store: ExistingInquiryStore,
                 operations: QuotationOperations, clock: Callable[[], datetime],
                 wait: Callable[[int], bool], stop_requested: Callable[[], bool] = lambda: False,
                 quote_reader: InsoQuotationReader | None = None, fx_provider=None, on_fx_success=lambda: None, on_query_success=lambda: None, automatic_refresh=True, brief_snapshot=lambda worksheet: ()):
        self._reader, self._store, self._operations = reader, store, operations
        self._clock, self._wait, self._stop = clock, wait, stop_requested
        self._quotes = quote_reader or InsoQuotationReader()
        self._fx = fx_provider
        self._on_fx_success = on_fx_success
        self._on_query_success = on_query_success
        self._automatic_refresh, self._brief_snapshot = automatic_refresh, brief_snapshot
        self.quote_age_skips = {"QUOTE_AGE_EXPIRED": 0, "QUOTE_AGE_UNVERIFIED": 0}
        self.quote_age_date_source = None

    def currency_rate(self, currency):
        if self._fx is None:
            raise V12Fault(FaultScope.GLOBAL_STOP, "V13_FX_UNAVAILABLE")
        from src.research.ecb_fx import EcbFxError
        try:
            quote = self._fx.get_quote()
            rate = quote.rate if currency == "USD" else self._fx.get_hkd_rmb_rate()
            self._on_fx_success()
            return rate
        except (EcbFxError, OSError):
            raise V12Fault(FaultScope.GLOBAL_STOP, "V13_FX_UNAVAILABLE") from None

    def run(self, worksheet: WorksheetIdentity, *, skip=lambda _: False, on_result=lambda result: result, after_closed_candidate=None) -> tuple[V13QuotationResult, ...]:
        try:
            return self._run(worksheet, skip=skip, on_result=on_result, after_closed_candidate=after_closed_candidate)
        except (V12Fault, V13Stopped):
            raise
        except Exception:  # noqa: BLE001 - includes close/result adapter contract failures
            raise V12Fault(FaultScope.GLOBAL_STOP, "V13_INTERNAL_FAILURE") from None

    def read_candidates(self, worksheet):
        def unverified():
            if self._automatic_refresh:
                self.quote_age_skips["QUOTE_AGE_UNVERIFIED"] += 1
        return read_v13_candidates(self._reader, worksheet, self._store, discovery=True,
                                   on_unverified_customer=unverified)

    def _run(self, worksheet, *, skip, on_result, after_closed_candidate=None):
        results = []
        for candidate in self.read_candidates(worksheet):
            if self._stop():
                raise V13Stopped("STOP_REQUESTED")
            if not skip(candidate):
                result = self.execute_candidate(candidate, worksheet, on_result=on_result)
                results.append(result)
                # Original query close AND on_result settlement completed first.
                # The integrated caller still certifies terminal/effect safety.
                if after_closed_candidate is not None:
                    after_closed_candidate(result)
        return tuple(results)

    def recheck_automatic_age(self, result):
        """Same policy immediately before a continuation or external update."""
        if not self._automatic_refresh or result.record_identity is None or result.inquiry_id is None:
            return None
        from .automatic_admission import age_reason, source_date
        item = self._store.get_by_inquiry_id(result.inquiry_id)
        worksheet = result.record_identity.worksheet
        rows = _read_source_rows(self._reader, worksheet)
        row = relocate_quotation_source(item.record_identity, rows, expected_brand=_expected_brand(item))
        value, _ = source_date(item.record_identity, row, self._brief_snapshot(worksheet),
                               lambda: self._store.inquiry_intake_at(result.inquiry_id))
        return age_reason(value, self._clock())

    def execute_candidate(self, candidate, worksheet, *, on_result=lambda result: result):
        """One original protected query; page closes before owner continuation."""
        if self._stop():
            raise V13Stopped("STOP_REQUESTED")
        try:
            return self._execute_candidate(candidate, worksheet, on_result=on_result)
        except (V12Fault, V13Stopped):
            raise
        except Exception:  # noqa: BLE001 - preserve canonical shared-fault policy
            raise V12Fault(FaultScope.GLOBAL_STOP, "V13_INTERNAL_FAILURE") from None

    def _execute_candidate(self, candidate, worksheet, *, on_result):
        if isinstance(candidate, V13QuotationResult):
            return on_result(candidate)

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
            # Query-only work may reuse discovery; the updater independently
            # re-reads identity/status before any baseline or business write.
            fresh_rows = _read_source_rows(self._reader, worksheet, discovery=True)
            try:
                row = relocate_quotation_source(
                    item.record_identity, fresh_rows, expected_brand=_expected_brand(item),
                )
            except QuotationSourceAmbiguous:
                raise V13SourceRowError(RowErrorReason.SOURCE_IDENTITY_AMBIGUOUS) from None
            except SheetRecordConflict:
                raise V13SourceRowError(RowErrorReason.SOURCE_CHANGED) from None
            from src.sheets.worksheet_schema import worksheet_schema
            if row.cells.get(worksheet_schema(worksheet.worksheet).status_column) != candidate.source_status:
                raise V13SourceRowError(RowErrorReason.SOURCE_CHANGED)
            bindings, ambiguous = _source_bindings(_ledger_items(self._store), worksheet, fresh_rows)
            bound = bindings.get(row.row_position, [])
            if row.row_position in ambiguous or len(bound) != 1:
                raise V13SourceRowError(RowErrorReason.SOURCE_IDENTITY_AMBIGUOUS)
            if bound[0].inquiry_id != candidate.inquiry_id:
                raise V13SourceRowError(RowErrorReason.SOURCE_CHANGED)
            if self._automatic_refresh:
                from .quotation_age import age_reason, quotation_age_date
                def intake():
                    read = getattr(self._store, "inquiry_intake_at", None)
                    try:
                        return read(candidate.inquiry_id) if callable(read) else None
                    except Exception as exc:
                        raise V12Fault(FaultScope.GLOBAL_STOP, "WORKFLOW_LEDGER_UNAVAILABLE") from exc
                value, self.quote_age_date_source = quotation_age_date(
                    candidate, row, self._brief_snapshot(worksheet), intake)
                if self._stop():
                    raise V13Stopped("STOP_REQUESTED")
                reason = age_reason(value, self._clock())
                if reason is not None:
                    self.quote_age_skips[reason] += 1  # Two fixed bounded diagnostic keys.
                    raise _QuotationAgeSkip(reason)
            if self._stop():
                raise V13Stopped("STOP_REQUESTED")
            access = self._operations.open(candidate.inquiry_id)
            try:
                rows = self._quotes.read(access, candidate.queried_mpn)
                self._on_query_success()  # INSO read succeeded even if another site's FX fails.
                # Query-time clock sampled after this attempt completes, not batch start.
                try:
                    quote = select_recent_lowest(rows, queried_mpn=candidate.queried_mpn,
                                                 now=self._clock(), currency_rate=self.currency_rate)
                    return quote, True
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
                reset=getattr(self._operations, "reset", self._operations.close), wait=self._wait,
                stop_fault=lambda: V13Stopped("STOP_REQUESTED"),
            )
        except _QuotationAgeSkip as exc:
            # No INSO open/query/reset, updater, baseline, hold or SMTP for this skip.
            return on_result(V13QuotationResult(
                candidate.inquiry_id, candidate.record_identity, candidate.queried_mpn,
                QuotationOutcome(exc.reason), None, source_worksheet=worksheet,
                source_row_position=candidate.source_row_position, source_status=candidate.source_status))
        except V13SourceRowError as exc:
            self._operations.close()
            return on_result(V13QuotationResult(
                candidate.inquiry_id, candidate.record_identity, candidate.queried_mpn,
                QuotationOutcome.ROW_FAILED, None, exc.reason, worksheet, candidate.source_row_position, candidate.source_status,
            ))
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
        return on_result(V13QuotationResult(
            candidate.inquiry_id, candidate.record_identity, candidate.queried_mpn,
            QuotationOutcome.QUOTE_FOUND if quote is not None else QuotationOutcome.NO_RECENT_QUOTE,
            quote, source_worksheet=worksheet, source_row_position=candidate.source_row_position,
            source_status=candidate.source_status,
        ))


def expected_source_brand(item: WorkItem) -> object:
    """Public source-brand contract shared by quote binding and purchase completion."""
    return _expected_brand(item)


def _expected_brand(item: WorkItem) -> object:
    return (item.resolved_brand if item.brand_update_status == "UPDATED"
            else item.record_identity.identifying_snapshot.brand)
