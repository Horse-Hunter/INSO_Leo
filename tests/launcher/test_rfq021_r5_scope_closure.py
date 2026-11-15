"""RFQ-021-R5: the last automatic write paths must obey the same scope.

`_site_recovered` settles site-level incidents, and an incident row's evidence can
name any order on that site. A one-order trial must settle only the records it
has standing for -- the program-level ones and its own orders. These tests drive
the backend method directly -- not a button, not a flag.
"""

from __future__ import annotations

from types import SimpleNamespace

from src.launcher.backend import ProductionBackend
from src.launcher.run_scope import parse_run_scope

ORDER = "inq_" + "a" * 24
_UNSET = object()


class RecordingStore:
    def __init__(self) -> None:
        self.calls = []

    def resolve_incidents(self, site, *, at, within=_UNSET):
        self.calls.append((site, within))


def scoped():
    return parse_run_scope(
        inquiry_ids=ORDER, modules="inquiry", write_targets="", approval="")


def _backend(tmp_path, *, enforce):
    scope = scoped() if enforce else None
    backend = ProductionBackend(root=tmp_path, run_scope=scope, enforce_scope=enforce)
    backend._v12_store = RecordingStore()
    return backend


def test_a_scoped_run_settles_only_its_own_orders_and_program_records(tmp_path):
    backend = _backend(tmp_path, enforce=True)

    backend._site_recovered("INSO")

    assert backend._v12_store.calls == [("INSO", frozenset({ORDER}))]
    assert "INSO" not in backend._site_outages


def test_an_unscoped_run_still_settles_them_without_a_filter(tmp_path):
    backend = _backend(tmp_path, enforce=False)

    backend._site_recovered("INSO")

    assert backend._v12_store.calls == [("INSO", _UNSET)]


def test_a_scoped_run_without_a_scope_object_settles_only_program_records(tmp_path):
    """Refused before start(), but the method must still be safe if reached."""

    backend = ProductionBackend(root=tmp_path, enforce_scope=True)
    backend._v12_store = RecordingStore()

    backend._site_recovered("INSO")

    assert backend._v12_store.calls == [("INSO", frozenset())]


def test_the_local_outage_bookkeeping_clears_in_both_modes(tmp_path):
    for enforce in (True, False):
        backend = _backend(tmp_path, enforce=enforce)
        backend._site_outages["INSO"] = SimpleNamespace()
        backend._site_manual_wait.add("INSO")

        backend._site_recovered("INSO")

        assert "INSO" not in backend._site_outages
        assert "INSO" not in backend._site_manual_wait


class TouchingStore:
    """A store that fails the test if a refused action even looks at the order."""

    def all_items(self):  # status rendering only; no order is read
        return ()

    def get_by_inquiry_id(self, _inquiry_id):  # pragma: no cover - must not run
        raise AssertionError("an out-of-scope action must not read the order store")


def test_the_manual_executor_refuses_an_out_of_scope_order(tmp_path):
    """RFQ-021-R5: the final executor repeats the scope check, not just the button."""

    other = "inq_" + "b" * 24
    backend = ProductionBackend(
        root=tmp_path,
        run_scope=parse_run_scope(inquiry_ids=ORDER, modules="inquiry",
                                  write_targets="google",
                                  approval="OWNER-APPROVED:RFQ-021-R5"),
        enforce_scope=True,
    )
    backend._store = TouchingStore()

    backend._execute_order_action(("request", other, "purchase", None, None))

    assert backend._manual_result is not None
    assert backend._manual_result.success is False
    assert "受控试运行范围" in backend._manual_result.message


def test_the_manual_executor_refuses_an_unapproved_write_on_an_in_scope_order(tmp_path):
    backend = ProductionBackend(
        root=tmp_path,
        run_scope=parse_run_scope(inquiry_ids=ORDER, modules="inquiry",
                                  write_targets="", approval=""),
        enforce_scope=True,
    )
    backend._store = TouchingStore()

    backend._execute_order_action(("request", ORDER, "purchase", None, None))

    assert backend._manual_result is not None
    assert backend._manual_result.success is False
