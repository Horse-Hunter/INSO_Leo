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


def test_initial_build_and_shutdown_share_lifecycle_gate(tmp_path, monkeypatch):
    from threading import Event, Thread

    import src.launcher.mail_research_composition as composition
    from src.launcher.backend import ProductionBackend

    entered, release = Event(), Event()
    calls = []
    service = SimpleNamespace(start=lambda: calls.append("start"), close=lambda: calls.append("close"))
    def build(_):
        entered.set()
        assert release.wait(2)
        return service
    monkeypatch.setattr(composition, "build_mail_research", build)
    backend = ProductionBackend(root=tmp_path)
    starter = Thread(target=backend.start_process_services)
    starter.start()
    assert entered.wait(2)
    closer = Thread(target=backend.shutdown)
    closer.start()
    try:
        assert not backend._closed
    finally:
        release.set()
        starter.join(timeout=3)
        closer.join(timeout=3)
    assert not starter.is_alive() and not closer.is_alive()
    assert backend._closed and calls == ["close"]


def test_business_start_does_not_wait_for_service_initialization(tmp_path):
    from threading import Event, Thread
    from time import monotonic

    from src.launcher.backend import ProductionBackend

    backend = ProductionBackend(root=tmp_path)
    entered, release = Event(), Event()
    def hold_gate():
        with backend._mail_start_retry_lock:
            entered.set()
            assert release.wait(2)
    holder = Thread(target=hold_gate)
    holder.start()
    assert entered.wait(2)
    before = monotonic()
    try:
        backend.start()
        assert monotonic()-before < 0.5
        assert backend._thread is None
    finally:
        release.set()
        holder.join(timeout=2)
        backend.shutdown()


def test_exit_intent_immediately_stops_service_before_final_shutdown(tmp_path):
    from threading import Event

    from src.launcher.backend import ProductionBackend

    backend = ProductionBackend(root=tmp_path)
    service = SimpleNamespace(stop_event=Event(), wake=Event(), close=lambda: None)
    backend._mail_research_service = service
    backend.request_process_service_stop()
    assert backend._closing_intent.is_set()
    assert service.stop_event.is_set() and service.wake.is_set()
    assert not backend._closed
    backend.shutdown()
    assert backend._closed


def test_composition_retries_after_preparation_without_migration_or_claim_reset(tmp_path, monkeypatch):
    import pytest

    import src.launcher.mail_research_composition as composition

    config = _write_config(tmp_path, _mapping(cdp={"cdp_url": "http://127.0.0.1:9222"}))
    production = tmp_path / "production.json"
    production.write_text(json.dumps({"sqlite_path": "workflow.sqlite3"}), encoding="utf-8")
    backend = ProductionBackend(root=tmp_path, config_path=config, production_config_path=production)
    original = composition.PageResourceAdmission
    monkeypatch.setattr(composition, "PageResourceAdmission", lambda **kwargs: (_ for _ in ()).throw(RuntimeError("synthetic composition failure")))
    with pytest.raises(RuntimeError):
        build_mail_research(backend)
    assert backend._mail_research_prepared is not None
    production.write_text(json.dumps({"sqlite_path": "other.sqlite3"}), encoding="utf-8")
    with pytest.raises(ValueError, match="MAIL_RESEARCH_CONFIG_CHANGED_RESTART_REQUIRED"):
        build_mail_research(backend)
    production.write_text(json.dumps({"sqlite_path": "workflow.sqlite3"}), encoding="utf-8")
    monkeypatch.setattr(composition, "PageResourceAdmission", original)
    def forbidden(*args, **kwargs):
        raise AssertionError("retry must not reinitialize or migrate")
    monkeypatch.setattr(composition, "WorkflowStateStore", forbidden)
    monkeypatch.setattr(composition, "migrate_v12", forbidden)
    monkeypatch.setattr(composition, "V13HoldStore", forbidden)
    monkeypatch.setattr(composition, "MailResearchStore", forbidden)
    service = build_mail_research(backend)
    assert service.store.path == service.outbox.database_path == tmp_path / "workflow.sqlite3"
    service.close()
    backend.shutdown()


def test_completed_preparation_can_retry_failed_composition(tmp_path, monkeypatch):
    from threading import Event

    import src.launcher.mail_research_composition as composition

    backend = ProductionBackend(root=tmp_path)
    calls = []
    service = SimpleNamespace(threads=[], stop_event=Event(), wake=Event(),
        start=lambda: calls.append("start"), close=lambda: calls.append("close"))
    def build(owner):
        calls.append("build")
        if owner._mail_research_prepared is None:
            owner._mail_research_prepared = object()
            raise RuntimeError("synthetic post-preparation failure")
        return service
    monkeypatch.setattr(composition, "build_mail_research", build)
    monkeypatch.setattr(composition, "verify_prepared_configuration", lambda owner: None)
    backend.start_process_services()
    assert backend._mail_start_failed and backend._mail_research_service is None
    backend._mail_start_retry_at = 0
    backend.retry_failed_process_service()
    backend._mail_start_retry_thread.join(timeout=2)
    assert calls == ["build", "build", "start"]
    assert backend._mail_research_service is service and not backend._mail_start_failed
    backend.shutdown()


