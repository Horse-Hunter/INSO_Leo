"""Finite read-only CPU/foreground observation of the known visible Mock PID."""
import ctypes
import json
import os
import time
from ctypes import wintypes as w
from pathlib import Path
k=ctypes.WinDLL('kernel32',use_last_error=True)
u=ctypes.WinDLL('user32',use_last_error=True)
k.OpenProcess.argtypes=[w.DWORD,w.BOOL,w.DWORD]
k.OpenProcess.restype=w.HANDLE
k.GetProcessTimes.argtypes=[w.HANDLE]+[ctypes.POINTER(w.FILETIME)]*4
k.CloseHandle.argtypes=[w.HANDLE]
u.GetForegroundWindow.restype=w.HWND
u.GetWindowThreadProcessId.argtypes=[w.HWND,ctypes.POINTER(w.DWORD)]
out=Path(__file__).resolve().parent
pid=json.loads((out/'environment.json').read_text(encoding='utf-8'))['pid']
h=k.OpenProcess(0x1000,False,pid)
assert h
rows=[]
try:
 for i in range(7):
  created,exited,kernel,user=(w.FILETIME() for _ in range(4))
  assert k.GetProcessTimes(h,*[ctypes.byref(v) for v in (created,exited,kernel,user)])
  foreground=w.DWORD()
  foreground_handle=u.GetForegroundWindow()
  u.GetWindowThreadProcessId(foreground_handle,ctypes.byref(foreground))
  cpu=sum((v.dwHighDateTime<<32)+v.dwLowDateTime for v in (kernel,user))/1e7
  rows.append(dict(wall=time.monotonic(),cpu_seconds=cpu,foreground_handle_present=bool(foreground_handle),mock_is_foreground=foreground.value==pid))
  if i<6:time.sleep(10)
finally:k.CloseHandle(h)
span=rows[-1]['wall']-rows[0]['wall']
one=(rows[-1]['cpu_seconds']-rows[0]['cpu_seconds'])/span*100
result=dict(pid=pid,seconds=span,cpu_one_core_percent=one,cpu_host_percent=one/(os.cpu_count() or 1),
 foreground_at_all_seven_points=all(r['mock_is_foreground'] for r in rows),
 qualification='No injected input during this interval; point observations do not prove continuous foreground',samples=rows)
(out/'foreground-cpu-owner.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result))
