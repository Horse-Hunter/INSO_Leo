"""One native SDK owner-loop deadline shared across browser adapters."""
from __future__ import annotations

import asyncio
import inspect
from contextlib import contextmanager
from contextvars import ContextVar
from math import isfinite
from time import monotonic

NATIVE_PROTOCOL_TIMEOUT_MS = 10000
_BUDGET = ContextVar("native_browser_budget", default=None)
_OBSERVER = ContextVar("native_browser_observer", default=None)


class NativeProtocolTimeout(TimeoutError):
    """Local protocol wait ended; no assertion about a remote write outcome."""


@contextmanager
def browser_call_budget(milliseconds, *, independent=False):
    if not isinstance(milliseconds, (int, float)) or isinstance(milliseconds, bool) or not isfinite(milliseconds) or milliseconds <= 0:
        raise ValueError("INVALID_NATIVE_OPERATION_TIMEOUT")
    end = monotonic() + milliseconds / 1000
    parent = _BUDGET.get()
    token = _BUDGET.set(end if independent or parent is None else min(parent, end))
    try:
        yield
    finally:
        _BUDGET.reset(token)


@contextmanager
def observe_browser_calls(observer):
    token = _OBSERVER.set(observer)
    try:
        yield
    finally:
        _OBSERVER.reset(token)


def bounded_browser_call(port, operation, *args, timeout_ms=None, **kwargs):
    """Explicit async protocol call on its existing SDK thread; never a new client."""
    from playwright._impl._sync_base import SyncBase, mapping
    milliseconds = ((kwargs.get("timeout") or NATIVE_PROTOCOL_TIMEOUT_MS)+1000 if timeout_ms is None else timeout_ms)
    if not isinstance(milliseconds, (int, float)) or isinstance(milliseconds, bool) or not isfinite(milliseconds) or milliseconds <= 0:
        raise ValueError("INVALID_NATIVE_OPERATION_TIMEOUT")
    end = monotonic() + milliseconds / 1000
    parent = _BUDGET.get()
    if parent is not None:
        end = min(end, parent)
    if end <= monotonic():
        raise NativeProtocolTimeout("CDP_OPERATION_TIMEOUT")
    observer = _OBSERVER.get()
    token = object()
    if observer is not None:
        observer("begin", token, end)
    try:
        if not isinstance(port, SyncBase):
            return getattr(port, operation)(*args, **kwargs)
        impl = getattr(port._impl_obj, operation)
        if not inspect.iscoroutinefunction(impl):
            # Cached synchronous getters have no protocol wait to cancel.
            return getattr(port, operation)(*args, **kwargs)
        impl_args = tuple(getattr(arg, "_impl_obj", arg) for arg in args)
        impl_kwargs = {key.split("_")[0]+"".join(part.title() for part in key.split("_")[1:]):
                       (port._wrap_handler(value) if key == "predicate" and callable(value)
                        else getattr(value, "_impl_obj", value)) for key, value in kwargs.items()}
        async def bounded():
            return await asyncio.wait_for(impl(*impl_args, **impl_kwargs), max(.001, end-monotonic()))
        try:
            return mapping.from_maybe_impl(port._sync(bounded()))
        except TimeoutError:
            raise NativeProtocolTimeout("CDP_OPERATION_TIMEOUT") from None
    finally:
        if observer is not None:
            observer("end", token, end)
