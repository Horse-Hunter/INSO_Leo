"""Internal counter endpoints provide continuous >=600s independent windows."""
import json,sys,os
from pathlib import Path
p=Path(sys.argv[1]);path=p/'gui.jsonl'
rows=[json.loads(s) for s in path.read_text(encoding='utf-8').splitlines()] if path.exists() else json.loads((p/'component-samples.json').read_text(encoding='utf-8'))
groups={}
for phase in sorted(set(r['phase'] for r in rows)):
 subset=[r for r in rows if r['phase']==phase and r['seconds']>=60 and 'warmup' not in phase]
 if len(subset)<2:continue
 a,b=subset[0],subset[-1];x,y=a['native'],b['native'];dt=y['wall']-x['wall']
 if dt<=0:continue
 vals=dict(seconds=dt,points=len(subset),first_seconds=a['seconds'],last_seconds=b['seconds'],cpu_host_percent=((y['kernel']-x['kernel'])+(y['user']-x['user']))/dt*100/(os.cpu_count() or 1),user_seconds=y['user']-x['user'],kernel_seconds=y['kernel']-x['kernel'],foreground_points=sum(r['native']['foreground'] for r in subset),max_gap=max(v['native']['wall']-u['native']['wall'] for u,v in zip(subset,subset[1:])),rss_range=[min(r['native']['rss'] for r in subset),max(r['native']['rss'] for r in subset)],private_range=[min(r['native']['private'] for r in subset),max(r['native']['private'] for r in subset)])
 old={(t['tid'],t['created']):t for t in x['threads']};leaders=[]
 for t in y['threads']:
  before=old.get((t['tid'],t['created']))
  if before:leaders.append(dict(tid=t['tid'],module=t['start_module'],user=t['user']-before['user'],kernel=t['kernel']-before['kernel']))
 vals['thread_leaders']=sorted(leaders,key=lambda x:x['user']+x['kernel'],reverse=True)[:5]
 if 'events' in a:vals['event_deltas']={k:b['events'].get(k,0)-a['events'].get(k,0) for k in set(a['events'])|set(b['events'])}
 if 'timings' in a:vals['callback_deltas']={k:[b['timings'][k][i]-a['timings'].get(k,[0,0,0])[i] for i in range(3)] for k in b['timings']}
 if 'self_sampler_thread_cpu_seconds' in a:vals['self_sampler_thread_cpu_seconds']=sum(r['self_sampler_thread_cpu_seconds'] for r in subset)
 groups[phase]=vals
(p/'gui-summary.json').write_text(json.dumps(dict(qualification='Warmup>=60s; internal GetProcessTimes/GetThreadTimes endpoints; all actual focus observations retained; no interpolation across absent endpoints.',groups=groups),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:{key:v[key] for key in ('seconds','cpu_host_percent','user_seconds','kernel_seconds','foreground_points','points')} for k,v in groups.items()},indent=2))
