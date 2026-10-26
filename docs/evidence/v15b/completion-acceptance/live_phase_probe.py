"""Bounded ordinary six-source read; no production Backend/DB/TP/SMTP/write API.
Real source callbacks feed the existing observer and GUI DTO on the Tk thread.
"""
import json
import logging
import os
import queue
import re
import smtplib
import sqlite3
import sys
import threading
import time
from dataclasses import replace
from datetime import UTC,datetime
from pathlib import Path
ROOT=Path('C:/Users/Leo/.codex/worktrees/v1-5-tp-research/INSO_Leo')
OUT=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
os.environ['INSO_RUNTIME_ROOT']=str(OUT)
logging.disable(logging.CRITICAL)  # no raw page/client log or credential exception text
def deny(*a,**kw):raise AssertionError('LIVE_PROBE_SQL_SMTP_FORBIDDEN')
smtplib.SMTP=smtplib.SMTP_SSL=sqlite3.connect=deny
from src.gui.app import InsoDashboardApp
from src.gui.mock_backend import MockBackend
from src.gui.contracts import LogEntry,RunState,WorkbenchSnapshot
from src.launcher.workbench_snapshot import RuntimeObservation
from verify_workbench_ui import capture

events=queue.Queue(maxsize=128)
facts=[]
def safe_code(exc):
 value=getattr(exc,'reason_code',None) or getattr(exc,'code',None)
 return value if isinstance(value,str) and re.fullmatch('[A-Z_0-9]+',value) else type(exc).__name__
