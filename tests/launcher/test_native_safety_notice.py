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


@pytest.mark.parametrize("wrapped",[False,True])
def test_actual_halted_google_auth_has_accurate_owner_notice_once(tmp_path,monkeypatch,wrapped):
    from src.sheets.google_reader import GoogleSheetsReadError
    from src.workflow.v12_faults import FaultScope, V12Fault
    backend,worker,smtp=harness(tmp_path,monkeypatch)
    fault=V12Fault(FaultScope.GLOBAL_STOP,"GOOGLE_AUTHENTICATION_REQUIRED")
    if wrapped:
        error=GoogleSheetsReadError("synthetic wrapper");error.__cause__=fault
    else:error=fault
    try:
        backend._runtime_error(error)
        assert backend._runtime_stop_reason=="GOOGLE_AUTHENTICATION_REQUIRED"
        assert worker.run_due(now=NOW)==1 and smtp.send_attempts==1
        body=smtp.message.get_content()
        assert "登录" in body and "访问权限" in body and "不能据此判断Google整体不可用" in body
        assert "尚不能确认此次写入成功或失败" not in body
        backend._runtime_error(error)
        assert worker.run_due(now=NOW)==0 and smtp.send_attempts==1
    finally:backend.shutdown()

@pytest.mark.parametrize("reason", ["QUOTE_INPUT_INFRASTRUCTURE_UNAVAILABLE", "UNEXPECTED_INTERNAL_FAILURE"])
def test_actual_internal_stop_with_current_order_uses_owner_stop_notice_not_order_failure(tmp_path,monkeypatch,reason):
    from src.workflow.v12_faults import FaultScope, V12Fault
    backend,worker,smtp=harness(tmp_path,monkeypatch)
    routed=[]
    backend._active_inso_inquiry='synthetic-current-order'
    monkeypatch.setattr(backend,'_record_fault_alert',lambda *args:routed.append(args))
    try:
        backend._runtime_error(V12Fault(FaultScope.V12_PAUSE,reason))
        assert backend._stop.is_set()
        assert worker.run_due(now=NOW)==1 and smtp.send_attempts==1
        assert not routed
        body=smtp.message.get_content()
        assert '内部操作' in body and '不能据此判断Google整体不可用' in body
        assert smtp.message['To']=='linan229@qq.com'
        backend._run_id='restarted'
        backend._runtime_error(V12Fault(FaultScope.V12_PAUSE,reason))
        assert worker.run_due(now=NOW)==0 and smtp.send_attempts==1
    finally:backend.shutdown()


@pytest.mark.parametrize('change',['recovered','owner_stop','closed','reason_changed'])
def test_internal_stop_must_remain_current_before_smtp(tmp_path,monkeypatch,change):
    from src.gui.contracts import RunState
    from src.workflow.v12_faults import FaultScope, V12Fault
    backend,worker,smtp=harness(tmp_path,monkeypatch)
    try:
        backend._runtime_error(V12Fault(FaultScope.V12_PAUSE,'QUOTE_INPUT_INFRASTRUCTURE_UNAVAILABLE'))
        if change=='recovered':backend._stop.clear();backend._state=RunState.RUNNING
        elif change=='owner_stop':backend._owner_stop_requested=True
        elif change=='closed':backend._closed=True
        else:backend._runtime_stop_reason='DIFFERENT_STOP'
        worker.run_due(now=NOW)
        assert smtp.send_attempts==0
    finally:backend.shutdown()
