"""Original owner stalls: detect without parallel business or fake cancellation."""
import threading
from contextlib import nullcontext
from types import SimpleNamespace

import pytest

from src.gui.contracts import RunState
from src.launcher.operation_progress import OperationProgress
from src.workflow.service import WorkflowRuntime
from tests.launcher.test_runtime_safety_notice import harness
from tests.workflow.test_v12_notifications import NOW


def test_native_completion_and_os_resume_require_fresh_persistent_evidence():
    clock=[0.];p=OperationProgress(clock=lambda:clock[0]);trips=[]
    with p.scope('quotation') as native:
        token=object();native('begin',token,1)
        clock[0]=2000
        assert p.check(excluded=lambda:False,trip=lambda:trips.append(True) or True) is None
        clock[0]+=4
        assert p.check(excluded=lambda:False,trip=lambda:trips.append(True) or True) is None
        native('end',token,1)
        clock[0]+=2
        assert p.check(excluded=lambda:False,trip=lambda:trips.append(True) or True) is None
    assert not trips


@pytest.mark.parametrize('blocked',['owner_stop','closed'])
def test_excluded_owner_actions_do_not_turn_long_wait_into_stop_notice(blocked):
    clock=[0.];p=OperationProgress(clock=lambda:clock[0]);exclude=[False];trips=[]
    with p.scope('quotation'):
        clock[0]=601;p.check(excluded=lambda:exclude[0],trip=lambda:True)
        exclude[0]=True;clock[0]+=6
        assert p.check(excluded=lambda:exclude[0],trip=lambda:trips.append(True) or True) is None
    assert not trips and p.stalled is None


def test_large_healthy_batch_nested_module_and_120_second_wait_are_not_stalls():
    clock=[0.];p=OperationProgress(clock=lambda:clock[0]);trips=[]
    def check():p.check(excluded=lambda:False,trip=lambda:trips.append(True) or True)
    with p.scope('inquiry') as native:
        for _ in range(20):
            token=object();native('begin',token,clock[0]+10)
            clock[0]+=2;native('end',token,clock[0]);check()
            clock[0]+=120;check()
            with p.scope('tp') as child:
                t=object();child('begin',t,clock[0]+20)
                clock[0]+=10;child('end',t,clock[0]);check()
            check()
    assert not trips and clock[0]>600


def test_actual_backend_stalled_quote_notifies_once_without_releasing_browser_owner(tmp_path,monkeypatch):
    b,worker,smtp=harness(tmp_path,monkeypatch)
    clock=[0.];b._operation_progress=OperationProgress(clock=lambda:clock[0])
    runtime=WorkflowRuntime(None,None,());runtime.configure_modules({'inquiry':900,'quotation':900,'tp':900},timer=lambda:clock[0])
    b._module_runtime=runtime;b._observation.enable(quotation=True,tp=True)
    entered=threading.Event();release=threading.Event();calls=[];closed=[];errors=[]
    def inquiry(*a,**kw):calls.append('inquiry')
    def quote(*a,**kw):calls.append('quotation');entered.set();assert release.wait(3)
    b._combined=SimpleNamespace(run_inquiry=inquiry,run_quotation=quote)
    b._purchase_completion=SimpleNamespace(retry_saved_statuses=lambda **kw:None)
    b._tp=SimpleNamespace(run=lambda *a,**kw:calls.append('tp'))
    for name in ('_check_site_recovery','_begin_poll_projection','_idle_login_tick','_notify','_cache_workbench'):
        monkeypatch.setattr(b,name,lambda *a,**kw:None)
    monkeypatch.setattr(b,'_close_inso_order_tab',lambda:closed.append(True))
    def run():
        try:b._run_independent_poll(runtime,{'spreadsheet_id':'synthetic'},None,SimpleNamespace(poll_scope=nullcontext),SimpleNamespace(discovery_scope=nullcontext),(),None)
        except Exception as e:errors.append(e)  # noqa: BLE001
    actor=threading.Thread(target=run);actor.start()
    try:
        assert entered.wait(1)
        clock[0]=601;b._check_operation_progress();assert not b._stop.is_set()
        clock[0]=607;b._check_operation_progress()
        assert b._stop.is_set() and b._state is RunState.GLOBAL_STOP
        assert actor.is_alive() and runtime.module_plans()['quotation'][1]
        assert calls==['inquiry','quotation'] and len(closed)==1
        assert worker.run_due(now=NOW)==1 and smtp.send_attempts==1
        body=smtp.message.get_content()
        assert '曾长时间' in body and '在途操作' in body and '不能据此判断Google整体不可用' in body
        b._check_operation_progress();assert worker.run_due(now=NOW)==0 and smtp.send_attempts==1
    finally:
        release.set();actor.join(3);b.shutdown()
    assert not actor.is_alive() and not errors and 'tp' not in calls


@pytest.mark.parametrize('change',['owner_stop','recovered','different_run','closed','wrong_generation'])
def test_stall_notice_rechecks_actual_pause_and_owner_intent_before_smtp(tmp_path,monkeypatch,change):
    b,worker,smtp=harness(tmp_path,monkeypatch);clock=[0.]
    b._operation_progress=OperationProgress(clock=lambda:clock[0])
    try:
        with b._operation_progress.scope('quotation'):
            clock[0]=601;b._check_operation_progress();clock[0]=607;b._check_operation_progress()
            if change=='owner_stop':b._owner_stop_requested=True
            elif change=='recovered':b._stop.clear();b._state=RunState.RUNNING
            elif change=='different_run':b._run_id='new'
            elif change=='closed':b._closed=True
            else:b._operation_progress.stalled=None
            worker.run_due(now=NOW)
            assert smtp.send_attempts==0
    finally:b.shutdown()


