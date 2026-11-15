"""RFQ-021-R3: a scope must also stop the *background* effects.

The R2 review found that `PurchaseCompletionActions.retry_saved_statuses`
iterated every workflow item, so a SAVED order outside the scope could still
cause a Google status write (and a local business-state change) during a scoped
run -- even when `google` was an allowed write target.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.launcher import backend as launcher
from src.launcher import purchase_completion as completion
from src.launcher.backend import ProductionBackend
from src.launcher.purchase_completion import PurchaseCompletionActions
from src.launcher.run_scope import ScopeError, parse_run_scope
from src.workflow.v12_contracts import BusinessState, PurchaseOutcome

ORDER = "inq_" + "a" * 24
OTHER = "inq_" + "b" * 24


def scoped(writes: str = ""):
    return parse_run_scope(
        inquiry_ids=ORDER,
        modules="inquiry",
        write_targets=writes,
        approval="OWNER-APPROVED:RFQ-021-R3" if writes else "",
    )


class RecordingV12Store:
    def __init__(self, saved_ids):
        self._saved = set(saved_ids)
        self.state_changes = []

    def business_state(self, inquiry_id):
        return BusinessState.PURCHASE_RECORDED

    def purchase_state(self, inquiry_id):
        if inquiry_id in self._saved:
            return PurchaseOutcome.SAVED
        raise KeyError(inquiry_id)

    def set_business_state(self, inquiry_id, state, event):
        self.state_changes.append(inquiry_id)

    def notification_already_created(self, *args, **kwargs):
        return True


class WorkflowStore:
    def __init__(self, ids):
        self._items = tuple(
            SimpleNamespace(
                inquiry_id=iid,
                record_identity=f"row:{iid}",
                status=SimpleNamespace(value="COMPLETED"),
                last_error=None,
                mpn="MPN",
                brand="BRAND",
                quantity=1,
            )
            for iid in ids
        )

    def all_items(self):
        return self._items

    def get_by_inquiry_id(self, inquiry_id):
        return next(item for item in self._items if item.inquiry_id == inquiry_id)


def build_actions(ids, saved, *, scope_ids, writes_calls):
    actions = PurchaseCompletionActions(
        workflow_store=WorkflowStore(ids),
        v12_store=RecordingV12Store(saved),
        reader=object(),
        writer_factory=lambda: object(),
        automatic_admission=lambda _iid, _at: True,
        inquiry_ids=scope_ids,
    )
    return actions


@pytest.fixture()
def google_writes(monkeypatch):
    calls = []

    monkeypatch.setattr(completion, "expected_source_brand", lambda item: "BRAND")
    monkeypatch.setattr(completion, "purchase_status_satisfied",
                        lambda *a, **k: False, raising=True)
    monkeypatch.setattr(completion, "write_purchase_status_safely",
                        lambda reader, writer, identity, **k: calls.append(identity) or True,
                        raising=True)
    return calls


def test_saved_order_outside_the_scope_never_reaches_a_google_write(google_writes):
    actions = build_actions([ORDER, OTHER], [ORDER, OTHER], scope_ids={ORDER}, writes_calls=google_writes)

    actions.retry_saved_statuses(at=None)

    assert google_writes == [f"row:{ORDER}"]


def test_unscoped_run_keeps_reconciling_every_saved_order(google_writes):
    actions = build_actions([ORDER, OTHER], [ORDER, OTHER], scope_ids=None, writes_calls=google_writes)

    actions.retry_saved_statuses(at=None)

    assert sorted(google_writes) == sorted([f"row:{ORDER}", f"row:{OTHER}"])


def test_background_status_reconciliation_is_blocked_even_when_google_is_allowed():
    """`google` being an approved target is not permission to touch other orders."""
    scope = scoped(writes="google")
    assert scope.allows_write("google") is True

    calls = []
    actions = PurchaseCompletionActions(
        workflow_store=WorkflowStore([OTHER]),
        v12_store=RecordingV12Store([OTHER]),
        reader=object(),
        writer_factory=lambda: object(),
        automatic_admission=lambda _iid, _at: True,
        inquiry_ids=scope.inquiry_ids,
    )
    actions._write_back = lambda item, at: calls.append(item.inquiry_id) or True
    actions.retry_saved_statuses(at=None)
    assert calls == []


def test_a_completion_result_from_another_order_is_ignored():
    actions = build_actions([ORDER], [], scope_ids={ORDER}, writes_calls=[])
    result = SimpleNamespace(inquiry_id=OTHER, purchase_outcome=PurchaseOutcome.SAVED)

    assert actions.process(result, at=None) is False


def test_conflicting_explicit_ids_and_scope_are_refused(tmp_path):
    with pytest.raises(ScopeError) as info:
        ProductionBackend(
            root=tmp_path, inquiry_ids=frozenset({OTHER}),
            run_scope=scoped(), enforce_scope=True)
    assert info.value.reason == "SCOPE_INQUIRY_IDS_CONFLICT"


def test_matching_explicit_ids_and_scope_are_accepted(tmp_path):
    backend = ProductionBackend(
        root=tmp_path, inquiry_ids=frozenset({ORDER}),
        run_scope=scoped(), enforce_scope=True)
    assert backend._inquiry_scope == frozenset({ORDER})


def test_the_backend_hands_the_scope_to_the_completion_actions(tmp_path, monkeypatch):
    from tests.launcher.test_backend import _write_runtime_configs

    production, research, _rows = _write_runtime_configs(tmp_path, pending_count=1)
    monkeypatch.setattr(launcher, "compose_v12_production",
                        lambda **_k: (_ for _ in ()).throw(RuntimeError("stop")), raising=True)
    monkeypatch.setattr(launcher, "assess_readiness", lambda *_a, **_k: SimpleNamespace(
        missing_site_ids=(), ready=True))

    backend = ProductionBackend(
        config_path=research, production_config_path=production,
        cdp_probe=lambda _url: True, run_scope=scoped(), enforce_scope=True)
    backend.start()
    thread = backend._thread
    if thread is not None:
        thread.join(timeout=10)

    assert backend._purchase_completion is not None
    assert backend._purchase_completion._inquiry_ids == frozenset({ORDER})
    backend.shutdown()


# --- P0-C: the sweep and the manual actions, at the backend ------------------

def test_login_sweep_is_refused_in_a_scoped_run_even_with_google_allowed(tmp_path):
    backend = ProductionBackend(root=tmp_path, run_scope=scoped(writes="google"), enforce_scope=True)
    assert backend._write_policy.allows("google") is True

    backend.start_login_all_sites()

    assert backend._login_all_thread is None


def test_login_sweep_is_refused_in_preview(tmp_path):
    backend = ProductionBackend(root=tmp_path, preview_mode=True)
    backend.start_login_all_sites()
    assert backend._login_all_thread is None


def test_manual_action_audit_follows_modules_and_write_targets(tmp_path):
    read_only = ProductionBackend(root=tmp_path, run_scope=scoped(), enforce_scope=True)
    assert read_only._action_in_scope("edit") is False         # writes a Google cell
    assert read_only._action_in_scope("resync") is True        # read + local ledger
    assert read_only._action_in_scope("purchase") is False     # needs inso and google
    assert read_only._action_in_scope("quotation") is False    # module cannot be scoped
    assert read_only._action_in_scope("tp") is False           # module cannot be scoped

    google_only = ProductionBackend(
        root=tmp_path, run_scope=scoped(writes="google"), enforce_scope=True)
    assert google_only._action_in_scope("edit") is True
    assert google_only._action_in_scope("purchase") is False   # still needs inso

    both = ProductionBackend(
        root=tmp_path, run_scope=scoped(writes="google,inso"), enforce_scope=True)
    assert both._action_in_scope("purchase") is True
    assert both._action_in_scope("quotation") is False


def test_manual_purchase_request_is_refused_without_the_inso_target(tmp_path):
    backend = ProductionBackend(root=tmp_path, run_scope=scoped(), enforce_scope=True)
    message = backend.request_order_action(ORDER, "purchase")
    assert message == "当前受控范围不允许该操作（模块或写入目标未授权）。"
