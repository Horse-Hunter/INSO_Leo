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
from src.workflow.mail_research import InquiryCatalog, MailResearchService
from src.workflow.mail_research_store import MailResearchStore
from src.workflow.store import WorkflowStateStore
from src.workflow.v12_notifications import V12NotificationWorker
from src.workflow.v12_smtp_transport import QQSMTPConfig, QQSMTPTransport
from src.workflow.v12_store import V12Store, migrate_v12
from src.workflow.v13_integration import V13HoldStore


def verify_prepared_configuration(backend):
    """Require the prepared ledger, sheet and runtime configuration to match."""
    prepared = backend._mail_research_prepared
    if prepared is None:
        return
    current_cfg = json.loads(backend.production_path.read_text(encoding="utf-8"))
    current_rc = load_runtime_config(backend.config_path)
    if current_cfg != prepared[0] or current_rc != prepared[1]:
        raise ValueError("MAIL_RESEARCH_CONFIG_CHANGED_RESTART_REQUIRED")


def build_mail_research(backend):
    prepared = getattr(backend, "_mail_research_prepared", None)
    if prepared is None:
        backend._mail_prepare_phase = "CONFIG"
        cfg = json.loads(backend.production_path.read_text(encoding="utf-8"))
        rc = load_runtime_config(backend.config_path)
        path = resolve_app_path(cfg.get("sqlite_path", "runtime/production/workflow.sqlite3"), root=backend.root)
        # Linearize exit intent and admission to DB preparation. A phase
        # already admitted before exit may still finish its transactions.
        with backend._mail_phase_lock:
            if backend._closing_intent.is_set():
                raise RuntimeError("MAIL_RESEARCH_EXIT_REQUESTED")
            backend._mail_prepare_phase = "MUTATING"
        workflow = WorkflowStateStore(path)  # Preserve original V1.1 baseline initialization.
        # Only the initial quiescent entry may migrate or recover claims.
        migrate_v12(path, path.parent / "backups" / "v12-upgrade", quiesce=nullcontext)
        V13HoldStore(path).migrate()
        store = MailResearchStore(path)
        store.migrate()
        outbox = V12Store(path)
        outbox.recover_abandoned_notification_attempts(at=datetime.now(UTC), scope="mail")
        # Publish only after every migration and abandoned-claim recovery succeeds.
        # Later composition retries reuse these exact owners and never reset claims.
        backend._mail_research_prepared = (cfg, rc, workflow, store, outbox)
        backend._mail_prepare_phase = "PREPARED"
    else:
        cfg, rc, workflow, store, outbox = prepared
        # Never silently bind a prepared ledger to changed sheet/account/browser
        # configuration; completing that change requires a fresh process start.
        verify_prepared_configuration(backend)
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
    def refresh_catalog(job):
        from src.sheets.google_reader import GoogleSheetsRowReader
        from src.sheets.tp_brief import BriefReader

        from .google_web import build_google_web_service
        catalog = InquiryCatalog()
        worksheets = tuple(WorksheetIdentity(cfg["spreadsheet_id"], title) for title in cfg["worksheet_titles"])
        brief_source = WorksheetIdentity(cfg["spreadsheet_id"], "RFQ_BRIEF")
        catalog.configure_sources((*worksheets, brief_source))
        with budget.background() as checkpoint, DetailedReadSession(rc, admission) as session:
            deadline = service.timer()+120
            def guard():
                admission.require_open()
                checkpoint()
                if service.timer() > deadline:
                    raise TimeoutError("ORDER_SOURCE_READ_BUDGET_EXHAUSTED")
            web = build_google_web_service(rc.cdp.cdp_url, provider=session.shared_provider,
                read_guard=guard, stop_requested=service.stop_event.is_set, isolated_read=True,
                page_admission=admission)
            def retry_wait(seconds):
                guard()
                stopped = service.stop_event.wait(seconds)
                guard()
                return stopped
            brief_started = service.clock()
            brief = BriefReader(web, retry_wait=retry_wait).read(cfg["spreadsheet_id"])
            catalog.observe(brief_source, (), observed_at=brief_started)
            items = workflow.all_items()
            reader = GoogleSheetsRowReader(web, retry_wait=retry_wait)
            for worksheet in worksheets:
                guard()
                started = service.clock()
                rows = reader.read_rows(worksheet)
                guard()
                backend._catalog_source(worksheet, rows, items, observed_at=started,
                                        catalog=catalog, brief_lines=brief)
            guard()
        return catalog

    worker = V12NotificationWorker(outbox, QQSMTPTransport(config=QQSMTPConfig(sender_address="1069599116@qq.com")), scope="mail",
        review_current=lambda command, now: service.review_mail(command, now),
        prepare_content=lambda command, now: service.prepare_mail(command, now))
    service = MailResearchService(store=store, inbox_factory=ResearchInbox, source_reader=read,
        fx_provider=EcbDailyUsdRmbProvider(), catalog=backend._research_catalog,
        outbox=outbox, worker=worker,
        refresh_catalog=refresh_catalog,
        review_business_job=lambda job, payload, now: review_business_job(backend, job, payload, now),
        recover_business=lambda now: recover_business_reports_and_supplements(backend, now),
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
    return replace(command, text_body=command.text_body+"\n\n"+report["text"], html_body=body, delivery_content_kind="detailed", delivery_report_completed_at=report["completed_at"], delivery_report_reference_at=report["reference_at"], delivery_source_observed_at=report["source_observed_at"])


# Existing120s mail poll budget, measured from the original durable notice.
# No sleep/timer, schema, or retry/restart reset; final business review still gates SMTP.
BUSINESS_REPORT_WAIT = timedelta(seconds=120)


def _business_report_unavailable(command, order, *, follow_up, snapshot=None):
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
    if snapshot is not None:
        from decimal import Decimal

        from src.workflow.v12_notifications import business_snapshot_time
        lines += ["已记录的分流参考（非当前市场报价或采购成交价）：",
                  business_snapshot_time(snapshot),
                  "参考价格来源："+("、".join(snapshot.get("price_sources", [])) or "原调研记录，来源标记未核实"),
                  "当时市场参考单价："+(f"{Decimal(snapshot['reference_unit_rmb']):,.2f} 元" if snapshot.get("reference_unit_rmb") is not None else "未记录"),
                  f"当时预估询价总价：{Decimal(snapshot['estimated_total_rmb']):,.2f} 元",
                  "详细市场报价暂不可用／未核实。以上仅为已记录的分流参考；当前价格与库存尚未核实。"]
    else:
        lines += ["详细市场报价暂不可用／未核实。价格与库存尚未核实，本通知不含市场数据或估算金额。"]
    text = "\n".join(lines)
    return replace(command, text_body=text, html_body="<html><body><pre>"+html.escape(text)+"</pre></body></html>", delivery_content_kind="basic")


def prepare_business_report(backend, command, now):
    import json

    from src.research.detailed import DetailedOrder
    from src.sheets.worksheet_schema import worksheet_schema
    from src.workflow.v12_contracts import NotificationKind
    proof = json.loads(command.review or "{}")
    if proof.get("business_supplement"):
        reason, report = review_business_supplement(backend, command, now)
        return append_report(command, report) if reason is None else None
    if command.kind is not NotificationKind.IMPORTANT_ORDER and proof.get("reason_code") != "PURCHASE_FOLLOW_UP_REQUIRED":
        return command
    current = backend._current_mail_source(command.inquiry_id, now, manual=proof.get("manual") is True)
    if current is None:
        return None
    item, row, observed_at, date_origin, day = current
    from src.workflow.v12_notifications import verified_business_snapshot
    snapshot = verified_business_snapshot(command, item, row)
    if proof.get("correction_of") and snapshot is None:
        return None
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
                          date_source=("本地订单日期（近似）" if date_origin == "LOCAL_INTAKE_APPROXIMATION" else
                                     "原表日期（非客户发信时间）" if date_origin == "SOURCE_ORDER_DATE" else None))
    expired = now-command.created_at >= BUSINESS_REPORT_WAIT
    service = backend._mail_research_service
    try:
        if service is not None:
            cached = service.cached_report(order, now)
            if cached is not None and cached.get("usable") is True:
                return append_report(command, {**cached, "source_observed_at": observed_at.isoformat()})
            job = service.store.get(command.command_id)
            if job is not None and job["state"] == "READY":
                from dataclasses import asdict
                if job["origin"] != "business" or json.loads(job["payload"]) != asdict(order):
                    raise ValueError("BUSINESS_REPORT_ORDER_UNCONFIRMED")
                report = json.loads(job["report"])
                if report.get("usable") is True and all(timedelta(0) <= now-datetime.fromisoformat(report[key]) <= timedelta(minutes=15) for key in ("completed_at", "reference_at")):
                    return append_report(command, {**report, "source_observed_at": observed_at.isoformat()})
                if not expired:
                    service.store.refresh_business(command.command_id)
                    service.wake.set()
            elif job is None:
                service.store.request_business(command, order, now)
                service.wake.set()
    except Exception as error:  # noqa: BLE001 - optional enrichment never disables verified business notices
        logging.getLogger(__name__).warning("Business mail detailed report unavailable; class=%s", type(error).__name__)
    if not expired:
        return None
    return _business_report_unavailable(command, order,
        follow_up=proof.get("reason_code") == "PURCHASE_FOLLOW_UP_REQUIRED", snapshot=snapshot)


