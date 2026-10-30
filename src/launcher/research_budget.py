"""Same Chrome budget: foreground is preferred; background owns only one read."""
import threading
from contextlib import contextmanager
from functools import wraps


class ResearchDeferred(RuntimeError):
    pass


class ResearchBudget:
    def __init__(self):
        self.gate, self.condition = threading.RLock(), threading.Lock()
        self.waiters = 0

    @contextmanager
    def foreground(self):
        with self.condition:
            self.waiters += 1
        try:
            with self.gate:
                yield
        finally:
            with self.condition:
                self.waiters -= 1

    @contextmanager
    def background(self):
        with self.condition:
            allowed = self.waiters == 0 and self.gate.acquire(blocking=False)
        if not allowed:
            raise ResearchDeferred("FOREGROUND_PRIORITY")
        try:
            yield
        finally:
            self.gate.release()


def foreground_resources(fn):
    @wraps(fn)
    def guarded(self, *args, **kwargs):
        budget = getattr(self, "_background_research_budget", None)
        if budget is None:
            return fn(self, *args, **kwargs)
        with budget.foreground():
            return fn(self, *args, **kwargs)
    return guarded
