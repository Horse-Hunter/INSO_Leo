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
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from src.core.app_paths import app_root, resolve_app_path, runtime_config_path
from src.gui.contracts import (
    DiagnosticSnapshot,
    GuiBackend,
    HealthItem,
    HealthReport,
    LogEntry,
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
from src.research.credentials import CoreLoginBridge
from src.research.excel_output import ResearchExcelOutput
from src.research.inso_history import INSO_SITE_ID
from src.research.runtime import (
    ResearchRuntimeConfigError,
    assess_readiness,
    build_research_service,
    load_runtime_config,
    probe_loopback_endpoint,
)
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
from src.workflow.v12_contracts import (
    DeliveryOutcome,
    EventType,
    NotificationRecipient,
    PurchaseDraftResult,
    PurchaseOutcome,
    ReasonCode,
)
from src.workflow.v12_duplicate import InsoDuplicateHistoryChecker
from src.workflow.v12_smtp_transport import QQSMTPConfig, QQSMTPTransport
from src.workflow.v12_store import (
    V12_SCHEMA_VERSION,
    V12DatabaseError,
    V12Store,
    migrate_v12,
)

from .browser_bootstrap import BrowserBootstrapError, BrowserHandle, acquire_cdp_browser
from .diagnostics import log_step
from .inso_session import (
    InsoAuthenticationError,
    InsoResearchSession,
    InsoSessionGuard,
    InsoSessionOutcome,
    attach_inso_research_session,
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
from .v12_gui import read_v12_order_state

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
        remarks = (result.remarks or "").casefold()
        if any(marker in remarks for marker in self._HUMAN_ACTION_MARKERS):
            self.manual_review(item.inquiry_id, result.remarks or "")
            # Do not let a partial result route into notification/purchase or
            # consume this inquiry. Existing queue release makes it resumable.
            raise ResearchPreparationError("Research requires session repair")
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
                access.close_owned_operation_tab()

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
                if not writer.dismiss_order_surface():
                    log.warning(
                        "the INSO 采购临时询价 window did not close after this order"
                    )
                    log_step("surface-left-open")

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
        except Exception as exc:  # noqa: BLE001 - never retry an irreversible action
            log_step("save-and-send-unconfirmed", cause=exc)
            if self._store.purchase_state(command.inquiry_id) is PurchaseOutcome.AI_RECOGNIZED:
                # A pre-dispatch failure is held for review too, never retried.
                self._store.begin_save_dispatch(
                    command.inquiry_id, at=submitted_at, save_and_send=True,
                )
        writer.dismiss_order_surface()
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

    The V1.2 flow checks for a repeat *before* Research, but the shared INSO
    session is attached only when the Research worker prepares. Without this the
    first duplicate lookup of a run reaches INSO before that session exists, so
    every check downgraded to ``DUPLICATE_LOOKUP_UNAVAILABLE``. Preparation is
    idempotent and gated; a preparation failure falls through so the checker
    keeps owning its fail-closed downgrade and the Research path still surfaces
    the manual-handling requirement.
    """

    def __init__(self, checker, prepare=None, *, begin_inquiry=None) -> None:
        self._checker = checker
        self._prepare = prepare
        self._begin_inquiry = begin_inquiry

    def check(self, inquiry_id, mpn, quantity, *, at):
        if self._begin_inquiry is not None:
            self._begin_inquiry(inquiry_id)
        if self._prepare is not None:
            try:
                self._prepare()
            except Exception:
                # The checker owns the fail-closed downgrade.
                log.warning(
                    "duplicate-check INSO session preparation failed",
                    exc_info=True,
                )
        return self._checker.check(inquiry_id, mpn, quantity, at=at)


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
        self._inquiries = []
        self._results = ()
        self._history = ()
        self._history_fingerprint = None
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
                or self._state in (RunState.RUNNING, RunState.STOPPING_AFTER_CYCLE)
                or (self._thread is not None and self._thread.is_alive())
                or (self._login_all_thread is not None and self._login_all_thread.is_alive())
            ):
                return
            self._run_id = "run_" + str(uuid.uuid4())
            self._started = utc_now()
            self._stopped = None
            self._inquiries = []
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
            if self._state is RunState.RUNNING:
                self._state = RunState.STOPPING_AFTER_CYCLE
                self._next_poll_at = None
                with self._poll_gate:
                    self._drain_due_on_stop.set()
                    self._stop.set()
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
            status_writer = None

            def get_status_writer():
                nonlocal status_writer
                if status_writer is None:
                    status_writer = GoogleSheetsPurchaseStatusWriter(
                        build_read_write_google_sheets_service(client, allow_interactive=False)
                    )
                return status_writer

            self._purchase_completion = PurchaseCompletionActions(
                workflow_store=self._store, v12_store=self._v12_store,
                reader=reader, writer_factory=get_status_writer,
            )
            # An item can only be RESEARCHING while the process that claimed it
            # is alive: the claim and the result write share one worker call. A
            # row still in that state therefore belongs to an interrupted run,
            # and claim_due (which only takes QUEUED/RETRY_WAIT) would never look
            # at it again, stalling the inquiry forever. Research only reads, so
            # releasing the claim is the safe recovery. This runs before any
            # worker starts.
            requeued = self._store.requeue_interrupted_research(now=utc_now())
            if requeued:
                self._append_log(
                    "warning",
                    f"released {requeued} interrupted Research claim(s) back to the queue",
                )
            research = build_research_service(
                rc,
                inso_operation_access=self._inso_operation_access,
                playwright_provider=self._research_playwright_provider,
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
                )
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
                            if self._v12_composition is None:
                                raise V12DatabaseError("V1.2 production composition is unavailable")
                            # V1.2 owns the poll-to-research handoff.  It still
                            # reads through the same Sheets adapter, but never
                            # falls back to the V1.1-only runtime path.
                            for worksheet in worksheets:
                                if self._immediate_stop_requested():
                                    return
                                cycle_results = self._v12_composition.coordinator.poll_and_process(
                                    reader, worksheet, now=self._last_poll
                                )
                                for flow_result in cycle_results:
                                    self._seen(flow_result.inquiry_id)
                            if self._immediate_stop_requested():
                                return
                            self._purchase_completion.retry_saved_statuses(at=utc_now())
                            self._v12_composition.coordinator.run_notifications(
                                now=utc_now()
                            )
                            with self._lock:
                                if self._state is RunState.RUNNING:
                                    self._next_poll_at = utc_now() + runtime.poll_interval
                            browser_state = "已连接" if self._research_ready else "待命"
                            self._set_health(("正常", browser_state, "正常", "正常"), "正常")
                        finally:
                            self._close_inso_order_tab()
                            self._poll_idle.set()
                        if self._stop.wait(runtime.poll_interval.total_seconds()):
                            return
                except Exception as exc:  # noqa: BLE001 - fail closed at runtime boundary
                    self._runtime_error(exc)
                finally:
                    BrowserHandle.drain_deferred_stops()

            def worker_loop():
                try:
                    while True:
                        if self._stop.is_set():
                            return
                        BrowserHandle.drain_deferred_stops()
                        self._refresh()
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
                if self._state is not RunState.MANUAL_REVIEW:
                    self._state = RunState.STOPPED
                self._stopped = utc_now()
                self._notify()

    def _seen(self, inquiry):
        with self._lock:
            if inquiry not in self._inquiries:
                self._inquiries.append(inquiry)

    def _begin_inso_inquiry(self, inquiry_id):
        self._seen(inquiry_id)
        if self._active_inso_inquiry != inquiry_id:
            self._close_inso_order_tab()
            self._active_inso_inquiry = inquiry_id

    def _close_inso_order_tab(self):
        session = self._inso_session
        if session is not None:
            close = getattr(session, "close_owned_operation_tab", None)
            if callable(close):
                close()
        self._inso_session = None
        self._inso_guard = None
        self._research_ready = False
        self._active_inso_inquiry = None

    def _complete_inquiry(self, result):
        """Settle each row before starting the next; never defer to batch drain."""
        try:
            self._seen(result.inquiry_id)
            settled = self._purchase_completion.process(result, at=utc_now())
            self._v12_composition.coordinator.run_notifications(now=utc_now())
            if settled is False or not self._v12_store.notifications_settled(result.inquiry_id):
                with self._lock:
                    self._state = RunState.MANUAL_REVIEW
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
                self._open_research_session(research_config, production_config)
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
        if session is not None:
            try:
                self._research_cycle_drained = True
                session.close_after_drain()
            except Exception as exc:  # noqa: BLE001 - cleanup boundary
                log.warning("Unready INSO session shutdown failed (%s)", type(exc).__name__)
        if handle is not None and session is None:
            try:
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
        if session is not None:
            try:
                session.close_after_drain()
            except Exception as exc:  # noqa: BLE001 - cleanup boundary
                log.warning("INSO session shutdown failed (%s)", type(exc).__name__)
        if handle is not None and session is None:
            try:
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
            self._state = RunState.MANUAL_REVIEW
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
        cause = exc
        while cause is not None:
            if isinstance(cause, InsoAuthenticationError):
                self._alert_owner_of_login(stop_reason="INSO：登录不可用")
                break
            cause = cause.__cause__

    def _preparation_error(self, exc: ResearchPreparationError) -> None:
        """Fail closed for CDP setup without consuming a Research retry."""

        self._runtime_error(exc)
        self._release_idle_browser(force=True)

    def _manual_review(self, inquiry_id, remarks: str = ""):
        with self._lock:
            self._manual_inquiries.add(inquiry_id)
            self._state = RunState.MANUAL_REVIEW
            self._next_poll_at = None
            self._drain_due_on_stop.clear()
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
        # The run is already stopped above, so the Owner's screen says what
        # happened before the mail round trip is attempted. The mail is what
        # tells them while they are away from the machine.
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
            self._results = tuple(results)

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
            return RunSession(
                self._run_id,
                self._state,
                self._started,
                self._stopped,
                len(self._inquiries),
                sum(
                    i.inquiry_id in self._inquiries
                    and self._business_completed(i.inquiry_id)
                    for i in items
                ),
                int(self._active_inso_inquiry is not None),
                sum(
                    i.status in (WorkflowStatus.QUEUED, WorkflowStatus.RETRY_WAIT)
                    for i in items
                ),
                self._next_poll_at if self._state is RunState.RUNNING else None,
            )

    def _business_completed(self, inquiry_id):
        if self._v12_store is None:
            return False
        try:
            state = self._v12_store.business_state(inquiry_id)
        except KeyError:
            return False
        return state.value in {"PURCHASE_RECORDED", "DUPLICATE_STOPPED", "INVALID_INPUT_SKIPPED"}

    def get_current_run_results(self):
        with self._lock:
            return self._results

    def get_result_history(self):
        with self._lock:
            return self._history

    def get_v12_order_state(self, inquiry_id):
        if self._v12_store is None:
            return None
        try:
            return read_v12_order_state(self._v12_store, inquiry_id)
        except KeyError:
            return None

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
            if self._state in (RunState.RUNNING, RunState.STOPPING_AFTER_CYCLE):
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
        report = SiteLoginReport(tuple(results), started_at, utc_now())
        with self._lock:
            self._login_all_report = report
            callbacks = tuple(self._login_all_callbacks)
        for callback in callbacks:
            try:
                callback(report)
            except Exception as exc:  # noqa: BLE001 - fail closed at runtime boundary
                log.debug("login sweep callback failed (%s)", type(exc).__name__)

    def _run_login_sweep(self) -> tuple[SiteLoginResult, ...]:
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
            handle = self._browser_acquirer(
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
                    "无法连接或启动已授权的 Chrome，请先打开该浏览器",
                ),
            )
        try:
            return sweep_sites(
                handle.browser,
                bom_ai=research_config.bom_ai,
                timeout_ms=research_config.browser.timeout_ms,
            )
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
