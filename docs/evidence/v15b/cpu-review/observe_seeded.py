"""Finite external sampler: process/thread deltas, never controls target."""
import json,os,sys,time
from datetime import UTC,datetime
from pathlib import Path
from native_cpu import snapshot
out=Path(__file__).resolve().parent
count=int(sys.argv[1]);folder=out/f'seeded-{count}'
deadline=time.monotonic()+30
while not (folder/'environment.json').exists() and time.monotonic()<deadline:time.sleep(.2)
pid=json.loads((folder/'environment.json').read_text(encoding='utf-8'))['pid']
start=time.monotonic()
while time.monotonic()-start<1400:
 before=time.process_time()
 try:state=json.loads((folder/'state.json').read_text(encoding='utf-8'))
 except (FileNotFoundError,json.JSONDecodeError):state={}
 row=dict(at=datetime.now(UTC).isoformat(),seconds=time.monotonic()-start,state=state,targets=[snapshot(p) for p in (pid,71024)])
 row['observer_cpu_seconds']=time.process_time()-before
 with (folder/'native.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(row)+'\n')
 if (folder/'complete.json').exists():break
 time.sleep(10)
(folder/'observer-complete.json').write_text(json.dumps(dict(seconds=time.monotonic()-start,observer_pid=os.getpid(),observer_cpu_seconds=time.process_time(),logical_cpus=os.cpu_count()),indent=2),encoding='utf-8')
