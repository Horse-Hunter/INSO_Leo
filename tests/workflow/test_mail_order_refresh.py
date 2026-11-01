"""Synthetic source refresh regression; no sockets, real mailbox or production rows."""
from datetime import timedelta

from src.research.detailed import DetailedOrder
from src.workflow.mail_research import InquiryCatalog
from tests.workflow.test_mail_research import receive, scene
from tests.workflow.test_v12_notifications import NOW


def test_new_mail_refreshes_stopped_main_old_catalog_before_market_and_send(tmp_path):
    service, inbox, smtp, reads, *_ = scene(tmp_path)
    service.catalog.configure_sources(("one", "two"))
    service.catalog.observe("one", (("old", DetailedOrder("MPN", quantity=999), NOW),), observed_at=NOW-timedelta(days=1))
    calls=[]
    def refresh(job):
        calls.append(job["task_id"])
        c=InquiryCatalog();c.configure_sources(("one", "two"))
        c.observe("one", (("new", DetailedOrder("MPN", "TI", 300, "SYNTHETIC", "2026-10-30"), NOW),), observed_at=NOW)
        c.observe("two", (), observed_at=NOW)
        return c
    service.refresh_catalog=refresh
    receive(service,inbox);service.run_one();service.worker.run_due(now=NOW)
    assert calls and all(q==300 for _,_,q in reads)
    with service.store.connect() as db:
        text=db.execute("SELECT text_body FROM workflow_v12_notification_commands WHERE command_id LIKE 'mail-research:%'").fetchone()[0]
    assert "SYNTHETIC" in text and "订单总价" in text and len(smtp.calls)==1
    service.store.migrate();service.worker.run_due(now=NOW)
    assert len(smtp.calls)==1


def test_failed_fresh_read_still_researches_but_does_not_claim_no_order(tmp_path):
    service,inbox,smtp,reads,*_=scene(tmp_path)
    def refresh(_job):raise TimeoutError("synthetic")
    service.refresh_catalog=refresh
    receive(service,inbox);service.run_one();service.worker.run_due(now=NOW)
    with service.store.connect() as db:
        text=db.execute("SELECT text_body FROM workflow_v12_notification_commands WHERE command_id LIKE 'mail-research:%'").fetchone()[0]
    assert "订单来源暂未核实" in text and "订单总价：" not in text
    assert len(reads)==6 and len(smtp.calls)==1


import pytest


@pytest.mark.parametrize("kind",["empty","conflict","missing_date"])
def test_refreshed_conflicts_and_absence_are_explicit_and_never_invent_total(tmp_path,kind):
    service,inbox,smtp,reads,*_=scene(tmp_path)
    def refresh(_job):
        c=InquiryCatalog();c.configure_sources(("one","two"))
        order=DetailedOrder("MPN","TI",300,"SYNTHETIC","2026-09-01")
        c.observe("one",() if kind=="empty" else (("a",order,None if kind=="missing_date" else NOW),),observed_at=NOW)
        c.observe("two",(("b",order,NOW),) if kind=="conflict" else (),observed_at=NOW)
        return c
    service.refresh_catalog=refresh;receive(service,inbox);service.run_one();service.worker.run_due(now=NOW)
    with service.store.connect() as db:text=db.execute("select text_body from workflow_v12_notification_commands where command_id like 'mail-research:%'").fetchone()[0]
    assert {"empty":"未找到同型号询价","conflict":"同日多单冲突","missing_date":"日期未能核实"}[kind] in text
    assert "订单总价：" not in text and all(q is None for _,_,q in reads) and len(smtp.calls)==1


def test_wrapped_foreground_preemption_defers_without_market_or_mail(tmp_path):
    from src.launcher.research_budget import ResearchDeferred
    from src.sheets.google_reader import GoogleSheetsReadError
    service,inbox,smtp,reads,*_=scene(tmp_path)
    def refresh(_job):
        try:raise ResearchDeferred("FOREGROUND_PRIORITY")
        except ResearchDeferred as e:raise GoogleSheetsReadError("synthetic") from e
    service.refresh_catalog=refresh;receive(service,inbox)
    assert not service.run_one() and not reads and not smtp.calls


def test_wrapped_native_google_cleanup_uncertainty_persists_resource_hold(tmp_path):
    from src.sheets.google_reader import GoogleSheetsReadError
    from src.workflow.v12_faults import FaultScope, V12Fault
    service,inbox,_smtp,reads,*_=scene(tmp_path)
    def refresh(_job):
        try:raise V12Fault(FaultScope.GLOBAL_STOP,"GOOGLE_OPERATION_NOT_CLOSED")
        except V12Fault as e:raise GoogleSheetsReadError("synthetic") from e
    service.refresh_catalog=refresh;receive(service,inbox);service.run_one()
    assert service.store.resource_blocked() and not reads and not service.run_one()


def test_send_time_expired_catalog_refresh_retains_same_verified_order(tmp_path):
    service,inbox,smtp,reads,clock,*_=scene(tmp_path)
    calls=[]
    def refresh(_job):
        calls.append(clock[0]);c=InquiryCatalog();c.configure_sources(("one",))
        c.observe("one",(("a",DetailedOrder("MPN","TI",300,"SYNTHETIC","2026-09-01"),NOW),),observed_at=clock[0]);return c
    service.refresh_catalog=refresh;receive(service,inbox);service.run_one()
    clock[0]+=timedelta(seconds=121)
    service.worker.run_due(now=clock[0])
    assert len(calls)==2 and len(smtp.calls)==1
    with service.store.connect() as db:
        text=db.execute("select text_body from workflow_v12_notification_commands where command_id like 'mail-research:%'").fetchone()[0]
    assert "SYNTHETIC" in text and "订单总价" in text and len(reads)==6