def _supplement_id(original_id, recipient):
    from hashlib import sha256
    identity = json.dumps([original_id, recipient.recipient_id, recipient.address],
                          ensure_ascii=False, separators=(",", ":"))
    return "business-supplement:" + sha256(identity.encode("utf-8")).hexdigest()


def review_business_supplement(backend, command, now):
    """Re-prove original delivery, live business eligibility and a fresh bound report."""
    from dataclasses import asdict

    from src.research.detailed import DetailedOrder
    from src.sheets.worksheet_schema import worksheet_schema
    from src.workflow.v12_contracts import NotificationKind

    try:
        proof = json.loads(command.review or "{}")
        metadata = proof["business_supplement"]
        if not isinstance(metadata, dict) or len(command.recipients) != 1:
            return "SUPPLEMENT_IDENTITY_UNVERIFIED", None
        recipient = command.recipients[0]
        original_id = metadata["original"]
        original = backend._v12_store.notification_command(original_id)
        if (command.command_id != _supplement_id(original_id, recipient)
                or original.inquiry_id != command.inquiry_id or original.kind != command.kind
                or recipient not in original.recipients
                or not backend._v12_store.notification_received_basic(original_id, recipient.recipient_id, recipient.address)):
            return "SUPPLEMENT_IDENTITY_UNVERIFIED", None
        original_proof = json.loads(original.review or "{}")
        if (original.kind is not NotificationKind.IMPORTANT_ORDER
                and (original.kind is not NotificationKind.PURCHASE_EXCEPTION
                     or original_proof.get("reason_code") != "PURCHASE_FOLLOW_UP_REQUIRED")):
            return "SUPPLEMENT_IDENTITY_UNVERIFIED", None
        original_one = replace(original, recipients=(recipient,))
        reason = backend._review_current_mail(original_one, now)
        if reason is not None:
            return reason, None
        current = backend._current_mail_source(original.inquiry_id, now, manual=original_proof.get("manual") is True)
        if current is None:
            return "CURRENT_REVIEW_PENDING", None
        item, row, observed_at, date_origin, day = current
        if original.kind is NotificationKind.IMPORTANT_ORDER:
            from src.workflow.v12_notifications import verified_business_snapshot
            if verified_business_snapshot(original, item, row) is None:
                return "BUSINESS_TRIGGER_CHANGED", None
        schema = worksheet_schema(item.record_identity.worksheet.worksheet)
        quantity = quantity_value(item.quantity)
        if quantity <= 0:
            return "SUPPLEMENT_IDENTITY_UNVERIFIED", None
        customer = schema.fixed_customer_name or row.cells.get(schema.customer_name_column) if schema.customer_name_column else schema.fixed_customer_name
        order = DetailedOrder(item.mpn, item.resolved_brand or item.brand or None, quantity,
            customer, str(day), item.record_identity.worksheet.worksheet, row.row_position,
            spreadsheet=item.record_identity.worksheet.spreadsheet,
            date_source=("本地订单日期（近似）" if date_origin == "LOCAL_INTAKE_APPROXIMATION" else
                         "原表日期（非客户发信时间）" if date_origin == "SOURCE_ORDER_DATE" else None))
        service = backend._mail_research_service
        job = service.store.get(original_id) if service is not None else None
        if (job is None or job["origin"] != "business" or job["state"] != "READY"
                or json.loads(job["payload"]) != asdict(order)):
            return "CURRENT_REVIEW_PENDING", None
        report = json.loads(job["report"])
        if (report.get("usable") is not True or not isinstance(report.get("text"), str)
                or not isinstance(report.get("html"), str)
                or not all(timedelta(0) <= now-datetime.fromisoformat(report[key]) <= timedelta(minutes=15) for key in ("completed_at", "reference_at"))):
            return "CURRENT_REVIEW_PENDING", None
        return None, {**report, "source_observed_at": observed_at.isoformat()}
    except (ValueError, TypeError, KeyError, AttributeError, OverflowError):
        return "CURRENT_REVIEW_PENDING", None


