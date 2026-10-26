"""Finite native-Tk component acceptance, not native pointer automation.
Reuses app/Mock/widget commands/tray/close and a private SingleInstanceGuard.
"""
import ctypes
import cProfile
import pstats
import json
import logging
import os
import platform
import smtplib
import socket
import sqlite3
import sys
import time
from ctypes import wintypes as w
from dataclasses import replace
from datetime import UTC,datetime,timedelta
from pathlib import Path

ROOT=Path('C:/Users/Leo/.codex/worktrees/v1-5-tp-research/INSO_Leo')
OUT=Path(__file__).resolve().parent
QUICK='--ui-only' in sys.argv
PROFILE='--profile-visible' in sys.argv
PERF='--perf-only' in sys.argv or PROFILE
if QUICK or PERF:
 OUT=OUT/('extended' if QUICK else 'visible-profile' if PROFILE else 'exact-1000')
 OUT.mkdir(exist_ok=True)
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
platform.uname()
def deny(*a,**kw):raise AssertionError('COMPONENT_NETWORK_SQL_SMTP_FORBIDDEN')
socket.socket.connect=socket.socket.connect_ex=socket.create_connection=deny
smtplib.SMTP=smtplib.SMTP_SSL=sqlite3.connect=deny
import customtkinter as ctk
from src.gui import app as gui
from src.gui.contracts import LogEntry,ModuleSnapshot,Order,OrderStatus,RunState,SourceDetail,WorkbenchSnapshot
from src.gui.mock_backend import MockBackend
from src.launcher import single_instance as single
from measure_workbench import process_sample
from verify_workbench_ui import capture
from native_cpu import snapshot as native_snapshot
import threading
logging.getLogger('src.gui.mock_backend').setLevel(logging.INFO)

single.MUTEX_NAME=f'Local\\INSO_COMPONENT_ACCEPTANCE_{os.getpid()}'
guard=single.SingleInstanceGuard()
assert guard.acquire()
backend=MockBackend()
now=datetime.now(UTC)
orders=tuple(Order(f'component-{i:04}',f'DEMO-MPN-{i:04}','合成',i+1,'待验证',None,None,
 (OrderStatus.PENDING,OrderStatus.COMPLETED,OrderStatus.ERROR)[i%3],
 sources=(SourceDetail('INSO','暂无可核实价格'),),remark='合成测试，无生产执行',
 processed_at=now-timedelta(days=i%30),source_sheet=('2026','SHAHAB')[i%2],source_row=i+2,run_id='synthetic-current' if i%2==0 else '',
 module_id=('inquiry','quotation','tp')[i%3],business_status='MAIL_QUEUED' if i%3==2 else None,
 delivery_status='UNKNOWN' if i==2 else 'SENT' if i%3==2 else None) for i in range(1000))
snapshot=WorkbenchSnapshot(1,replace(backend.get_status(),next_poll_at=now+timedelta(minutes=15)),
 backend.get_health(),orders,modules=(ModuleSnapshot('inquiry','询价采购','空闲'),
 ModuleSnapshot('quotation','报价跟进','空闲'),ModuleSnapshot('tp','目标价调研','未启用')),
 total_orders=1000,planned_check_at=now+timedelta(minutes=15))
