"""Process-lifetime composition; invoked before business Start, never by a poll."""
import json
import logging
from contextlib import nullcontext
from dataclasses import replace
from datetime import UTC, datetime, timedelta

from src.core.app_paths import resolve_app_path
from src.order_mail.research_requests import ResearchInbox
from src.research.cdp_pages import PageResourceAdmission
from src.research.ecb_fx import EcbDailyUsdRmbProvider
from src.research.mail_session import DetailedReadSession
from src.research.runtime import load_runtime_config
from src.sheets.tp_brief import quantity_value
from src.workflow.mail_research import MailResearchService
from src.workflow.mail_research_store import MailResearchStore
from src.workflow.store import WorkflowStateStore
from src.workflow.v12_notifications import V12NotificationWorker
from src.workflow.v12_smtp_transport import QQSMTPConfig, QQSMTPTransport
from src.workflow.v12_store import V12Store, migrate_v12
from src.workflow.v13_integration import V13HoldStore


def build_mail_research(backend):
    cfg = json.loads(backend.production_path.read_text(encoding="utf-8"))
    rc = load_runtime_config(backend.config_path)
    path = resolve_app_path(cfg.get("sqlite_path", "runtime/production/workflow.sqlite3"), root=backend.root)
    WorkflowStateStore(path)  # Preserve original V1.1 baseline initialization.
    # This entry is before the GUI starts business workers. The local history
    # loader has joined. No migration is invoked by a mailbox poll or task.
    migrate_v12(path, path.parent / "backups" / "v12-upgrade", quiesce=nullcontext)
    V13HoldStore(path).migrate()
    store = MailResearchStore(path)
    store.migrate()
    outbox = V12Store(path)
    outbox.recover_abandoned_notification_attempts(at=datetime.now(UTC), scope="mail")
    from src.sheets.pending import WorksheetIdentity

    rc = replace(rc, icnet=replace(rc.icnet, mode="cdp"))  # Attach only; no new browser.
    backend._research_catalog.configure_sources(
        WorksheetIdentity(cfg["spreadsheet_id"], title) for title in cfg.get("worksheet_titles", ())
    )
    admission = PageResourceAdmission(parent=backend._page_admission)
    budget = backend._background_research_budget
    def read(key, source, order, reference, fx):
        from src.research.cdp_pages import PageTargetCleanupError

        from .research_budget import ResearchDeferred
        with budget.background() as checkpoint:
            try:
                with DetailedReadSession(rc, admission) as session:
                    session.read_checkpoint = checkpoint
                    checkpoint()
                    result = session.read_source(key, source, order, reference, fx)
                    checkpoint()
                    return result
            except PageTargetCleanupError:
                if not admission.failed_locally:
                    raise ResearchDeferred("SHARED_RESOURCE_WAITING_OWNER") from None
                raise
    worker = V12NotificationWorker(outbox, QQSMTPTransport(config=QQSMTPConfig(sender_address="1069599116@qq.com")), scope="mail",
        review_current=lambda command, now: service.review_mail(command, now),
        prepare_content=lambda command, now: service.prepare_mail(command, now))
    service = MailResearchService(store=store, inbox_factory=ResearchInbox, source_reader=read,
        fx_provider=EcbDailyUsdRmbProvider(), catalog=backend._research_catalog,
        outbox=outbox, worker=worker,
        admit=lambda: (backend._poll_idle.is_set() and not backend._manual_busy
                       and backend._manual_request is None and not backend.login_all_running() and not backend.order_mail_running()))
    return service


def append_report(command, report):
    import html
    body = command.html_body or "<html><body><pre>"+html.escape(command.text_body)+"</pre></body></html>"
    if "</body>" in body:
        body = body.replace("</body>", report["html"]+"</body>", 1)
    else:
        body = "<html><body>"+body+report["html"]+"</body></html>"
    return replace(command, text_body=command.text_body+"\n\n"+report["text"], html_body=body)


# Existing120s mail poll budget, measured from the original durable notice.
# No sleep/timer, schema, or retry/restart reset; final business review still gates SMTP.
BUSINESS_REPORT_WAIT = timedelta(seconds=120)


def _business_report_unavailable(command, order, *, follow_up):
    import html

    lines = (["该订单发给采购后已超过3个工作小时，原表仍为‘发给采购’，请人工跟进采购报价；不要重发采购。"]
             if follow_up else ["原重要询价通知：请及时跟进该询价。"])
    lines += [f"客户名称：{order.customer or '未核实'}", f"型号：{order.mpn}",
              f"品牌：{order.brand or '未核实'}", f"数量：{order.quantity}",
              "询价日期："+str(order.rfq_date)+(f"（{order.date_source}）" if order.date_source else "")]
    if follow_up:
        # Preserve only the native confirmed purchase timestamp from the original
        # episode notice; never copy its whole body or historical market facts.
        lines += [line for line in command.text_body.splitlines() if line.startswith("发给采购时间：")]
    lines += ["详细市场报价暂不可用／未核实。价格与库存尚未核实，本通知不含市场数据或估算金额。"]
    text = "\n".join(lines)
    return replace(command, text_body=text, html_body="<html><body><pre>"+html.escape(text)+"</pre></body></html>")


def prepare_business_report(backend, command, now):
    import json

    from src.research.detailed import DetailedOrder
    from src.sheets.worksheet_schema import worksheet_schema
    from src.workflow.v12_contracts import NotificationKind
    proof = json.loads(command.review or "{}")
    if command.kind is not NotificationKind.IMPORTANT_ORDER and proof.get("reason_code") != "PURCHASE_FOLLOW_UP_REQUIRED":
        return command
    current = backend._current_mail_source(command.inquiry_id, now, manual=proof.get("manual") is True)
    if current is None:
        return None
    item, row, _, date_origin, day = current
    schema = worksheet_schema(item.record_identity.worksheet.worksheet)
    try:
        quantity = quantity_value(item.quantity)
        if quantity <= 0:
            return None
    except (ValueError, TypeError):
        return None
    customer = schema.fixed_customer_name or row.cells.get(schema.customer_name_column) if schema.customer_name_column else schema.fixed_customer_name
    order = DetailedOrder(item.mpn, item.resolved_brand or item.brand or None, quantity,
                          customer, str(day), item.record_identity.worksheet.worksheet, row.row_position,
                          spreadsheet=item.record_identity.worksheet.spreadsheet,
                          date_source="本地订单日期（近似）" if date_origin == "LOCAL_INTAKE_APPROXIMATION" else None)
    expired = now-command.created_at >= BUSINESS_REPORT_WAIT
    service = backend._mail_research_service
    try:
        if service is not None:
            cached = service.cached_report(order, now)
            if cached is not None:
                return append_report(command, cached)
            job = service.store.get(command.command_id)
            if job is not None and job["state"] == "READY":
                report = json.loads(job["report"])
                if timedelta(0) <= now-datetime.fromisoformat(report["completed_at"]) <= timedelta(minutes=15):
                    return append_report(command, report)
                if not expired:
                    service.store.refresh_business(command.command_id)
                    service.wake.set()
            elif job is None and not expired:
                service.store.request_business(command, order, now)
                service.wake.set()
    except Exception as error:  # noqa: BLE001 - optional enrichment never disables verified business notices
        logging.getLogger(__name__).warning("Business mail detailed report unavailable; class=%s", type(error).__name__)
    if not expired:
        return None
    return _business_report_unavailable(command, order,
        follow_up=proof.get("reason_code") == "PURCHASE_FOLLOW_UP_REQUIRED")