def queue_ready_business_supplements(backend, now):
    """Recover READY-to-outbox gaps through the original recipient-scoped queue."""
    from src.workflow.v12_contracts import NotificationCommand, NotificationRecipient
    service = backend._mail_research_service
    if service is None or backend._v12_store is None:
        return 0
    offset = getattr(backend, "_supplement_scan_offset", 0)
    if type(offset) is not int or offset < 0:
        offset = 0
    from time import monotonic
    deadline = monotonic() + 1.0
    with service.store.connect(timeout=0.1) as db:
        import sqlite3
        db.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, 1048576)
        db.set_progress_handler(lambda: int(monotonic() >= deadline), 1000)
        rows = db.execute("""SELECT DISTINCT c.command_id,r.recipient_id,r.address
            FROM workflow_mail_research m
            JOIN workflow_v12_notification_commands c ON c.command_id=m.task_id
            JOIN workflow_v12_notification_recipients r ON r.command_id=c.command_id
            JOIN workflow_v12_events e ON e.inquiry_id=c.inquiry_id AND e.attempt=r.attempt_count
            WHERE m.origin='business' AND m.state='READY' AND r.outcome='SENT'
              AND e.event_type='NOTIFICATION_DELIVERY_SUCCEEDED' AND e.source_module='notification'
              AND CASE WHEN json_valid(e.payload_json) THEN json_extract(e.payload_json,'$.notification_content.kind') END='basic'
              AND CASE WHEN json_valid(e.payload_json) THEN json_extract(e.payload_json,'$.notification_content.command_id') END=c.command_id
              AND CASE WHEN json_valid(m.report) THEN json_extract(m.report,'$.usable') END=1
              AND datetime(CASE WHEN json_valid(m.report) THEN json_extract(m.report,'$.completed_at') END)
                  BETWEEN datetime(?) AND datetime(?)
              AND datetime(CASE WHEN json_valid(m.report) THEN json_extract(m.report,'$.reference_at') END)
                  BETWEEN datetime(?) AND datetime(?)
              AND NOT EXISTS (
                  SELECT 1 FROM workflow_v12_notification_commands s
                  JOIN workflow_v12_notification_recipients sr ON sr.command_id=s.command_id
                  WHERE s.command_id LIKE 'business-supplement:%'
                    AND CASE WHEN json_valid(s.review_json) THEN json_extract(s.review_json,'$.business_supplement.original') END=c.command_id
                    AND sr.recipient_id=r.recipient_id AND sr.address=r.address)
            ORDER BY m.created_at DESC, c.command_id, r.recipient_id LIMIT 256 OFFSET ?""",
            ((now-timedelta(minutes=15)).isoformat(), now.isoformat(),
             (now-timedelta(minutes=15)).isoformat(), now.isoformat(), offset)).fetchall()
    queued = 0
    for index, row in enumerate(rows):
        if monotonic() >= deadline:
            break
        backend._supplement_scan_offset = offset + index + 1
        original_id, recipient_id, address = tuple(row)
        try:
            from src.workflow.v12_contracts import NotificationKind
            original = backend._v12_store.notification_command(original_id, timeout=0.1, deadline=deadline)
            recipient = NotificationRecipient(recipient_id, address)
            proof = json.loads(original.review or "{}")
            if (recipient not in original.recipients
                    or not backend._v12_store.notification_received_basic(original_id, recipient_id, address, timeout=0.1, deadline=deadline)
                    or (original.kind is NotificationKind.IMPORTANT_ORDER and not isinstance(proof.get("business_decision"), dict))
                    or (original.kind is not NotificationKind.IMPORTANT_ORDER
                        and (original.kind is not NotificationKind.PURCHASE_EXCEPTION
                             or proof.get("reason_code") != "PURCHASE_FOLLOW_UP_REQUIRED"))):
                continue
            proof["business_supplement"] = {"original": original_id}
            command = NotificationCommand(_supplement_id(original_id, recipient), original.inquiry_id,
                original.kind, (recipient,), "详细调研补充："+original.subject,
                "以下是原通知的详细市场调研补充。", None, now, review=json.dumps(proof, sort_keys=True))
            if backend._v12_store.notification_already_created(command.command_id, command.inquiry_id, command.kind, command.recipients, timeout=0.1, deadline=deadline):
                continue
            backend._v12_store.enqueue_notification(command, timeout=0.1, deadline=deadline, defer_stale_review=True)
            queued += 1
        except (ValueError, TypeError, KeyError, AttributeError):
            continue
        if queued >= 2:
            break
    else:
        if len(rows) < 256:
            backend._supplement_scan_offset = 0
    return queued


