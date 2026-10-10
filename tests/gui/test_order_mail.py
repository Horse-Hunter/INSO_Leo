import threading
import time

from src.gui.app import InsoDashboardApp
from src.gui.contracts import RunState
from src.gui.mock_backend import MockBackend
from tests.gui.test_gui_contracts import _close_test_app, _CloseBackend


def test_close_waits_for_mail_worker():
    events = []
    backend = _CloseBackend(events, RunState.STOPPED)
    backend.order_mail_running = lambda: True
    app = _close_test_app(backend, events)
    app._on_close()
    assert not app._close_finalized
    backend.order_mail_running = lambda: False
    app._root.run_next()
    assert app._close_finalized


def test_real_tk_equal_split_and_sanitized_result():
    # Real Tk widget geometry, synthetic backend only: no Vault/network/DB.
    backend = MockBackend()
    checks = []
    backend.start_order_mail_check = lambda: checks.append(1) or True
    backend.order_mail_running = lambda: False
    backend.get_order_mail_report = lambda: "synthetic sanitized result"
    app = InsoDashboardApp(backend)
    try:
        deadline = time.monotonic() + 3
        while app._order_mail_button.winfo_width() <= 1 and time.monotonic() < deadline:
            app._root.update()
            time.sleep(.02)
        left, right = app._login_all_button, app._order_mail_button
        assert left.cget("text") == "一键登录所有网站"
        assert right.cget("text") == "自动订单录单"
        assert left.winfo_width() > 100
        assert abs(left.winfo_width() - right.winfo_width()) <= 1
        assert left.winfo_rootx() + left.winfo_width() <= right.winfo_rootx()
        assert left.winfo_rooty() == right.winfo_rooty()
        app._on_order_mail()
        assert checks == [1]
        assert right.cget("state") == "disabled"
        app._sync_order_mail()
        assert right.cget("state") == "normal"
        assert app._shown_order_mail_report == "synthetic sanitized result"
        assert threading.get_ident() == app._main_thread_id
    finally:
        app._root.destroy()
        backend.shutdown()
