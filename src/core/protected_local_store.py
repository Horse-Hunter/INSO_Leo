"""Small Windows CurrentUser DPAPI boundary for local opaque secret bytes."""

from __future__ import annotations

import ctypes
import os
from ctypes import wintypes
from pathlib import Path


class ProtectedStoreError(RuntimeError):
    """Local user protection is unavailable or the stored value is invalid."""


class _DataBlob(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]


def _transform(value: bytes, *, protect: bool) -> bytes:
    if os.name != "nt":
        raise ProtectedStoreError("Windows CurrentUser protection is required")
    buffer = ctypes.create_string_buffer(value)
    source = _DataBlob(len(value), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte)))
    result = _DataBlob()
    crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
    operation = crypt32.CryptProtectData if protect else crypt32.CryptUnprotectData
    operation.restype = wintypes.BOOL
    if protect:
        operation.argtypes = [
            ctypes.POINTER(_DataBlob), wintypes.LPCWSTR, ctypes.c_void_p,
            ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD,
            ctypes.POINTER(_DataBlob),
        ]
        ok = operation(ctypes.byref(source), None, None, None, None, 0,
                       ctypes.byref(result))
    else:
        operation.argtypes = [
            ctypes.POINTER(_DataBlob), ctypes.c_void_p, ctypes.c_void_p,
            ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD,
            ctypes.POINTER(_DataBlob),
        ]
        ok = operation(ctypes.byref(source), None, None, None, None, 0,
                       ctypes.byref(result))
    if not ok:
        raise ProtectedStoreError(
            f"Windows CurrentUser protection failed ({ctypes.get_last_error()})"
        )
    try:
        return ctypes.string_at(result.pbData, result.cbData)
    finally:
        local_free = ctypes.windll.kernel32.LocalFree
        local_free.argtypes = [ctypes.c_void_p]
        local_free.restype = ctypes.c_void_p
        local_free(result.pbData)


def protect_bytes(value: bytes) -> bytes:
    return _transform(value, protect=True)


def unprotect_bytes(value: bytes) -> bytes:
    return _transform(value, protect=False)


def local_app_data_dir() -> Path:
    root = os.environ.get("LOCALAPPDATA")
    if not root:
        raise ProtectedStoreError("LOCALAPPDATA is unavailable")
    return Path(root) / "INSO_Leo"
