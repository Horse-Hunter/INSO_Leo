"""Finite external installed-process resource sampling, no window control."""
from pathlib import Path
import sys,json,time,os
from datetime import datetime,UTC
root=Path('C:/Users/Leo/.codex/worktrees/v1-5-tp-research/INSO_Leo')
sys.path.insert(0,str(root/'docs/evidence/v15b/cpu-review'))
from native_cpu import snapshot
out=Path(__file__).resolve().parent
pid=int(sys.argv[1]);watch=int(sys.argv[2]);tag=sys.argv[3] if len(sys.argv)>3 else 'first'
rows=[];started=time.monotonic()
for i in range(13):
 row=dict(at=datetime.now(UTC).isoformat(),seconds=time.monotonic()-started,targets=[snapshot(pid),snapshot(watch)])
 rows.append(row)
 if 'unavailable' in row['targets'][0]:break
 if i<12:time.sleep(10)
summary=dict(pid=pid,watch_pid=watch,elapsed=time.monotonic()-started,samples=len(rows),logical_cpus=os.cpu_count(),qualification='Finite read-only GetProcessTimes/GetThreadTimes on installed idle process and its existing observer; menu/tray activity may occur; no business started.')
for index,label in ((0,'app'),(1,'observer')):
 valid=[r['targets'][index] for r in rows if 'kernel' in r['targets'][index]]
 if len(valid)>1:
  a,b=valid[0],valid[-1];dt=b['wall']-a['wall'];summary[label]=dict(seconds=dt,cpu_host_percent=((b['user']-a['user'])+(b['kernel']-a['kernel']))/dt*100/(os.cpu_count() or 1),rss_min=min(r['rss'] for r in valid),rss_max=max(r['rss'] for r in valid),private_min=min(r['private'] for r in valid),private_max=max(r['private'] for r in valid),threads_min=min(len(r['threads']) for r in valid),threads_max=max(len(r['threads']) for r in valid),handles_min=min(r['handles'] for r in valid),handles_max=max(r['handles'] for r in valid),gdi_range=[min(r['gdi'] for r in valid),max(r['gdi'] for r in valid)],user_range=[min(r['user_objects'] for r in valid),max(r['user_objects'] for r in valid)])
(out/f'installed-{tag}-samples.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
(out/f'installed-{tag}-resources.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
print(json.dumps(summary))