def test_unfinished_preparation_is_never_retried_while_database_state_unknown(tmp_path, monkeypatch):
    import src.launcher.mail_research_composition as composition

    backend = ProductionBackend(root=tmp_path)
    calls = []
    def fail(_):
        calls.append("build")
        raise RuntimeError("synthetic unknown migration state")
    monkeypatch.setattr(composition, "build_mail_research", fail)
    backend.start_process_services()
    backend._mail_start_retry_at = 0
    backend.retry_failed_process_service()
    assert calls == ["build"]
    assert backend._mail_start_retry_thread is None
    assert backend._mail_research_prepared is None
    backend.shutdown()


def test_failed_service_start_does_not_retry_after_configuration_changes(tmp_path, monkeypatch):
    import src.launcher.mail_research_composition as composition

    config = _write_config(tmp_path, _mapping(cdp={"cdp_url": "http://127.0.0.1:9222"}))
    production = tmp_path / "production.json"
    production.write_text(json.dumps({"sqlite_path": "workflow.sqlite3"}), encoding="utf-8")
    backend = ProductionBackend(root=tmp_path, config_path=config, production_config_path=production)
    def fail(_):
        raise RuntimeError("synthetic startup failure")
    monkeypatch.setattr(composition.MailResearchService, "start", fail)
    backend.start_process_services()
    assert backend._mail_start_failed and backend._mail_research_service is not None
    production.write_text(json.dumps({"sqlite_path": "different.sqlite3"}), encoding="utf-8")
    starts = []
    monkeypatch.setattr(composition.MailResearchService, "start", lambda _: starts.append(True))
    backend._mail_start_retry_at = 0
    backend.retry_failed_process_service()
    backend._mail_start_retry_thread.join(timeout=2)
    assert starts == [] and backend._mail_start_failed
    backend.shutdown()


def test_pre_database_config_failure_retries_while_initially_quiescent(tmp_path, monkeypatch):
    import src.launcher.mail_research_composition as composition

    config = _write_config(tmp_path, _mapping(cdp={"cdp_url": "http://127.0.0.1:9222"}))
    production = tmp_path / "production.json"
    backend = ProductionBackend(root=tmp_path, config_path=config, production_config_path=production)
    started = []
    monkeypatch.setattr(composition.MailResearchService, "start", lambda _: started.append(True))
    backend.start_process_services()
    assert backend._mail_prepare_phase == "CONFIG" and backend._mail_start_failed
    production.write_text(json.dumps({"sqlite_path": "workflow.sqlite3"}), encoding="utf-8")
    backend._mail_start_retry_at = 0
    backend.retry_failed_process_service()
    backend._mail_start_retry_thread.join(timeout=4)
    assert started == [True] and backend._mail_prepare_phase == "PREPARED"
    assert backend._mail_research_service is not None and not backend._mail_start_failed
    backend.shutdown()


def test_pre_database_retry_stops_after_another_owner_started(tmp_path, monkeypatch):

    config = _write_config(tmp_path, _mapping(cdp={"cdp_url": "http://127.0.0.1:9222"}))
    production = tmp_path / "production.json"
    backend = ProductionBackend(root=tmp_path, config_path=config, production_config_path=production)
    backend.start_process_services()
    assert backend._mail_prepare_phase == "CONFIG" and backend._mail_start_failed
    monkeypatch.setattr(backend, "_order_mail_worker", lambda: None)
    assert backend.start_order_mail_check()
    backend._order_mail_thread.join(timeout=2)
    production.write_text(json.dumps({"sqlite_path": "workflow.sqlite3"}), encoding="utf-8")
    backend._mail_start_retry_at = 0
    backend.retry_failed_process_service()
    assert backend._mail_start_retry_thread is None
    assert not (tmp_path / "workflow.sqlite3").exists()
    backend.shutdown()


def test_failure_after_database_mutation_begins_is_not_retried(tmp_path, monkeypatch):
    import src.launcher.mail_research_composition as composition

    config = _write_config(tmp_path, _mapping(cdp={"cdp_url": "http://127.0.0.1:9222"}))
    production = tmp_path / "production.json"
    production.write_text(json.dumps({"sqlite_path": "workflow.sqlite3"}), encoding="utf-8")
    backend = ProductionBackend(root=tmp_path, config_path=config, production_config_path=production)
    def fail(_):
        raise RuntimeError("synthetic DB initialization failure")
    monkeypatch.setattr(composition, "WorkflowStateStore", fail)
    backend.start_process_services()
    assert backend._mail_prepare_phase == "MUTATING" and not backend._mail_start_failed
    backend._mail_start_retry_at = 0
    backend.retry_failed_process_service()
    assert backend._mail_start_retry_thread is None
    backend.shutdown()


def test_exit_intent_blocks_new_order_mail_and_login_owners(tmp_path):
    backend = ProductionBackend(root=tmp_path)
    backend.request_process_service_stop()
    assert backend.start_order_mail_check() is False
    backend.start_login_all_sites()
    assert backend._order_mail_thread is None and backend._login_all_thread is None
    backend.shutdown()


