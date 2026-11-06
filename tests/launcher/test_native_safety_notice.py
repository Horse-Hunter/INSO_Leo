"""Verified browser resource stops must not disappear behind false-alert guards."""
import pytest

from src.research.cdp_pages import (
    PageTargetCleanupError,
    PageTargetCreationUncertain,
    PageTargetOwnershipError,
)
from tests.launcher.test_runtime_safety_notice import harness
from tests.workflow.test_v12_notifications import NOW


@pytest.mark.parametrize("kind",[PageTargetCreationUncertain,PageTargetOwnershipError,PageTargetCleanupError])
def test_verified_native_safety_stop_notifies_owner_once_and_never_blames_google(tmp_path,monkeypatch,kind):
    backend,worker,smtp=harness(tmp_path,monkeypatch)
    try:
        backend._runtime_error(kind((TimeoutError(),)))
        assert worker.run_due(now=NOW)==1 and smtp.send_attempts==1
        assert smtp.message["To"]=="linan229@qq.com"
        body=smtp.message.get_content()
        assert "浏览器" in body and "不能据此判断Google整体不可用" in body
        backend._runtime_error(kind((TimeoutError(),)))
        assert worker.run_due(now=NOW)==0 and smtp.send_attempts==1
    finally:backend.shutdown()


@pytest.mark.parametrize("reason",["GOOGLE_TAB_IDENTITY_UNCONFIRMED","GOOGLE_OPERATION_NOT_CLOSED","GOOGLE_WRITE_SETTLEMENT_UNCONFIRMED"])
def test_wrapped_read_error_keeps_actual_safety_stop_reason_and_owner_notice(tmp_path,monkeypatch,reason):
    from src.sheets.google_reader import GoogleSheetsReadError
    from src.workflow.v12_faults import FaultScope, V12Fault
    backend,worker,smtp=harness(tmp_path,monkeypatch)
    wrapped=GoogleSheetsReadError("synthetic read wrapper")
    wrapped.__cause__=V12Fault(FaultScope.GLOBAL_STOP,reason)
    try:
        backend._runtime_error(wrapped)
        assert backend._runtime_stop_reason==reason
        assert worker.run_due(now=NOW)==1 and smtp.send_attempts==1
        assert "不能据此判断Google整体不可用" in smtp.message.get_content()
    finally:backend.shutdown()
