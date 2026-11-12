"""Persist the step a launcher leg died at -- and nothing else.

A failed run is read back from ``runtime/logs/INSO_V1.2.log``, but that file is
one the operator can open, so the runtime filter in ``src/gui/main.py`` drops
everything that is not our own vocabulary. Field values, customer names, page
text and ERP identifiers must never reach it.

That filter is also why this module exists: a plain ``log.warning`` from a leg
was silently discarded, so a draft that never reached the AI录单 panel looked
exactly like one that died after the ERP handed its row back. The step label is
one of our own constants and the cause is an exception *class name*; together
they are the entire payload, and that is the whole point.
"""

from __future__ import annotations

import logging
from typing import Final

#: The one logger the runtime log filter rebuilds instead of dropping. Changing
#: it without teaching the filter the new name silently loses every step again.
LOG_NAME: Final = "inso.diagnostics"

_LOG = logging.getLogger(LOG_NAME)

# Exact internal messages only; arbitrary exception text is never written.
_SECURITY_DETAILS = {
    "operation identity is required": "OPERATION_IDENTITY_MISSING",
    "app-owned browser cycle has not drained": "BROWSER_CYCLE_NOT_DRAINED",
    "session lease is not active": "SESSION_LEASE_INACTIVE",
    "browser or context is stale": "BROWSER_CONTEXT_STALE",
    "browser endpoint identity changed": "BROWSER_ENDPOINT_CHANGED",
    "browser identity changed": "BROWSER_IDENTITY_CHANGED",
    "context belongs to a different browser": "BROWSER_CONTEXT_MISMATCH",
    "context identity changed": "CONTEXT_IDENTITY_CHANGED",
    "verified shell page is closed": "SHELL_PAGE_CLOSED",
    "verified shell page identity changed": "SHELL_PAGE_CHANGED",
    "verified INSO shell identity is stale": "INSO_SHELL_STALE",
    "INSO_OPERATION_NOT_CLOSED": "INSO_OPERATION_NOT_CLOSED",
    "INSO authenticated context is not unique": "INSO_CONTEXT_NOT_UNIQUE",
    "verified authenticated INSO shell is not unique": "INSO_SHELL_NOT_UNIQUE",
    "INSO origin is not verified": "INSO_ORIGIN_UNVERIFIED",
    "AI entry frame identity is not verified": "AI_FRAME_UNVERIFIED",
    "AI entry panel did not open": "AI_PANEL_NOT_OPENED",
    "AI entry panel is not open": "AI_PANEL_NOT_OPEN",
    "AI entry dialog is not unique": "AI_DIALOG_NOT_UNIQUE",
    "AI entry control is not uniquely actionable": "AI_CONTROL_UNAVAILABLE",
    "parent form frame is unavailable": "PARENT_FRAME_UNAVAILABLE",
    "parent form frame is not unique": "PARENT_FRAME_NOT_UNIQUE",
    "parent product field is not uniquely actionable": "PARENT_FIELD_UNAVAILABLE",
    "select menu option is missing or ambiguous": "SELECT_OPTION_UNAVAILABLE",
    "select menu did not close": "SELECT_MENU_NOT_CLOSED",
    "field read-back did not match input": "FIELD_READBACK_MISMATCH",
    "purchaser selection was not confirmed": "PURCHASER_NOT_CONFIRMED",
    "order form frame is not unique": "ORDER_FRAME_NOT_UNIQUE",
    "order window dialog is not unique": "ORDER_DIALOG_NOT_UNIQUE",
    "INSO control changed before dispatch": "INSO_CONTROL_CHANGED",
    "allowlisted control was not found": "CONTROL_NOT_FOUND",
    "allowlisted control is ambiguous": "CONTROL_AMBIGUOUS",
    "resolved control is not actionable": "CONTROL_NOT_ACTIONABLE",
    "resolved control semantics changed": "CONTROL_SEMANTICS_CHANGED",
}
SECURITY_DETAIL_CODES = frozenset(_SECURITY_DETAILS.values()) | {"SECURITY_OTHER"}
LOGIN_FAILURE_REASONS = frozenset({
    "AUTHENTICATION_REQUIRED", "BROWSER_TIMEOUT", "LOGIN_PAGE_UNAVAILABLE",
    "AUTHENTICATED_SHELL_UNAVAILABLE", "SESSION_IDENTITY_UNVERIFIED",
    "MANUAL_VERIFICATION_REQUIRED", "CREDENTIAL_REJECTED", "OTHER",
})
DIAGNOSTIC_ORIGIN_MODULES = frozenset({
    "src.inso.session", "src.inso.purchase_writer", "src.inso.write_safety",
    "src.inso.discovery", "src.launcher.inso_session", "src.launcher.v12_composition",
    "src.launcher.backend", "src.workflow.v12_flow",
})


def _safe_security_diagnostic(cause):
    if cause is None or type(cause).__name__ != "SecurityViolation" or type(cause).__module__ != "src.inso.session":
        return None, None
    try:
        detail = _SECURITY_DETAILS.get(str(cause), "SECURITY_OTHER")
    except Exception:  # noqa: BLE001 - logging must never alter business control flow
        detail = "SECURITY_OTHER"
    origin, trace = None, cause.__traceback__
    while trace is not None:
        module = trace.tb_frame.f_globals.get("__name__")
        if (isinstance(module, str) and module in DIAGNOSTIC_ORIGIN_MODULES
                and 0 < trace.tb_lineno < 10000):
            origin = f"{module}:{trace.tb_lineno}"
        trace = trace.tb_next
    return detail, origin


def log_purchase_login_failure(phase: str, reason: str | None, *, inquiry_id: str | None = None) -> None:
    if not isinstance(phase, str) or phase not in {"before", "after"}:
        return
    safe_reason = reason if isinstance(reason, str) and reason in LOGIN_FAILURE_REASONS else "OTHER"
    _LOG.warning("purchase login failure", extra={
        "inso_login_phase": phase, "inso_login_reason": safe_reason,
        "diagnostic_inquiry": inquiry_id,
    })


def log_step(step: str, *, cause: BaseException | None = None, inquiry_id: str | None = None) -> None:
    """Record which control-flow step one leg failed at.

    ``step`` is one of our own labels (``prepare``, ``commit-ai-entry``,
    ``parent-row-missing``, ...), never site or field text. ``cause``
    contributes only ``type(cause).__name__``: the exception's message is where
    page and customer text hides, so it is never read.
    """

    detail, origin = _safe_security_diagnostic(cause)
    _LOG.warning(
        "workflow step failed at %s",
        step,
        extra={
            "inso_step": step,
            "inso_cause": None if cause is None else type(cause).__name__,
            "inso_detail": detail,
            "inso_origin": origin,
            "diagnostic_inquiry": inquiry_id,
        },
        # An exception *instance* is accepted here and pins the traceback to the
        # cause we were handed rather than to whatever is on the stack.
        exc_info=cause,
    )