def test_initial_service_initialization_is_consumed_once_even_after_failure(tmp_path, monkeypatch):
    import src.launcher.mail_research_composition as composition

    backend = ProductionBackend(root=tmp_path)
    calls = []
    def fail(_):
        calls.append("attempt")
        raise RuntimeError("synthetic initialization failure")
    monkeypatch.setattr(composition, "build_mail_research", fail)
    backend.start_process_services()
    backend.start_process_services()
    assert calls == ["attempt"]
    backend.shutdown()


def test_pre_database_retry_excludes_other_business_owners(tmp_path, monkeypatch):
    from threading import Event

    import src.launcher.mail_research_composition as composition

    backend = ProductionBackend(root=tmp_path)
    entered, release = Event(), Event()
    calls = []
    service = SimpleNamespace(threads=[], stop_event=Event(), wake=Event(),
        start=lambda: calls.append("started"), close=lambda: None)
    def build(owner):
        owner._mail_prepare_phase = "CONFIG"
        calls.append("build")
        if len(calls) == 1:
            raise RuntimeError("synthetic config read failure")
        entered.set()
        assert release.wait(2)
        return service
    monkeypatch.setattr(composition, "build_mail_research", build)
    backend.start_process_services()
    backend._mail_start_retry_at = 0
    backend.retry_failed_process_service()
    assert entered.wait(2)
    try:
        assert backend.start() is False
        assert backend.start_order_mail_check() is False
        backend.start_login_all_sites()
        assert backend._thread is None and backend._order_mail_thread is None and backend._login_all_thread is None
    finally:
        release.set()
        backend._mail_start_retry_thread.join(timeout=3)
        backend.shutdown()
    assert calls == ["build", "build", "started"]


def test_close_during_local_loader_wait_prevents_database_initialization(tmp_path, monkeypatch):
    from threading import Event, Thread

    import src.launcher.mail_research_composition as composition

    backend = ProductionBackend(root=tmp_path)
    entered, release = Event(), Event()
    def local():
        entered.set()
        assert release.wait(2)
    backend._local_view_thread = Thread(target=local)
    backend._local_view_thread.start()
    assert entered.wait(2)
    calls = []
    monkeypatch.setattr(composition, "build_mail_research", lambda _: calls.append("build"))
    starter = Thread(target=backend.start_process_services)
    starter.start()
    closer = Thread(target=backend.shutdown)
    closer.start()
    assert backend._closing_intent.wait(2)
    release.set()
    starter.join(timeout=3)
    closer.join(timeout=3)
    assert not starter.is_alive() and not closer.is_alive()
    assert backend._closed and calls == []


def test_exit_during_config_read_prevents_first_database_mutation(tmp_path, monkeypatch):
    from threading import Event, Thread

    import src.launcher.mail_research_composition as composition

    config = _write_config(tmp_path, _mapping(cdp={"cdp_url": "http://127.0.0.1:9222"}))
    production = tmp_path / "production.json"
    production.write_text(json.dumps({"sqlite_path": "workflow.sqlite3"}), encoding="utf-8")
    backend = ProductionBackend(root=tmp_path, config_path=config, production_config_path=production)
    entered, release = Event(), Event()
    original = composition.load_runtime_config
    def slow_config(path):
        entered.set()
        assert release.wait(2)
        return original(path)
    monkeypatch.setattr(composition, "load_runtime_config", slow_config)
    starter = Thread(target=backend.start_process_services)
    starter.start()
    assert entered.wait(2)
    closer = Thread(target=backend.shutdown)
    closer.start()
    assert backend._closing_intent.wait(2)
    release.set()
    starter.join(timeout=3)
    closer.join(timeout=3)
    assert not starter.is_alive() and not closer.is_alive()
    assert not (tmp_path / "workflow.sqlite3").exists()
    assert backend._mail_prepare_phase == "CONFIG" and backend._closed


def test_config_retry_that_reaches_unknown_database_state_never_repeats(tmp_path, monkeypatch):
    import src.launcher.mail_research_composition as composition

    config = _write_config(tmp_path, _mapping(cdp={"cdp_url": "http://127.0.0.1:9222"}))
    production = tmp_path / "production.json"
    backend = ProductionBackend(root=tmp_path, config_path=config, production_config_path=production)
    backend.start_process_services()
    assert backend._mail_prepare_phase == "CONFIG" and backend._mail_start_failed
    production.write_text(json.dumps({"sqlite_path": "workflow.sqlite3"}), encoding="utf-8")
    calls = []
    def fail(_):
        calls.append("DB attempt")
        raise RuntimeError("synthetic uncertain DB state")
    monkeypatch.setattr(composition, "WorkflowStateStore", fail)
    backend._mail_start_retry_at = 0
    backend.retry_failed_process_service()
    backend._mail_start_retry_thread.join(timeout=2)
    assert calls == ["DB attempt"] and backend._mail_prepare_phase == "MUTATING"
    assert not backend._mail_start_failed
    backend._mail_start_retry_at = 0
    backend.retry_failed_process_service()
    assert calls == ["DB attempt"]
    backend.shutdown()
