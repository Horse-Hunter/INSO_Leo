"""Summarize finite counter deltas without smoothing or extrapolation."""
from pathlib import Path
from collections import defaultdict
import json,os,sys
folder=Path(sys.argv[1]);rows=[json.loads(s) for s in (folder/'native.jsonl').read_text(encoding='utf-8').splitlines()]
groups=defaultdict(list);cpu_count=os.cpu_count() or 1
for prev,cur in zip(rows,rows[1:]):
 phase=cur['state'].get('phase')
 if phase!=prev['state'].get('phase') or phase not in ('visible_measure','tray_measure'):continue
 for index in (0,1):
  a,b=prev['targets'][index],cur['targets'][index]
  if 'kernel' not in a or 'kernel' not in b:continue
  dt=b['wall']-a['wall']
  if not 5<dt<30:continue
  foreground='foreground_points' if a['foreground'] and b['foreground'] else 'not_both_foreground'
  entry=dict(seconds=dt,user=b['user']-a['user'],kernel=b['kernel']-a['kernel'],rss=b['rss'],private=b['private'],handles=b['handles'],gdi=b['gdi'],user_objects=b['user_objects'],threads=[])
  old={(t['tid'],t['created']):t for t in a['threads']}
  for t in b['threads']:
   prior=old.get((t['tid'],t['created']))
   if prior:entry['threads'].append(dict(tid=t['tid'],start_module=t['start_module'],start_offset=t['start_offset'],user=t['user']-prior['user'],kernel=t['kernel']-prior['kernel']))
  entry['host_percent']=(entry['user']+entry['kernel'])/dt*100/cpu_count
  groups[(str(b['pid']),phase,'all')].append(entry)
  groups[(str(b['pid']),phase,foreground)].append(entry)
output={}
for (pid,phase,fg),items in groups.items():
 dt=sum(i['seconds'] for i in items);usr=sum(i['user'] for i in items);ker=sum(i['kernel'] for i in items)
 threads=defaultdict(lambda:dict(user=0,kernel=0))
 for i in items:
  for t in i['threads']:
   x=threads[(t['tid'],t['start_module'],t['start_offset'])];x['user']+=t['user'];x['kernel']+=t['kernel']
 leaders=sorted([dict(tid=k[0],module=k[1],offset=k[2],**v) for k,v in threads.items()],key=lambda x:x['user']+x['kernel'],reverse=True)
 output['/'.join((pid,phase,fg))]=dict(intervals=len(items),sampled_seconds=dt,cpu_user_seconds=usr,cpu_kernel_seconds=ker,cpu_host_percent=(usr+ker)/dt*100/cpu_count,cpu_one_core_percent=(usr+ker)/dt*100,interval_host_min=min(i['host_percent'] for i in items),interval_host_max=max(i['host_percent'] for i in items),rss_min=min(i['rss'] for i in items),rss_max=max(i['rss'] for i in items),private_min=min(i['private'] for i in items),private_max=max(i['private'] for i in items),handles_min=min(i['handles'] for i in items),handles_max=max(i['handles'] for i in items),gdi_min=min(i['gdi'] for i in items),gdi_max=max(i['gdi'] for i in items),user_objects_min=min(i['user_objects'] for i in items),user_objects_max=max(i['user_objects'] for i in items),thread_leaders=leaders[:8],thread_accounted_seconds=sum(t['user']+t['kernel'] for t in leaders))
summary=dict(logical_cpus=cpu_count,observations=len(rows),wall_span=rows[-1]['seconds']-rows[0]['seconds'],max_gap=max(b['seconds']-a['seconds'] for a,b in zip(rows,rows[1:])),observer_sample_cpu_seconds=sum(r['observer_cpu_seconds'] for r in rows),qualification='GetProcessTimes/GetThreadTimes cumulative100ns units; host%=one-core%/logical CPUs; warmup and transition excluded; foreground at interval endpoints is not continuous focus proof; thread exits can leave unaccounted residual.',groups=output)
(folder/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:{key:v[key] for key in ('sampled_seconds','cpu_host_percent','cpu_user_seconds','cpu_kernel_seconds')} for k,v in output.items()},indent=2))
