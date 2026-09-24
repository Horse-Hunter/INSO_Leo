"""Tests for resource management utilities."""

import logging
import threading
from time import sleep

from src.gui.resources import ResourceManager, RingBufferLog, get_process_memory_mb


def test_ring_buffer_respects_capacity():
    buf = RingBufferLog(capacity=5)
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(logging.Formatter("%(message)s"))
    buf.setFormatter(handler.formatter)

    for i in range(10):
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg=f"msg-{i}",
            args=(),
            exc_info=None,
        )
        buf.emit(record)

    snapshot = buf.snapshot()
    assert len(snapshot) == 5
    assert snapshot[0].message == "msg-5"
    assert snapshot[-1].message == "msg-9"


def test_ring_buffer_listener_receives_entries():
    buf = RingBufferLog(capacity=10)
    buf.setFormatter(logging.Formatter("%(message)s"))
    received = []

    def listener(entry):
        received.append(entry.message)

    buf.add_listener(listener)
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="hello",
        args=(),
        exc_info=None,
    )
    buf.emit(record)

    assert received == ["hello"]

    buf.remove_listener(listener)
    buf.emit(record)
    assert len(received) == 1


def test_resource_manager_joins_threads():
    manager = ResourceManager()
    thread = threading.Thread(target=lambda: sleep(0.05), name="test-thread")
    thread.start()
    manager.add_thread(thread, "test-thread")
    manager.close_all()
    assert not thread.is_alive()


def test_resource_manager_close_is_idempotent():
    manager = ResourceManager()
    manager.close_all()
    manager.close_all()  # should not raise


def test_get_process_memory_mb_returns_non_negative():
    value = get_process_memory_mb()
    assert isinstance(value, float)
    assert value >= 0.0
