"""RFQ-004 operation adapter; no GUI, scheduler, mail or release integration."""
from contextlib import ExitStack, contextmanager
from contextvars import ContextVar

from src.inso.session import SecurityViolation
from src.research.cdp_pages import PageTargetOwnershipError, mark_owned_page, page_owner
from src.workflow.v12_faults import FaultScope, V12Fault

from .inso_session import (
    InsoAuthenticationError,
    InsoSessionGuard,
    InsoSessionOutcome,
    attach_inso_research_session,
    authenticated_inso_shell_available,
)

_POLL_OPERATIONS = ContextVar("poll_quotation_operations", default=None)


@contextmanager
def quotation_operation_scope():
    operations = []
    token = _POLL_OPERATIONS.set(operations)
    try:
        yield
    finally:
        _POLL_OPERATIONS.reset(token)
        with ExitStack() as closing:
            for operation in operations:
                operation._retain = False
                closing.callback(operation.close)


def settle_quotation_operations():
    """Confirm/release only this original Owner's closed quotation operations."""
    operations = _POLL_OPERATIONS.get()
    if operations is None:
        return False
    for operation in operations:
        if operation._protected or operation._session is not None and not operation._released:
            return False
        if operation._session is not None:
            page = operation._session.operation_access().operation_page().page
            if page_owner(page) != "quotation-operation":
                operation.preserve()
                raise PageTargetOwnershipError((ValueError("QUOTATION_OWNER_UNCONFIRMED"),))
            if not authenticated_inso_shell_available(operation._handle.browser):
                operation.preserve()  # Observation only; no login or credential action.
                return False
        operation.reset()  # Existing exact-owned-tab cleanup, never a guessed page.
        if operation._session is not None:
            raise V12Fault(FaultScope.GLOBAL_STOP, "INSO_OPERATION_NOT_CLOSED")
    return True


def quotation_operations(*, browser_handle, login):
    """One quotation tab across both worksheets, outside polls retain old behavior."""
    pool = _POLL_OPERATIONS.get()
    available = [operation for operation in pool or [] if not operation._protected]
    if available:
        operation = available[-1]
        if operation._handle is not browser_handle:
            raise V12Fault(FaultScope.GLOBAL_STOP, "CDP_SESSION_UNAVAILABLE")
        return operation
    operation = V13QuotationOperations(browser_handle=browser_handle, login=login)
    if pool is not None:
        operation._retain = True
        pool.append(operation)
    return operation


class V13QuotationOperations:
    """Use the caller's existing fixed CDP handle and Core-login capability.

    No browser acquisition, configuration or credential implementation is added.
    Caller owns the shared client; normal cleanup closes only this owned tab.
    RFQ-006 will compose this adapter into the existing production runtime.
    """
    def __init__(self, *, browser_handle, login, attach=attach_inso_research_session):
        if browser_handle.owned:
            raise ValueError("V1.3 requires the existing protected shared CDP handle")
        self._handle, self._login, self._attach = browser_handle, login, attach
        self._session = None
        self._protected = False
        self._retain = False
        self._released = False

    def open(self, inquiry_id):
        if self._protected:
            raise V12Fault(FaultScope.GLOBAL_STOP, "INSO_AUTHENTICATION_REQUIRED")
        if self._session is not None:
            if not self._retain or not self._released:
                raise V12Fault(FaultScope.GLOBAL_STOP, "INSO_OPERATION_NOT_CLOSED")
            try:
                # Re-establish the known list through the existing login/menu guard.
                # An invalid old lease is preserved, never navigated blindly.
                page = self._session.operation_access().operation_page().page
            except SecurityViolation:
                # The previous phase lost its menu/identity. Leave that page
                # untouched and let the new phase take the ordinary fresh path.
                self._session = None
            else:
                return self._reopen(page, inquiry_id)
        try:
            self._session = self._attach(
                "http://127.0.0.1:9222", self._handle,
                cycle_id=inquiry_id, cycle_is_drained=lambda _: False,
                login=self._login, fresh_page=True,
            )
            if not self._session.owns_operation_page:
                self.preserve()
                raise V12Fault(FaultScope.GLOBAL_STOP, "FRESH_OPERATION_REQUIRED")
            self._released = False
            if self._retain:
                mark_owned_page(self._session.operation_access().operation_page().page, "quotation-operation")
            return self._session.operation_access()
        except InsoAuthenticationError:
            # Existing RFQ-002 attachment preserves manual-verification pages.
            self.preserve()
            raise V12Fault(FaultScope.GLOBAL_STOP, "INSO_AUTHENTICATION_REQUIRED") from None
        except V12Fault:
            raise
        except Exception:  # noqa: BLE001 - shared acquisition failure, never no quotation
            raise V12Fault(FaultScope.GLOBAL_STOP, "CDP_SESSION_UNAVAILABLE") from None

    def _reopen(self, page, inquiry_id):
        try:
            guard = InsoSessionGuard(login=self._login, context=lambda: page.context,
                                     page=lambda: page)
            status = guard.ensure_authenticated()
            if status.outcome is InsoSessionOutcome.DEAD:
                raise InsoAuthenticationError(status.reason_code)
            self._session = self._attach(
                "http://127.0.0.1:9222", self._handle,
                cycle_id=inquiry_id, cycle_is_drained=lambda _: False,
                operation_page=page, owns_operation_page=True,
                preserve_operation_page_on_failure=True,
            )
            self._released = False
            return self._session.operation_access()
        except (SecurityViolation, InsoAuthenticationError):
            self.preserve()
            raise V12Fault(FaultScope.GLOBAL_STOP, "INSO_AUTHENTICATION_REQUIRED") from None
        except V12Fault:
            raise
        except Exception:  # noqa: BLE001 - shared acquisition failure, never no quotation
            raise V12Fault(FaultScope.GLOBAL_STOP, "CDP_SESSION_UNAVAILABLE") from None

    def preserve(self):
        self._protected = True

    def reset(self):
        # Failed reads still close BEFORE the existing 120-second retry wait.
        retain, self._retain = self._retain, False
        try:
            self.close()
        finally:
            self._retain = retain

    def close(self):
        if self._protected:
            return
        if self._session is not None:
            session = self._session
            try:
                page = session.operation_access().operation_page().page
            except SecurityViolation:
                self.preserve()
                raise V12Fault(FaultScope.GLOBAL_STOP, "INSO_AUTHENTICATION_REQUIRED") from None
            if self._retain:
                self._released = True
                return
            session.close_owned_operation_tab()
            if not page.is_closed():
                raise V12Fault(FaultScope.GLOBAL_STOP, "INSO_OPERATION_NOT_CLOSED")
            self._session = None
