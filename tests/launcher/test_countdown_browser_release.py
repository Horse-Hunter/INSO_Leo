"""Offline real-client coverage of browser teardown during the poll countdown."""

from threading import Event, Thread, get_ident
from time import monotonic
from types import SimpleNamespace

import pytest
from playwright.sync_api import sync_playwright

from src.gui.contracts import RunState
from src.launcher.backend import ProductionBackend
from src.launcher.browser_bootstrap import BrowserHandle


@pytest.mark.parametrize('deferred', [False, True])
def test_countdown_releases_real_client_before_next_poll(tmp_path, deferred):
    """No Chrome/profile/network: observe actual Playwright stop on its owner."""
    backend = ProductionBackend(root=tmp_path)
    backend._state = RunState.RUNNING
    entered = Event()
    observed = []
    owner = get_ident()
    real_client = sync_playwright().start()

    def stopped():
        observed.append(get_ident())
        real_client.stop()
        entered.set()

    handle = BrowserHandle(owned=False, playwright=SimpleNamespace(stop=stopped), browser=object())
    if deferred:
        worker = Thread(target=handle.disconnect)
        worker.start()
        worker.join(2)
        assert not worker.is_alive()
    else:
        backend._browser_handle = handle
    assert not entered.is_set()

    def observer():
        entered.wait(1)
        backend._stop.set()  # Bound the test; never wait an actual 15 minutes.
        with backend._manual_condition:
            backend._manual_condition.notify_all()

    monitor = Thread(target=observer)
    monitor.start()
    try:
        assert backend._wait_between_polls(900) is True
        assert entered.is_set(), 'Client stayed attached throughout countdown'
        assert observed == [owner]
        assert backend._browser_handle is None
        assert BrowserHandle.drain_deferred_stops() == 0
        # The next cycle can start a real sync client after the old one exits.
        with sync_playwright():
            pass
    finally:
        backend._stop.set()
        monitor.join(2)
        handle.disconnect()
        BrowserHandle.drain_deferred_stops()
        backend.shutdown()


def test_countdown_drains_release_arriving_after_wait_started(tmp_path):
    backend = ProductionBackend(root=tmp_path)
    backend._state = RunState.RUNNING
    queued = Event()
    released = Event()
    calls = []
    owner = get_ident()
    handle = BrowserHandle(owned=False, playwright=SimpleNamespace(stop=lambda: (calls.append(get_ident()), released.set())))
    original_wait = backend._manual_condition.wait

    def wait(timeout):
        queued.set()
        return original_wait(timeout)

    backend._manual_condition.wait = wait

    def worker():
        assert queued.wait(2)
        handle.disconnect()
        released.wait(1)
        backend._stop.set()
        with backend._manual_condition:
            backend._manual_condition.notify_all()

    thread = Thread(target=worker)
    thread.start()
    try:
        started = monotonic()
        assert backend._wait_between_polls(900) is True
        assert released.is_set(), 'A release queued during countdown was ignored'
        assert calls == [owner]
        assert monotonic() - started < 1
    finally:
        backend._stop.set()
        thread.join(2)
        BrowserHandle.drain_deferred_stops()
        backend.shutdown()


@pytest.mark.parametrize('protection', ['pending-order', 'human-login', 'local-pause'])
def test_countdown_disconnect_keeps_review_pages_and_browser(tmp_path, protection):
    backend = ProductionBackend(root=tmp_path)
    backend._state = RunState.RUNNING
    calls = []

    def disconnect():
        calls.append('disconnect')
        backend._stop.set()

    def forbidden():
        pytest.fail('Countdown must preserve review pages and the shared browser')

    backend._browser_handle = BrowserHandle(
        owned=False, playwright=SimpleNamespace(stop=disconnect),
        browser=SimpleNamespace(close=forbidden), close_fn=forbidden,
    )
    backend._inso_session = SimpleNamespace(close_after_drain=forbidden)
    if protection == 'pending-order':
        backend._keepalive_protected_targets.add('synthetic-review-target')
    elif protection == 'human-login':
        backend._site_manual_wait.add('INSO')
    else:
        backend._state = RunState.MODULE_PAUSED
    try:
        assert backend._wait_between_polls(900) is True
        assert calls == ['disconnect']
    finally:
        backend.shutdown()
