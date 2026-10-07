"""Shared RFQ-003 read-query recovery; no inter-row cooldown."""
from collections.abc import Callable
from typing import TypeVar

from .v12_faults import FaultScope, V12Fault

T = TypeVar("T")


def run_inso_query(
    operation: Callable[[], T], *, succeeded: Callable[[T], bool],
    reset: Callable[[], None], wait: Callable[[int], bool],
    prepare: Callable[[], None] = lambda: None,
    stop_fault: Callable[[], Exception] = lambda: V12Fault(FaultScope.V12_PAUSE, "STOP_REQUESTED"),
) -> T:
    """Initial + three retries, close BEFORE interruptible 180-second wait.

    Operation adapters classify recoverable query failures as unsuccessful
    results. Typed authentication/shared faults propagate immediately, with no
    reset that could close a human-needed page.
    """
    for attempt in range(4):
        prepare()
        result = operation()
        if succeeded(result):
            return result
        reset()
        if attempt == 3:
            raise V12Fault(FaultScope.GLOBAL_STOP, "INSO_QUERY_RETRIES_EXHAUSTED")
        if wait(180):
            raise stop_fault()
    raise AssertionError("bounded query loop exhausted")
