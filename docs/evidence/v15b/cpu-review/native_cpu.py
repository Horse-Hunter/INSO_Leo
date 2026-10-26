"""Finite diagnostic Win32 counters only; no UI control, debug or suspension."""
import ctypes as c
from ctypes import wintypes as w
import os,time
k=c.WinDLL('kernel32',use_last_error=True);u=c.WinDLL('user32',use_last_error=True)
nt=c.WinDLL('ntdll');ps=c.WinDLL('psapi')
class Thread(c.Structure):
 _fields_=[('size',w.DWORD),('usage',w.DWORD),('tid',w.DWORD),('pid',w.DWORD),('base',w.LONG),('delta',w.LONG),('flags',w.DWORD)]
class Module(c.Structure):
 _fields_=[('size',w.DWORD),('id',w.DWORD),('pid',w.DWORD),('glob',w.DWORD),('proc',w.DWORD),('base',c.c_void_p),('bytes',w.DWORD),('handle',w.HMODULE),('name',w.WCHAR*256),('path',w.WCHAR*260)]
class Memory(c.Structure):
 _fields_=[('cb',w.DWORD),('faults',w.DWORD)]+[(name,c.c_size_t) for name in ('peak_rss','rss','peak_paged','paged','peak_nonpaged','nonpaged','pagefile','peak_pagefile','private')]
k.OpenProcess.argtypes=[w.DWORD,w.BOOL,w.DWORD];k.OpenProcess.restype=w.HANDLE
k.OpenThread.argtypes=[w.DWORD,w.BOOL,w.DWORD];k.OpenThread.restype=w.HANDLE
k.CloseHandle.argtypes=[w.HANDLE]
k.CreateToolhelp32Snapshot.argtypes=[w.DWORD,w.DWORD];k.CreateToolhelp32Snapshot.restype=w.HANDLE
for name,typ in [('Thread32First',Thread),('Thread32Next',Thread),('Module32FirstW',Module),('Module32NextW',Module)]:
 getattr(k,name).argtypes=[w.HANDLE,c.POINTER(typ)]
for name in ('GetProcessTimes','GetThreadTimes'):
 getattr(k,name).argtypes=[w.HANDLE]+[c.POINTER(w.FILETIME)]*4
k.GetProcessHandleCount.argtypes=[w.HANDLE,c.POINTER(w.DWORD)]
k.GetThreadDescription.argtypes=[w.HANDLE,c.POINTER(c.c_wchar_p)]
k.LocalFree.argtypes=[c.c_void_p]
ps.GetProcessMemoryInfo.argtypes=[w.HANDLE,c.POINTER(Memory),w.DWORD]
nt.NtQueryInformationThread.argtypes=[w.HANDLE,w.ULONG,c.c_void_p,w.ULONG,c.c_void_p]
u.GetForegroundWindow.restype=w.HWND
u.GetWindowThreadProcessId.argtypes=[w.HWND,c.POINTER(w.DWORD)]
u.GetGuiResources.argtypes=[w.HANDLE,w.DWORD]
def times(handle,fn):
 fields=[w.FILETIME() for _ in range(4)]
 if not fn(handle,*[c.byref(f) for f in fields]):return None
 vals=[((f.dwHighDateTime<<32)+f.dwLowDateTime)/1e7 for f in fields]
 return dict(created=vals[0],kernel=vals[2],user=vals[3])
def snapshot(pid,threads=True):
 h=k.OpenProcess(0x410,False,pid)
 if not h:return dict(pid=pid,unavailable=c.get_last_error())
 try:
  result=dict(pid=pid,wall=time.monotonic(),**times(h,k.GetProcessTimes))
  foreground=w.DWORD();hwnd=u.GetForegroundWindow();u.GetWindowThreadProcessId(hwnd,c.byref(foreground))
  mem=Memory();mem.cb=c.sizeof(mem);ps.GetProcessMemoryInfo(h,c.byref(mem),mem.cb)
  handles=w.DWORD();k.GetProcessHandleCount(h,c.byref(handles))
  result.update(foreground=foreground.value==pid,foreground_handle_present=bool(hwnd),rss=mem.rss,private=mem.private,handles=handles.value,gdi=u.GetGuiResources(h,0),user_objects=u.GetGuiResources(h,1))
  if not threads:return result
  modules=[];mh=k.CreateToolhelp32Snapshot(0x18,pid)
  if mh!=c.c_void_p(-1).value:
   try:
    m=Module();m.size=c.sizeof(m);more=k.Module32FirstW(mh,c.byref(m))
    while more:
     modules.append((m.base,m.base+m.bytes,m.name));more=k.Module32NextW(mh,c.byref(m))
   finally:k.CloseHandle(mh)
  rows=[];sh=k.CreateToolhelp32Snapshot(4,0)
  try:
   t=Thread();t.size=c.sizeof(t);more=k.Thread32First(sh,c.byref(t))
   while more:
    if t.pid==pid:
     th=k.OpenThread(0x40,False,t.tid)
     if th:
      try:
       row=times(th,k.GetThreadTimes)
       if row:
        row['tid']=t.tid;addr=c.c_void_p();status=nt.NtQueryInformationThread(th,9,c.byref(addr),c.sizeof(addr),None)
        row['start_module']=next((name for lo,hi,name in modules if addr.value and lo<=addr.value<hi),'UNKNOWN') if status==0 else 'ACCESS_UNKNOWN'
        row['start_offset']=next((hex(addr.value-lo) for lo,hi,name in modules if addr.value and lo<=addr.value<hi),None)
        desc=c.c_wchar_p()
        if k.GetThreadDescription(th,c.byref(desc))==0:
         row['description']=desc.value or '';k.LocalFree(c.cast(desc,c.c_void_p))
        rows.append(row)
      finally:k.CloseHandle(th)
    more=k.Thread32Next(sh,c.byref(t))
  finally:k.CloseHandle(sh)
  result['threads']=rows
  return result
 finally:k.CloseHandle(h)
