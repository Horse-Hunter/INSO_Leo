"""One shared admission owns Google document write holds for every client."""

import threading
from types import SimpleNamespace

import pytest

from src.research.cdp_pages import (
    DocumentWriteBusy,
    DocumentWriteHeld,
    PageResourceAdmission,
    google_document_key,
    google_document_key_for_spreadsheet,
)

DOC = ("https", "docs.google.com", "/spreadsheets/d/test/edit")
OTHER = ("https", "docs.google.com", "/spreadsheets/d/other/edit")


def test_child_hold_is_visible_to_root_and_siblings():
    root = PageResourceAdmission()
    child = PageResourceAdmission(parent=root)
    sibling = PageResourceAdmission(parent=root)
    owner = object()

    child.hold_document(DOC, owner, "GOOGLE_QUOTE_WRITE_UNCONFIRMED")

    for admission in (root, child, sibling):
        with pytest.raises(DocumentWriteHeld) as raised:
            admission.require_document_writable(DOC)
        assert raised.value.reason == "GOOGLE_QUOTE_WRITE_UNCONFIRMED"
        assert raised.value.document == DOC


def test_root_hold_blocks_child_and_other_document_stays_writable():
    root = PageResourceAdmission()
    child = PageResourceAdmission(parent=root)

    root.hold_document(DOC, object(), "GOOGLE_WRITE_UNCONFIRMED")

    with pytest.raises(DocumentWriteHeld):
        child.require_document_writable(DOC)
    child.require_document_writable(OTHER)
    assert child.document_hold(OTHER) is None


def test_release_only_clears_the_same_owner():
    root = PageResourceAdmission()
    first, second = object(), object()
    root.hold_document(DOC, first, "first-unknown")
    root.hold_document(DOC, second, "second-unknown")

    root.release_document(DOC, first)
    with pytest.raises(DocumentWriteHeld) as raised:
        root.require_document_writable(DOC)
    assert raised.value.reason == "second-unknown"

    root.release_document(DOC, second)
    root.require_document_writable(DOC)


def test_duplicate_hold_is_idempotent_and_keeps_first_reason():
    root = PageResourceAdmission()
    owner = object()
    root.hold_document(DOC, owner, "first-reason")
    root.hold_document(DOC, owner, "second-reason")

    assert root.document_hold(DOC) == "first-reason"
    root.release_document(DOC, owner)
    assert root.document_hold(DOC) is None


def test_hold_does_not_break_reads_or_global_open_state():
    root = PageResourceAdmission()
    root.hold_document(DOC, object(), "GOOGLE_WRITE_UNCONFIRMED")

    root.require_open()
    assert root.is_open_nonblocking() is True


def test_document_keys_are_canonical_for_quote_url_and_api_id():
    assert google_document_key("https://docs.google.com/spreadsheets/d/test/edit#gid=0") == DOC
    assert google_document_key_for_spreadsheet("test") == DOC
    with pytest.raises(ValueError, match="GOOGLE_DOCUMENT_UNCONFIRMED"):
        google_document_key("https://example.com/spreadsheets/d/test/edit")


def test_unconfirmed_write_hold_survives_the_held_page_closing():
    """P0-A: page closure is not write-settlement evidence."""
    root = PageResourceAdmission()
    page = SimpleNamespace(is_closed=lambda: True)
    root.hold_document(DOC, object(), "GOOGLE_WRITE_UNCONFIRMED", page=page)

    assert root.document_hold(DOC) == "GOOGLE_WRITE_UNCONFIRMED"
    with pytest.raises(DocumentWriteHeld):
        root.require_document_writable(DOC)


def test_atomic_document_write_refuses_held_document():
    root = PageResourceAdmission()
    root.hold_document(DOC, object(), "GOOGLE_WRITE_UNCONFIRMED")
    with pytest.raises(DocumentWriteHeld):
        root.begin_document_write(DOC, object())


def test_atomic_document_write_allows_same_owner_and_rejects_competitor_thread():
    """P1-C: acquisition is atomic; same owner may nest; no sleep-based race."""
    root = PageResourceAdmission()
    owner = object()
    competitor = object()
    root.begin_document_write(DOC, owner)
    root.begin_document_write(DOC, owner)  # same-owner reentry

    outcomes = []
    started = threading.Event()

    def compete():
        started.set()
        try:
            root.begin_document_write(DOC, competitor)
        except DocumentWriteBusy:
            outcomes.append("busy")
        else:
            outcomes.append("admitted")
            root.end_document_write(DOC, competitor)

    thread = threading.Thread(target=compete)
    thread.start()
    assert started.wait(2) is True
    thread.join(2)
    assert not thread.is_alive()
    assert outcomes == ["busy"]

    root.end_document_write(DOC, owner)
    root.end_document_write(DOC, owner)
    root.begin_document_write(DOC, competitor)
    root.end_document_write(DOC, competitor)


def test_atomic_write_other_document_can_proceed_while_one_document_is_busy():
    root = PageResourceAdmission()
    first_owner, other_owner = object(), object()
    root.begin_document_write(DOC, first_owner)

    with pytest.raises(DocumentWriteBusy):
        root.begin_document_write(DOC, object())
    root.begin_document_write(OTHER, other_owner)
    root.end_document_write(OTHER, other_owner)
