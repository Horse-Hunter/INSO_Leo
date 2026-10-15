from threading import get_ident
from types import SimpleNamespace

from src.gui.app import InsoDashboardApp


def app():
    instance = InsoDashboardApp.__new__(InsoDashboardApp)
    instance._main_thread_id = get_ident()
    instance._closing = False
    calls = []
    instance._tray = SimpleNamespace(start=lambda: True, stop=lambda: calls.append('stop-icon'))
    instance._root = SimpleNamespace(withdraw=lambda: calls.append('hide'),
        deiconify=lambda: calls.append('show'), lift=lambda: calls.append('raise'))
    return instance, calls


def test_x_hides_without_requesting_business_stop_and_restore_works():
    instance, calls = app()
    instance._backend = SimpleNamespace(request_stop_after_cycle=lambda: calls.append('BAD-stop'))
    instance._on_window_close()
    assert calls == ['hide'] and not instance._closing
    instance._on_tray_command('show')
    assert calls == ['hide', 'show', 'raise']


def test_only_tray_exit_enters_existing_graceful_shutdown():
    instance, calls = app()
    instance._on_close = lambda: calls.append('graceful-exit')
    instance._on_tray_command('exit')
    assert calls == ['graceful-exit']


def test_failed_tray_start_preserves_window_and_does_not_stop_business(monkeypatch):
    from src.gui import app as module
    instance, calls = app()
    instance._tray.start = lambda: False
    monkeypatch.setattr(module.messagebox, 'askyesno', lambda *a: calls.append('warning') or False)
    instance._on_window_close()
    assert calls == ['stop-icon', 'warning'] and instance._tray is None
    assert not instance._closing
