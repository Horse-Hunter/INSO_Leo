"""Exact target proof must not depend on a transient per-page CDP session."""
from types import SimpleNamespace

import pytest

from src.launcher.google_quote_update import _google_target_id
from src.workflow.v12_faults import FaultScope, V12Fault


def leased_page(*, answer=None, send_error=None, detach_error=None):
    calls = []
    def page_session(_):
        raise RuntimeError("synthetic stale page-session during process swap")
    context = SimpleNamespace(new_cdp_session=page_session)
    def send(method, params):
        calls.append((method, params))
        if send_error:
            raise send_error
        return {"targetInfo": answer if answer is not None else {"targetId": "exact", "type": "page"}}
    def detach():
        calls.append(("detach", None))
        if detach_error:
            raise detach_error
    browser = SimpleNamespace(new_browser_cdp_session=lambda: SimpleNamespace(send=send, detach=detach))
    page = SimpleNamespace(context=context, is_closed=lambda: False,
                           _inso_native_page_owner=("exact", "google-operation", context, browser))
    return page, calls


def test_factory_bound_exact_native_proof_survives_page_session_failure():
    page, calls = leased_page()
    assert _google_target_id(page) == "exact"
    assert calls == [("Target.getTargetInfo", {"targetId": "exact"}), ("detach", None)]


@pytest.mark.parametrize("answer", [{"targetId": "other", "type": "page"},
                                    {"targetId": "exact", "type": "worker"},
                                    {"targetId": "exact"}, {"type": "page"}])
def test_wrong_or_unconfirmed_target_remains_global_stop(answer):
    page, _ = leased_page(answer=answer)
    with pytest.raises(V12Fault) as err:
        _google_target_id(page)
    assert err.value.scope is FaultScope.GLOBAL_STOP


@pytest.mark.parametrize("failure", ["send", "detach", "context", "closed"])
def test_ownership_or_connection_or_cleanup_failure_still_stops(failure):
    page, _ = leased_page(send_error=RuntimeError("lost") if failure == "send" else None,
                          detach_error=RuntimeError("cleanup") if failure == "detach" else None)
    if failure == "context":
        page.context = SimpleNamespace()
    if failure == "closed":
        page.is_closed = lambda: True
    with pytest.raises(V12Fault, match="GOOGLE_TAB_IDENTITY_UNCONFIRMED") as err:
        _google_target_id(page)
    assert err.value.scope is FaultScope.GLOBAL_STOP


def test_reconnected_unleased_page_keeps_original_native_proof():
    calls = []
    def send(method):
        calls.append(method)
        return {"targetInfo": {"targetId": "reconnected"}}
    context = SimpleNamespace(new_cdp_session=lambda _p: SimpleNamespace(send=send, detach=lambda: None))
    assert _google_target_id(SimpleNamespace(context=context, is_closed=lambda: False)) == "reconnected"
    assert calls == ["Target.getTargetInfo"]
