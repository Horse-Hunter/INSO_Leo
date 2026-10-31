"""Nonblocking foreground admission; one isolated background read may drain."""
import threading
from contextlib import contextmanager
from functools import wraps


class ResearchDeferred(RuntimeError):
    pass


class ResearchBudget:
    def __init__(self):
        self.gate, self.condition = threading.Lock(), threading.Lock()
        self.foreground_gate = threading.RLock()
        self.waiters, self.generation = 0, 0

    @contextmanager
    def foreground(self):
        # Never acquire the background gate. Its read can be waiting on a site
        # or CDP indefinitely; exact target ownership makes safe overlap possible.
        with self.condition:
            self.waiters += 1
            self.generation += 1
        try:
            with self.foreground_gate:  # Retain original foreground-to-foreground serialization.
                yield
        finally:
            with self.condition:
                self.waiters -= 1

    @contextmanager
    def background(self):
        with self.condition:
            allowed = self.waiters == 0 and self.gate.acquire(blocking=False)
            generation = self.generation
        if not allowed:
            raise ResearchDeferred("FOREGROUND_PRIORITY")
        def checkpoint():
            with self.condition:
                if self.waiters or generation != self.generation:
                    raise ResearchDeferred("FOREGROUND_PRIORITY")
        try:
            yield checkpoint
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
