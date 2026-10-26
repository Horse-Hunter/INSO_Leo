"""Finite matched Mock GUI performance diagnosis. No business services."""
import ctypes,cProfile,json,logging,os,platform,smtplib,socket,sqlite3,sys,threading,time
from collections import Counter,defaultdict
from dataclasses import replace
from datetime import UTC,datetime,timedelta
from pathlib import Path
ROOT=Path('C:/Users/Leo/.codex/worktrees/v1-5-tp-research/INSO_Leo')
OUT=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
platform.uname()
os.environ['INSO_RUNTIME_ROOT']=str(OUT/'runtime')
def deny(*a,**kw):raise RuntimeError('CPU_REVIEW_EXTERNAL_SQL_SMTP_FORBIDDEN')
socket.socket.connect=socket.socket.connect_ex=socket.create_connection=deny
smtplib.SMTP=smtplib.SMTP_SSL=sqlite3.connect=deny
from src.gui.app import InsoDashboardApp
from src.gui.mock_backend import MockBackend
from src.gui.contracts import Order,OrderStatus,SourceDetail,ModuleSnapshot,WorkbenchSnapshot
from src.launcher import single_instance as single
from native_cpu import snapshot as native
import customtkinter as ctk
logging.getLogger('src.gui.mock_backend').setLevel(logging.INFO)
count=int(sys.argv[1]) if len(sys.argv)>1 else 250
OUT=OUT/f'rows-{count}';OUT.mkdir(exist_ok=True)
def save(name,value):(OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
single.MUTEX_NAME=f'Local\\INSO_CPU_DIAG_{os.getpid()}'
guard=single.SingleInstanceGuard();assert guard.acquire()
backend=MockBackend(cycle_seconds=900)
now=datetime.now(UTC)
orders=tuple(Order(f'demo-{i:04}',f'DEMO-STM32-{i:04}','合成品牌',100+i,'待验证',None,None,
 (OrderStatus.PENDING,OrderStatus.COMPLETED,OrderStatus.ERROR)[i%3],
 sources=tuple(SourceDetail(name,'暂无可核实价格') for name in ('IC.net','Findchips','华强','立创','BOM.AI','INSO')),
 remark='合成只读性能诊断',processed_at=now-timedelta(days=i%30),source_sheet=('2026','SHAHAB')[i%2],source_row=i+2,
 module_id=('inquiry','quotation','tp')[i%3]) for i in range(count))
view=WorkbenchSnapshot(1,replace(backend.get_status(),next_poll_at=now+timedelta(hours=1)),backend.get_health(),orders,
 modules=(ModuleSnapshot('inquiry','询价采购','等待'),ModuleSnapshot('quotation','报价跟进','空闲'),ModuleSnapshot('tp','目标价调研','未启用')),
 total_orders=count,planned_check_at=now+timedelta(hours=1))
backend.get_workbench_snapshot=lambda:view
backend.order_action_hint=lambda *a:False
app=InsoDashboardApp(backend)
app._root.title(f'V1.5 CPU专项只读诊断 | {count}条合成 | 自动结束')
app._root.geometry('1400x760+10+10')
errors=[];events=Counter();timings=defaultdict(lambda:[0,0.0,0.0]);phase='visible_warmup';began=time.monotonic()
app._root.report_callback_exception=lambda kind,value,tb:errors.append(kind.__name__)
def wrap(obj,name,label):
 old=getattr(obj,name)
 def measured(*a,**kw):
  start=time.perf_counter();cpu=time.thread_time()
  try:return old(*a,**kw)
  finally:
   row=timings[label];row[0]+=1;row[1]+=time.perf_counter()-start;row[2]+=time.thread_time()-cpu
 setattr(obj,name,measured)
wrap(app,'_schedule_tick','gui_tick');wrap(app._view,'render','view_render')
wrap(ctk.AppearanceModeTracker,'update','ctk_appearance')
wrap(ctk.ScalingTracker,'check_dpi_scaling','ctk_dpi')
for label in ('Expose','Configure','Motion','FocusIn','FocusOut','Map','Unmap'):
 app._root.bind_all('<'+label+'>',lambda event,label=label:events.update([label]),add='+')
def mark(newphase):
 global phase
 phase=newphase
 save('state.json',dict(pid=os.getpid(),main_tid=threading.get_native_id(),phase=phase,seconds=time.monotonic()-began,orders=count,geometry=app._root.geometry(),hidden=app._hidden))
def observe():
 start=time.thread_time()
 row=dict(at=datetime.now(UTC).isoformat(),seconds=time.monotonic()-began,phase=phase,pid=os.getpid(),main_tid=threading.get_native_id(),orders=count,
  geometry=app._root.geometry(),window_state=app._root.state(),hidden=app._hidden,page=app._view.page,after=len(app._root.tk.call('after','info')),
  events=dict(events),timings=dict(timings),queue=len(app._events._queue)+len(app._events._latest),native=native(os.getpid()))
 row['self_sampler_thread_cpu_seconds']=time.thread_time()-start
 with (OUT/'gui.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(row,ensure_ascii=False)+'\n')
 if not app._closing:app._root.after(30000,observe)
def tray():
 mark('transition_tray');app._on_window_close()
 if not app._hidden:errors.append('TRAY_HIDE_FAILED');app._on_close();return
 mark('tray_warmup');app._root.after(60000,lambda:mark('tray_measure'))
 app._root.after(665000,app._on_close)
def start():
 app._view.render(view,force=True)
 mark('visible_warmup');observe()
 app._root.after(60000,lambda:mark('visible_measure'))
 app._root.after(665000,tray)
save('environment.json',dict(pid=os.getpid(),main_tid=threading.get_native_id(),orders=count,logical_cpus=os.cpu_count(),source_sha='9f5522d7bef41a15fc099f9ad1545120dd9565c1',source_parent='7765f07ab8a30e27aae1f378eeda5b77483e4b4f',tp_enabled=False,production_backend=False,methods='Readonly per-thread Win32 counters; diagnostic callback wrappers, Tk event counters; unchanged business cadence; no focus/lift'))
app._root.after(1000,start)
try:app.run()
finally:
 backend.shutdown()
 if app._tray:app._tray.stop()
 guard.release()
 save('complete.json',dict(pid=os.getpid(),seconds=time.monotonic()-began,errors=errors,close_finalized=app._close_finalized,tray_thread_stopped=not(app._tray and app._tray.thread and app._tray.thread.is_alive()),timings=dict(timings),events=dict(events)))
