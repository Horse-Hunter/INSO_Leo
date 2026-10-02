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


def log_step(step: str, *, cause: BaseException | None = None) -> None:
    """Record which control-flow step one leg failed at.

    ``step`` is one of our own labels (``prepare``, ``commit-ai-entry``,
    ``parent-row-missing``, ...), never site or field text. ``cause``
    contributes only ``type(cause).__name__``: the exception's message is where
    page and customer text hides, so it is never read.
    """

    _LOG.warning(
        "workflow step failed at %s",
        step,
        extra={
            "inso_step": step,
            "inso_cause": None if cause is None else type(cause).__name__,
        },
        # An exception *instance* is accepted here and pins the traceback to the
        # cause we were handed rather than to whatever is on the stack.
        exc_info=cause,
    )
