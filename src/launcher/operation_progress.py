"""Passive progress receipts for the existing browser owner; no worker or I/O."""
from contextlib import contextmanager
from dataclasses import dataclass
from threading import Lock
from time import monotonic
from uuid import uuid4


@dataclass(frozen=True)
class StalledOperation:
    generation: str
    module: str


class OperationProgress:
    def __init__(self, *, clock=monotonic, idle_limit=600, grace=30, confirm=5):
        self.clock, self.idle_limit, self.grace, self.confirm = clock, idle_limit, grace, confirm
        self.lock = Lock()
        self.frames = []
        self.last_check = None
        self.stalled = None

    @contextmanager
    def scope(self, module):
        frame = {'generation':uuid4().hex, 'module':module, 'progressed':self.clock(),
                 'calls':{}, 'suspect':None}
        with self.lock:
            self.frames.append(frame)
        def native(event, token, deadline):
            with self.lock:
                if event == 'begin':
                    frame['calls'][token] = deadline
                else:
                    frame['calls'].pop(token, None)
                    frame['progressed'] = self.clock()
                    frame['suspect'] = None
        try:
            yield native
        finally:
            with self.lock:
                if self.frames[-1:] == [frame]:
                    self.frames.pop()
                if self.frames:
                    self.frames[-1]['progressed'] = self.clock()
                    self.frames[-1]['suspect'] = None

    def check(self, *, excluded, trip):
        """Atomically compare the same still-active generation; callback has no I/O."""
        with self.lock:
            now = self.clock()
            resumed = self.last_check is None or now-self.last_check > self.grace
            self.last_check = now
            if not self.frames or self.stalled is not None or excluded():
                return None
            frame = self.frames[-1]
            deadline = (min(frame['calls'].values())+self.grace if frame['calls']
                        else frame['progressed']+self.idle_limit)
            if now <= deadline:
                frame['suspect'] = None
                return None
            if resumed or frame['suspect'] is None:
                frame['suspect'] = now
                return None
            if now-frame['suspect'] < self.confirm or excluded():
                return None
            incident = StalledOperation(frame['generation'], frame['module'])
            if not trip():
                return None
            self.stalled = incident
            return incident