def test_same_gui_new_start_rearms_progress_only_after_previous_owner_drains(tmp_path,monkeypatch):
    from src.launcher.backend import ProductionBackend
    from src.launcher.operation_progress import StalledOperation
    b=ProductionBackend(root=tmp_path);old=b._operation_progress
    old.stalled=StalledOperation('old-generation','quotation');b._state=RunState.MODULE_PAUSED
    b._thread=SimpleNamespace(is_alive=lambda:True)
    b.start();assert b._operation_progress is old
    b._thread=None
    monkeypatch.setattr(b,'_run',lambda:None)
    try:
        b.start();b._thread.join(2)
        assert b._operation_progress is not old and b._operation_progress.stalled is None
        clock=[0.];b._operation_progress.clock=lambda:clock[0]
        with b._operation_progress.scope('quotation'):
            clock[0]=601;b._check_operation_progress();clock[0]=607;b._check_operation_progress()
            assert b._operation_progress.stalled is not None and b._stop.is_set()
    finally:b.shutdown()


def test_safe_inso_read_exhaustion_remains_retryable_after_hours_and_does_not_block_due_modules(tmp_path,monkeypatch):
    from src.workflow.v12_faults import FaultScope, V12Fault
    from tests.launcher.test_v16_backend import prepared
    b,runtime,clock=prepared(tmp_path,monkeypatch)
    b._site_outages['INSO']=0;clock.tick=15000
    b._module_execute=lambda _:(_ for _ in ()).throw(V12Fault(FaultScope.GLOBAL_STOP,'INSO_QUERY_RETRIES_EXHAUSTED'))
    assert runtime.claim_due_module()=='inquiry'
    b._run_independent_job('inquiry')
    assert not b._stop.is_set() and not runtime.module_plans()['inquiry'][2]
    assert runtime.claim_due_module()=='quotation'

@pytest.mark.parametrize('stop_kind',['stalled','authentication'])
def test_original_smtp_owner_sends_verified_stop_while_poller_cleanup_is_not_drained(tmp_path,monkeypatch,stop_kind):
    import json
    import time

    from src.launcher import backend as launcher
    from src.launcher.browser_bootstrap import BrowserHandle
    from src.workflow.v12_faults import FaultScope, V12Fault
    from src.workflow.v12_notifications import V12NotificationWorker
    from src.workflow.v12_smtp_transport import QQSMTPConfig, QQSMTPTransport
    from tests.launcher.test_backend import _SheetsService, _write_runtime_configs
    from tests.workflow.test_v12_smtp_transport import (
        FakeCredentials,
        ScriptedSMTP,
        login,
    )
    production,research,rows=_write_runtime_configs(tmp_path)
    cfg=json.loads(production.read_text(encoding='utf-8'));cfg.update(v16_enabled=True,v13_enabled=True,quotation_input={'input_row':1,'first_column':1,'gid':'0'})
    production.write_text(json.dumps(cfg),encoding='utf-8')
    monkeypatch.setattr(launcher,'build_google_web_service',lambda *a,**kw:_SheetsService(rows,threading.Event()))
    monkeypatch.setattr(launcher,'assess_readiness',lambda *a,**kw:SimpleNamespace(ready=True,missing_site_ids=()))
    b=launcher.ProductionBackend(config_path=research,production_config_path=production,cdp_probe=lambda _:True,browser_acquirer=lambda *a,**kw:BrowserHandle(owned=False))
    server=ScriptedSMTP();transport=QQSMTPTransport(config=QQSMTPConfig(sender_address='sender@example.invalid'),credentials=FakeCredentials(login()),smtp_factory=lambda *a,**kw:server)
    sent=threading.Event();owners=[];ready=threading.Event();blocked=threading.Event();release=threading.Event()
    # Preserve the real adapter before patching its method globally.
    real_send=transport.send_one
    def send(_self,command,recipient):
        owners.append(threading.current_thread().name)
        result=real_send(command,recipient);sent.set();return result
    monkeypatch.setattr(QQSMTPTransport,'send_one',send)
    original_bind=V12NotificationWorker.bind_delivery_thread
    def bind(worker):original_bind(worker);ready.set()
    monkeypatch.setattr(V12NotificationWorker,'bind_delivery_thread',bind)
    clock=[0.];progress=OperationProgress(clock=lambda:clock[0])
    monkeypatch.setattr('src.launcher.operation_progress.OperationProgress',lambda:progress)
    def poll(*a,**kw):
        assert ready.wait(3)
        if stop_kind=='authentication':raise V12Fault(FaultScope.GLOBAL_STOP,'GOOGLE_AUTHENTICATION_REQUIRED')
        with progress.scope('quotation'):
            blocked.set();assert release.wait(8)
    def cleanup(*a,**kw):
        if stop_kind=='authentication':blocked.set();assert release.wait(8)
    monkeypatch.setattr(b,'_run_independent_poll',poll)
    monkeypatch.setattr(b,'_retire_google_pages',cleanup)
    b.start()
    try:
        assert blocked.wait(4)
        if stop_kind=='stalled':
            clock[0]=601;b._check_operation_progress();clock[0]=607;b._check_operation_progress()
        assert sent.wait(3),'Original SMTP worker waited for poll drain instead of sending verified stop'
        assert not release.is_set() and b._thread.is_alive()
        assert server.send_attempts==1 and owners==['production-research-worker']
        time.sleep(.05);assert server.send_attempts==1
    finally:
        release.set();b._thread.join(6);b.shutdown()
    assert not b._thread.is_alive()
