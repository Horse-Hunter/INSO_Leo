"""RFQ-021 negatives: a write intent must outlive the process that made it."""

from __future__ import annotations

import pytest

from src.launcher.run_scope import ExternalWritePolicy, RunScope
from src.research.cdp_pages import (
    DocumentWriteBlocked,
    DocumentWriteHeld,
    PageResourceAdmission,
    _intent_document_key,
)
from src.workflow.write_intents import (
    SqliteWriteIntentJournal,
    WriteLedgerUnavailable,
)

DOCUMENT = ("https", "docs.google.com", "/spreadsheets/d/synthetic/edit")


def journal_at(path) -> SqliteWriteIntentJournal:
    journal = SqliteWriteIntentJournal(path)
    journal.migrate()
    return journal


def admission_with(path) -> PageResourceAdmission:
    admission = PageResourceAdmission()
    admission.attach_write_journal(journal_at(path))
    return admission


# --- journal primitives -----------------------------------------------------

def test_intent_is_durable_before_the_request(tmp_path):
    path = tmp_path / "safety.sqlite3"
    first = journal_at(path)
    intent = first.begin(_intent_document_key(DOCUMENT), "GOOGLE_WRITE")
    # A second connection (a restarted process) must already see it.
    restarted = SqliteWriteIntentJournal(path)
    assert restarted.open_reason(_intent_document_key(DOCUMENT)) == "WRITE_INTENT_PENDING"
    assert restarted.open_documents() == {_intent_document_key(DOCUMENT): "WRITE_INTENT_PENDING"}
    assert intent.startswith("wi_")


def test_settled_intent_no_longer_blocks(tmp_path):
    path = tmp_path / "safety.sqlite3"
    journal = journal_at(path)
    intent = journal.begin(_intent_document_key(DOCUMENT), "GOOGLE_WRITE")
    journal.settle(intent)
    assert journal.open_reason(_intent_document_key(DOCUMENT)) is None
    assert journal.open_documents() == {}


def test_unknown_intent_keeps_blocking(tmp_path):
    path = tmp_path / "safety.sqlite3"
    journal = journal_at(path)
    intent = journal.begin(_intent_document_key(DOCUMENT), "GOOGLE_WRITE")
    journal.mark_unknown(intent, "UPDATE_RESULT_UNCONFIRMED")
    assert journal.open_reason(_intent_document_key(DOCUMENT)).startswith("WRITE_INTENT_UNKNOWN")
    journal.settle(intent)  # explicit reconciliation is still allowed
    assert journal.open_reason(_intent_document_key(DOCUMENT)) is None


def test_unreadable_ledger_is_refused_by_the_journal(tmp_path):
    directory = tmp_path / "not-a-database"
    directory.mkdir()
    journal = SqliteWriteIntentJournal(directory)
    with pytest.raises(WriteLedgerUnavailable):
        journal.migrate()
    with pytest.raises(WriteLedgerUnavailable):
        journal.begin("k", "GOOGLE_WRITE")


# --- admission integration --------------------------------------------------

def test_a_crashed_write_blocks_the_next_process(tmp_path):
    path = tmp_path / "safety.sqlite3"
    crashed = admission_with(path)
    crashed.begin_document_write(DOCUMENT, object())
    # The process dies here: no end_document_write, no settlement.

    restarted = admission_with(path)
    with pytest.raises(DocumentWriteHeld) as info:
        restarted.begin_document_write(DOCUMENT, object())
    assert info.value.reason == "WRITE_INTENT_PENDING"
    with pytest.raises(DocumentWriteHeld):
        restarted.require_document_writable(DOCUMENT)


def test_an_unconfirmed_hold_is_not_settled_by_releasing_the_lease(tmp_path):
    path = tmp_path / "safety.sqlite3"
    admission = admission_with(path)
    owner = object()
    admission.begin_document_write(DOCUMENT, owner)
    admission.hold_document(DOCUMENT, owner, "UPDATE_RESULT_UNCONFIRMED")
    admission.end_document_write(DOCUMENT, owner)

    restarted = admission_with(path)
    with pytest.raises(DocumentWriteHeld) as info:
        restarted.require_document_writable(DOCUMENT)
    assert info.value.reason.startswith("WRITE_INTENT_UNKNOWN")


def test_a_confirmed_write_settles_and_reopens_the_document(tmp_path):
    path = tmp_path / "safety.sqlite3"
    admission = admission_with(path)
    owner = object()
    admission.begin_document_write(DOCUMENT, owner)
    admission.end_document_write(DOCUMENT, owner)

    restarted = admission_with(path)
    restarted.require_document_writable(DOCUMENT)  # no raise
    restarted.begin_document_write(DOCUMENT, object())


def test_an_unwritable_ledger_fails_closed_at_the_lease(tmp_path):
    admission = PageResourceAdmission()
    broken = SqliteWriteIntentJournal(tmp_path)  # a directory, not a database
    admission.attach_write_journal(broken)
    with pytest.raises(DocumentWriteHeld) as info:
        admission.begin_document_write(DOCUMENT, object())
    assert info.value.reason == "WRITE_LEDGER_UNAVAILABLE"


def test_scope_refusal_happens_before_any_intent_is_written(tmp_path):
    path = tmp_path / "safety.sqlite3"
    journal = journal_at(path)
    policy = ExternalWritePolicy(RunScope(
        inquiry_ids=frozenset({"inq_" + "a" * 24}),
        modules=frozenset({"inquiry"}),
        write_targets=frozenset(),
    ), enforced=True)
    admission = PageResourceAdmission(write_policy=policy)
    admission.attach_write_journal(journal)
    with pytest.raises(DocumentWriteBlocked) as info:
        admission.begin_document_write(DOCUMENT, object())
    assert info.value.reason == "EXTERNAL_WRITE_NOT_IN_SCOPE"
    assert journal.open_documents() == {}


def test_a_reentrant_same_owner_write_creates_only_one_intent(tmp_path):
    path = tmp_path / "safety.sqlite3"
    journal = journal_at(path)
    admission = PageResourceAdmission()
    admission.attach_write_journal(journal)
    owner = object()
    admission.begin_document_write(DOCUMENT, owner)
    admission.begin_document_write(DOCUMENT, owner)
    admission.end_document_write(DOCUMENT, owner)
    # Still leased after the first release: the intent must stay open.
    assert journal.open_documents() == {_intent_document_key(DOCUMENT): "WRITE_INTENT_PENDING"}
    admission.end_document_write(DOCUMENT, owner)
    assert journal.open_documents() == {}