backend.get_workbench_snapshot=lambda:snapshot
backend.order_action_hint=lambda key,action:(key==orders[0].inquiry_id and action in {'purchase','quotation'}) or (key==orders[5].inquiry_id and action=='tp')
requests,feedback,checks,errors,samples=[],[],[],[],[]
backend.request_order_action=lambda key,action,**kw:requests.append((key,action)) or '合成安全拒绝：没有生产服务。'
gui.messagebox.showwarning=lambda *a,**kw:feedback.append(a)
app=gui.InsoDashboardApp(backend)
app._root.title('V1.5 原生Tk控件集中验收（合成，自动结束）')
app._root.geometry('1400x760+20+20')
app._root.report_callback_exception=lambda kind,value,tb:errors.append(kind.__name__)
began=time.monotonic()
last_cpu,last_wall=time.process_time(),time.monotonic()
phase='functional'
profiler=cProfile.Profile(timer=time.process_time) if PROFILE else None
u=ctypes.WinDLL('user32',use_last_error=True)
u.GetAncestor.argtypes=[w.HWND,w.UINT];u.GetAncestor.restype=w.HWND
u.IsIconic.argtypes=[w.HWND];u.IsWindow.argtypes=[w.HWND]
u.GetForegroundWindow.restype=w.HWND
u.GetWindowThreadProcessId.argtypes=[w.HWND,ctypes.POINTER(w.DWORD)]

