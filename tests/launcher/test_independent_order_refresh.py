"""Native Sheets read/ownership and actual mail composition; all external ports fake."""
import json
import threading
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from src.launcher.backend import ProductionBackend
from src.launcher.google_web import GoogleSheetsWebService
from src.launcher.mail_research_composition import build_mail_research
from src.sheets import WorksheetIdentity
from src.sheets.google_reader import GoogleSheetsRowReader
from src.sheets.tp_brief import BRIEF_HEADERS
from tests.launcher import test_google_web as ports
from tests.launcher.test_google_web import TITLES
from tests.research.test_runtime import _mapping, _write_config
from tests.workflow.test_mail_research import scene


@pytest.fixture
def web(tmp_path):
    return ports.web.__wrapped__(tmp_path)


@pytest.mark.parametrize("unknown",[False,True])
def test_actual_composition_refreshes_stopped_main_from_native_google_and_sends_order(web,tmp_path,monkeypatch,unknown):
    import src.launcher.google_web as google
    import src.launcher.mail_research_composition as composition
    native,browser,rows,human=web
    monkeypatch.setitem(TITLES,"RFQ_BRIEF",51)
    rows["2026"][1]=["发给采购","","B","SYNTHETIC","TEST123","TI","300"]
    line={"sheet":"2026","sheet_row":"2","mpn":"TEST123","mfr":"TI","qty":"300","rfq_date":"2026-09-30","customer":"SYNTHETIC"}
    rows["RFQ_BRIEF"]=[list(BRIEF_HEADERS),[line.get(k,"") for k in BRIEF_HEADERS]]
    config=_write_config(tmp_path,_mapping(cdp={"cdp_url":"http://127.0.0.1:9222"}))
    production=tmp_path/"production.json"
    production.write_text(json.dumps({"sqlite_path":"workflow.sqlite3","spreadsheet_id":"test","worksheet_titles":["2026","SHAHAB"]}))
    backend=ProductionBackend(root=tmp_path,config_path=config,production_config_path=production)
    class Session:
        def __init__(self,*_):pass
        def __enter__(self):return self
        def __exit__(self,*_):pass
        def shared_provider(self):return None
    monkeypatch.setattr(composition,"DetailedReadSession",Session)
    options=[]
    def transport(*args,**kw):
        options.append(kw)
        assert kw["isolated_read"]
        return GoogleSheetsWebService(native._session,isolated_read=True,read_guard=kw["read_guard"])
    monkeypatch.setattr(google,"build_google_web_service",transport)
    composed=build_mail_research(backend)
    backend._stop.set()
    service,inbox,smtp,reads,*_=scene(tmp_path/"mail")
    service.clock=lambda:datetime.now(UTC)
    from tests.workflow.test_rfq016_regressions import real_fake_smtp
    worker,smtp=real_fake_smtp(service.outbox,now=service.clock(),review_current=service.review_mail)
    worker._scope,worker._prepare_content="mail",service.prepare_mail
    service.worker=worker
    if unknown:smtp._send_error=TimeoutError("synthetic uncertain SMTP")
    service.refresh_catalog=composed.refresh_catalog
    from src.order_mail.research_requests import TRIGGER_POLICY, ResearchMail
    service.poll_once()
    inbox.latest=101
    inbox.messages=[(101,ResearchMail("TEST123",None,None,TRIGGER_POLICY))]
    service.poll_once()
    assert service.run_one();service.worker.run_due(now=service.clock())
    assert all(q==300 for _,_,q in reads) and smtp.send_attempts==1
    if not unknown:
        assert str(smtp.message["To"])=="shawn@inso-hk.com"
        assert "SYNTHETIC" in smtp.message.get_body(preferencelist=("plain",)).get_content()
    service.store.migrate();worker.run_due(now=service.clock())
    assert smtp.send_attempts==1
    with service.store.connect() as db:
        text=db.execute("select text_body from workflow_v12_notification_commands where command_id like 'mail-research:%'").fetchone()[0]
    assert "SYNTHETIC" in text and "300" in text and "订单总价" in text
    assert not human.closed and browser.connected and len(options)==1
    assert all(p.closed for p in browser.contexts[0].pages[1:])
    composed.close();backend.shutdown()


def test_native_background_slow_read_does_not_block_due_main_or_close_its_page(web):
    native,browser,_,human=web
    bg=GoogleSheetsWebService(native._session,isolated_read=True)
    entered,release,progressed=threading.Event(),threading.Event(),threading.Event()
    failures=[]
    download=bg._download
    def slow(*args):
        entered.set()
        assert release.wait(4)
        return download(*args)
    bg._download=slow
    def background():
        try:GoogleSheetsRowReader(bg).read_rows(WorksheetIdentity("test","2026"))
        except Exception as e:failures.append(e)  # noqa: BLE001 - surface thread failures
    def foreground():
        try:
            GoogleSheetsRowReader(native).read_rows(WorksheetIdentity("test","SHAHAB"))
            progressed.set()
        except Exception as e:failures.append(e)  # noqa: BLE001 - surface thread failures
    b=threading.Thread(target=background);f=threading.Thread(target=foreground)
    b.start();assert entered.wait(1);f.start()
    try:assert progressed.wait(.25) and b.is_alive()
    finally:release.set();b.join(4);f.join(4)
    assert not failures and not human.closed and browser.connected


def test_isolated_google_rejects_write_before_native_effect(web):
    native,browser,_,human=web
    bg=GoogleSheetsWebService(native._session,isolated_read=True)
    with pytest.raises(ValueError,match="GOOGLE_MAIL_READ_ONLY"):
        bg.update(spreadsheetId="test",range="'2026'!F2",body={"values":[["BAD"]]},valueInputOption="RAW").execute()
    assert browser.contexts[0].pages==[human]


@pytest.mark.parametrize("role",["google-operation","google-mail-read"])
def test_google_role_never_recovers_or_closes_other_role_failed_page(web,role):
    from src.launcher.google_quote_update import GoogleQuotationUpdateActions
    from src.research.cdp_pages import page_owner
    native,_browser,_,human=web
    with native._session() as handle:
        other=GoogleQuotationUpdateActions(browser_handle=handle,location=SimpleNamespace(url="https://docs.google.com/spreadsheets/d/test/edit#gid=0"),page_role=role)
        old=other.open_sheet();old.read_failed=True
        target=GoogleSheetsWebService(native._session,isolated_read=(role=="google-operation"))
        GoogleSheetsRowReader(target).read_rows(WorksheetIdentity("test","2026"))
        assert not old.closed and page_owner(old)==role and not human.closed
        other.close()
