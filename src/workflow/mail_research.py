"""Two bounded process-lifetime workers; existing outbox owns ALL SMTP effects."""
import json
import logging
import threading
from collections import OrderedDict
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from time import monotonic
from types import SimpleNamespace

from src.core import CredentialError
from src.core.mpn import normalize_lookup_mpn
from src.order_mail.research_requests import ACCOUNT
from src.research.detailed import (
    DetailedOrder,
    TpFx,
    TpSourceResult,
    dump_source,
    finish_tp,
    load_source,
)
from src.research.report import render_market_report
from src.research.source_contracts import PRICE_SOURCES, SourceEvidence, SourceOutcome

from .v12_contracts import NotificationCommand, NotificationKind, NotificationRecipient

LOG = logging.getLogger("inso.mail_research")


class InquiryCatalog:
    """Immutable facts copied by the original source owner; never another reader."""
    def __init__(self):
        self.lock, self.sources = threading.Lock(), {}

    def observe(self, source, entries):
        with self.lock:
            self.sources[source] = tuple(entries)

    def match(self, mpn, *, now=None):
        with self.lock:
            matches = [(key, order, stamp) for entries in self.sources.values() for key, order, stamp in entries
                       if normalize_lookup_mpn(order.mpn) == normalize_lookup_mpn(mpn)]
        if not matches or any(stamp is None or stamp.tzinfo is None or (now is not None and stamp > now) for _, _, stamp in matches):
            return None
        latest = max(stamp for _, _, stamp in matches)
        recent = [(key, order) for key, order, stamp in matches if stamp == latest]
        unique = {(key, order) for key, order in recent}
        return next(iter(unique))[1] if len(unique) == 1 else None