def save(name,value):(OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
def emit(kind,**values):events.put(dict(kind=kind,at=datetime.now(UTC).isoformat(),**values))
def worker():
 from playwright.sync_api import sync_playwright
 from src.research.cdp_pages import page_owner,shared_playwright_factory
 from src.research.credentials import CoreLoginBridge
 from src.research.contracts import ResearchInput
 from src.research.inso_history import INSO_SITE_ID
 from src.research.runtime import load_runtime_config,build_research_service
 from src.research.icnet import CdpIcNetClient
 from src.launcher.browser_bootstrap import BrowserHandle
 from src.launcher.inso_session import attach_inso_research_session
 session=None
 try:
  with sync_playwright() as p:
   browser=p.chromium.connect_over_cdp('http://127.0.0.1:9222',timeout=10000)
   assert len(browser.contexts)==1,'CDP_CONTEXT_AMBIGUOUS'
   context=browser.contexts[0]
   original=tuple(context.pages)
   assert not any(page_owner(pg) for pg in original),'OWNED_TAB_CONFLICT'
   emit('stage',site='INSO',stage='复用既有认证与只读租约')
   login=CoreLoginBridge().login(INSO_SITE_ID)
   if login is None:
    emit('auth',status='NOT_VERIFIED',reason='CANONICAL_CREDENTIAL_UNAVAILABLE')
   else:
    try:
     session=attach_inso_research_session('http://127.0.0.1:9222',BrowserHandle(owned=False,playwright=p,browser=browser),
      cycle_id='readonly-ui-acceptance',cycle_is_drained=lambda _:True,login=login,fresh_page=True)
     emit('auth',status='VERIFIED_ORIGINAL_SESSION_GUARDS')
    except Exception as exc:emit('auth',status='NOT_VERIFIED',reason=safe_code(exc))
   del login
   config=load_runtime_config('D:/Program_Leo/INSO_Leo/dist/INSO_V1.4/runtime/research.json')
   config=replace(config,excel_output_path=OUT/'private-live-research.xlsx',
    browser=replace(config.browser,timeout_ms=20000))
   factory=shared_playwright_factory(lambda:(p,browser))
   def query(_key,source,operation):
    emit('stage',site=source.value,stage='真实单型号只读查询')
    return operation()
   def observed(_key,result):
    emit('source_result',site=result.source.value,outcome=result.outcome.value)
   try:
    service=build_research_service(config,
     icnet_client=CdpIcNetClient(timeout_ms=20000,playwright_factory=factory),
     inso_operation_access=session.operation_access if session else None,
     playwright_provider=lambda:(p,browser),source_query=query,source_observer=observed)
    result=service.execute(ResearchInput('readonly-ui-acceptance','STM32G0B0CET6',None,100,None))
    emit('result',status=result.status.value,private_local_excel_generated=config.excel_output_path.exists())
   finally:
    if session is not None:session.close_owned_operation_tab()
    emit('browser_final',original_pages_preserved=all(not pg.is_closed() for pg in original),
     new_pages_remaining=len([pg for pg in context.pages if pg not in original]))
 except Exception as exc:emit('failure',reason=safe_code(exc))
 finally:emit('done')

backend=MockBackend()
obs=RuntimeObservation();obs.enable(quotation=False,tp=False);obs.begin_cycle()
snapshot=WorkbenchSnapshot(0,replace(backend.get_status(),state=RunState.RUNNING),backend.get_health())
backend.get_workbench_snapshot=lambda:snapshot
app=InsoDashboardApp(backend)
app._root.title('V1.5 真实六源只读阶段验收（无采购/发信，TP关闭）')
app._root.geometry('1400x760+30+30')
started=time.monotonic()
callback_errors=[]
app._root.report_callback_exception=lambda kind,value,tb:callback_errors.append(kind.__name__)
thread=threading.Thread(target=worker,name='finite-readonly-source-probe',daemon=False)
safe_logs=[]
screens=[]
def refresh(event):
 global snapshot
 if event['kind']=='stage':obs.stage('inquiry',event['stage'],site=event['site'],order_ref='readonly-ui-acceptance')
 if event['kind']=='done':obs.end_cycle(None)
 revision,modules,began,tick,ended,timings,durations,plan,recovery=obs.snapshot()
 safe_logs.append(LogEntry(datetime.now(UTC),'INFO',json.dumps(event,ensure_ascii=False)))
 snapshot=replace(snapshot,revision=snapshot.revision+1,modules=modules,logs=tuple(safe_logs[-100:]),
  cycle_started_at=began,cycle_started_monotonic=tick,cycle_finished_at=ended,timings=timings,cycle_durations=durations,
  session=replace(snapshot.session,state=RunState.STOPPED if event['kind']=='done' else RunState.RUNNING))
 app._view.render(snapshot,force=True)
 if event['kind']=='stage':
  # Only safe stage/time data shown; no quote/customer contents cross this UI.
  app._root.update_idletasks()
  n=len(screens);path=OUT/f'live-stage-{n}.png'
  capture(app._root,path);screens.append(path.name)
  facts.append(dict(kind='ui_stage_rendered',site=event['site'],stage=event['stage'],
   rendered_at=datetime.now(UTC).isoformat(),module_site=snapshot.modules[0].site))
def drain():
 done=False
 try:
  while True:
   event=events.get_nowait();facts.append(event);refresh(event)
   if event['kind']=='done':done=True
 except queue.Empty:pass
 save('live-phase-events.json',facts)
 if done:
  app._root.after(1500,app._on_close)
 else:app._root.after(100,drain)
thread.start();app._root.after(100,drain)
app.run();thread.join(5);backend.shutdown()
save('live-phase-complete.json',dict(pid=os.getpid(),elapsed_seconds=time.monotonic()-started,
 worker_stopped=not thread.is_alive(),close_finalized=app._close_finalized,callback_errors=callback_errors,
 tp_enabled=False,production_backend=False,smtp_forbidden=True,sql_forbidden=True,
 source_results=[event for event in facts if event['kind']=='source_result'],
 ui_rendered_stages=sum(event['kind']=='ui_stage_rendered' for event in facts),
 screenshots=screens,qualification='Standalone diagnostic GUI bound to real readonly source callbacks; not production workflow polling'))
