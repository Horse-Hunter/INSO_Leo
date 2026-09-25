"""Windows named-mutex single-instance guard."""

from __future__ import annotations

import ctypes
import os
from ctypes import wintypes
from dataclasses import dataclass

ERROR_ALREADY_EXISTS = 183
MUTEX_NAME = r"Local\INSO_V1.1"


@dataclass
class SingleInstanceGuard:
    handle: object | None = None
    release_fn: object | None = None
    is_windows: bool | None = None
    api: object | None = None

    def acquire(self) -> bool:
        if (os.name == "nt") if self.is_windows is None else self.is_windows:
            return self._acquire_windows()
        return True

    def _acquire_windows(self) -> bool:
        if self.api is None:
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel32.CreateMutexW.argtypes = (
                wintypes.LPVOID,
                wintypes.BOOL,
                wintypes.LPCWSTR,
            )
            kernel32.CreateMutexW.restype = wintypes.HANDLE
            kernel32.ReleaseMutex.argtypes = (wintypes.HANDLE,)
            kernel32.ReleaseMutex.restype = wintypes.BOOL
            kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
            kernel32.CloseHandle.restype = wintypes.BOOL
            self.api = kernel32
        kernel32 = self.api
        if self.api is None:
            return True
        ctypes.set_last_error(0)
        handle = kernel32.create_mutex(MUTEX_NAME) if hasattr(kernel32, "create_mutex") else kernel32.CreateMutexW(None, True, MUTEX_NAME)
        if not handle:
            raise OSError(ctypes.get_last_error(), "CreateMutexW failed")
        self.handle = handle
        self.release_fn = kernel32
        last_error = kernel32.get_last_error() if hasattr(kernel32, "get_last_error") else ctypes.get_last_error()
        if last_error == ERROR_ALREADY_EXISTS:
            if hasattr(kernel32, "close_handle"):
                kernel32.close_handle(handle)
            else:
                kernel32.CloseHandle(handle)
            self.handle = None
            self.release_fn = None
            return False
        return True

    def release(self) -> None:
        if self.handle is None:
            return
        kernel32 = self.release_fn
        try:
            if hasattr(kernel32, "release_mutex"):
                kernel32.release_mutex(self.handle)
            else:
                kernel32.ReleaseMutex(self.handle)
        finally:
            if hasattr(kernel32, "close_handle"):
                kernel32.close_handle(self.handle)
            else:
                kernel32.CloseHandle(self.handle)
            self.handle = None
            self.release_fn = None