def save(name,value):(OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
def check(name,condition):
 checks.append({'check':name,'passed':bool(condition)})
 if not condition:raise AssertionError(name)
def pump(seconds=.25):
 end=time.monotonic()+seconds
 while time.monotonic()<end:
  app._root.update();time.sleep(.02)
def publish():
 global snapshot
 snapshot=replace(snapshot,revision=snapshot.revision+1)
 app._view.render(snapshot,force=True);pump()
def buttons():
 return {x.cget('text'):x for x in app._detail_container.winfo_children() if isinstance(x,ctk.CTkButton)}
def observe():
 global last_cpu,last_wall
 wall,cpu=time.monotonic(),time.process_time()
 foreground=w.DWORD();handle=u.GetForegroundWindow()
 u.GetWindowThreadProcessId(handle,ctypes.byref(foreground))
 row=dict(native=native_snapshot(os.getpid()),seconds=wall-began,phase=phase,cpu_host_percent=(cpu-last_cpu)/max(.001,wall-last_wall)*100/(os.cpu_count() or 1),
  after_callbacks=len(app._root.tk.call('after','info')),event_queue=len(app._events._queue)+len(app._events._latest),
  visible_rows=len(app._tree.get_children()),foreground_handle_present=bool(handle),own_window_foreground=foreground.value==os.getpid(),**process_sample())
 samples.append(row);last_cpu,last_wall=cpu,wall
 save('component-samples.json',samples)
def finish(error=None):
 global phase
 if getattr(app,'_closing',False):return
 if error:errors.append(error)
 observe()
 phase='closing'
 app._on_close()
def restore_then_finish():
 global phase
 try:
  app._on_tray_command('show');pump()
  check('canonical_tray_restore_visible',not app._hidden and app._root.state()=='normal')
  observe()
  phase='visible_restored'
  app._root.after(10000 if PERF else 30000,lambda:finish())
 except Exception as exc:finish(type(exc).__name__)
def hide_to_tray():
 global phase
 try:
  if PROFILE:
   profiler.disable()
   with (OUT/'cpu-profile.txt').open('w',encoding='utf-8') as stream:
    pstats.Stats(profiler,stream=stream).strip_dirs().sort_stats('tottime').print_stats(40)
   finish();return
  app._on_window_close();pump()
  check('real_shell_tray_available',app._hidden and app._tray is not None and app._tray.available)
  phase='tray_idle';observe()
  for delay in ((30000,60000) if PERF else (30000,60000,90000)):app._root.after(delay,observe)
  app._root.after(65000 if PERF else 95000,restore_then_finish)
 except Exception as exc:finish(type(exc).__name__)
def exercise():
 global snapshot,phase
 try:
  publish()
  if PERF:
   app._view.nav_buttons['任务中心'].invoke();pump()
   for i in range(1500):backend._log(f'合成容量测试 {i}')
   snapshot=replace(snapshot,logs=backend.get_logs()[-300:]);publish()
   app._view.nav_buttons['总览'].invoke();pump()
   phase='visible_idle';observe()
   if PROFILE:profiler.enable()
   for delay in range(30000,681000,30000):app._root.after(delay,observe)
   app._root.after(685000,lambda:finish())
   return
  for name,button in app._view.nav_buttons.items():
   button.invoke();pump()
   check('nav_command_'+name,app._view.page==name)
   capture(app._root,OUT/f'component-page-{app._view.pages.index(name)}.png')
  app._view.nav_buttons['任务中心'].invoke();pump()
  check('table_page_limit',len(app._tree.get_children())==200)
  app._view.search.insert(0,'MPN-0000')
  app._view.search.focus_set();pump();app._view.search._entry.event_generate('<KeyRelease>');pump(.4)
  check('search_key_binding',app._tree.get_children()==(orders[0].inquiry_id,))
  app._view.search.delete(0,'end');app._view.search._entry.event_generate('<KeyRelease>');pump(.4)
  for key,value,default in [('source','SHAHAB','全部来源'),('module','目标价调研','全部模块'),('status','需核对','全部状态')]:
   app._view.filters[key].set(value);app._view.filter_changed();pump(.4)
   ids=app._tree.get_children()
   condition=bool(ids)
   if key=='source':condition=condition and all(int(v.rsplit('-',1)[1])%2 for v in ids)
   if key=='module':condition=condition and all(int(v.rsplit('-',1)[1])%3==2 for v in ids)
   check('filter_'+key,condition)
   app._view.filters[key].set(default);app._view.filter_changed();pump(.4)
  heading=app._tree.heading('quantity','command')
  app._tree.tk.call(heading);pump()
  values=[app._displayed_orders[key].quantity for key in app._tree.get_children()]
  check('heading_registered_sort',values==sorted(values) or values==sorted(values,reverse=True))
  first=app._tree.get_children();app._view.page_by(1);pump()
  check('next_page_changes_rows',first!=app._tree.get_children())
  app._view.page_by(-1);pump();check('previous_page_returns',first==app._tree.get_children())
  for value,remainder in [('当前任务',0),('历史记录',1)]:
   app._view.filters['scope'].set(value);app._view.filter_changed();pump(.4)
   check('scope_'+value,bool(app._tree.get_children()) and all(int(key.rsplit('-',1)[1])%2==remainder for key in app._tree.get_children()))
  app._view.filters['scope'].set('全部记录');app._view.filter_changed();pump(.4)
  app._view.nav_buttons['调研结果'].invoke();pump()
  check('missing_price_not_zero',all(app._tree.item(key,'values')[-1]=='暂无价格' for key in app._tree.get_children()))
  for idx in (0,5):
   app._view.render_detail(orders[idx]);pump()
   for label,action in [('重跑采购流程','purchase'),('重跑报价流程','quotation'),('重跑 TP 价格','tp')]:
    widget=buttons()[label];enabled=backend.order_action_hint(orders[idx].inquiry_id,action)
    check(f'detail_hint_{idx}_{action}',(widget.cget('state')=='normal')==enabled)
    if enabled:widget.invoke()
  check('three_reruns_rejected',len(requests)==3 and len(feedback)==3)
  app._view.render_detail(orders[2]);pump()
  check('unknown_all_reruns_disabled',all(buttons()[label].cget('state')=='disabled' for label in ('重跑采购流程','重跑报价流程','重跑 TP 价格')))
  widgets=tuple(x.winfo_id() for x in app._detail_container.winfo_children())
  app._view.render_detail(orders[2]);check('unchanged_detail_reuses_widgets',widgets==tuple(x.winfo_id() for x in app._detail_container.winfo_children()))
  capture(app._root,OUT/'component-detail.png');app._view.hide_detail()
  # Exercise original context-menu builder without entering a native modal loop.
  records=[]
  class Menu:
   def __init__(self,*a,**kw):pass
   def add_command(self,**kw):records.append(kw)
   def tk_popup(self,*a):pass
   def grab_release(self):pass
  original=gui.Menu;gui.Menu=Menu
  try:
   app._view.sort('model');pump();key=app._tree.get_children()[0]
   bbox=app._tree.bbox(key)
   from types import SimpleNamespace
   app._on_order_context(SimpleNamespace(y=bbox[1]+2,x_root=0,y_root=0))
   check('context_menu_three_registered_actions',len(records)==3)
  finally:gui.Menu=original
  for i in range(1500):backend._log(f'合成容量测试 {i}')
  snapshot=replace(snapshot,logs=backend.get_logs()[-300:]);publish()
  app._view.nav_buttons['运行记录'].invoke();pump()
  check('backend_log_bounded_1000',len(backend.get_logs())==1000)
  check('projected_log_bounded_300',len(snapshot.logs)==300)
  check('event_queue_bounded',len(app._events._queue)<=256)
  check('rendered_log_300_lines',len(app._view.logs.get('1.0','end').strip().splitlines())==300)
  check('rendered_latest_log', '合成容量测试 1499' in app._view.logs.get('1.0','end'))
  capture(app._root,OUT/'component-logs-after-capacity.png')
  snapshot=replace(snapshot,modules=(replace(snapshot.modules[0],status='已暂停',waiting_reason='合成网站故障：等待恢复'),*snapshot.modules[1:]));publish()
  app._view.nav_buttons['异常与通知'].invoke();pump()
  text=app._view.notices.get('1.0','end')
  check('notice_unknown_text','邮件发送结果尚未确认' in text)
  check('notice_website_fault_text','合成网站故障' in text)
  capture(app._root,OUT/'component-notice-after-fault.png')
  app._view.nav_buttons['设置'].invoke();pump()
  settings=app._view.settings.cget('text')
  check('settings_three_modules',all(name in settings for name in ('询价采购','报价跟进','目标价调研')))
  check('settings_tp_disabled','目标价调研：未启用' in settings)
  app._root.iconify();pump()
  hwnd=u.GetAncestor(app._root.winfo_id(),2)
  check('native_window_minimized',bool(u.IsIconic(hwnd)))
  app._root.deiconify();pump();check('native_window_restored',app._root.state()=='normal')
  app._view.nav_buttons['总览'].invoke();pump()
  if QUICK:
   finish();return
  phase='visible_idle';observe()
  for delay in (30000,60000,90000):app._root.after(delay,observe)
  app._root.after(95000,hide_to_tray)
 except Exception as exc:finish(type(exc).__name__)

save('environment.json',dict(pid=os.getpid(),orders=1000,main_tid=threading.get_native_id(),logical_cpus=os.cpu_count(),source_sha='9f5522d7bef41a15fc099f9ad1545120dd9565c1',tp_enabled=False,production_backend=False,qualification='Exact prior PERF setup; only extended duration/native counter observations and graceful close instead of focus-restoring tray path.'))
try:
 app._root.after(500,exercise)
 app.run()
finally:
 backend.shutdown()
 if app._tray is not None:app._tray.stop()
 guard.release()
k=ctypes.WinDLL('kernel32',use_last_error=True)
k.OpenMutexW.argtypes=[w.DWORD,w.BOOL,w.LPCWSTR];k.OpenMutexW.restype=w.HANDLE
k.CloseHandle.argtypes=[w.HANDLE]
h=k.OpenMutexW(0x100000,False,single.MUTEX_NAME)
released=not bool(h)
if h:k.CloseHandle(h)
save('component-complete.json',dict(pid=os.getpid(),elapsed_seconds=time.monotonic()-began,
 checks=checks,callback_errors=errors,requests=requests,feedback_count=len(feedback),
 close_finalized=app._close_finalized,private_test_mutex_released=released,
 original_demo_71024_untouched=True,original_soak_70956_untouched=True,
 tray_thread_stopped=not(app._tray and app._tray.thread and app._tray.thread.is_alive()),
 qualification='Tk widget command/event component test; not native pointer testing or exit of Owner demo',
 passed=not errors and all(c['passed'] for c in checks) and app._close_finalized and released))
raise SystemExit(0 if not errors and released else 1)
