"""RFQ-005 serial idempotent Google update over frozen RFQ-004 quote results."""
from collections.abc import Callable, Iterable
from dataclasses import replace
from time import monotonic
from typing import Protocol

from src.quotation.update_result import UpdatePopupOutcome, parse_update_popup
from src.sheets import WorksheetRowReader
from src.sheets.brand_write import SheetRecordConflict
from src.sheets.quotation_candidates import (
    QuotationSourceAmbiguous,
    relocate_quotation_status,
)
from src.sheets.quotation_input import (
    QuotationInputAttemptFailed,
    QuotationInputUnavailable,
)
from src.sheets.worksheet_schema import worksheet_schema

from .v12_faults import FaultScope, V12Fault
from .v13_quotation import (
    ExistingInquiryStore,
    QuotationOutcome,
    RowErrorReason,
    V13QuotationResult,
    V13SourceRowError,
    V13Stopped,
)


class UpdateAttemptUnconfirmed(RuntimeError):
    """Recoverable owned Google surface/button/dialog failure; safe to repeat."""


class QuotationUpdateActions(Protocol):
    def open_quote_input(self) -> None: ...
    def click_update_quote(self) -> None: ...
    def read_update_result(self) -> str | None: ...
    def dismiss_result(self) -> None: ...
    def close(self) -> None: ...


class QuotationInput(Protocol):
    worksheet: object
    def validate_schema(self) -> None: ...
    def write_payload(self, payload: tuple[str, ...]) -> None: ...
    def read_payload(self) -> tuple[str, ...]: ...


class WorkflowQuotationSource:
    """Read-only original identity/status and competition verification."""
    def __init__(self, *, reader: WorksheetRowReader, store: ExistingInquiryStore):
        self._reader, self._store = reader, store

    def status(self, result: V13QuotationResult) -> str:
        if result.inquiry_id is None or result.record_identity is None:
            raise V13SourceRowError(RowErrorReason.SOURCE_CHANGED)
        try:
            item = self._store.get_by_inquiry_id(result.inquiry_id)
        except KeyError:
            raise V13SourceRowError(RowErrorReason.SOURCE_CHANGED) from None
        except Exception:  # noqa: BLE001 - only shared ledger read, sanitized
            raise V12Fault(FaultScope.GLOBAL_STOP, "WORKFLOW_LEDGER_UNAVAILABLE") from None
        try:
            items = tuple(self._store.all_items())
        except Exception:  # noqa: BLE001 - whole ledger read cannot become a row failure
            raise V12Fault(FaultScope.GLOBAL_STOP, "WORKFLOW_LEDGER_UNAVAILABLE") from None
        if item.record_identity != result.record_identity:
            raise V13SourceRowError(RowErrorReason.SOURCE_CHANGED)
        worksheet = result.record_identity.worksheet
        try:
            rows = tuple(self._reader.read_rows(worksheet))
        except Exception:  # noqa: BLE001 - only shared Sheets read
            raise V12Fault(FaultScope.GLOBAL_STOP, "SHEETS_READ_UNAVAILABLE") from None
        def locate(original):
            brand = (original.resolved_brand if original.brand_update_status == "UPDATED"
                     else original.record_identity.identifying_snapshot.brand)
            return relocate_quotation_status(original.record_identity, rows,
                expected_brand=brand, accepted_statuses=("发给采购", "采购已报价"))
        try:
            target = locate(item)
        except SheetRecordConflict:
            raise V13SourceRowError(RowErrorReason.SOURCE_CHANGED) from None
        bindings = []
        for other in items:
            if other.record_identity.worksheet != worksheet:
                continue
            try:
                current = locate(other)
            except QuotationSourceAmbiguous as exc:
                if target.row_position in exc.row_positions:
                    raise V13SourceRowError(RowErrorReason.SOURCE_CHANGED) from None
                continue
            except SheetRecordConflict:
                continue
            if current.row_position == target.row_position:
                bindings.append(other.inquiry_id)
        if bindings != [result.inquiry_id]:
            raise V13SourceRowError(RowErrorReason.SOURCE_CHANGED)
        return str(target.cells[worksheet_schema(worksheet.worksheet).status_column])