def _recovery_order(backend, original, recipient, now, deadline, *, allow_current_a=False):
    """Bounded, current-source admission before starting optional research."""
    from src.research.detailed import DetailedOrder
    from src.sheets.worksheet_schema import worksheet_schema
    from src.workflow.purchase_follow_up import purchase_episode_overdue
    from src.workflow.v12_contracts import NotificationKind
    from src.workflow.v12_notifications import (
        current_business_tier,
        verified_business_snapshot,
    )
    from src.workflow.v13_follow_up_store import V13PurchaseFollowUpStore

    proof = json.loads(original.review or "{}")
    allowed = {"linan229@qq.com", "shawn@inso-hk.com"}
    if backend._v12_adapters is not None:
        allowed.update(r.address.strip().casefold() for r in backend._v12_adapters.recipients)
    if recipient not in original.recipients or recipient.address.strip().casefold() not in allowed:
        return None
    current = backend._current_mail_source(original.inquiry_id, now,
        module="quotation", manual=proof.get("manual") is True, deadline=deadline)
    if current is None:
        return None
    item, row, _, date_origin, day = current
    schema = worksheet_schema(item.record_identity.worksheet.worksheet)
    status = row.cells.get(schema.status_column)
    if original.kind is NotificationKind.IMPORTANT_ORDER:
        if status not in {"未发", "发给采购", "采购已报价"}:
            return None
        if (verified_business_snapshot(original, item, row) is None
                and not (allow_current_a and "business_decision" not in proof
                         and current_business_tier(item, row) == "A")):
            return None
    elif (original.kind is NotificationKind.PURCHASE_EXCEPTION
          and proof.get("reason_code") == "PURCHASE_FOLLOW_UP_REQUIRED"):
        if status != "发给采购":
            return None
        episode = V13PurchaseFollowUpStore(backend._v12_store.database_path).latest(
            original.inquiry_id, timeout=0.1, deadline=deadline)
        if episode is None or episode.episode_id != proof.get("original_event") or not purchase_episode_overdue(episode, now):
            return None
    else:
        return None
    quantity = quantity_value(item.quantity)
    if quantity <= 0:
        return None
    customer = schema.fixed_customer_name or row.cells.get(schema.customer_name_column) if schema.customer_name_column else schema.fixed_customer_name
    return DetailedOrder(item.mpn, item.resolved_brand or item.brand or None, quantity,
        customer, str(day), item.record_identity.worksheet.worksheet, row.row_position,
        spreadsheet=item.record_identity.worksheet.spreadsheet,
        date_source=("本地订单日期（近似）" if date_origin == "LOCAL_INTAKE_APPROXIMATION" else
                     "原表日期（非客户发信时间）" if date_origin == "SOURCE_ORDER_DATE" else None))



