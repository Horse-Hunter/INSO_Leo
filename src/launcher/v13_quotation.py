"""RFQ-004 operation adapter; no GUI, scheduler, mail or release integration."""
from src.inso.session import SecurityViolation
from src.workflow.v12_faults import FaultScope, V12Fault

from .inso_session import InsoAuthenticationError, attach_inso_research_session


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

    def open(self, inquiry_id):
        if self._protected:
            raise V12Fault(FaultScope.GLOBAL_STOP, "INSO_AUTHENTICATION_REQUIRED")
        if self._session is not None:
            raise V12Fault(FaultScope.GLOBAL_STOP, "INSO_OPERATION_NOT_CLOSED")
        try:
            self._session = self._attach(
                "http://127.0.0.1:9222", self._handle,
                cycle_id=inquiry_id, cycle_is_drained=lambda _: False,
                login=self._login, fresh_page=True,
            )
            if not self._session.owns_operation_page:
                self.preserve()
                raise V12Fault(FaultScope.GLOBAL_STOP, "FRESH_OPERATION_REQUIRED")
            return self._session.operation_access()
        except InsoAuthenticationError:
            # Existing RFQ-002 attachment preserves manual-verification pages.
            self.preserve()
            raise V12Fault(FaultScope.GLOBAL_STOP, "INSO_AUTHENTICATION_REQUIRED") from None
        except V12Fault:
            raise
        except Exception:  # noqa: BLE001 - shared acquisition failure, never no quotation
            raise V12Fault(FaultScope.GLOBAL_STOP, "CDP_SESSION_UNAVAILABLE") from None

    def preserve(self):
        self._protected = True

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
            session.close_owned_operation_tab()
            if not page.is_closed():
                raise V12Fault(FaultScope.GLOBAL_STOP, "INSO_OPERATION_NOT_CLOSED")
            self._session = None
