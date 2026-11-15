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


def pytest_configure(config):
    # A failed test can leave a worker alive past fixture teardown. Keep the
    # process-wide floor closed even between tests and after pytest returns;
    # explicit synthetic SMTP factories may still be installed per test.
    _OUTBOUND_ATTEMPTS.clear()
    smtplib.SMTP_SSL = _refuse
    smtplib.SMTP = _refuse


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


def pytest_sessionstart(session: pytest.Session) -> None:
    """Prove the session's temporary tree can hold a real WAL ledger.

    RFQ-021-R4 lost six launcher tests to `WORKFLOW_LEDGER_UNAVAILABLE <-
    sqlite3.OperationalError(attempt to write a readonly database)` in a run whose
    temporary tree was not writable (a restricted/sandboxed process had created
    it). Every one of those tests passes in a writable tree, and a WAL database
    whose side files cannot be written reproduces exactly that error on
    `BEGIN IMMEDIATE`.

    An environment that cannot host the ledger is a broken test environment, not
    six unrelated product failures. This probe says so once, up front, with the
    path and the underlying error, instead of leaving opaque partial failures
    behind. It does not skip, deselect or weaken any test.
    """

    import sqlite3
    import tempfile
    from pathlib import Path

    factory = session.config._tmp_path_factory  # pytest's own factory
    try:
        base = Path(factory.getbasetemp())
    except Exception as exc:  # noqa: BLE001 - report, never mask
        raise pytest.UsageError(
            f"pytest cannot create its temporary tree: {exc}. RFQ-021: run the suite "
            "from a session that may write its own temp directory."
        ) from None
    probe = os.path.join(tempfile.mkdtemp(prefix="ledger-probe-", dir=str(base)), "probe.sqlite3")
    try:
        connection = sqlite3.connect(probe, timeout=5)
        try:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("CREATE TABLE probe (a INTEGER)")
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("INSERT INTO probe VALUES (1)")
            connection.commit()
            rows = connection.execute("SELECT count(*) FROM probe").fetchone()[0]
        finally:
            connection.close()
        if rows != 1:
            raise sqlite3.OperationalError("the probe row did not persist")
    except (sqlite3.Error, OSError) as exc:
        raise pytest.UsageError(
            "RFQ-021: this session's temporary tree cannot hold a WAL ledger "
            f"({probe}): {exc}. The suite would fail with misleading "
            "'attempt to write a readonly database' faults; run it from a session "
            "that owns and may write its temp directory."
        ) from None