class V13QuotationUpdater:
    """No source write, INSO query, quarantine, GUI/mail or scheduler."""
    def __init__(self, *, source: WorkflowQuotationSource, quotation_input: QuotationInput,
                 actions: QuotationUpdateActions, wait: Callable[[float], bool],
                 stop_requested: Callable[[], bool] = lambda: False,
                 status_reads: int = 31, status_interval: float = 1.0,
                 clock: Callable[[], float] = monotonic):
        if not 1 <= status_reads <= 31 or not 0 < status_interval <= 5:
            raise ValueError("status polling must be short and bounded")
        self._source, self._input, self._actions = source, quotation_input, actions
        self._wait, self._stop = wait, stop_requested
        self._status_reads, self._status_interval = status_reads, status_interval
        self._clock = clock

    def run(self, results: Iterable[V13QuotationResult]) -> tuple[V13QuotationResult, ...]:
        output = []
        for result in results:
            self._check_stop()
            output.append(self.update_one(result))
        return tuple(output)

    def update_one(self, result: V13QuotationResult) -> V13QuotationResult:
        if result.outcome is not QuotationOutcome.QUOTE_FOUND:
            return result
        self._check_stop()
        if result.record_identity is None or result.quotation is None or result.inquiry_id is None:
            return self._failed(result, RowErrorReason.SOURCE_CHANGED)
        if self._input.worksheet.spreadsheet != result.record_identity.worksheet.spreadsheet:
            raise V12Fault(FaultScope.GLOBAL_STOP, "QUOTE_INPUT_LOCATION_INVALID")
        payload = result.quotation.payload
        try:
            for _attempt in range(4):
                self._check_stop()
                if self._current_status(result) == "采购已报价":
                    return self._success(result, UpdatePopupOutcome.ALREADY_EXISTS)
                # Binding/header faults must stop before opening a possibly wrong gid.
                self._input.validate_schema()
                try:
                    self._actions.open_quote_input()
                    write_reason = RowErrorReason.QUOTE_INPUT_WRITE_FAILED
                    for _write_attempt in range(4):
                        self._check_stop()
                        if self._current_status(result) == "采购已报价":
                            return self._success(result, UpdatePopupOutcome.ALREADY_EXISTS)
                        self._input.validate_schema()
                        try:
                            self._input.write_payload(payload)
                            write_reason = RowErrorReason.QUOTE_INPUT_READBACK_MISMATCH
                            if self._input.read_payload() != payload:
                                continue
                            # Source is still this order; final exact input read occurs
                            # immediately before the only submit action (no write in between).
                            if self._current_status(result) == "采购已报价":
                                return self._success(result, UpdatePopupOutcome.ALREADY_EXISTS)
                            if self._input.read_payload() != payload:
                                continue
                            break
                        except QuotationInputAttemptFailed as exc:
                            write_reason = (RowErrorReason.QUOTE_INPUT_READBACK_MISMATCH
                                            if str(exc) == "QUOTE_INPUT_READBACK_MISMATCH"
                                            else RowErrorReason.QUOTE_INPUT_WRITE_FAILED)
                    else:
                        return self._failed(result, write_reason)
                    self._actions.click_update_quote()
                    popup = parse_update_popup(self._actions.read_update_result())
                    if popup is UpdatePopupOutcome.UNCONFIRMED:
                        continue
                    # A successful popup is final submission proof; dismiss failure
                    # never re-enters update retries. Only source status is polled.
                    try:
                        self._actions.dismiss_result()
                    except UpdateAttemptUnconfirmed:
                        pass
                    return self._verify_status(result, popup)
                except UpdateAttemptUnconfirmed:
                    continue
                finally:
                    self._actions.close()
            return self._failed(result, RowErrorReason.UPDATE_RESULT_UNCONFIRMED)
        except V13SourceRowError as exc:
            return self._failed(result, exc.reason)
        except QuotationInputUnavailable as exc:
            raise V12Fault(FaultScope.GLOBAL_STOP, exc.reason) from None

    def _current_status(self, result):
        status = self._source.status(result)
        if status not in {"发给采购", "采购已报价"}:
            raise V13SourceRowError(RowErrorReason.SOURCE_CHANGED)
        return status

    def _verify_status(self, result, popup):
        # Both inserted and already-priced Script results are accepted execution.
        # Status must settle independently within a bounded 30-second window.
        deadline = self._clock() + 30.0
        for read_number in range(self._status_reads):
            self._check_stop()
            if self._current_status(result) == "采购已报价":
                return self._success(result, popup)
            remaining = deadline - self._clock()
            if remaining <= 0 or read_number + 1 == self._status_reads:
                break
            if self._wait(min(self._status_interval, remaining)):
                raise V13Stopped("STOP_REQUESTED")
        return self._failed(result, RowErrorReason.SOURCE_STATUS_NOT_UPDATED)

    def _check_stop(self):
        if self._stop():
            raise V13Stopped("STOP_REQUESTED")

    @staticmethod
    def _failed(result, reason):
        return replace(result, outcome=QuotationOutcome.ROW_FAILED, row_error_reason=reason)

    @staticmethod
    def _success(result, popup):
        return replace(result, outcome=(QuotationOutcome.UPDATED_INSERTED
            if popup is UpdatePopupOutcome.INSERTED else QuotationOutcome.UPDATED_ALREADY_EXISTS),
            row_error_reason=None)
