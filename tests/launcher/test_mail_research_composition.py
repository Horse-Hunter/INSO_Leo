"""Production composition with fake browser boundary, no credentials/network."""
import json
from types import SimpleNamespace

from src.launcher.backend import ProductionBackend
from src.launcher.mail_research_composition import build_mail_research
from src.research.detailed import DetailedOrder, TpFx
from src.research.source_contracts import ResearchSource
from tests.research.test_runtime import _mapping, _write_config
from tests.workflow.test_v12_notifications import NOW


def test_composition_same_db_and_endpoint_runs_while_main_stopped(tmp_path, monkeypatch):
    import src.launcher.mail_research_composition as composition
    config = _write_config(tmp_path, _mapping(cdp={"cdp_url": "http://127.0.0.1:9222"}))
    production = tmp_path / "production.json"
    production.write_text(json.dumps({"sqlite_path": "workflow.sqlite3"}), encoding="utf-8")
    backend = ProductionBackend(root=tmp_path, config_path=config, production_config_path=production)
    calls = []
    class Session:
        def __init__(self, rc, admission):
            assert rc.cdp.cdp_url == "http://127.0.0.1:9222" and rc.icnet.mode == "cdp"
            admission.require_open()
        def __enter__(self):
            calls.append("attach")
            return self
        def __exit__(self, *_):
            calls.append("detach")
        def read_source(self, *args):
            return "synthetic-confirmed", None
    monkeypatch.setattr(composition, "DetailedReadSession", Session)
    service = build_mail_research(backend)
    assert service.store.path == service.outbox.database_path == tmp_path / "workflow.sqlite3"
    backend._stop.set()
    assert service.admit() and not service.stop_event.is_set()
    assert service.source_reader("mail-research:one", ResearchSource.HQEW, DetailedOrder("MPN"), NOW, TpFx(None, NOW)) == ("synthetic-confirmed", None)
    assert calls == ["attach", "detach"]
    service.close(); backend.shutdown()


def test_process_lifetime_start_once_and_only_exit_closes_service(tmp_path, monkeypatch):
    import src.launcher.mail_research_composition as composition
    calls = []
    service = SimpleNamespace(start=lambda: calls.append("start"), close=lambda: calls.append("close"))
    monkeypatch.setattr(composition, "build_mail_research", lambda backend: service)
    backend = ProductionBackend(root=tmp_path)
    backend.start_process_services(); backend.start_process_services()
    backend.request_stop_after_cycle()
    assert calls == ["start"]
    backend.shutdown(); backend.shutdown()
    assert calls == ["start", "close"]
