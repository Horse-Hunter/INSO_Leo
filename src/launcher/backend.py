"""Production GUI adapter over the canonical Workflow and Research runtimes."""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import subprocess
import sys
import threading
import uuid
from contextlib import nullcontext
from dataclasses import replace
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from time import monotonic

from src.core.app_paths import app_root, resolve_app_path, runtime_config_path
from src.gui.contracts import (
    DiagnosticSnapshot,
    GuiBackend,
    HealthItem,
    HealthReport,
    LogEntry,
    ManualOrderResult,
    Order,
    OrderStatus,
    RunSession,
    RunState,
    SiteLoginOutcome,
    SiteLoginReport,
    SiteLoginResult,
    SourceDetail,
)
from src.gui.state import utc_now
from src.inso.duplicate_history import InsoDuplicateHistoryReader
from src.inso.purchase_writer import InsoPurchaseWriter, PlaywrightParentProductFields
from src.inso.write_safety import OwnerAuthorizedSaveAndSendGate
from src.launcher.purchase_completion import PurchaseCompletionActions
from src.research import ResearchInput, ResearchResult
from src.research.cdp_pages import new_background_page
from src.research.credentials import CoreLoginBridge
from src.research.ecb_fx import EcbDailyUsdRmbProvider
from src.research.excel_output import ResearchExcelOutput
from src.research.inso_history import INSO_SITE_ID
from src.research.runtime import (
    ResearchRuntimeConfigError,
    assess_readiness,
    build_research_service,
    load_runtime_config,
    probe_loopback_endpoint,
)
from src.research.source_contracts import ResearchSource, SourceOutcome
from src.sheets import WorksheetIdentity
from src.sheets.google_oauth import (
    build_read_only_google_sheets_service,
    build_read_write_google_sheets_service,
)
from src.sheets.google_reader import GoogleSheetsRowReader
from src.sheets.google_writer import GoogleSheetsPurchaseStatusWriter
from src.workflow import (
    ResearchPreparationError,
    WorkflowPoller,
    WorkflowRuntime,
    WorkflowStateStore,
    WorkflowStatus,
    WorkflowWorker,
)
from src.workflow.dashboard_counts import read_dashboard_counts
from src.workflow.inso_query import run_inso_query
from src.workflow.purchase_follow_up import PurchaseFollowUp
from src.workflow.v12_contracts import (
    DeliveryOutcome,
    EventType,
    NotificationCommand,
    NotificationKind,
    NotificationRecipient,
    PurchaseDraftResult,
    PurchaseOutcome,
    ReasonCode,
)
from src.workflow.v12_duplicate import InsoDuplicateHistoryChecker
from src.workflow.v12_faults import FaultScope, V12Fault
from src.workflow.v12_smtp_transport import QQSMTPConfig, QQSMTPTransport
from src.workflow.v12_store import (
    V12_SCHEMA_VERSION,
    V12DatabaseError,
    V12Store,
    migrate_v12,
)
from src.workflow.v13_follow_up_store import V13PurchaseFollowUpStore
from src.workflow.v13_integration import CombinedCycle, V13HoldStore, V13IntegratedCycle
from src.workflow.v13_quotation import V13QuotationCycle, V13Stopped

from .browser_bootstrap import (
    BrowserBootstrapError,
    BrowserHandle,
    acquire_cdp_browser,
    park_shared_cdp,
)
from .diagnostics import log_step
from .google_quote_update import build_v13_quotation_updater
from .inso_session import (
    InsoAuthenticationError,
    InsoResearchSession,
    InsoSessionGuard,
    InsoSessionOutcome,
    attach_inso_research_session,
)
from .manual_order import (
    CurrentQuotationStore,
    ManualRetryHolds,
    SingleRowReader,
    current_record,
    editable_value,
)
from .site_login_sweep import SiteSweepError, sweep_sites
from .v12_composition import (
    CoordinatorPurchaseDraftWriter,
    PlaywrightReadOnlySaveReconciler,
    ResearchExcelFactsProvider,
    SaveReconciliationTarget,
    V12ProductionAdapters,
    V12ProductionComposition,
    compose_v12_production,
)
from .v12_gui import read_startup_interruptions, read_v12_order_state
from .v13_integration import (
    notify_quotation,
    notify_quotation_model_difference,
    notify_runtime_fault,
    notify_website_issue,
    quotation_gui,
    quotation_location,
)
from .v13_quotation import V13QuotationOperations

log = logging.getLogger(__name__)

#: The one mailbox an operational login alert goes to. Owner rule
#: (2026-10-01): the alert is for the person who can log back in, and for nobody
#: else -- it must not be added to the order-notification recipient list.
_LOGIN_ALERT_SENDER = "1069599116@qq.com"
_LOGIN_ALERT_RECIPIENT = "linan229@qq.com"


class ProductionConfigurationError(RuntimeError):
    """Safe startup failure for missing local production configuration."""


def _login_alert_body(stop_reason: str) -> str:
    """The alert's plain text: what stopped, and what to do about it."""

    lines = [
        "INSO_V1.2 程序已停止：采集网站遇到登录或人工验证问题（不一定是 INSO 网站）。",
        "",
        "处理步骤：",
        "1. 打开本机的已授权 Chrome；",
        "2. 在对应网站完成登录（如出现验证码／滑块／短信验证，需要人工完成）；",
        "3. 回到 INSO_V1.2 面板，点击「开始询价」继续。",
        "",
        "也可以先点击面板上的「一键登录所有网站」，确认各站登录状态。",
    ]
    if stop_reason.strip():
        lines += ["", f"本轮各来源的说明：{stop_reason.strip()}"]
    return "\n".join(lines)


class _Observer:
    """Track actual Research attempts and surface interactive challenges."""

    #: Every wording a source uses when what failed is the *session*, not the
    #: result. Owner rule (2026-10-01): a login problem stops the run and mails
    #: the Owner, because a run that carries on without one of its sites quietly
    #: produces a price pool that is missing a source. These are exactly the
    #: phrases ``research.aggregation._failure_reason`` renders, plus the English
    #: challenge words, and nothing else -- a parse failure must not stop a run.
    _HUMAN_ACTION_MARKERS = (
        "需要人工验证",
        "账号或密码被站点拒绝",
        "没有可用的登录凭据",
        "站点登录表单已变化",
        "登录前选项未能勾选",
        "登录不可用",
        "captcha",
        "otp",
        "设备验证",
    )

    def __init__(self, service, seen, manual_review, prepare=None):
        self.service = service
        self.seen = seen
        self.manual_review = manual_review
        self.prepare = prepare

    def execute(self, item: ResearchInput) -> ResearchResult:
        self.seen(item.inquiry_id)
        if self.prepare is not None:
            try:
                self.prepare()
            except BrowserBootstrapError as exc:
                raise ResearchPreparationError(
                    "CDP browser requires manual handling"
                ) from exc
        result = self.service.execute(item)
        for detail in (result.remarks or "").split("；"):
            remarks = detail.casefold()
            if not any(marker in remarks for marker in self._HUMAN_ACTION_MARKERS):
                continue
            self.manual_review(item.inquiry_id, detail)
            # Do not let a partial result route into notification/purchase or
            # consume this inquiry. Existing queue release makes it resumable.
            if "ic.net" in remarks or "inso" in remarks or "英索" in remarks:
                raise V12Fault(FaultScope.GLOBAL_STOP if "inso" in remarks or "英索" in remarks
                    else FaultScope.V12_PAUSE, "Research requires session repair")
        return result