def review_business_job(backend, job, payload, now):
    """Revalidate the exact order before every optional external source read."""
    from dataclasses import asdict
    from time import monotonic

    if backend._closed or backend._owner_stop_requested or backend._v12_store is None:
        return False
    deadline = monotonic()+1.0
    try:
        original = backend._v12_store.notification_command(job["task_id"], timeout=0.1, deadline=deadline)
        if original is None:
            return False
        with backend._mail_research_service.store.connect(timeout=0.1) as db:
            recovered = db.execute("SELECT 1 FROM workflow_mail_research WHERE task_id=?", ("business-recovery:"+job["task_id"],)).fetchone()
        allow_current_a = recovered is None
        for recipient in original.recipients:
            order = _recovery_order(backend, original, recipient, now, deadline, allow_current_a=allow_current_a)
            if order is not None and asdict(order) == payload:
                return True
    except Exception:  # noqa: BLE001 - uncertain source cannot authorize an external read.
        return False
    return False


def recover_missing_business_reports(backend, now):
    """Recover missing/failed reports with original evidence and persistent backoff."""
    import sqlite3
    from time import monotonic

    from src.workflow.v12_contracts import NotificationRecipient

    service = backend._mail_research_service
    if (service is None or backend._v12_store is None or service._resource_blocked
            or not service.admit() or backend._closed or backend._owner_stop_requested):
        return 0
    deadline = monotonic()+1.0
    offset = getattr(backend, "_business_recovery_offset", 0)
    if type(offset) is not int or offset < 0:
        offset = 0
    with service.store.connect(timeout=0.1) as db:
        db.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, 1048576)
        db.set_progress_handler(lambda: int(monotonic() >= deadline), 1000)
        rows = db.execute("""SELECT DISTINCT c.command_id,r.recipient_id,r.address,m.state,m.report
            FROM workflow_v12_notification_commands c
            JOIN workflow_v12_notification_recipients r ON r.command_id=c.command_id
            JOIN workflow_v12_events e ON e.inquiry_id=c.inquiry_id AND e.attempt=r.attempt_count
            LEFT JOIN workflow_mail_research m ON m.task_id=c.command_id
            LEFT JOIN workflow_mail_research control ON control.task_id='business-recovery:'||c.command_id
            WHERE r.outcome='SENT' AND e.event_type='NOTIFICATION_DELIVERY_SUCCEEDED' AND e.source_module='notification'
              AND CASE WHEN json_valid(e.payload_json) THEN json_extract(e.payload_json,'$.notification_content.kind') END='basic'
              AND CASE WHEN json_valid(e.payload_json) THEN json_extract(e.payload_json,'$.notification_content.command_id') END=c.command_id
              AND (control.task_id IS NULL OR (control.state='RECOVERY_WAIT' AND control.attempts<3
                   AND (control.next_at IS NULL OR control.next_at<=?)))
              AND (m.task_id IS NULL OR (m.origin='business' AND
                   ((m.state='FAILED' AND (m.next_at IS NULL OR m.next_at<=?)) OR
                    (m.state='READY' AND (CASE WHEN json_valid(m.report) THEN json_extract(m.report,'$.usable') END IS NOT 1
                       OR datetime(CASE WHEN json_valid(m.report) THEN json_extract(m.report,'$.reference_at') END) IS NULL
                       OR datetime(CASE WHEN json_valid(m.report) THEN json_extract(m.report,'$.reference_at') END)<datetime(?))))))
              AND NOT EXISTS (
                  SELECT 1 FROM workflow_v12_notification_commands s
                  JOIN workflow_v12_notification_recipients sr ON sr.command_id=s.command_id
                  WHERE s.command_id LIKE 'business-supplement:%'
                    AND CASE WHEN json_valid(s.review_json) THEN json_extract(s.review_json,'$.business_supplement.original') END=c.command_id
                    AND sr.recipient_id=r.recipient_id AND sr.address=r.address)
            ORDER BY c.created_at DESC,c.command_id,r.recipient_id LIMIT 128 OFFSET ?""",
            (now.isoformat(), now.isoformat(), (now-timedelta(minutes=15)).isoformat(), offset)).fetchall()
    recovered = 0
    for index, row in enumerate(rows):
        if monotonic() >= deadline:
            break
        backend._business_recovery_offset = offset+index+1
        original_id, recipient_id, address, state, report = tuple(row)
        try:
            original = backend._v12_store.notification_command(original_id, timeout=0.1, deadline=deadline)
            recipient = NotificationRecipient(recipient_id, address)
            if not backend._v12_store.notification_received_basic(original_id, recipient_id, address, timeout=0.1, deadline=deadline):
                continue
            order = _recovery_order(backend, original, recipient, now, deadline)
            if order is None:
                service.store.defer_business_recovery(original_id, now, deadline=deadline)
                continue
            if service.store.schedule_business_recovery(original, recipient, order, now,
                    deadline=deadline, expected_state=state, expected_report=report):
                service.wake.set()
                recovered += 1
                break
        except (ValueError, TypeError, KeyError, AttributeError):
            continue
    else:
        if len(rows) < 128:
            backend._business_recovery_offset = 0
    return recovered


def recover_business_reports_and_supplements(backend, now):
    # Recovery here only targets already-sent basic notices. With supplemental
    # emails disabled, those jobs cannot enrich an unsent original notice.
    # Ordinary pending notices still request their own research in preparation.
    return None
