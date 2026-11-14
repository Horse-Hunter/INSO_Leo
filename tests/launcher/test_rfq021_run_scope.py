"""RFQ-021 negatives for the controlled (scoped) business start."""

from __future__ import annotations

import pytest

from src.inso.session import SecurityViolation
from src.inso.write_safety import OwnerAuthorizedSaveAndSendGate, ProductionWriteGate
from src.launcher.backend import ProductionBackend
from src.launcher.run_scope import (
    ExternalWritePolicy,
    RunScope,
    ScopedInsoWriteGate,
    ScopeError,
    ScopeViolation,
    parse_run_scope,
)

ORDER = "inq_" + "a" * 24


def scope(**overrides) -> RunScope:
    values = {
        "inquiry_ids": frozenset({ORDER}),
        "modules": frozenset({"inquiry"}),
        "write_targets": frozenset(),
        "approval_reference": "",
    }
    values.update(overrides)
    return RunScope(**values)


# --- scope validation -------------------------------------------------------

def test_scope_without_orders_is_refused():
    with pytest.raises(ScopeError) as info:
        scope(inquiry_ids=frozenset())
    assert info.value.reason == "SCOPE_REQUIRES_INQUIRY_IDS"


def test_scope_rejects_a_malformed_order_id():
    with pytest.raises(ScopeError) as info:
        scope(inquiry_ids=frozenset({"not-an-inquiry"}))
    assert info.value.reason == "SCOPE_INVALID_INQUIRY_ID"


def test_scope_must_keep_the_inquiry_driver():
    with pytest.raises(ScopeError) as info:
        scope(modules=frozenset({"quotation"}))
    assert info.value.reason == "SCOPE_REQUIRES_INQUIRY_MODULE"


def test_scope_rejects_unknown_module_and_target():
    with pytest.raises(ScopeError) as info:
        scope(modules=frozenset({"inquiry", "everything"}))
    assert info.value.reason == "SCOPE_UNKNOWN_MODULE"
    with pytest.raises(ScopeError) as info:
        scope(write_targets=frozenset({"filesystem"}))
    assert info.value.reason == "SCOPE_UNKNOWN_WRITE_TARGET"


def test_writes_without_owner_approval_are_refused():
    with pytest.raises(ScopeError) as info:
        scope(write_targets=frozenset({"google"}))
    assert info.value.reason == "SCOPE_WRITES_REQUIRE_OWNER_APPROVAL"
    approved = scope(write_targets=frozenset({"google"}),
                     approval_reference="OWNER-APPROVED:RFQ-021-TRIAL-1")
    assert approved.allows_write("google")
    assert not approved.allows_write("smtp")


def test_parse_run_scope_splits_cli_text():
    parsed = parse_run_scope(
        inquiry_ids=f"{ORDER}, inq_" + "b" * 24,
        modules="inquiry, quotation",
        write_targets="google",
        approval="OWNER-APPROVED:RFQ-021-TRIAL-1",
    )
    assert parsed.inquiry_ids == frozenset({ORDER, "inq_" + "b" * 24})
    assert parsed.modules == frozenset({"inquiry", "quotation"})
    assert parsed.allows_write("google")


def test_scope_warns_when_a_module_has_no_write_target():
    warnings = scope(modules=frozenset({"inquiry", "quotation"})).warnings()
    assert warnings == [
        "MODULE_WRITES_DISABLED:inquiry->inso",
        "MODULE_WRITES_DISABLED:quotation->google",
    ]


# --- write policy -----------------------------------------------------------

def test_unenforced_policy_keeps_the_legacy_path_open():
    policy = ExternalWritePolicy(None, enforced=False)
    assert policy.allows("google") and policy.allows("inso") and policy.allows("smtp")


def test_enforced_policy_without_a_scope_denies_every_target():
    policy = ExternalWritePolicy(None, enforced=True)
    for target in ("google", "inso", "smtp"):
        assert not policy.allows(target)
        with pytest.raises(ScopeViolation):
            policy.require(target)


def test_enforced_policy_allows_only_the_named_targets():
    policy = ExternalWritePolicy(
        scope(write_targets=frozenset({"google"}),
              approval_reference="OWNER-APPROVED:RFQ-021-TRIAL-1"),
        enforced=True,
    )
    assert policy.allows("google")
    assert not policy.allows("inso")
    assert policy.denial_reason("inso") == "EXTERNAL_WRITE_NOT_IN_SCOPE"


def test_a_broken_safety_record_blocks_writes_even_inside_a_scope():
    policy = ExternalWritePolicy(
        scope(write_targets=frozenset({"google"}),
              approval_reference="OWNER-APPROVED:RFQ-021-TRIAL-1"),
        enforced=True,
    )
    policy.block_all_writes("WRITE_LEDGER_UNAVAILABLE")
    assert not policy.allows("google")
    assert policy.denial_reason("google") == "WRITE_LEDGER_UNAVAILABLE"


# --- INSO gate narrowing ----------------------------------------------------

def test_inso_gate_refuses_a_purchase_outside_the_scope():
    gate = ScopedInsoWriteGate(
        OwnerAuthorizedSaveAndSendGate(), ExternalWritePolicy(None, enforced=True), "inso")
    with pytest.raises(ScopeViolation) as info:
        gate.require_save_and_send()
    assert info.value.reason == "SCOPE_MISSING"
    with pytest.raises(ScopeViolation):
        gate.require_open()


def test_scoped_inso_gate_never_reopens_the_production_save_gate():
    policy = ExternalWritePolicy(
        scope(write_targets=frozenset({"inso"}),
              approval_reference="OWNER-APPROVED:RFQ-021-TRIAL-1"),
        enforced=True,
    )
    gate = ScopedInsoWriteGate(ProductionWriteGate(), policy, "inso")
    with pytest.raises(SecurityViolation):
        gate.require_open()
    with pytest.raises(SecurityViolation):
        gate.require_save_and_send()


# --- backend start gate -----------------------------------------------------

def test_release_backend_refuses_start_without_a_scope(tmp_path):
    backend = ProductionBackend(root=tmp_path, enforce_scope=True)
    assert backend.scope_blockers() == ("SCOPE_MISSING",)
    assert backend.start() is False
    assert backend._thread is None


def test_preview_backend_refuses_start_and_process_services(tmp_path):
    backend = ProductionBackend(root=tmp_path, preview_mode=True)
    assert backend.preview_mode is True
    assert backend.scope_blockers() == ("PREVIEW_ONLY",)
    backend.start_process_services()
    assert backend._mail_research_service is None
    assert backend._mail_initial_start_consumed is False
    assert backend.start() is False
    assert backend._thread is None


def test_scoped_backend_reports_no_blocker(tmp_path):
    backend = ProductionBackend(
        root=tmp_path, run_scope=scope(), enforce_scope=True)
    assert backend.scope_blockers() == ()
    assert backend.run_scope is scope() or backend.run_scope == scope()


def test_scoped_backend_denies_notification_dispatch(tmp_path):
    backend = ProductionBackend(
        root=tmp_path, run_scope=scope(), enforce_scope=True)
    calls = []

    class Composition:
        class coordinator:
            @staticmethod
            def run_notifications(now=None):
                calls.append(now)
                return 1

    backend._v12_composition = Composition()
    assert backend._run_notifications(None) == 0
    assert calls == []