class _LivePurchaseDraftWriter:
    """Create only an unsaved V1.2 draft in the verified INSO session.

    Nothing here opens a browser page: the AI录单 panel and the 采购临时询价
    window are dialogs on the verified INSO home page. Owner rule (2026-09-30):
    every order must leave that home page entered through 业务询价 with nothing
    open, because the ERP otherwise carries the previous order's form into the
    next one -- which is how one order ended up selecting two purchasers.

    ``session_guard_factory`` is what keeps a dead login from being reported as
    a missing control. It is consulted before the ERP is touched, and again when
    the draft fails: only a session that is *proven* to have expired is worth
    retrying, because then the ERP provably never rendered the row and nothing
    can be duplicated. A healthy session leaves the failure exactly as it was,
    and a guard that cannot be prepared at all leaves the flow untouched.
    """

    def __init__(self, access, *, session_guard_factory=None, login_problem=None,
                 store: V12Store | None = None) -> None:
        self._access = access
        self._session_guard_factory = session_guard_factory
        self._login_problem = login_problem
        self._store = store

    def _guard(self):
        if self._session_guard_factory is None:
            return None
        try:
            return self._session_guard_factory()
        except Exception:
            # No guard is the pre-existing behaviour, so a launcher that cannot
            # build one must keep working exactly as it did before.
            log.warning("the INSO session guard could not be prepared", exc_info=True)
            return None

    def prepare(self, command):
        guard = self._guard()
        if guard is not None:
            # Owner rule (2026-10-01): every INSO entry opens the ERP again and
            # re-establishes the login, because the session does not survive
            # between workflow steps and no cheaper signal about it can be
            # trusted. Doing it here also means a login that is already gone is
            # never discovered halfway through building a draft.
            status = guard.ensure_authenticated(force_login=True)
            if status.outcome is InsoSessionOutcome.DEAD:
                return self._session_stale(command, status)
        result = self._prepare_once(command)
        if guard is None or result.outcome is not PurchaseOutcome.VALIDATION_FAILED:
            return result
        # A retry cannot duplicate anything: ``ai_appendRow`` is the ERP's own
        # client-side row hand-off, and a session that is *proven* gone means
        # that hand-off never ran. This call deliberately does not force a
        # login: it has to be able to answer "was it the session?" honestly, so
        # a healthy session must not be re-logged-in into looking recovered.
        status = guard.ensure_authenticated()
        if status.outcome is not InsoSessionOutcome.RESTORED:
            if status.outcome is InsoSessionOutcome.DEAD:
                return self._session_stale(command, status)
            return result
        log.warning("the INSO session had expired and was restored; retrying the draft")
        return self._prepare_once(command)

    def _session_stale(self, command, status):
        """Report an unrecoverable login loss as itself, not as a lost control."""

        log.warning(
            "the INSO session expired and could not be restored (%s)",
            status.reason_code,
        )
        if self._login_problem is not None:
            self._login_problem(command.inquiry_id, "INSO：登录不可用")
        return PurchaseDraftResult(
            command_id=command.command_id,
            outcome=PurchaseOutcome.VALIDATION_FAILED,
            completed_at=utc_now(),
            reason_code=ReasonCode.SESSION_STALE,
        )

    def _prepare_once(self, command):
        access = self._access()
        try:
            return self._prepare_on_page(command, access)
        finally:
            if self._store is not None and any(
                event.event_type is EventType.SAVE_DISPATCH_ARMED
                for event in self._store.event_history(command.inquiry_id)
            ):
                try:
                    access.close_owned_operation_tab()
                except (sqlite3.Error, V12DatabaseError):
                    raise
                except Exception as exc:  # noqa: BLE001 - cleanup must not replay a dispatched row
                    log_step("owned-tab-cleanup", cause=exc)

    def _prepare_on_page(self, command, access):
        with access.operation_page() as form:
            writer = InsoPurchaseWriter(
                form_page=form,
                gate=OwnerAuthorizedSaveAndSendGate() if self._store is not None else None,
            )
            # A crashed or interrupted run can skip the close below, so the
            # surface is also cleared here, before this order touches the form.
            if not writer.dismiss_order_surface():
                log.warning("an earlier order left the INSO 业务询价 surface open")
                # The same reason code the row read-back failures use, so the
                # step is what tells this apart from a draft that died later.
                log_step("dismiss-surface")
                return PurchaseDraftResult(
                    command_id=command.command_id,
                    outcome=PurchaseOutcome.VALIDATION_FAILED,
                    completed_at=utc_now(),
                    reason_code=ReasonCode.CONTROL_NOT_FOUND,
                )
            try:
                baseline = None
                if self._store is not None:
                    try:
                        baseline = PlaywrightReadOnlySaveReconciler.submission_baseline(
                            form.shell_frame, command.mpn,
                        )
                    except Exception as exc:  # noqa: BLE001 - incomplete baseline forbids submission
                        log_step("submission-baseline", cause=exc)
                        return PurchaseDraftResult(
                            command.command_id, PurchaseOutcome.VALIDATION_FAILED,
                            utc_now(), reason_code=ReasonCode.RECONCILIATION_UNREADABLE,
                        )
                result = CoordinatorPurchaseDraftWriter(
                    actions=writer,
                    parent_fields=PlaywrightParentProductFields(form),
                ).prepare(command)
                if self._store is not None and result.outcome is PurchaseOutcome.AI_RECOGNIZED:
                    result = self._submit_validated(command, result, writer, form, access, baseline)
                return result
            finally:
                try:
                    if not writer.dismiss_order_surface():
                        log_step("surface-left-open")
                except (sqlite3.Error, V12DatabaseError):
                    raise
                except Exception as exc:  # noqa: BLE001 - retain the durable submission result
                    log_step("surface-cleanup", cause=exc)

    def _submit_validated(self, command, result, writer, form, access, baseline):
        """Connect the existing draft, durable dispatch and read-only upper query."""
        self._store.set_purchase_state(
            command.inquiry_id, command.command_id, PurchaseOutcome.AI_RECOGNIZED,
            at=result.completed_at,
        )
        submitted_at = utc_now()
        try:
            writer.save_and_send(self._store, command.inquiry_id, at=submitted_at)
            form.page.wait_for_timeout(5000)
        except Exception as exc:
            log_step("save-and-send-unconfirmed", cause=exc)
            if isinstance(exc, (sqlite3.Error, V12DatabaseError)):
                raise
            if self._store.purchase_state(command.inquiry_id) is PurchaseOutcome.AI_RECOGNIZED:
                return replace(result, outcome=PurchaseOutcome.VALIDATION_FAILED,
                    reason_code=ReasonCode.CONTROL_NOT_FOUND, completed_at=utc_now())
        try:
            writer.dismiss_order_surface()
        except Exception:  # noqa: BLE001 - after dispatch, never repeat the click
            outcome = self._store.mark_submit_unconfirmed(command.inquiry_id, at=utc_now())
            return replace(result, outcome=outcome, completed_at=utc_now(),
                reason_code=ReasonCode.SAVE_OUTCOME_UNKNOWN)
        target = SaveReconciliationTarget(
            command.mpn, command.brand, command.quantity, submitted_at, baseline,
        )
        reconciler = PlaywrightReadOnlySaveReconciler(
            operation_access=access,
            target_for_inquiry=lambda inquiry_id: target if inquiry_id == command.inquiry_id else None,
        )
        outcome = self._store.reconcile_unknown_save(
            command.inquiry_id, reconciler, at=utc_now(),
        )
        return replace(
            result, outcome=outcome, completed_at=utc_now(),
            reason_code=None if outcome is PurchaseOutcome.SAVED else ReasonCode.SAVE_OUTCOME_UNKNOWN,
        )


class _PreparedDuplicateChecker:
    """Prepare the verified INSO session before the V1.2 duplicate lookup.

    Reuse the lower-history reader. Query failures get at most three fresh-tab
    retries after interruptible waits; authentication failures stop immediately.
    """

    def __init__(self, checker, prepare=None, *, begin_inquiry=None, reset=None, wait=None) -> None:
        self._checker = checker
        self._prepare = prepare
        self._begin_inquiry = begin_inquiry
        self._reset = reset
        self._wait = wait

    def check(self, inquiry_id, mpn, quantity, *, at):
        if self._begin_inquiry is not None:
            self._begin_inquiry(inquiry_id)
        def prepare():
            if self._begin_inquiry is not None:
                self._begin_inquiry(inquiry_id)
            if self._prepare is not None:
                try:
                    self._prepare()
                except BrowserBootstrapError as exc:
                    raise V12Fault(FaultScope.GLOBAL_STOP, "INSO_AUTHENTICATION_REQUIRED") from exc

        def operation():
            try:
                return self._checker.check(inquiry_id, mpn, quantity, at=at)
            except (sqlite3.Error, V12DatabaseError):
                raise
            except Exception:
                if self._wait is None:
                    raise
                return None

        if self._wait is None:
            prepare()
            return operation()
        return run_inso_query(
            operation, prepare=prepare,
            succeeded=lambda result: result is not None and result.outcome.value == "CONFIRMED",
            reset=self._reset or (lambda: None), wait=self._wait,
        )


