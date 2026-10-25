import sys

import pytest

from src.gui import main as launcher


@pytest.mark.parametrize('loading', [False, True])
@pytest.mark.parametrize('start', [False, True])
def test_explicit_start_flag_reuses_backend_after_gui_and_keeps_default_idle(monkeypatch, tmp_path, start, loading):
    events = []
    class Guard:
        def acquire(self):
            events.append('acquire')
            return True
        def release(self):
            events.append('release')
    class Backend:
        def local_view_loading(self):
            return loading
        def start(self):
            events.append('start')
        def shutdown(self):
            events.append('shutdown')
    class App:
        def __init__(self, backend):
            assert isinstance(backend, Backend)
            events.append('gui-ready')
        def run(self):
            assert getattr(self, '_start_on_ready', False) == (start and loading)
            events.append('gui-run')
    monkeypatch.setattr(sys, 'argv', ['INSO_V1.4.exe'] + (['--start-inquiry'] if start else []))
    monkeypatch.setattr(launcher, 'app_root', lambda: tmp_path)
    monkeypatch.setattr(launcher, '_configure_startup_log', lambda _: None)
    monkeypatch.setattr(launcher, 'InsoDashboardApp', App)
    assert launcher.main(guard_factory=Guard, backend_factory=Backend) == 0
    assert events == ['acquire', 'gui-ready'] + (['start'] if start and not loading else []) + ['gui-run', 'shutdown', 'release']
