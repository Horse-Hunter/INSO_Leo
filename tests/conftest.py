"""Suite-wide guards that no ordinary test is allowed to cross.

The load-bearing one is the mail guard.

``ProductionBackend`` composes the *real* production adapters, the QQ SMTP
transport included, because that is exactly what the launcher must do. A test
that merely observes that composition therefore holds a live transport, and one
of them reached it through a real code path: it handed the captured observer a
``remarks="需要人工验证"`` result, the observer called the real
``backend._manual_review``, and the real transport delivered the operator alert
to the Owner's mailbox. Running the suite mailed a human -- once per run.

Tests are not the operator. So a connection has to be impossible rather than
merely discouraged: these guards replace the SMTP entry points with something
that raises, which turns "this test forgot to inject a fake" into a loud local
failure instead of an email nobody asked for.
"""

from __future__ import annotations

import os
import smtplib
from typing import Any

import pytest


class OutboundMailForbidden(RuntimeError):
    """A test tried to open a real SMTP connection instead of injecting a fake."""


#: Every refused attempt, as ``(test id, mail was attempted)``. Recorded rather
#: than merely raised because the production alert path is *supposed* to swallow
#: its own delivery failures -- the operator's run must not be disturbed by a
#: mail server. Swallowing is right in production and invisible in a test, so
#: the attempt is what has to be made visible.
_OUTBOUND_ATTEMPTS: list[str] = []


def _refuse(*_args: Any, **_kwargs: Any) -> Any:
    _OUTBOUND_ATTEMPTS.append(os.environ.get("PYTEST_CURRENT_TEST", "unknown test"))
    raise OutboundMailForbidden(
        "a test tried to open a real SMTP connection; inject a transport or an "
        "smtp_factory instead (see tests/workflow/test_v12_smtp_transport.py)"
    )


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """Shout about every outbound-mail attempt once the run is over."""

    if not _OUTBOUND_ATTEMPTS:
        return
    reporter = session.config.pluginmanager.get_plugin("terminalreporter")
    if reporter is None:
        return
    reporter.write_sep("=", "OUTBOUND MAIL WAS ATTEMPTED BY THESE TESTS")
    for attempt in _OUTBOUND_ATTEMPTS:
        reporter.write_line(f"  {attempt}")
    reporter.write_line(
        "  (blocked locally -- nothing left the machine, but each one must be "
        "given a fake instead)"
    )


@pytest.fixture(autouse=True)
def _forbid_outbound_mail(monkeypatch: pytest.MonkeyPatch):
    """Make every real SMTP entry point unusable for the duration of a test."""

    monkeypatch.setattr(smtplib, "SMTP_SSL", _refuse, raising=False)
    monkeypatch.setattr(smtplib, "SMTP", _refuse, raising=False)
    yield