class ProductionBackend(GuiBackend):
    """Own one GUI run session and stop it only at safe Workflow boundaries."""

    def __init__(
        self, config_path=None, production_config_path=None, *, cdp_probe=None,
        root=None, browser_acquirer=acquire_cdp_browser,
        v12_adapters: V12ProductionAdapters | None = None,
        inquiry_ids: frozenset[str] | None = None,
    ):
        self.root = Path(root) if root is not None else app_root()
        self._inquiry_scope = inquiry_ids
        self.config_path = Path(config_path) if config_path is not None else runtime_config_path("research.json", root=self.root)
        self.production_path = Path(production_config_path) if production_config_path is not None else runtime_config_path("production.json", root=self.root)
        self.cdp_probe = cdp_probe
        self._browser_acquirer = browser_acquirer
        self._browser_handle: BrowserHandle | None = None
        self._inso_session: InsoResearchSession | None = None
        self._inso_cdp_url: str | None = None
        self._inso_guard: tuple[object, InsoSessionGuard] | None = None
        self._research_ready = False
        self._research_cycle_drained = True
        self._research_acquire_failure = None
        self._research_gate = threading.Lock()
        self._lock = threading.RLock()
        self._manual_condition = threading.Condition(self._lock)
        self._manual_request = None
        self._manual_busy = False
        self._manual_result = None
        self._manual_reader = self._manual_write_service = self._manual_quote = None
        self._source_overrides = {}
        self._v13_states = {}
        self._v13_unbound = {}
        self._combined = None
        self._v13_ledger_ready = False
        self._v13_enabled = False
        self._stop = threading.Event()
        self._drain_due_on_stop = threading.Event()
        self._poll_gate = threading.Lock()
        self._poll_idle = threading.Event()
        self._poll_idle.set()
        self._thread = None
        self._closed = False
        self._run_id = None
        self._state = RunState.STOPPED
        self._started = self._stopped = self._last_poll = None
        self._next_poll_at = None
        self._keepalive_protected_targets = set()
        self._idle_empty_polls = 0
        self._idle_login_since = utc_now()
        self._row_cooldown_until = None
        self._inquiries = []
        self._poll_inquiries = set()
        self._poll_quotation_completed = set()
        self._dashboard_counts = None
        self._results = ()
        self._history = ()
        self._history_fingerprint = None
        self._startup_interruptions = {}
        self._store = None
        self._v12_store = None
        self._purchase_completion = None
        self._active_inso_inquiry = None
        self._v12_adapters = v12_adapters
        self._v12_composition: V12ProductionComposition | None = None
        self._excel = None
        self._manual_inquiries = set()
        self._login_alert_run_id: str | None = None
        self._login_all_thread: threading.Thread | None = None
        self._login_all_report: SiteLoginReport | None = None
        self._login_all_callbacks = []
        try:
            configured_excel = load_runtime_config(self.config_path).excel_output_path
            self._excel = (
                configured_excel
                if configured_excel.is_absolute()
                else resolve_app_path(configured_excel, root=self.root)
            )
        except ResearchRuntimeConfigError as exc:
            log.debug("Research output path unavailable (%s)", type(exc).__name__)
        self._refresh_history(force=True)
        self._logs = []
        self._status_callbacks = []
        self._log_callbacks = []
        self._health = HealthReport(
            tuple(HealthItem(n, "未知", "尚未检查") for n in self._components()),
            "需要人工处理",
        )
        if self.production_path.is_file():
            try:
                startup_cfg = json.loads(self.production_path.read_text(encoding="utf-8"))
                path = resolve_app_path(Path(startup_cfg.get("sqlite_path", "runtime/production/workflow.sqlite3")), root=self.root)
                self._startup_interruptions = read_startup_interruptions(path)
                known = {o.inquiry_id for o in self._history}
                self._history += tuple(Order(iid, model or "", brand, _integer(quantity, 0),
                    "待验证", None, None, OrderStatus.ERROR, (), "", "", None, None)
                    for iid, (_dto, model, brand, quantity) in self._startup_interruptions.items() if iid not in known)
            except (sqlite3.Error, ValueError):
                self._state = RunState.GLOBAL_STOP
                self._append_log("ERROR", "订单台账不可读，已停止共享业务；未恢复任何订单。")

    @staticmethod
    def _components():
        return ("Google Sheets", "Browser/CDP", "Credential", "Research")

    @property
    def run_id(self):
        with self._lock:
            return self._run_id

    def start(self):
        with self._lock:
            if (
                self._closed
                or self._state in (RunState.RUNNING, RunState.QUOTATION_RUNNING, RunState.STOPPING_AFTER_CYCLE)
                or (self._thread is not None and self._thread.is_alive())
                or (self._login_all_thread is not None and self._login_all_thread.is_alive())
            ):
                return
            self._combined = None
            self._v13_ledger_ready = False
            self._v13_enabled = False
            self._v13_states.clear()
            self._v13_unbound.clear()
            self._idle_empty_polls = 0
            self._idle_login_since = utc_now()
            self._run_id = "run_" + str(uuid.uuid4())
            self._started = utc_now()
            self._stopped = None
            self._inquiries = []
            self._manual_request = None
            self._manual_busy = False
            self._manual_result = None
            self._poll_inquiries.clear()
            self._poll_quotation_completed.clear()
            self._dashboard_counts = None
            self._manual_inquiries.clear()
            self._results = ()
            self._last_poll = None
            self._next_poll_at = None
            self._stop.clear()
            self._drain_due_on_stop.clear()
            self._research_ready = False
            self._poll_idle.set()
            self._login_alert_run_id = None
            self._state = RunState.RUNNING
            self._thread = threading.Thread(
                target=self._run, name="production-launcher", daemon=False
            )
            self._thread.start()
            self._notify()

    def request_stop_after_cycle(self):
        with self._lock:
            if self._state in {RunState.RUNNING, RunState.QUOTATION_RUNNING}:
                self._state = RunState.STOPPING_AFTER_CYCLE
                self._next_poll_at = None
                with self._poll_gate:
                    self._drain_due_on_stop.set()
                    self._stop.set()
                    self._manual_condition.notify_all()
                self._notify()

    def _immediate_stop_requested(self):
        return self._stop.is_set() and not self._drain_due_on_stop.is_set()

    def _run(self):
        try:
            cfg = json.loads(self.production_path.read_text(encoding="utf-8"))
            if (
                not cfg.get("spreadsheet_id")
                or not cfg.get("worksheet_titles")
                or not cfg.get("client_secret_file")
            ):
                raise ProductionConfigurationError(
                    "production.json requires spreadsheet_id, worksheet_titles and client_secret_file"
                )
            rc = load_runtime_config(self.config_path)
            if not rc.excel_output_path.is_absolute():
                rc = replace(rc, excel_output_path=resolve_app_path(rc.excel_output_path, root=self.root))
            # Credential configuration can be checked before polling, while the
            # browser itself stays dormant until a due inquiry needs Research.
            # This keeps empty 15-minute Sheets polls from launching Chrome.
            credential_readiness = assess_readiness(
                rc.cdp.cdp_url,
                cdp_probe=lambda _url: True,
            )
            if credential_readiness.missing_site_ids:
                raise RuntimeError("Research credential readiness requires manual handling")
            client = Path(cfg["client_secret_file"])
            client = resolve_app_path(client, root=self.root)
            reader = GoogleSheetsRowReader(
                build_read_only_google_sheets_service(client)
            )
            worksheets = tuple(
                WorksheetIdentity(cfg["spreadsheet_id"], title)
                for title in cfg["worksheet_titles"]
            )
            db = Path(cfg.get("sqlite_path", "runtime/production/workflow.sqlite3"))
            db = resolve_app_path(db, root=self.root)
            self._excel = (
                rc.excel_output_path
                if rc.excel_output_path.is_absolute()
                else resolve_app_path(rc.excel_output_path, root=self.root)
            )
            self._store = WorkflowStateStore(db)
            # The V1.2 release owns this startup boundary before any worker is
            # started.  The existing migration makes a verified timestamped
            # backup and only adds V1.2 schema; a clean V1.1 database therefore
            # never requires hand preparation.
            migrate_v12(
                db,
                db.parent / "backups",
                quiesce=lambda: nullcontext(),
            )
            self._v12_store = V12Store(db)
            follow_up_store = None
            if cfg.get("v13_enabled") is True or (
                    getattr(sys, "frozen", False) and Path(sys.executable).stem == "INSO_V1.3"):
                follow_up_store = V13PurchaseFollowUpStore(db)
                follow_up_store.migrate()
            status_writer = None
            write_service = None

            self._manual_reader = reader

            def get_write_service():
                nonlocal write_service
                if write_service is None:
                    write_service = build_read_write_google_sheets_service(client, allow_interactive=False)
                return write_service

            def get_status_writer():
                nonlocal status_writer
                if status_writer is None:
                    status_writer = GoogleSheetsPurchaseStatusWriter(
                        get_write_service()
                    )
                return status_writer

            self._purchase_completion = PurchaseCompletionActions(
                workflow_store=self._store, v12_store=self._v12_store,
                reader=reader, writer_factory=get_status_writer, follow_up_store=follow_up_store,
            )
            # RFQ-003: historical unfinished rows are quarantined below before
            # workers start. Never release an old claim for automatic replay.
            research = build_research_service(
                rc,
                inso_operation_access=self._inso_operation_access,
                playwright_provider=self._research_playwright_provider,
                source_observer=self._observe_source_failure,
                inso_query=lambda iid, operation: self._run_inso_query(iid, operation, lambda: self._ensure_research_ready(rc, cfg)),
                source_query=lambda iid, site, operation: self._run_source_query(iid, site, operation,
                    lambda: self._open_research_session(rc, cfg)),
            )

            def prepare_research() -> None:
                self._ensure_research_ready(rc, cfg)

            research_observer = _Observer(
                research,
                self._seen,
                self._manual_review,
                prepare=prepare_research,
            )
            if self._v12_adapters is None:
                self._v12_adapters = V12ProductionAdapters.with_qq_smtp(
                    duplicate_checker=_PreparedDuplicateChecker(
                        InsoDuplicateHistoryChecker(
                            InsoDuplicateHistoryReader(
                                list_url="https://yingsuo.alperp.cn",
                                operation_access=self._inso_operation_access,
                                procurement_history=True,
                            )
                        ),
                        prepare_research,
                        begin_inquiry=self._begin_inso_inquiry,
                        reset=self._close_inso_order_tab,
                        wait=self._stop.wait,
                    ),
                    research_facts=ResearchExcelFactsProvider(ResearchExcelOutput(self._excel)),
                    purchase_writer=_LivePurchaseDraftWriter(
                        self._inso_operation_access,
                        session_guard_factory=self._inso_purchase_session_guard,
                        login_problem=self._manual_review,
                        store=self._v12_store,
                    ),
                    smtp_config=QQSMTPConfig(sender_address="1069599116@qq.com"),
                    recipients=(
                        NotificationRecipient("owner", "linan229@qq.com"),
                        NotificationRecipient("ops", "shawn@inso-hk.com"),
                    ),
                    save_reconciler=PlaywrightReadOnlySaveReconciler(
                        operation_access=self._inso_operation_access,
                        target_for_inquiry=lambda inquiry_id: self._save_target(inquiry_id),
                    ),
                )
            if self._v12_adapters is not None:
                self._v12_composition = compose_v12_production(
                    workflow_store=self._store,
                    v12_store=self._v12_store,
                    research=research_observer,
                    adapters=self._v12_adapters,
                    stop_requested=self._immediate_stop_requested,
                    on_result=self._complete_inquiry,
                    inquiry_ids=self._inquiry_scope,
                    row_wait=self._wait_between_rows,
                )
                self._v12_composition.coordinator.initialize_run_state(now=utc_now())
            else:
                if cfg.get("v12_release_required") is True:
                    raise V12DatabaseError("V1.2 production adapters are required")
                log.warning("V1.2 composition unavailable: production adapters are missing")
            # The V1.2 coordinator owns both polling and the synchronous
            # V1.1 Research worker it deliberately reuses.  Do not also start
            # the legacy worker loop: that would make the production path race
            # and could process an item without V1.2 duplicate/routing state.
            runtime = WorkflowRuntime(
                WorkflowPoller(self._store, reader),
                WorkflowWorker(self._store, research_observer, brand_updater=None),
                worksheets,
            )
            self._v13_enabled = cfg.get("v13_enabled") is True or (
                getattr(sys, "frozen", False) and Path(sys.executable).stem == "INSO_V1.3")
            if self._v13_enabled:
                holds = V13HoldStore(db)
                holds.migrate()
                self._v13_ledger_ready = True
                location = quotation_location(cfg)  # Missing/unknown config stops before business.

                quotation_fx = EcbDailyUsdRmbProvider()

                def run_quotation(worksheet, *, source_store=None, source_reader=None, hold_store=None):
                    active_reader = source_reader or reader
                    active_store = source_store or self._store
                    active_holds = hold_store or holds
                    cycle = V13QuotationCycle(reader=active_reader, store=active_store,
                        operations=self._v13_operations(rc, cfg), clock=utc_now,
                        wait=self._stop.wait, stop_requested=self._stop.is_set, fx_provider=quotation_fx)
                    def updater():
                        handle = self._v13_browser(rc, cfg)
                        try:
                            service = get_write_service()
                        except Exception:  # noqa: BLE001 - shared cached Sheets authorization boundary
                            raise V12Fault(FaultScope.GLOBAL_STOP,"SHEETS_AUTH_UNAVAILABLE") from None
                        return build_v13_quotation_updater(
                            service=service, source_reader=active_reader,
                            store=active_store, browser_handle=handle, location=location,
                            wait=self._stop.wait, stop_requested=self._immediate_stop_requested,
                            notify_model_difference=lambda result, model: notify_quotation_model_difference(
                                self._v12_store, result, model, at=utc_now()))
                    integrated = V13IntegratedCycle(reader=active_reader, store=active_store,
                        holds=active_holds, cycle=cycle, updater_factory=updater,
                        follow_up=PurchaseFollowUp(reader=active_reader, workflow_store=active_store,
                            v12_store=self._v12_store, clock=utc_now, episodes=follow_up_store).run,
                        notify=lambda result,key,episode: notify_quotation(self._v12_store,
                            result,key,episode,at=utc_now()), observe=self._observe_quotation,
                        stop_requested=self._stop.is_set)
                    for recovery in range(4):
                        try:
                            return integrated.run(worksheet)
                        except V12Fault as exc:
                            if exc.reason != "CDP_SESSION_UNAVAILABLE" or recovery == 3:
                                raise
                            handle = self._browser_handle
                            if handle is not None:
                                handle.disconnect()
                            self._browser_handle = None
                            self._v13_browser(rc,cfg)
                self._manual_quote = (run_quotation, holds)
                self._combined = CombinedCycle(self._v12_composition.coordinator,
                    run_quotation, on_pause=self._pause_v12,
                    stop_requested=self._stop.is_set)
            self._manual_write_service = get_write_service
            self._refresh_history(force=True)
            self._set_health(("正常", "待命", "正常", "正常"), "正常")

            def poll_loop():
                try:
                    while True:
                        # This thread starts the Playwright client (the V1.2
                        # duplicate check prepares the session first), so it also
                        # has to stop clients parked by the worker thread's idle
                        # release. Stopping them anywhere else raises
                        # greenlet.error and orphans the driver process.
                        BrowserHandle.drain_deferred_stops()
                        with self._poll_gate:
                            if self._stop.is_set():
                                return
                            self._poll_idle.clear()
                        try:
                            self._last_poll = utc_now()
                            self._cycle_id = "cycle_" + uuid.uuid4().hex
                            self._begin_poll_projection()
                            self._refresh_dashboard_counts(reader, worksheets,
                                episodes=follow_up_store, now=self._last_poll)
                            if self._combined is not None:
                                self._combined.run(reader, worksheets, now=self._last_poll)
                            else:
                                self._v12_composition.coordinator.begin_poll_cycle()
                                for worksheet in worksheets:
                                    if self._immediate_stop_requested():
                                        return
                                    self._v12_composition.coordinator.poll_and_process(reader,worksheet,now=self._last_poll)
                            if self._immediate_stop_requested():
                                return
                            self._idle_login_tick(now=utc_now())
                            if self._immediate_stop_requested():
                                return
                            self._purchase_completion.retry_saved_statuses(at=utc_now())
                            self._v12_composition.coordinator.run_notifications(
                                now=utc_now()
                            )
                            with self._lock:
                                if self._state in {RunState.RUNNING, RunState.QUOTATION_RUNNING}:
                                    self._next_poll_at = utc_now() + runtime.poll_interval
                            browser_state = "已连接" if self._research_ready else "待命"
                            self._set_health(("正常", browser_state, "正常", "正常"), "正常")
                        except V12Fault as exc:
                            if exc.scope is FaultScope.GLOBAL_STOP:
                                self._state = RunState.GLOBAL_STOP  # Preserve human-needed pages before finally.
                            raise
                        except (sqlite3.Error, V12DatabaseError):
                            self._state = RunState.GLOBAL_STOP
                            raise
                        finally:
                            self._close_inso_order_tab()
                            self._poll_idle.set()
                        if self._wait_between_polls(runtime.poll_interval.total_seconds()):
                            return
                except V13Stopped:
                    pass
                except Exception as exc:  # noqa: BLE001 - fail closed at runtime boundary
                    self._runtime_error(exc)
                finally:
                    if self._v13_enabled:
                        self._release_idle_browser(force=True)
                    BrowserHandle.drain_deferred_stops()

            def worker_loop():
                try:
                    while True:
                        if self._stop.is_set():
                            return
                        BrowserHandle.drain_deferred_stops()
                        self._refresh()
                        if self._v12_composition is not None:
                            self._v12_composition.coordinator.run_notifications(now=utc_now())
                        self._release_idle_browser()
                        self._stop.wait(runtime.worker_idle_interval.total_seconds())
                except ResearchPreparationError as exc:
                    self._preparation_error(exc)
                except Exception as exc:  # noqa: BLE001 - fail closed at runtime boundary
                    self._runtime_error(exc)
                finally:
                    BrowserHandle.drain_deferred_stops()

            poll_thread = threading.Thread(
                target=poll_loop, name="production-sheets-poller"
            )
            worker_thread = threading.Thread(
                target=worker_loop, name="production-research-worker"
            )
            poll_thread.start()
            worker_thread.start()
            while poll_thread.is_alive() or worker_thread.is_alive():
                self._refresh()
                poll_thread.join(timeout=0.1)
                worker_thread.join(timeout=0.1)
        except Exception as exc:  # noqa: BLE001 - fail closed at runtime boundary
            log.warning("Production runtime stopped (%s)", type(exc).__name__)
            self._append_log(
                "ERROR",
                f"需要人工处理：{type(exc).__name__}；请检查本地配置、授权、CDP 与人工验证状态",
            )
            self._runtime_error(exc)
        finally:
            self._refresh()
            if self._browser_handle is not None:
                self._research_cycle_drained = True
                self._release_idle_browser(force=True)
            with self._lock:
                if self._state not in {RunState.MANUAL_REVIEW, RunState.MODULE_PAUSED, RunState.GLOBAL_STOP}:
                    self._state = RunState.STOPPED
                self._stopped = utc_now()
                self._notify()

    def _pause_v12(self, fault):
        with self._lock:
            self._state = RunState.QUOTATION_RUNNING
        inquiry = self._active_inso_inquiry or (self._inquiries[-1] if self._inquiries else None)
        if inquiry is not None:
            if inquiry not in self._manual_inquiries:
                self._record_fault_alert(inquiry,"FAULT",fault.reason)
        else:
            notify_runtime_fault(self._v12_store,self._run_id or "run",fault.reason,at=utc_now())
        self._append_log("WARNING", "采购模块暂停，报价模块继续；请检查采购网站或订单。")
        self._notify()

    def _v13_browser(self, rc, cfg):
        for attempt in range(4):
            handle = self._browser_handle
            if handle is not None and handle.browser is not None and handle.browser.is_connected():
                return handle
            try:
                if handle is not None:
                    handle.disconnect()
                self._browser_handle = self._browser_acquirer(rc.cdp.cdp_url,self.root,cfg,
                    probe=self.cdp_probe or probe_loopback_endpoint)
                if self._browser_handle.browser.is_connected():
                    return self._browser_handle
            except Exception:  # noqa: BLE001 - only shared CDP acquisition
                log.warning("V1.3 shared CDP recovery attempt failed")
        raise V12Fault(FaultScope.GLOBAL_STOP,"CDP_RECONNECT_EXHAUSTED")

    def _v13_operations(self, rc, cfg):
        backend = self
        class SharedOperations:
            current = None
            def open(self, inquiry_id):
                backend._seen(inquiry_id)
                backend._active_inso_inquiry = inquiry_id
                handle = backend._v13_browser(rc,cfg)
                try:
                    login = CoreLoginBridge().login(INSO_SITE_ID)
                except Exception:  # noqa: BLE001 - only the shared login bridge
                    raise V12Fault(FaultScope.GLOBAL_STOP,"INSO_AUTHENTICATION_REQUIRED") from None
                self.current = V13QuotationOperations(browser_handle=handle,login=login)
                return self.current.open(inquiry_id)
            def preserve(self):
                if self.current:
                    self.current.preserve()
            def close(self):
                if self.current:
                    self.current.close()
                    self.current = None
                backend._active_inso_inquiry = None
        return SharedOperations()

    def _observe_quotation(self, result, key):
        dto = quotation_gui(result,key)
        with self._lock:
            inquiry = result.inquiry_id or key
            self._poll_inquiries.add(inquiry)
            if result.outcome.value in {"NO_RECENT_QUOTE", "ROW_FAILED", "UPDATED_INSERTED", "UPDATED_ALREADY_EXISTS"}:
                self._poll_quotation_completed.add(inquiry)
        if dto is not None:
            with self._lock:
                self._v13_states[key] = dto
                if result.inquiry_id is None:
                    self._v13_unbound[key] = Order(key,result.queried_mpn or "",None,0,
                        "",None,None,OrderStatus.ERROR,remark=dto.waiting_label,run_id=self._run_id or "")
            if result.inquiry_id:
                self._seen(result.inquiry_id)
        log.warning("combined cycle result",extra={"cycle_id":getattr(self,"_cycle_id",None),
            "business_module":"V1.3","inquiry_id":result.inquiry_id,"stage":"quotation",
            "reason":result.row_error_reason.value if result.row_error_reason else result.outcome.value})
        if result.row_error_reason is not None and result.row_error_reason.value == "SOURCE_STATUS_NOT_UPDATED":
            self._append_log("WARNING", "报价脚本已成功，30秒内表格状态未更新；已安排229异常提醒，请人工核对。")
        self._refresh()
        self._notify()

    def _manual_idle(self):
        return (self._state in {RunState.RUNNING, RunState.QUOTATION_RUNNING}
            and self._next_poll_at is not None and self._next_poll_at > utc_now()
            and self._poll_idle.is_set() and not self._stop.is_set()
            and not self._manual_busy and self._manual_request is None)

    def can_order_action(self, inquiry_id, action):
        with self._lock:
            if not self._manual_idle() or self._store is None or self._manual_reader is None:
                return False
            try:
                self._store.get_by_inquiry_id(inquiry_id)
                if action == "purchase":
                    return (self._state is RunState.RUNNING and self._v12_store is not None
                        and self._v12_store.manual_purchase_retry_allowed(inquiry_id))
                return action == "edit" or (action == "quotation" and self._manual_quote is not None)
            except (KeyError, sqlite3.Error, V12DatabaseError):
                return False

    def request_order_action(self, inquiry_id, action, *, field=None, value=None):
        with self._manual_condition:
            if not self.can_order_action(inquiry_id, action):
                return "仅能在倒计时期间操作可定位的订单；已发送或结果不明的采购不能重发。"
            try:
                if action == "edit":
                    value = editable_value(field, value)
            except ValueError as exc:
                return str(exc)
            self._manual_request = (uuid.uuid4().hex, inquiry_id, action, field, value)
            self._manual_result = None
            self._manual_condition.notify_all()
        self._notify()
        return None

    def get_manual_order_result(self):
        with self._lock:
            return self._manual_result

    def _wait_between_polls(self, seconds):
        deadline = monotonic() + seconds
        while not self._stop.is_set():
            with self._manual_condition:
                if self._stop.is_set():
                    self._manual_request = None
                    return True
                request, self._manual_request = self._manual_request, None
                if request is None:
                    remaining = deadline - monotonic()
                    if remaining <= 0:
                        return False
                    self._manual_condition.wait(min(remaining, 0.25))
                    continue
                self._manual_busy = True
                self._next_poll_at = None
                self._poll_idle.clear()
            self._notify()
            try:
                self._execute_order_action(request)
            finally:
                self._close_inso_order_tab()
                with self._lock:
                    self._manual_busy = False
                    self._poll_idle.set()
                    if self._state in {RunState.RUNNING, RunState.QUOTATION_RUNNING} and not self._stop.is_set():
                        self._next_poll_at = utc_now() + timedelta(seconds=seconds)
                self._notify()
            deadline = monotonic() + seconds
        return True

    def _execute_order_action(self, request):
        request_id, inquiry, action, field, value = request
        success, message = False, "操作未执行。"
        try:
            item = self._store.get_by_inquiry_id(inquiry)
            identity = item.record_identity
            record, status = current_record(self._manual_reader, identity.worksheet, identity.row_position)
            scoped_reader = SingleRowReader(self._manual_reader, identity.worksheet, identity.row_position)
            if action == "edit":
                from src.sheets.google_writer import GoogleSheetsBrandWriter
                writer = GoogleSheetsBrandWriter(self._manual_write_service())
                writer.write_order_field(identity.worksheet, identity.row_position, field, value)
                record, _ = current_record(self._manual_reader, identity.worksheet, identity.row_position)
                if getattr(record, "importance_raw" if field == "importance" else field) != value:
                    raise ValueError("写入结果未能确认，请重新读取表格；不会自动重复写入。")
                message = "单元格已同步并读回确认。"
            elif action == "purchase":
                if status != "未发":
                    raise ValueError("采购重跑要求当前Google状态为未发，未修改状态。")
                self._poll_quotation_completed.discard(inquiry)
                self._v13_states.pop(inquiry, None)
                self._v12_composition.coordinator.rerun_unsubmitted(inquiry, record, scoped_reader, now=utc_now())
                message = "采购流程本次处理结束，请查看订单状态。"
            else:
                if status != "发给采购":
                    raise ValueError("报价重跑要求当前Google状态为发给采购，未修改状态。")
                runner, holds = self._manual_quote
                manual_holds = ManualRetryHolds(holds, inquiry, identity)
                for key, _, observed, reason, _ in manual_holds.matched_old:
                    if reason == "SOURCE_STATUS_NOT_UPDATED":
                        snapshot = json.loads(observed)["identifying_snapshot"]
                        if all(snapshot[name] == getattr(record, name) for name in ("model", "brand", "quantity")):
                            raise ValueError("此前报价脚本已成功，主表状态待核对；不会重复更新报价。")
                results = runner(identity.worksheet, source_reader=scoped_reader,
                    source_store=CurrentQuotationStore(item, record), hold_store=manual_holds)
                if not self._stop.is_set():
                    manual_holds.finalize(results)
                message = "报价流程本次处理结束，请查看订单状态。"
            if action != "edit":
                record, _ = current_record(self._manual_reader, identity.worksheet, identity.row_position)
            with self._lock:
                self._source_overrides[inquiry] = {"model": record.model, "brand": record.brand,
                    "quantity": _integer(record.quantity, 0), "importance": record.importance_raw}
            success = True
            self._refresh_history(force=True)
        except V12Fault as exc:
            if exc.scope is FaultScope.GLOBAL_STOP:
                self._state = RunState.GLOBAL_STOP
                raise
            if self._combined is not None:
                self._combined.v12_paused = True
            self._pause_v12(exc)
            message = "采购流程需要人工处理，报价轮询保持原有独立策略。"
        except (KeyError, ValueError) as exc:
            message = str(exc) if isinstance(exc, ValueError) else "找不到订单的源表定位，未执行操作。"
        except Exception:  # noqa: BLE001 - targeted edit/read failure is shown without raw provider text
            if action != "edit":
                raise V12Fault(FaultScope.GLOBAL_STOP, "V13_INTERNAL_FAILURE" if action == "quotation" else "V12_MANUAL_RETRY_FAILED") from None
            message = "单元格同步失败或结果未确认，请重新读取表格；不会自动重复写入。"
        with self._lock:
            self._manual_result = ManualOrderResult(request_id, inquiry, action, success, message)
        self._append_log("INFO" if success else "WARNING", message)
        self._refresh()

    def _refresh_dashboard_counts(self, reader, worksheets, *, episodes, now):
        counts = read_dashboard_counts(reader, worksheets, store=self._store,
                                       episodes=episodes, now=now)
        with self._lock:
            self._dashboard_counts = counts
        self._notify()

    def _begin_poll_projection(self):
        with self._lock:
            self._poll_inquiries.clear()
            self._poll_quotation_completed.clear()
            self._next_poll_at = None
        self._notify()

    def _seen(self, inquiry):
        with self._lock:
            self._poll_inquiries.add(inquiry)
            if inquiry not in self._inquiries:
                self._inquiries.append(inquiry)

    def _observe_source_failure(self, inquiry_id, result):
        if result.outcome is not SourceOutcome.SOURCE_UNAVAILABLE:
            return
        code = next((str(f.value) for f in result.evidence.fields if f.key == "failure_code"), "SOURCE_UNAVAILABLE")
        notified = self._v12_store is not None
        if notified:
            mpn = self._store.get_by_inquiry_id(inquiry_id).mpn if self._store is not None else None
            notify_website_issue(self._v12_store, inquiry_id, result.source, code, mpn=mpn, at=utc_now())
        login = any(token in code for token in ("LOGIN", "CREDENTIAL", "AUTHENTICATION", "VERIFICATION", "CHALLENGE", "SESSION_STALE"))
        if result.source is ResearchSource.IC_NET:
            self._manual_review(inquiry_id, "IC.net：需要人工验证" if login else "IC.net：查询不可用", notify=False)
            raise V12Fault(FaultScope.V12_PAUSE, "IC_NET_UNAVAILABLE")
        if result.source is ResearchSource.INSO and login:
            self._manual_review(inquiry_id, "INSO：登录不可用", notify=False)
            raise V12Fault(FaultScope.GLOBAL_STOP, "INSO_AUTHENTICATION_REQUIRED")

    def _run_inso_query(self, inquiry_id, operation, prepare):
        first_attempt = True

        def prepare_attempt():
            nonlocal first_attempt
            if first_attempt:
                first_attempt = False
                return
            self._begin_inso_inquiry(inquiry_id)
            prepare()

        def read_attempt():
            try:
                return operation()
            except (sqlite3.Error, V12DatabaseError, V12Fault):
                raise
            except Exception:  # noqa: BLE001 - failed reads never become empty history
                return None

        def succeeded(result):
            if result is None:
                return False
            self._observe_source_failure(inquiry_id, result)
            code = next((str(f.value) for f in result.evidence.fields if f.key == "failure_code"), "SOURCE_UNAVAILABLE")
            return result.outcome is not SourceOutcome.SOURCE_UNAVAILABLE or "FX" in code

        return run_inso_query(
            read_attempt, prepare=prepare_attempt, succeeded=succeeded,
            reset=self._close_inso_order_tab, wait=self._stop.wait,
        )

    def _run_source_query(self, inquiry_id, site, operation, reconnect):
        """Three bounded shared-CDP recoveries, independent of per-query retry."""
        for attempt in range(4):
            result = operation()
            source_result = result.source_result if site is ResearchSource.IC_NET else result
            code = next((str(f.value) for f in source_result.evidence.fields if f.key == "failure_code"), "")
            if not any(token in code for token in ("CDP", "PLAYWRIGHT", "CONTEXT")):
                return result
            if attempt == 3:
                raise V12Fault(FaultScope.GLOBAL_STOP, "CDP_RECONNECT_EXHAUSTED")
            self._release_idle_browser(force=True)
            try:
                self._begin_inso_inquiry(inquiry_id)
                reconnect()
            except BrowserBootstrapError as exc:
                if isinstance(exc.__cause__, InsoAuthenticationError):
                    raise V12Fault(FaultScope.GLOBAL_STOP, "INSO_AUTHENTICATION_REQUIRED") from exc
                if attempt == 2:
                    raise V12Fault(FaultScope.GLOBAL_STOP, "CDP_RECONNECT_EXHAUSTED") from exc
        raise AssertionError("bounded CDP loop exhausted")

    def _begin_inso_inquiry(self, inquiry_id):
        self._seen(inquiry_id)
        if self._active_inso_inquiry != inquiry_id:
            self._close_inso_order_tab()
            self._active_inso_inquiry = inquiry_id

    @staticmethod
    def _page_target_id(page):
        session = page.context.new_cdp_session(page)
        try:
            return session.send("Target.getTargetInfo")["targetInfo"]["targetId"]
        finally:
            session.detach()

    def _protect_keepalive_pages(self, pages):
        for page in pages:
            if not page.is_closed() and page.url != "about:blank":
                self._keepalive_protected_targets.add(self._page_target_id(page))

    def _live_keepalive_pages(self, browser):
        if not self._keepalive_protected_targets:
            return ()
        context, = browser.contexts
        live = {self._page_target_id(p): p for p in context.pages if not p.is_closed()}
        self._keepalive_protected_targets.intersection_update(live)
        return tuple(live[target] for target in self._keepalive_protected_targets)

    def _park_browser(self, browser):
        protected = self._live_keepalive_pages(browser)
        if protected:
            context, = browser.contexts
            if not any(not p.is_closed() and p.url == "about:blank" for p in context.pages):
                new_background_page(browser, context, timeout_ms=10000)
            return
        park_shared_cdp(browser)

    def _close_inso_order_tab(self):
        session = self._inso_session
        if session is not None and self._state not in {RunState.MANUAL_REVIEW, RunState.MODULE_PAUSED, RunState.GLOBAL_STOP}:
            close = getattr(session, "close_owned_operation_tab", None)
            protected = False
            if self._keepalive_protected_targets:
                try:
                    page = session.operation_access().operation_page().page
                    protected = self._page_target_id(page) in self._keepalive_protected_targets
                except Exception:  # noqa: BLE001 - uncertain owned page must remain available to the Owner
                    protected = True
            if callable(close) and not protected:
                close()
        self._inso_session = None
        self._inso_guard = None
        self._research_ready = False
        self._active_inso_inquiry = None
        browser = getattr(self._browser_handle, "browser", None)
        if browser is not None and self._state not in {RunState.MANUAL_REVIEW, RunState.MODULE_PAUSED, RunState.GLOBAL_STOP}:
            self._park_browser(browser)

    def _complete_inquiry(self, result):
        """Settle each row before starting the next; never defer to batch drain."""
        try:
            log.warning("combined cycle result", extra={"cycle_id":getattr(self,"_cycle_id",None),
                "business_module":"V1.2","inquiry_id":result.inquiry_id,"stage":"purchase",
                "reason":getattr(getattr(result,"business_state",None),"value","UNKNOWN")})
            self._seen(result.inquiry_id)
            settled = self._purchase_completion.process(result, at=utc_now())
            self._v12_composition.coordinator.run_notifications(now=utc_now())
            if settled is False:
                with self._lock:
                    self._state = RunState.MODULE_PAUSED
                    self._next_poll_at = None
                    self._drain_due_on_stop.clear()
                    self._stop.set()
                self._append_log("ERROR", "当前订单提交、状态写回或通知尚未确认，已停止后续订单；不会重发采购。")
            self._refresh()
            self._notify()
        finally:
            self._close_inso_order_tab()

    def _ensure_research_ready(self, research_config, production_config) -> None:
        """Start or reuse CDP only for a due inquiry, then verify readiness."""

        with self._research_gate:
            if self._research_ready:
                return
            # The duplicate lookup and Research both prepare this one session,
            # so a poll may ask twice. Acquiring the browser is the expensive and
            # side-effecting step: remember a failure for the rest of the poll so
            # each poll attempts it exactly once, then recovers on the next poll.
            failure = self._research_acquire_failure
            if failure is not None and failure[0] == self._last_poll:
                raise failure[1]
            try:
                for attempt in range(3):
                    try:
                        self._open_research_session(research_config, production_config)
                        break
                    except BrowserBootstrapError as failure:
                        if isinstance(failure.__cause__, InsoAuthenticationError):
                            raise
                        if attempt == 2:
                            raise V12Fault(FaultScope.GLOBAL_STOP, "CDP_RECONNECT_EXHAUSTED") from failure
            except BrowserBootstrapError as exc:
                self._research_acquire_failure = (self._last_poll, exc)
                raise
        self._set_health(("正常", "已连接", "正常", "正常"), "正常")

    def _open_research_session(self, research_config, production_config) -> None:
        """Acquire or reuse the approved CDP browser and verify the INSO shell."""

        probe = self.cdp_probe or probe_loopback_endpoint
        try:
            self._browser_handle = self._browser_handle or self._browser_acquirer(
                research_config.cdp.cdp_url,
                self.root,
                production_config,
                probe=probe,
            )
        except BrowserBootstrapError:
            raise
        except Exception as exc:
            raise BrowserBootstrapError(
                "approved CDP browser could not be acquired"
            ) from exc
        try:
            readiness = assess_readiness(
                research_config.cdp.cdp_url,
                cdp_probe=probe,
            )
        except Exception as exc:
            self._discard_unready_browser()
            raise BrowserBootstrapError("CDP research readiness failed") from exc
        if not readiness.ready:
            self._discard_unready_browser()
            raise BrowserBootstrapError("CDP research readiness failed")
        try:
            if self._browser_handle.browser is not None:
                self._park_browser(self._browser_handle.browser)
            self._research_cycle_drained = False
            self._inso_session = attach_inso_research_session(
                research_config.cdp.cdp_url,
                self._browser_handle,
                cycle_id=self._run_id or "research-cycle",
                cycle_is_drained=lambda _cycle: self._research_cycle_drained,
                login=CoreLoginBridge().login(INSO_SITE_ID),
                fresh_page=True,
            )
            self._inso_cdp_url = research_config.cdp.cdp_url
            self._inso_guard = None
        except Exception as exc:
            self._discard_unready_browser()
            raise BrowserBootstrapError(
                "INSO research session identity could not be verified"
            ) from exc
        self._research_ready = True

    def _discard_unready_browser(self) -> None:
        """Close a just-acquired owned browser when readiness cannot be proven."""

        handle = self._browser_handle
        session = self._inso_session
        self._browser_handle = None
        self._inso_session = None
        self._inso_guard = None
        self._research_ready = False
        if session is not None and not self._keepalive_protected_targets:
            try:
                self._research_cycle_drained = True
                session.close_after_drain()
            except Exception as exc:  # noqa: BLE001 - cleanup boundary
                log.warning("Unready INSO session shutdown failed (%s)", type(exc).__name__)
        if handle is not None and (session is None or self._keepalive_protected_targets):
            try:
                if self._keepalive_protected_targets:
                    handle.disconnect()
                else:
                    handle.close()
            except Exception as exc:  # noqa: BLE001 - cleanup boundary
                log.warning("Unready browser shutdown failed (%s)", type(exc).__name__)

    def _release_idle_browser(self, *, force: bool = False) -> None:
        """Release an app-owned browser after this due-work batch is drained."""

        if not force and not self._poll_idle.is_set():
            # A poll is mid-flow: the V1.2 handoff still owns the shared INSO
            # session for its duplicate lookup, Research and routing. The worker
            # tick runs every second, so releasing here tore the session out from
            # under that work and made every attempt fail.
            return
        with self._research_gate:
            if not self._research_ready and self._browser_handle is None:
                return
            self._research_cycle_drained = True
            handle = self._browser_handle
            session = self._inso_session
            self._browser_handle = None
            self._inso_session = None
            self._inso_guard = None
            self._research_ready = False
        if self._keepalive_protected_targets and handle is not None:
            handle.disconnect()  # Target IDs survive detach; never close protected Chrome/pages.
            return
        if handle is not None and self._state in {
            RunState.MANUAL_REVIEW, RunState.MODULE_PAUSED, RunState.GLOBAL_STOP,
        }:
            # A human-needed page is not a drained order. Detach only the client;
            # never close its lease/tab, Chrome, context, profile or cookies.
            disconnect = getattr(handle, "disconnect", None)
            if callable(disconnect):
                try:
                    disconnect()
                except Exception as exc:  # noqa: BLE001 - preserve the human page even if detach fails
                    log.warning("Paused client detach failed (%s)", type(exc).__name__)
            return
        if session is not None:
            try:
                session.close_after_drain()
            except Exception as exc:  # noqa: BLE001 - cleanup boundary
                log.warning("INSO session shutdown failed (%s)", type(exc).__name__)
        if handle is not None and (session is None or self._keepalive_protected_targets):
            try:
                if self._keepalive_protected_targets:
                    handle.disconnect()
                else:
                    handle.close()
            except Exception as exc:  # noqa: BLE001 - cleanup boundary
                log.warning("Idle browser shutdown failed (%s)", type(exc).__name__)
        with self._lock:
            running = self._state is RunState.RUNNING
        if running:
            self._set_health(("正常", "待命", "正常", "正常"), "正常")

    def _inso_operation_access(self):
        session = self._inso_session
        if session is None:
            raise BrowserBootstrapError("verified INSO Research session is unavailable")
        return session.operation_access()

    def _inso_context(self):
        """Return the one live browsing context, or fail closed.

        The session probe and the re-login both act on it, so an ambiguous or
        missing context must stop recovery rather than be guessed at.
        """

        browser = getattr(self._browser_handle, "browser", None)
        if browser is None:
            session = self._inso_session
            browser = getattr(getattr(session, "lease", None), "browser", None)
            browser = getattr(browser, "browser", None)
        contexts = tuple(getattr(browser, "contexts", ())) if browser is not None else ()
        if len(contexts) != 1:
            raise InsoAuthenticationError("AUTHENTICATION_REQUIRED")
        return contexts[0]

    def _inso_purchase_session_guard(self):
        """Build the guard that owns in-run login recovery, once per session.

        Returns ``None`` when there is no session or no stored credential: the
        guard is an addition, so a launcher that cannot build one keeps the
        pre-existing fail-closed behaviour instead of inventing a new failure.
        """

        session = self._inso_session
        if session is None:
            return None
        cached = self._inso_guard
        if cached is not None and cached[0] is session:
            return cached[1]
        login = CoreLoginBridge().login(INSO_SITE_ID)
        if login is None:
            log.warning("no stored INSO credential: session recovery is unavailable")
            return None
        guard = InsoSessionGuard(
            login=login,
            context=self._inso_context,
            page=lambda: session.operation_access().operation_page().page,
            reattach=lambda: self._reattach_inso_session(
                operation_page=guard.authenticated_page,
                owns_operation_page=session.owns_operation_page,
            ),
        )
        self._inso_guard = (session, guard)
        return guard

    def _reattach_inso_session(self, *, operation_page=None, owns_operation_page=False) -> None:
        """Re-lease the verified shell after an in-run re-login.

        A lease is pinned to one page identity, so a login invalidates it even
        though the session is healthy again. The old lease is dropped and never
        closed: the browser is shared, and closing it here would tear down the
        session this call has just restored.
        """

        with self._research_gate:
            handle = self._browser_handle
            cdp_url = self._inso_cdp_url
            if handle is None or not cdp_url:
                raise InsoAuthenticationError("AUTHENTICATION_REQUIRED")
            previous = self._inso_session
            self._inso_session = None
            self._inso_guard = None
            self._research_ready = False
            if previous is not None:
                invalidate = getattr(
                    getattr(previous, "lease", None), "invalidate", None
                )
                if callable(invalidate):
                    invalidate()
            self._research_cycle_drained = False
            self._inso_session = attach_inso_research_session(
                cdp_url,
                handle,
                cycle_id=self._run_id or "research-cycle",
                cycle_is_drained=lambda _cycle: self._research_cycle_drained,
                # The guard has just logged in and clicked the native menu.
                # Re-lease that verified page; a second login here navigates
                # away from it and races the lease we are trying to establish.
                operation_page=operation_page,
                owns_operation_page=owns_operation_page,
            )
            self._research_ready = True
        self._set_health(("正常", "已连接", "正常", "正常"), "正常")

    def _research_playwright_provider(self):
        """Return the launcher's live ``(playwright, browser)`` CDP attachment.

        Playwright's synchronous API can only be started once per thread, so the
        browser-backed Research sources must reuse this single protected session
        instead of opening their own. Returns ``None`` until the session is
        acquired (and after it is released), which lets each source fall back to
        its own connection rather than failing.
        """

        handle = self._browser_handle
        playwright = getattr(handle, "playwright", None)
        browser = getattr(handle, "browser", None)
        if playwright is None or browser is None:
            return None
        return playwright, browser

    def _save_target(self, inquiry_id):
        if self._store is None:
            return None
        if self._v12_store is not None and any(
            event.event_type is EventType.SAVE_DISPATCH_ARMED
            for event in self._v12_store.event_history(inquiry_id)
        ):
            # Restart cannot reconstruct the baseline. Never use the legacy
            # old-record lookup for a new Save-and-Send attempt.
            return None
        try:
            item = self._store.get_by_inquiry_id(inquiry_id)
        except KeyError:
            return None
        brand = item.resolved_brand or item.brand
        if not isinstance(brand, str):
            return None
        return SaveReconciliationTarget(item.mpn, brand, item.quantity)

    def _runtime_error(self, exc):
        log.warning("Production runtime worker failed (%s)", type(exc).__name__)
        with self._lock:
            self._state = RunState.MODULE_PAUSED
            cause = exc
            while cause is not None:
                if isinstance(cause, V12Fault):
                    self._state = (RunState.GLOBAL_STOP if cause.scope is FaultScope.GLOBAL_STOP
                                   else RunState.MODULE_PAUSED)
                    break
                if isinstance(cause, (sqlite3.Error, V12DatabaseError, InsoAuthenticationError, ProductionConfigurationError)) or type(cause).__name__.startswith("GoogleSheets"):
                    self._state = RunState.GLOBAL_STOP
                    break
                cause = cause.__cause__
            self._next_poll_at = None
            self._drain_due_on_stop.clear()
            with self._poll_gate:
                self._stop.set()
            if isinstance(exc, ProductionConfigurationError):
                statuses = (
                    HealthItem("Google Sheets", "需要配置", "缺少生产数据源配置"),
                    HealthItem("Browser/CDP", "待命", "未启动"),
                    HealthItem("Credential", "需要配置", "缺少授权文件配置"),
                    HealthItem("Research", "待命", "等待生产配置"),
                )
            else:
                statuses = tuple(
                    HealthItem(name, "需要人工处理", "运行组件停止")
                    for name in self._components()
                )
            self._health = HealthReport(statuses, "需要人工处理")
        message = (
            "需要配置：请补齐本地生产数据源与授权文件"
            if isinstance(exc, ProductionConfigurationError)
            else f"需要人工处理：{type(exc).__name__}；检查本地运行状态"
        )
        self._append_log("ERROR", message)
        self._notify()
        fault_inquiry = self._active_inso_inquiry or (self._inquiries[-1] if self._inquiries else None)
        reason = "V12_INTERNAL_FAILURE"
        cause = exc
        while cause is not None:
            if isinstance(cause, V12Fault):
                reason = cause.reason
                break
            if isinstance(cause, (sqlite3.Error, V12DatabaseError)):
                reason = "WORKFLOW_LEDGER_UNAVAILABLE"
                break
            if isinstance(cause, InsoAuthenticationError):
                reason = "INSO_AUTHENTICATION_REQUIRED"
                break
            if type(cause).__name__.startswith("GoogleSheets"):
                reason = "GOOGLE_SHEETS_UNAVAILABLE"
                break
            cause = cause.__cause__
        if fault_inquiry not in self._manual_inquiries:
            self._record_fault_alert(fault_inquiry, "FAULT", reason)
        if fault_inquiry is None and self._v13_ledger_ready:
            try:
                notify_runtime_fault(self._v12_store,self._run_id or "run",reason,at=utc_now())
                self._v12_composition.coordinator.run_notifications(now=utc_now())
            except (sqlite3.Error,V12DatabaseError):
                self._alert_owner_of_login(stop_reason=self._state.value)
        elif self._purchase_completion is None or fault_inquiry is None:
            self._alert_owner_of_login(stop_reason=self._state.value)

    def _record_fault_alert(self, inquiry_id, phase, reason):
        if self._purchase_completion is None or inquiry_id is None:
            return
        try:
            self._purchase_completion.notify(inquiry_id, phase, reason, at=utc_now())
            if self._v12_composition is not None:
                self._v12_composition.coordinator.run_notifications(now=utc_now())
        except (sqlite3.Error, V12DatabaseError):
            self._state = RunState.GLOBAL_STOP
            self._stop.set()
            self._append_log("ERROR", "订单台账不可用，无法记录故障通知；全部共享业务已停止。")
            self._alert_owner_of_login(stop_reason="订单台账不可用；全部共享业务已停止")

    def _preparation_error(self, exc: ResearchPreparationError) -> None:
        """Fail closed for CDP setup without consuming a Research retry."""

        self._runtime_error(exc)
        self._release_idle_browser(force=True)

    def _manual_review(self, inquiry_id, remarks: str = "", *, notify=True):
        lower = remarks.casefold()
        if not any(site in lower for site in ("inso", "英索", "ic.net")):
            if self._purchase_completion is not None:
                self._record_fault_alert(inquiry_id, "SESSION", remarks)
            else:
                self._alert_owner_of_login(stop_reason=remarks, inquiry_id=inquiry_id)
            return
        with self._lock:
            self._manual_inquiries.add(inquiry_id)
            self._state = (RunState.GLOBAL_STOP if "inso" in lower or "英索" in lower else RunState.MODULE_PAUSED)
            self._next_poll_at = None
            self._drain_due_on_stop.clear()
            if not (self._v13_enabled and self._state is RunState.MODULE_PAUSED):
                with self._poll_gate:
                    self._stop.set()
            self._health = HealthReport(
                tuple(
                    HealthItem(
                        name,
                        "需要人工处理" if name == "Research" else "已停止",
                        "采集遇到需要人工介入的登录或安全验证",
                    )
                    for name in self._components()
                ),
                "需要人工处理",
            )
        self._append_log(
            "WARNING",
            "采集需要人工处理；请在 Chrome 完成登录后再次点击「开始询价」",
        )
        self._refresh()
        self._notify()
        if not notify:
            return
        # The run is already stopped above, so the Owner's screen says what
        # happened before the mail round trip is attempted. The mail is what
        # tells them while they are away from the machine.
        if self._purchase_completion is not None:
            self._record_fault_alert(inquiry_id, "SESSION", "INSO_AUTHENTICATION_REQUIRED"
                if "inso" in lower or "英索" in lower else "IC_NET_UNAVAILABLE")
        else:
            self._alert_owner_of_login(stop_reason=remarks, inquiry_id=inquiry_id)

    def _alert_owner_of_login(self, *, stop_reason: str, inquiry_id: str | None = None) -> None:
        """Mail the one address that repairs sessions, at most once per run.

        Owner rule (2026-10-01): only ``linan229@qq.com``. The message never
        carries page text or a credential -- the site verdicts the run already
        rendered are the whole payload, plus what to do about them. Delivery is
        best effort: a mail that cannot be sent must never change what the run
        did or leave the operator waiting.
        """

        with self._lock:
            run_id = self._run_id or ""
            if self._login_alert_run_id == run_id:
                return
            self._login_alert_run_id = run_id
        try:
            transport = QQSMTPTransport(
                config=QQSMTPConfig(sender_address=_LOGIN_ALERT_SENDER)
            )
            body = _login_alert_body(stop_reason)
            if inquiry_id is not None and self._store is not None:
                item = self._store.get_by_inquiry_id(inquiry_id)
                body += (f"\n订单识别码：{inquiry_id}\n型号：{item.mpn}\n"
                         f"品牌：{item.resolved_brand or item.brand}\n数量：{item.quantity}\n"
                         "阶段：网站登录/调研；本次未完成采购提交。")
            result = transport.send_operator_alert(
                recipient=NotificationRecipient("owner", _LOGIN_ALERT_RECIPIENT),
                subject="【INSO】询价已停止：需要重新登录网站",
                text_body=body,
            )
        except Exception as exc:  # noqa: BLE001 - fail closed at runtime boundary
            log.warning("the login alert could not be delivered (%s)", type(exc).__name__)
            self._append_log("ERROR", "登录提醒邮件发送失败；请检查邮件配置与网络")
            return
        if result.outcome is DeliveryOutcome.SENT:
            self._append_log(
                "WARNING", f"已发送登录提醒邮件至 {_LOGIN_ALERT_RECIPIENT}"
            )
        else:
            self._append_log(
                "ERROR",
                "登录提醒邮件未能送达；请检查邮件配置与网络",
            )

    def _refresh(self):
        if not self._store:
            return
        self._refresh_history()
        items = {i.inquiry_id: i for i in self._store.all_items()}
        ids = [i for i in self._inquiries if i in items]
        history_by_id = {order.inquiry_id: order for order in self._history}
        results = []
        for key in ids:
            item = items[key]
            historical = history_by_id.get(key)
            status = {
                WorkflowStatus.COMPLETED: (
                    OrderStatus.PARTIAL
                    if item.research_status == "PARTIAL_SUCCESS"
                    else OrderStatus.COMPLETED
                ),
                WorkflowStatus.MANUAL_REVIEW: OrderStatus.ERROR,
                WorkflowStatus.FAILED: OrderStatus.ERROR,
            }.get(item.status, OrderStatus.PENDING)
            if key in self._manual_inquiries:
                status = OrderStatus.ERROR
            results.append(
                Order(
                    key,
                    historical.model if historical else item.mpn,
                    historical.brand if historical else item.brand,
                    historical.quantity if historical else item.quantity,
                    historical.stock_label if historical else "待验证",
                    historical.min_reference_price if historical else None,
                    historical.total_price if historical else None,
                    status,
                    historical.sources if historical else (),
                    historical.remark if historical else (item.last_error or ""),
                    self._run_id or "",
                    historical.importance if historical else item.importance_raw,
                    historical.processed_at if historical else None,
                )
            )
        with self._lock:
            self._results = tuple(results) + tuple(self._v13_unbound.values())

    def _refresh_history(self, *, force=False):
        if not self._excel:
            return
        try:
            stat = self._excel.stat() if self._excel.is_file() else None
            fingerprint = (stat.st_mtime_ns, stat.st_size) if stat else None
        except OSError:
            fingerprint = None
        with self._lock:
            if not force and fingerprint == self._history_fingerprint:
                return
        try:
            records = ResearchExcelOutput(self._excel).read_history()
        except Exception as exc:  # noqa: BLE001 - history display must not stop runtime
            log.warning("Research history unavailable (%s)", type(exc).__name__)
            with self._lock:
                self._history_fingerprint = fingerprint
            return
        status_map = {
            "SUCCESS": OrderStatus.COMPLETED,
            "PARTIAL_SUCCESS": OrderStatus.PARTIAL,
            "EXCEPTION": OrderStatus.ERROR,
            "MANUAL_REVIEW_REQUIRED": OrderStatus.ERROR,
            "RETRYABLE_FAILURE": OrderStatus.ERROR,
        }
        orders = tuple(
            Order(
                inquiry_id=record.inquiry_id,
                model=record.mpn or "",
                brand=record.brand,
                quantity=_integer(record.quantity, 0),
                stock_label=record.stock_label or "待验证",
                min_reference_price=_decimal(record.market_reference),
                total_price=_decimal(record.estimated_total),
                status=status_map.get(record.research_status, OrderStatus.UNKNOWN),
                sources=tuple(SourceDetail(name, value) for name, value in record.source_values),
                remark=record.remarks or "",
                importance=record.importance_raw,
                processed_at=record.processed_at,
            )
            for record in records
        )
        with self._lock:
            self._history = orders
            self._history_fingerprint = fingerprint

    def get_status(self):
        with self._lock:
            items = self._store.all_items() if self._store else ()
            known_ids = {item.inquiry_id for item in items}
            return RunSession(
                self._run_id,
                self._state,
                self._started,
                self._stopped,
                len(self._poll_inquiries),
                sum(inquiry in self._poll_quotation_completed or
                    (inquiry in known_ids and self._business_completed(inquiry))
                    for inquiry in self._poll_inquiries),
                int(self._active_inso_inquiry is not None or self._manual_busy),
                sum(
                    i.status in (WorkflowStatus.QUEUED, WorkflowStatus.RETRY_WAIT)
                    for i in items
                ),
                self._next_poll_at if self._state in {RunState.RUNNING, RunState.QUOTATION_RUNNING} else None,
                self._row_cooldown_until,
                new_orders=self._dashboard_counts.new_orders if self._dashboard_counts else None,
                awaiting_quotation=self._dashboard_counts.awaiting_quotation if self._dashboard_counts else None,
                overdue_quotation=self._dashboard_counts.overdue_quotation if self._dashboard_counts else None,
            )

    def _wait_between_rows(self, seconds):
        """Expose the existing interruptible row wait without changing its policy."""
        with self._lock:
            self._row_cooldown_until = utc_now() + timedelta(seconds=seconds)
        try:
            return self._stop.wait(seconds)
        finally:
            with self._lock:
                self._row_cooldown_until = None

    def _business_completed(self, inquiry_id):
        if self._v12_store is None:
            return False
        try:
            state = self._v12_store.business_state(inquiry_id)
        except KeyError:
            return False
        if state.value == "PURCHASE_EXCEPTION":
            try:
                if self._v12_store.purchase_state(inquiry_id) in {
                    PurchaseOutcome.UNKNOWN_WRITE_OUTCOME, PurchaseOutcome.MANUAL_REVIEW,
                    PurchaseOutcome.READ_ONLY_RECONCILIATION_REQUIRED,
                }:
                    return False
            except KeyError:
                pass
        return state.value in {"PURCHASE_RECORDED", "DUPLICATE_STOPPED", "INVALID_INPUT_SKIPPED",
            "SUBMIT_UNCONFIRMED", "STATUS_WRITE_PENDING", "RESEARCH_FAILED", "PURCHASE_EXCEPTION",
            "SOURCE_CHANGED", "HUMAN_COMPLETED"}

    def get_current_run_results(self):
        with self._lock:
            return self._results

    def get_result_history(self):
        with self._lock:
            return tuple(replace(order, **self._source_overrides[order.inquiry_id])
                if order.inquiry_id in self._source_overrides else order for order in self._history)

    def get_v12_order_state(self, inquiry_id):
        if inquiry_id in self._v13_states:
            return self._v13_states[inquiry_id]
        if self._v12_store is None:
            preview = self._startup_interruptions.get(inquiry_id)
            return preview[0] if preview else None
        try:
            return read_v12_order_state(self._v12_store, inquiry_id)
        except KeyError:
            return None

    def _idle_login_tick(self, *, now):
        """Optional maintenance at the serial poll boundary; never a business fault."""
        if not self._v13_enabled:
            return
        paused = self._combined is not None and self._combined.v12_paused
        if self._state is not RunState.RUNNING or paused or self._immediate_stop_requested():
            self._idle_empty_polls = 0
            self._idle_login_since = now
            return
        if self._v12_composition.coordinator.pending_rows_seen:
            self._idle_empty_polls = 0
            self._idle_login_since = now
            return
        browser = getattr(self._browser_handle, "browser", None)
        if browser is None and self._keepalive_protected_targets:
            # Reuse the canonical sweep attach path to resolve Owner-closed targets.
            try:
                self._run_login_sweep(background=True, check_only=True)
            except Exception:  # noqa: BLE001 - optional maintenance/page check cannot block workflow
                self._append_log("WARNING", "保活人工页面状态暂不可确认，继续保留。")
            self._idle_empty_polls = 0
            self._idle_login_since = now
            return
        try:
            protected = bool(self._live_keepalive_pages(browser)) if self._keepalive_protected_targets else False
        except Exception:  # noqa: BLE001 - uncertainty retains the human boundary
            protected = True
        if protected:
            # Owner has an open repair boundary. Do not accumulate another failed sweep.
            self._idle_empty_polls = 0
            self._idle_login_since = now
            return
        self._idle_empty_polls += 1
        if self._idle_empty_polls < 2 or now - self._idle_login_since < timedelta(minutes=30):
            return
        self._idle_empty_polls = 0
        self._idle_login_since = now
        self._append_log("INFO", "连续空闲30分钟，开始后台网站登录保活。")
        try:
            results = tuple(self._run_login_sweep(background=True))
            if (not results and not self._immediate_stop_requested()) or any(
                    not isinstance(r, SiteLoginResult) or not isinstance(r.outcome, SiteLoginOutcome)
                    or not isinstance(r.site, str) for r in results):
                raise ValueError("idle login result unavailable")
        except Exception:  # noqa: BLE001 - optional maintenance cannot stop business
            results = (SiteLoginResult("登录保活", SiteLoginOutcome.UNAVAILABLE),)
        for result in results:
            if result.outcome in {SiteLoginOutcome.SIGNED_IN, SiteLoginOutcome.ALREADY_SIGNED_IN}:
                continue
            self._append_log("WARNING", f"网站登录保活异常：{result.site}；{result.outcome.value}")
            try:
                recipients = (NotificationRecipient("owner", "linan229@qq.com"),)
                command_id = f"idle-login:{self._cycle_id}:{result.site}:{result.outcome.value}"
                if not self._v12_store.notification_already_created(
                        command_id, None, NotificationKind.PURCHASE_EXCEPTION, recipients):
                    self._v12_store.enqueue_notification(NotificationCommand(
                        command_id, None, NotificationKind.PURCHASE_EXCEPTION, recipients,
                        "网站登录保活异常",
                        f"网站：{result.site}\n结果：{result.outcome.value}\n请人工检查网站登录；询价轮询继续。",
                        None, now))
            except Exception:  # noqa: BLE001 - log maintenance/outbox failure without changing business state
                self._append_log("WARNING", "登录保活异常提醒未入队，请检查通知台账。")
        self._idle_login_since = utc_now()  # New idle window begins after the sweep finishes.

    def start_login_all_sites(self) -> None:
        """Walk every site once, in one background thread, and report back.

        Non-blocking on purpose: the dashboard button must stay responsive
        while a sweep takes minutes. A sweep and a run are never allowed to
        overlap -- both drive the same Chrome, and the sweep is meant to be the
        thing that happens *before* 开始询价.
        """

        with self._lock:
            if self._closed:
                return
            if self._login_all_thread is not None and self._login_all_thread.is_alive():
                return
            if self._state in (RunState.RUNNING, RunState.QUOTATION_RUNNING, RunState.STOPPING_AFTER_CYCLE):
                self._append_log(
                    "WARNING", "正在询价，请先等待本轮结束再执行一键登录"
                )
                return
            self._login_all_thread = threading.Thread(
                target=self._login_all_worker,
                name="production-login-all-sites",
                daemon=True,
            )
            thread = self._login_all_thread
        self._append_log("INFO", "开始依次登录所有网站…")
        thread.start()

    def login_all_running(self) -> bool:
        with self._lock:
            thread = self._login_all_thread
        return thread is not None and thread.is_alive()

    def get_login_all_report(self) -> SiteLoginReport | None:
        with self._lock:
            return self._login_all_report

    def on_login_all(self, callback) -> None:
        with self._lock:
            if callback is None:
                self._login_all_callbacks.clear()
            elif callback not in self._login_all_callbacks:
                self._login_all_callbacks.append(callback)

    def _login_all_worker(self) -> None:
        started_at = utc_now()
        try:
            results = self._run_login_sweep()
        except Exception as exc:  # noqa: BLE001 - always return a visible verdict
            log_step("login-sweep-worker", cause=exc)
            results = (SiteLoginResult("登录检查", SiteLoginOutcome.UNAVAILABLE,
                                       "登录检查未完成，请在 Chrome 检查后重试"),)
        self._idle_empty_polls = 0
        self._idle_login_since = utc_now()
        report = SiteLoginReport(tuple(results), started_at, utc_now())
        with self._lock:
            self._login_all_report = report
            callbacks = tuple(self._login_all_callbacks)
        for callback in callbacks:
            try:
                callback(report)
            except Exception as exc:  # noqa: BLE001 - fail closed at runtime boundary
                log.debug("login sweep callback failed (%s)", type(exc).__name__)

    def _run_login_sweep(self, *, background=False, check_only=False) -> tuple[SiteLoginResult, ...]:
        """Attach the approved CDP browser, sweep it, then give it back."""

        try:
            production_config = json.loads(
                self.production_path.read_text(encoding="utf-8")
            )
            research_config = load_runtime_config(self.config_path)
        except Exception as exc:  # noqa: BLE001 - fail closed at runtime boundary
            log_step("login-sweep-config", cause=exc)
            return (
                SiteLoginResult(
                    "本地配置",
                    SiteLoginOutcome.UNAVAILABLE,
                    "本地运行配置不可用，无法开始登录",
                ),
            )
        probe = self.cdp_probe or probe_loopback_endpoint
        try:
            borrowed = background and self._browser_handle is not None
            handle = self._browser_handle if borrowed else self._browser_acquirer(
                research_config.cdp.cdp_url,
                self.root,
                production_config,
                probe=probe,
            )
        except Exception as exc:  # noqa: BLE001 - fail closed at runtime boundary
            log_step("login-sweep-cdp", cause=exc)
            return (
                SiteLoginResult(
                    "浏览器（CDP）",
                    SiteLoginOutcome.UNAVAILABLE,
                    ("Chrome 已启动，但会话初始化超时；标签页可能无响应。"
                     "请先保留未保存内容，恢复或关闭无响应标签页后重试"
                     if getattr(exc, "reason_code", None) == "CDP_SESSION_INITIALIZATION_TIMEOUT"
                     else "无法连接或启动已授权的 Chrome，请先打开该浏览器"),
                ),
            )
        try:
            if check_only:
                self._park_browser(handle.browser)
                return ()
            if background and self._live_keepalive_pages(handle.browser):
                self._park_browser(handle.browser)
                return ()
            existing_pages = tuple(handle.browser.contexts[0].pages) if background else ()
            if background:
                self._protect_keepalive_pages(existing_pages)
            options = ({"present_failures": False,
                        "stop_requested": self._immediate_stop_requested,
                        "wait": self._stop.wait} if background else {})
            results = sweep_sites(
                handle.browser,
                bom_ai=research_config.bom_ai,
                timeout_ms=research_config.browser.timeout_ms,
                **options,
            )
            if any(r.outcome not in {
                    SiteLoginOutcome.SIGNED_IN, SiteLoginOutcome.ALREADY_SIGNED_IN} for r in results):
                self._protect_keepalive_pages(handle.browser.contexts[0].pages)
            if background and not self._immediate_stop_requested():
                context, = handle.browser.contexts
                if not any(not p.is_closed() and p.url == "about:blank" for p in context.pages):
                    new_background_page(handle.browser, context, timeout_ms=research_config.browser.timeout_ms)
                if all(r.outcome in {SiteLoginOutcome.SIGNED_IN,
                                     SiteLoginOutcome.ALREADY_SIGNED_IN} for r in results) and results and not any(
                        not p.is_closed() and p.url != "about:blank" for p in existing_pages):
                    self._park_browser(handle.browser)
                # Failed or pre-existing nonblank pages are retained for human review.
            return results
        except SiteSweepError as exc:
            log_step("login-sweep-start", cause=exc)
            return (
                SiteLoginResult(
                    "浏览器（CDP）",
                    SiteLoginOutcome.UNAVAILABLE,
                    "浏览器里没有可用的会话上下文",
                ),
            )
        finally:
            if not borrowed:
                self._release_sweep_browser(handle)

    @staticmethod
    def _release_sweep_browser(handle: BrowserHandle) -> None:
        """Detach the sweep client; never stop the protected session browser."""

        try:
            # Even a browser launched by this sweep contains the manual-login
            # pages and persistent session. Only detach our client.
            handle.disconnect()
        except Exception as exc:  # noqa: BLE001 - fail closed at runtime boundary
            log.warning("the login sweep browser could not be released (%s)", type(exc).__name__)

    def reconcile_v12_save(self, inquiry_id: str, *, at: datetime):
        """Run only the existing read-only reconciliation contract.

        Production composition must supply the verified read-only adapter; a
        missing composition is not silently replaced with an absence guess.
        """

        if self._v12_store is None:
            raise V12DatabaseError("V1.2 persistence is unavailable")
        if self._v12_composition is None:
            raise V12DatabaseError("V1.2 read-only save reconciler is unavailable")
        reconciler = self._v12_composition.save_reconciler
        return self._v12_store.reconcile_unknown_save(
            inquiry_id, reconciler, at=at
        )

    def get_health(self):
        return self._health

    def get_logs(self):
        with self._lock:
            return tuple(self._logs)

    def get_diagnostics(self):
        with self._lock:
            return DiagnosticSnapshot(
                self._run_id,
                max(0, (utc_now() - self._started).total_seconds())
                if self._started
                else 0,
                0,
                "running" if self._thread and self._thread.is_alive() else "stopped",
                self._last_poll,
            )

    def open_excel(self):
        if self._excel and self._excel.exists():
            os.startfile(self._excel)

    def open_results_dir(self):
        path = self._excel.parent if self._excel else self.root / "runtime"
        if sys.platform == "win32":
            os.startfile(path)
        else:
            subprocess.Popen(["xdg-open", str(path)])

    def on_status_change(self, callback):
        with self._lock:
            if callback is None:
                self._status_callbacks.clear()
            elif callback not in self._status_callbacks:
                self._status_callbacks.append(callback)

    def on_log(self, callback):
        with self._lock:
            if callback is None:
                self._log_callbacks.clear()
            elif callback not in self._log_callbacks:
                self._log_callbacks.append(callback)

    def shutdown(self):
        with self._lock:
            if self._closed:
                return
            self._closed = True
            with self._poll_gate:
                self._stop.set()
            thread = self._thread
            login_thread = self._login_all_thread
        if thread and thread is not threading.current_thread():
            thread.join()
        if login_thread and login_thread is not threading.current_thread():
            login_thread.join()
        with self._lock:
            self._status_callbacks.clear()
            self._log_callbacks.clear()
            self._login_all_callbacks.clear()

    def _notify(self):
        status = self.get_status()
        for cb in tuple(self._status_callbacks):
            cb(status)

    def _append_log(self, level, message):
        entry = LogEntry(utc_now(), level, message)
        with self._lock:
            self._logs = (self._logs + [entry])[-1000:]
            callbacks = tuple(self._log_callbacks)
        for cb in callbacks:
            cb(entry)

    def _set_health(self, statuses, overall):
        self._health = HealthReport(
            tuple(
                HealthItem(n, s)
                for n, s in zip(self._components(), statuses, strict=True)
            ),
            overall,
        )


def _integer(value, fallback):
    try:
        return int(value)
    except (ValueError, TypeError):
        return fallback if isinstance(fallback, int) else 0


def _decimal(value):
    if value is None:
        return None
    text = str(value).strip().splitlines()[0].replace("¥", "").replace(",", "")
    try:
        return Decimal(text) if text else None
    except InvalidOperation:
        return None


def _open_v12_store_if_migrated(database_path):
    try:
        with sqlite3.connect(database_path) as connection:
            version = int(connection.execute("PRAGMA user_version").fetchone()[0])
        return V12Store(database_path) if version == V12_SCHEMA_VERSION else None
    except (OSError, sqlite3.Error, ValueError, V12DatabaseError):
        return None
