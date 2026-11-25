"""A page that would not come up must not stop the program for a day.

Production 2026-11-24 20:52: the quotation cycle failed with
``InsoAuthenticationError(AUTHENTICATED_SHELL_UNAVAILABLE)``, the module boundary
treated it as a shared stop, and the program sat dead for 25 hours. Nobody was
told either, because the stop's own code could not be recorded.
"""
import re

import pytest

from src.launcher.backend import (
    _INSO_TRANSIENT_SESSION_CODES,
    _UNCLASSIFIED_STOP_REASON,
    _classified_stop_reason,
    _is_transient_inso_session_failure,
)
from src.launcher.inso_session import InsoAuthenticationError
from src.workflow.v12_faults import FaultScope, V12Fault

#: The four codes a human really has to handle.
HUMAN_CODES = (
    "MANUAL_VERIFICATION_REQUIRED", "CREDENTIAL_REJECTED",
    "AUTHENTICATION_REQUIRED", "SESSION_IDENTITY_UNVERIFIED",
)


def _stopped_chain(code):
    """The exact shape production produced: a wrapper that hides the real reason.

    ``from None`` clears ``__cause__`` but keeps ``__context__``, which is what the
    classifier walks.
    """

    try:
        raise InsoAuthenticationError(code)
    except InsoAuthenticationError:
        try:
            raise V12Fault(FaultScope.GLOBAL_STOP, "V13_INTERNAL_FAILURE") from None
        except V12Fault as fault:
            return fault


@pytest.mark.parametrize("code", sorted(_INSO_TRANSIENT_SESSION_CODES))
def test_a_page_or_connection_failure_is_not_a_shared_stop(code):
    assert _is_transient_inso_session_failure(_stopped_chain(code)) is True


@pytest.mark.parametrize("code", HUMAN_CODES)
def test_a_real_challenge_or_rejection_still_stops_the_world(code):
    """The narrowing must not soften a genuine login verdict."""

    assert _is_transient_inso_session_failure(_stopped_chain(code)) is False


def test_an_unrelated_shared_stop_is_untouched():
    ledger = V12Fault(FaultScope.GLOBAL_STOP, "WORKFLOW_LEDGER_UNAVAILABLE")

    assert _is_transient_inso_session_failure(ledger) is False
    assert _classified_stop_reason(ledger) == "WORKFLOW_LEDGER_UNAVAILABLE"


def test_the_recorded_code_comes_from_the_chain_not_the_wrapper():
    """The wrapper's own code cannot be recorded (digits); the real one can."""

    assert _classified_stop_reason(_stopped_chain("AUTHENTICATED_SHELL_UNAVAILABLE")) == (
        "AUTHENTICATED_SHELL_UNAVAILABLE")


def test_a_stop_with_no_usable_code_says_so_and_stays_reviewable():
    bare = V12Fault(FaultScope.GLOBAL_STOP, "V13_INTERNAL_FAILURE")

    assert _classified_stop_reason(bare) == _UNCLASSIFIED_STOP_REASON
    # The notification review enforces this shape; the old fallback failed it,
    # which is why the 2026-11-24 stop was silently suppressed.
    assert re.fullmatch(r"[A-Z_]{1,64}", _UNCLASSIFIED_STOP_REASON)
