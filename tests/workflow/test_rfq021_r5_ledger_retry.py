"""RFQ-021-R5: a *contended* WAL `BEGIN IMMEDIATE` is retried; a broken one is not.

Measured on this host (full suite, 2026-11-15): a sibling connection holding the
write lock makes `BEGIN IMMEDIATE` fail with `SQLITE_BUSY` even after the
connection timeout, and the same statement succeeds on a fresh connection one
moment later.

`SQLITE_READONLY` is deliberately *not* retried. It means the ledger cannot be
written at all -- the RFQ-021-R4 full-suite failures carried exactly that message
from a temporary tree that was not writable by the process. Retrying such a
ledger would only delay the fail-closed path and blur the real fault, so the
store still reports it immediately.

These tests pin both halves: a lock race is survivable, and a ledger that cannot
be written (or read) still fails closed without replaying anything.
"""

from __future__ import annotations

import sqlite3

import pytest

from src.workflow import v12_store
from src.workflow.v12_store import _transaction


class FlakyConnection:
    """A connection whose first BEGINs raise the configured error."""

    def __init__(self, failures: int, error: str = "database is locked"):
        self.failures = failures
        self.error = error
        self.begins = 0
        self.closed = False
        self.committed = False
        self.rolled_back = False

    def execute(self, statement, *_args):
        assert statement == "BEGIN IMMEDIATE"
        self.begins += 1
        if self.begins <= self.failures:
            raise sqlite3.OperationalError(self.error)
        return self

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


def _install(monkeypatch, connections):
    remaining = list(connections)

    def fake_connect(*_args, **_kwargs):
        return remaining.pop(0) if remaining else FlakyConnection(0)

    monkeypatch.setattr(v12_store, "_connect", fake_connect, raising=True)


def test_a_contended_begin_is_retried_and_the_body_runs(monkeypatch, tmp_path):
    first = FlakyConnection(failures=1)
    second = FlakyConnection(failures=0)
    _install(monkeypatch, [first, second])

    ran = []
    with _transaction(tmp_path / "ledger.sqlite3") as connection:
        ran.append(connection)

    assert ran == [second]
    assert first.closed is True
    assert first.rolled_back is False
    assert second.committed is True
    assert second.closed is True


def test_a_busy_extended_code_is_recognised(monkeypatch, tmp_path):
    error = sqlite3.OperationalError("database is locked")
    error.sqlite_errorcode = 517  # SQLITE_BUSY_SNAPSHOT

    class ReturnsBusySnapshot(FlakyConnection):
        def execute(self, statement, *_args):
            assert statement == "BEGIN IMMEDIATE"
            self.begins += 1
            raise error

    second = FlakyConnection(failures=0)
    _install(monkeypatch, [ReturnsBusySnapshot(failures=0), second])

    with _transaction(tmp_path / "ledger.sqlite3") as connection:
        assert connection is second


def test_a_persistent_lock_still_fails_closed(monkeypatch, tmp_path):
    # One attempt plus one per configured delay: the bound, not an endless loop.
    attempts = len(v12_store._BEGIN_RETRY_DELAYS) + 1
    connections = [FlakyConnection(failures=1) for _ in range(attempts)]
    _install(monkeypatch, connections)

    with pytest.raises(sqlite3.OperationalError) as info, _transaction(tmp_path / "ledger.sqlite3"):
        raise AssertionError("the body must never run on a locked ledger")

    assert "locked" in str(info.value)
    assert sum(connection.begins for connection in connections) == attempts
    assert all(connection.closed for connection in connections)


def test_a_readonly_ledger_is_not_retried(monkeypatch, tmp_path):
    """A ledger that cannot be written must fail at once, not after 0.35 s."""

    only = FlakyConnection(failures=1, error="attempt to write a readonly database")
    _install(monkeypatch, [only])

    with pytest.raises(sqlite3.OperationalError) as info, _transaction(tmp_path / "ledger.sqlite3"):
        raise AssertionError("the body must never run on a read-only ledger")

    assert "readonly" in str(info.value)
    assert only.begins == 1
    assert only.closed is True


def test_a_non_retryable_error_is_not_retried(monkeypatch, tmp_path):
    only = FlakyConnection(failures=1, error="no such table: workflow_items")
    _install(monkeypatch, [only])

    with pytest.raises(sqlite3.OperationalError), _transaction(tmp_path / "ledger.sqlite3"):
        raise AssertionError("the body must never run")


def test_a_real_wal_ledger_still_commits(tmp_path):
    """The retry path must not change the ordinary commit."""

    database = tmp_path / "ledger.sqlite3"
    connection = sqlite3.connect(database)
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("CREATE TABLE probe (a INTEGER)")
    connection.commit()
    connection.close()

    with _transaction(database) as connection:
        connection.execute("INSERT INTO probe VALUES (1)")

    check = sqlite3.connect(database)
    try:
        assert check.execute("SELECT count(*) FROM probe").fetchone()[0] == 1
    finally:
        check.close()