class MailResearchService:
    def __init__(self, *, store, inbox_factory, source_reader, fx_provider, catalog,
                 outbox, worker, clock=lambda: datetime.now(UTC), timer=monotonic,
                 admit=lambda: True):
        self.store, self.inbox_factory, self.source_reader = store, inbox_factory, source_reader
        self.fx_provider, self.catalog, self.outbox, self.worker = fx_provider, catalog, outbox, worker
        self.clock, self.timer, self.admit = clock, timer, admit
        self.stop_event, self.wake = threading.Event(), threading.Event()
        self.threads, self.next_poll, self.health = [], 0.0, "INITIALIZING"
        self._failures = 0
        self._auth_failures = 0
        self._resource_blocked = self.store.resource_blocked()
        self._report_lock, self._report_cache = threading.Lock(), OrderedDict()

    @staticmethod
    def _report_key(order):
        return (getattr(order, "spreadsheet", None), normalize_lookup_mpn(order.mpn), order.brand, order.quantity,
                order.customer, str(order.rfq_date).split("T")[0].split(" ")[0], order.sheet, order.row)

    def remember_report(self, order, result, now):
        if not any(s.outcome is not SourceOutcome.SOURCE_UNAVAILABLE for s in result.sources):
            return
        text, html = render_market_report(order, result, target=False)
        report = {"text": text, "html": html, "completed_at": now.isoformat()}
        self.remember_rendered(order, report)

    def remember_rendered(self, order, report):
        key = self._report_key(order)
        with self._report_lock:
            self._report_cache[key] = report
            self._report_cache.move_to_end(key)
            while len(self._report_cache) > 64:
                self._report_cache.popitem(last=False)

    def cached_report(self, order, now):
        with self._report_lock:
            report = self._report_cache.get(self._report_key(order))
        if report and timedelta(0) <= now-datetime.fromisoformat(report["completed_at"]) <= timedelta(minutes=15):
            return dict(report)
        return None

    def poll_once(self):
        now = self.clock()
        try:
            with self.inbox_factory() as inbox:
                cursor = self.store.cursor(ACCOUNT)
                if cursor is None or cursor[0] != inbox.validity:
                    count = self.store.accept_scan(ACCOUNT, inbox.validity, inbox.latest, (), now)
                else:
                    upper, messages = inbox.read(cursor[1])
                    count = self.store.accept_scan(ACCOUNT, inbox.validity, upper, messages, now)
            self.health, self._failures, self._auth_failures = "READY", 0, 0
            self.outbox.resolve_incidents("mail_research", at=now, reason_code="IMAP_AUTH_REQUIRED")
            LOG.info("IMAP check complete; accepted=%s", count)
            if cursor is not None and cursor[0] == inbox.validity and inbox.latest > cursor[1] and self.store.cursor(ACCOUNT) == cursor:
                self.health = "QUEUE_FULL"
                LOG.warning("Research queue full; mailbox UID cursor retained; no request discarded")
            if count:
                self.wake.set()
        except CredentialError:
            self.health = "CREDENTIAL_REQUIRED"
            LOG.warning("229 mailbox needs IMAP authorization in existing Vault (imap.qq.com)")
        except Exception as error:  # noqa: BLE001 - isolated service boundary; sanitized class only
            self._failures += 1
            self.health = "WAITING_RECOVERY"
            LOG.warning("IMAP check deferred; class=%s", type(error).__name__)
            # Native authentication rejection only; no network timeout escalation.
            from src.order_mail.research_requests import ImapAuthenticationRequired
            self._auth_failures = self._auth_failures+1 if isinstance(error, ImapAuthenticationRequired) else 0
            if isinstance(error, ImapAuthenticationRequired):
                self.raise_alert("IMAP_AUTH_REQUIRED", "imap-auth", now)

    def tick(self):
        if self.timer() >= self.next_poll:
            self.next_poll = self.timer() + 120
            self.poll_once()

    def _receive(self):
        while not self.stop_event.is_set():
            self.tick()
            self.stop_event.wait(max(.05, min(1, self.next_poll - self.timer())))

    def run_one(self):
        if self.stop_event.is_set() or self._resource_blocked or not self.admit():
            return False
        now = self.clock()
        job = self.store.claim(now)
        if job is None:
            return False
        key = job["task_id"]
        try:
            progress = json.loads(job["progress"])
            payload = json.loads(job["payload"])
            if progress.get("reference_at"):
                age = now-datetime.fromisoformat(progress["reference_at"])
                if not timedelta(0) <= age <= timedelta(minutes=15):
                    progress = {}  # Stale current-price/FX facts must be reacquired, read-only.
            if "order" in progress:
                order = DetailedOrder(**progress["order"])
            else:
                order = (self.catalog.match(payload["mpn"], now=now) or DetailedOrder(payload["mpn"])) if job["origin"] == "imap" else DetailedOrder(**payload)
                progress["order"] = asdict(order)
                progress["reference_at"] = now.isoformat()
                self.store.checkpoint(key, progress)
            reference = datetime.fromisoformat(progress["reference_at"])
            fx = TpFx(self.fx_provider, reference)
            if progress.get("fx_rate"):
                from decimal import Decimal

                from src.research.fx import UsdRmbQuote
                fx.quote = UsdRmbQuote(Decimal(progress["fx_rate"]), reference, "saved task FX")
                fx.hkd = Decimal(progress["hkd"]) if progress.get("hkd") else None
            for source in PRICE_SOURCES:
                if source.value in progress:
                    continue
                if self.stop_event.is_set() or not self.admit():
                    self.store.finish(key, state="PENDING")
                    return False
                try:
                    result, stock = self.source_reader(key, source, order, reference, fx)
                except Exception as error:
                    # Uncertain resource ownership must never be turned into a successful report.
                    from src.research.cdp_pages import PageTargetCleanupError
                    if type(error).__name__ == "ResearchDeferred" or isinstance(error, PageTargetCleanupError):
                        raise
                    result = TpSourceResult(source, SourceOutcome.SOURCE_UNAVAILABLE,
                        SourceEvidence(source, order.mpn, None, SourceOutcome.SOURCE_UNAVAILABLE, reference))
                    stock = None
                    LOG.warning("Read-only research source unavailable; source=%s class=%s", source.value, type(error).__name__)
                progress[source.value] = dump_source(result)
                if stock:
                    progress["stock"] = stock
                if fx.quote:
                    progress["fx_rate"] = str(fx.quote.rate)
                if fx.hkd:
                    progress["hkd"] = str(fx.hkd)
                self.store.checkpoint(key, progress)
            results = tuple(load_source(progress[source.value], order.mpn) for source in PRICE_SOURCES)
            result = finish_tp(order, SimpleNamespace(stock_label=progress.get("stock", "待验证")), results, target_rmb=None, fx=fx)
            all_unavailable = not any(s.outcome is not SourceOutcome.SOURCE_UNAVAILABLE for s in results)
            if all_unavailable and (job["origin"] == "imap" or job["attempts"] < 2):
                # Retry failed reads with bounded attempts; never call an empty outage success.
                progress = {k: v for k, v in progress.items() if k not in {s.value for s in PRICE_SOURCES}}
                self.store.checkpoint(key, progress)
                raise ValueError("ALL_SOURCES_UNAVAILABLE")
            context = (("邮件指令调研", "请求型号：" + payload["mpn"], "来源邮件时间：" + (payload.get("sent_at") or "未核实"),
                        "匹配情况：" + ("唯一最近询价" if order.rfq_date else "未可靠匹配询价；仅市场单价"))
                       if job["origin"] == "imap" else ())
            if all_unavailable:
                context = (*context, "六来源详细调研暂未完成；未取得有效报价不代表市场无报价。")
                LOG.warning("Detailed research unavailable; original business notice retained; task=%s", key[-12:])
            text, html = render_market_report(order, result, target=False, context=context)
            report = {"text": text, "html": html, "completed_at": self.clock().isoformat()}
            if job["origin"] == "business" and not all_unavailable:
                self.remember_rendered(order, report)
            self.store.finish(key, state="READY", report=report)
            if job["origin"] == "imap":
                self.enqueue_report(key, report, now)
            LOG.info("Detailed research ready; origin=%s task=%s", job["origin"], key[-12:])
        except Exception as error:  # noqa: BLE001 - isolated service boundary; sanitized class only
            if type(error).__name__ == "ResearchDeferred":
                self.store.finish(key, state="PENDING")
                return False
            from src.research.cdp_pages import PageTargetCleanupError
            if isinstance(error, PageTargetCleanupError):
                self._resource_blocked = True
                self.store.block_resource(now)
                self.raise_alert("CDP_RESOURCE_UNCONFIRMED", "owned-read-resource", now)
            attempts = job["attempts"] + 1
            self.store.finish(key, state="BLOCKED" if self._resource_blocked else "PENDING" if attempts < 3 else "FAILED",
                failure=type(error).__name__, next_at=now+timedelta(seconds=120))
            LOG.warning("Detailed research deferred; task=%s attempt=%s class=%s", key[-12:], attempts, type(error).__name__)
        return True

    def enqueue_report(self, key, report, now):
        self.outbox.enqueue_notification(NotificationCommand(key, None, NotificationKind.TP_RESEARCH,
            (NotificationRecipient("ops", "shawn@inso-hk.com"),), "【INSO】邮件指令调研",
            report["text"], report["html"], now))

    def raise_alert(self, code, event, now):
        actions = {"IMAP_AUTH_REQUIRED": "请检查229邮箱IMAP授权；不要重发业务订单。",
                   "REPORT_DELIVERY_UNKNOWN": "请人工核对Shawn是否收到调研报告；程序不会盲目重发。",
                   "CDP_RESOURCE_UNCONFIRMED": "请检查邮件调研专属页面状态；不要重启或关闭主业务Chrome。"}
        incident_key = "mail-research:"+code+":"+("report-delivery" if code == "REPORT_DELIVERY_UNKNOWN" else event)
        previous = self.outbox.active_incident_evidence(incident_key)
        if previous and code == "REPORT_DELIVERY_UNKNOWN":
            event = previous["original_event"]  # One unresolved delivery incident, not one alert per queued report.
        proof = {"incident_key": incident_key, "module": "mail_research", "account": ACCOUNT,
                 "category": "service_stop", "reason_code": code, "original_event": event,
                 "active": True, "current_business": True, "needs_owner": True, "verified": True,
                 "verified_at": now.isoformat(), "action": actions[code],
                 "uncertainty": "已确认独立邮件调研存在上述问题；主业务状态尚未据此核实。"}
        command = NotificationCommand("review-pending", None, NotificationKind.PURCHASE_EXCEPTION,
            (NotificationRecipient("owner", "linan229@qq.com"),), "【需要处理】邮件调研待人工核对",
            actions[code]+"\n"+proof["uncertainty"], None, now)
        return self.outbox.observe_incident(command, proof, occurrence=str(self._failures) if code == "IMAP_AUTH_REQUIRED" else now.isoformat())

    def review_mail(self, command, now):
        if command.kind is NotificationKind.PURCHASE_EXCEPTION:
            proof = json.loads(command.review or "{}")
            if proof.get("module") != "mail_research" or any(r.address != "linan229@qq.com" for r in command.recipients):
                return "RECIPIENT_NOT_CONFIGURED"
            code = proof.get("reason_code")
            if code == "IMAP_AUTH_REQUIRED":
                return None if self.health == "WAITING_RECOVERY" and self._auth_failures >= 3 else "EVENT_RECOVERED"
            if code == "REPORT_DELIVERY_UNKNOWN":
                with self.store.connect() as db:
                    unknown = db.execute("SELECT 1 FROM workflow_v12_notification_recipients WHERE command_id=? AND outcome='UNKNOWN'", (proof["original_event"],)).fetchone()
                return None if unknown else "EVENT_RECOVERED"
            if code == "CDP_RESOURCE_UNCONFIRMED":
                return None if self._resource_blocked else "EVENT_RECOVERED"
            return "CURRENT_REVIEW_PENDING"
        job = self.store.get(command.command_id)
        if job is None or job["origin"] != "imap" or job["state"] != "READY":
            return "EVENT_NOT_CURRENT"
        if command.kind is not NotificationKind.TP_RESEARCH or command.inquiry_id is not None or any(
                r.address != "shawn@inso-hk.com" for r in command.recipients):
            return "RECIPIENT_NOT_CONFIGURED"
        return None

    def audit_delivery(self):
        """Bounded local delivery facts and incident repair, never another sender."""
        with self.store.connect() as db:
            rows = db.execute("""SELECT m.task_id,m.progress,r.outcome FROM workflow_mail_research m
                JOIN workflow_v12_notification_recipients r ON r.command_id=m.task_id
                WHERE m.origin='imap' AND m.state='READY' AND (json_extract(m.progress,'$.delivery_logged') IS NULL
                    OR json_extract(m.progress,'$.delivery_logged')!=r.outcome)
                ORDER BY m.created_at LIMIT 16""").fetchall()
        for row in rows:
            progress = json.loads(row[1])
            if row[2] == "UNKNOWN" and not progress.get("unknown_alerted"):
                progress["unknown_alerted"] = self.raise_alert("REPORT_DELIVERY_UNKNOWN", row[0], self.clock())
            LOG.info("Report delivery state; task=%s outcome=%s", row[0][-12:], row[2])
            progress["delivery_logged"] = row[2]
            self.store.checkpoint(row[0], progress)
            self.store.close_delivery(row[0], row[2])

    def _work(self):
        while not self.stop_event.is_set():
            try:
                # Recover a crash between result persistence and outbox enqueue.
                with self.store.connect() as db:
                    rows = db.execute("SELECT task_id,report FROM workflow_mail_research WHERE origin='imap' AND state='READY' AND task_id NOT IN (SELECT command_id FROM workflow_v12_notification_commands) LIMIT 16").fetchall()
                for row in rows:
                    if not self.outbox.notification_already_created(row[0], None, NotificationKind.TP_RESEARCH,
                            (NotificationRecipient("ops", "shawn@inso-hk.com"),)):
                        self.enqueue_report(row[0], json.loads(row[1]), self.clock())
                self.run_one()
                self.worker.run_due(now=self.clock())
                self.audit_delivery()
            except Exception as error:  # noqa: BLE001 - isolated service boundary; sanitized class only
                LOG.warning("Independent research protected wait; class=%s", type(error).__name__)
            self.wake.wait(1)
            self.wake.clear()

    def start(self):
        if self.threads:
            return
        self.threads = [threading.Thread(target=fn, name=name) for fn, name in
                        ((self._receive, "mail-research-imap"), (self._work, "mail-research-worker"))]
        for thread in self.threads:
            thread.start()

    def close(self):
        self.stop_event.set()
        self.wake.set()
        for thread in self.threads:
            if thread is not threading.current_thread():
                thread.join()  # Network adapters have bounded timeouts; release only on owner thread.
