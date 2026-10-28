"""Production GUI adapter over the canonical Workflow and Research runtimes."""

from __future__ import annotations

import json
import logging
import os
import re
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
    V12BusinessLabel,
    V12ReasonCode,
    WorkbenchSnapshot,
)
from src.gui.state import utc_now
from src.inso.duplicate_history import InsoDuplicateHistoryReader
from src.inso.purchase_writer import InsoPurchaseWriter, PlaywrightParentProductFields
from src.inso.session import SecurityViolation
from src.inso.write_safety import OwnerAuthorizedSaveAndSendGate
from src.launcher.purchase_completion import PurchaseCompletionActions
from src.research import ResearchInput, ResearchResult
from src.research.cdp_pages import (
    PageResourceAdmission,
    PageTargetCleanupError,
    bind_page_admission,
    new_background_page,
)
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
from src.research.site_login import AUTH_SESSION_STOP_REASONS
from src.research.source_contracts import ResearchSource, SourceOutcome
from src.sheets import WorksheetIdentity
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
from src.workflow.service import OrderResourceOwnershipError
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
from src.workflow.v13_price_store import ProcurementPriceStore
from src.workflow.v13_quotation import V13QuotationCycle, V13Stopped

from .browser_bootstrap import (
    BrowserBootstrapError,
    BrowserHandle,
    acquire_cdp_browser,
    park_shared_cdp,
)
from .diagnostics import log_step
from .google_quote_update import build_v13_quotation_updater
from .google_web import build_google_web_service
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
    notify_refresh_uncertain,
    notify_runtime_fault,
    notify_website_issue,
    quotation_gui,
    quotation_location,
)
from .v13_quotation import (
    quotation_operation_scope,
    quotation_operations,
    settle_quotation_operations,
)

log = logging.getLogger(__name__)

#: The one mailbox an operational login alert goes to. Owner rule
#: (2026-10-01): the alert is for the person who can log back in, and for nobody
#: else -- it must not be added to the order-notification recipient list.
_LOGIN_ALERT_SENDER = "1069599116@qq.com"
_LOGIN_ALERT_RECIPIENT = "linan229@qq.com"

# Shared by the INSO query boundary and final source observer. Authenticated
# READ_EMPTY/READ_UNAVAILABLE are read failures, not authentication failures.
_INSO_AUTH_STOP_CODES = AUTH_SESSION_STOP_REASONS


class ProductionConfigurationError(RuntimeError):
    """Safe startup failure for missing local production configuration."""


def _login_alert_body(stop_reason: str) -> str:
    """The alert's plain text: what stopped, and what to do about it."""

    # Keep only closed status hints; never copy raw source remarks.
    if "台账" in stop_reason or stop_reason == "WORKFLOW_LEDGER_UNAVAILABLE":
        return "情况：本机订单台账不可用，相关业务已暂停。\n处理：请检查本机台账和运行提示；不要重发采购单。"
    if stop_reason in {"V12_INTERNAL_FAILURE", "V13_INTERNAL_FAILURE", "QUOTE_INPUT_CONFIGURATION_REQUIRED",
                       "SHEETS_SCHEMA_UNAVAILABLE"}:
        return "情况：本机配置、表格结构或处理结果尚未确认，相关业务已暂停。\n处理：请核对程序提示；不能据此判断网站登录失效。"
    if any(token in stop_reason for token in ("全局", "基础设施", "台账", "GLOBAL_STOP")):
        return ("情况：询价因运行异常停止。\n"
            "处理：检查网络、授权和程序订单详情，确认后点击“开始询价”；不要直接重发采购单。")
    labels = (("IC.NET", "IC.net"), ("IC_NET", "IC.net"), ("INSO", "INSO"),
        ("英索", "INSO"), ("立创", "立创"), ("LCSC", "立创"),
        ("华强", "华强"), ("HQEW", "华强"), ("FINDCHIPS", "Findchips"), ("BOM.AI", "Bom.Ai"))
    sites = list(dict.fromkeys(label for token, label in labels if token in stop_reason.upper()))
    hint = ("、".join(sites) or "网站") + "需要重新登录或人工验证。"
    return (f"情况：询价已停止，{hint}\n"
        "处理：在程序使用的Chrome中完成登录或验证，再点击“开始询价”。\n"
        "也可点击“一键登录所有网站”检查登录状态。")



class _Observer:
    """Track actual Research attempts and surface interactive challenges."""

    #: Every wording a source uses when what failed is the *session*, not the
    #: result. Login failures propagate to the canonical recovery boundary;
    #: short outages retain polling and never become a missing-price result.
    #: These are exactly the
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

    def _prepare(self, item):
        self.seen(item.inquiry_id)
        if self.prepare is not None:
            try:
                self.prepare()
            except BrowserBootstrapError as exc:
                raise ResearchPreparationError(
                    "CDP browser requires manual handling"
                ) from exc
    def begin_detailed(self, item, *, now=None):
        self._prepare(item)
        return self.service.begin_detailed(item, now=now)

    def execute(self, item: ResearchInput) -> ResearchResult:
        self._prepare(item)
        return self.review_result(self.service.execute(item))

    def review_result(self, result):
        for detail in (result.remarks or "").split("；"):
            remarks = detail.casefold()
            if not any(marker in remarks for marker in self._HUMAN_ACTION_MARKERS):
                continue
            self.manual_review(result.inquiry_id, detail)
            # Do not let a partial result route into notification/purchase or
            # consume this inquiry. Existing queue release makes it resumable.
            if "ic.net" in remarks or "inso" in remarks or "英索" in remarks:
                raise V12Fault(FaultScope.GLOBAL_STOP if "inso" in remarks or "英索" in remarks
                    else FaultScope.V12_PAUSE, "INSO_AUTHENTICATION_REQUIRED"
                    if "inso" in remarks or "英索" in remarks else "IC_NET_UNAVAILABLE")
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
                 store: V12Store | None = None, observe=None) -> None:
        self._access = access
        self._session_guard_factory = session_guard_factory
        self._login_problem = login_problem
        self._store = store
        self._observe = observe

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
        if self._observe is not None:
            self._observe("inquiry", "采购草稿与提交安全核验", site="INSO", order_ref=command.inquiry_id)
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
            self._login_problem(command.inquiry_id, "INSO：" + (status.reason_code or "登录不可用"))
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
    retries after interruptible waits; authentication failures preserve their
    page and propagate to the shared website-recovery policy.
    """

    def __init__(self, checker, prepare=None, *, begin_inquiry=None, reset=None, wait=None,
                 on_success=lambda: None) -> None:
        self._checker = checker
        self._prepare = prepare
        self._begin_inquiry = begin_inquiry
        self._reset = reset
        self._wait = wait
        self._on_success = on_success

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
            except (sqlite3.Error, V12DatabaseError, V12Fault, InsoAuthenticationError):
                raise
            except Exception:
                if self._wait is None:
                    raise
                return None

        if self._wait is None:
            prepare()
            return operation()
        result = run_inso_query(
            operation, prepare=prepare,
            succeeded=lambda result: result is not None and result.outcome.value == "CONFIRMED",
            reset=self._reset or (lambda: None), wait=self._wait,
        )
        self._on_success()
        return result


def _website_failure(exc):
    """Identify a failed dependency without treating local data errors as outages."""
    from .market_continuation import MarketContinuationFault
    if (isinstance(exc, MarketContinuationFault) and exc.source is not None
            and exc.fault.scope.value in {"site_defer", "failed"}):
        return {"ic.net": "IC.net", "findchips": "Findchips", "hqew": "华强",
                "lcsc": "立创", "bom.ai": "正能量", "inso": "INSO"}.get(exc.source.value)
    chain, seen = [], set()
    while exc is not None and id(exc) not in seen:
        seen.add(id(exc))
        chain.append(exc)
        exc = exc.__cause__ or exc.__context__
    if any(isinstance(e, (sqlite3.Error, V12DatabaseError, ProductionConfigurationError)) for e in chain):
        return None
    reasons = {getattr(e, "reason", "") for e in chain}
    if reasons & {"SHEETS_SCHEMA_UNAVAILABLE", "QUOTE_INPUT_LOCATION_INVALID",
                  "QUOTE_INPUT_LOCATION_BINDING_MISMATCH", "QUOTE_INPUT_METADATA_INVALID",
                  "GOOGLE_WRITE_SETTLEMENT_UNCONFIRMED", "GOOGLE_SCRIPT_SETTLEMENT_UNCONFIRMED"}:
        return None
    if ("INSO_AUTHENTICATION_REQUIRED" in reasons or "INSO_QUERY_RETRIES_EXHAUSTED" in reasons
            or any(isinstance(e, InsoAuthenticationError) for e in chain)):
        return "INSO"
    if (reasons & {"SHEETS_READ_UNAVAILABLE", "SHEETS_AUTH_UNAVAILABLE", "GOOGLE_SHEETS_UNAVAILABLE",
                   "GOOGLE_AUTHENTICATION_REQUIRED", "GOOGLE_SPREADSHEET_UNAVAILABLE",
                   "GOOGLE_SHEET_UNCONFIRMED", "QUOTE_INPUT_METADATA_UNAVAILABLE"}
            or any(type(e).__name__ in {"GoogleSheetsReadError", "GoogleSheetsReadUnavailable"} for e in chain)):
        return "Google Sheets"
    if "IC_NET_UNAVAILABLE" in reasons:
        return "IC.net"
    if "V13_FX_UNAVAILABLE" in reasons:
        return "汇率网站"
    if (reasons & {"CDP_SESSION_UNAVAILABLE", "CDP_RECONNECT_EXHAUSTED",
                   "GOOGLE_OPERATION_NOT_CLOSED", "INSO_OPERATION_NOT_CLOSED"}
            or any(isinstance(e, BrowserBootstrapError) for e in chain)):
        return "Browser/CDP"
    return None


class ProductionBackend(GuiBackend):
    """Own one GUI run session and stop it only at safe Workflow boundaries."""

    def __init__(
        self, config_path=None, production_config_path=None, *, cdp_probe=None,
        root=None, browser_acquirer=acquire_cdp_browser,
        v12_adapters: V12ProductionAdapters | None = None,
        defer_local_view: bool = False,
        inquiry_ids: frozenset[str] | None = None,
        market_actor_factory=None,
    ):
        self.root = Path(root) if root is not None else app_root()
        self._inquiry_scope = inquiry_ids
        self.config_path = Path(config_path) if config_path is not None else runtime_config_path("research.json", root=self.root)
        self.production_path = Path(production_config_path) if production_config_path is not None else runtime_config_path("production.json", root=self.root)
        self.cdp_probe = cdp_probe
        self._browser_acquirer = browser_acquirer
        self._page_admission = PageResourceAdmission()
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
        self._tp = None  # opt-in only; ordinary V1.4 composition is unchanged
        self._module_runtime = None
        self._module_execute = None
        self._market_actor_factory = market_actor_factory
        self._market_actors = None
        self._continuation_pump = None
        self._continuation_reader = None
        self._quotation_factory = None
        self._module_failures = {}
        self._module_pause_requested = None
        self._module_contexts = []
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
        self._cycle_id = None
        self._state = RunState.STOPPED
        self._started = self._stopped = self._last_poll = None
        self._next_poll_at = None
        self._site_outages = {}
        self._site_manual_wait = set()
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
        self._order_mail_thread = None
        self._order_mail_report = None
        self._order_mail_stage = None
        self._order_notifications = None
        self._logs = []
        self._status_callbacks = []
        self._log_callbacks = []
        self._health = HealthReport(
            tuple(HealthItem(n, "未知", "尚未检查") for n in self._components()),
            "需要人工处理",
        )
        from .workbench_snapshot import RuntimeObservation
        self._observation = RuntimeObservation()
        self._view_gate = threading.Lock()
        self._snapshot_lock = threading.Lock()
        self._view_last_refresh = 0.0
        self._view_state_cache = {}
        self._view_dirty = set()
        self._view_snapshot = WorkbenchSnapshot(0, self.get_status(), self._health)
        self._view_loading = defer_local_view
        self._local_view_thread = None
        if defer_local_view:
            # One-shot local I/O only; no browser/business work or permanent UI worker.
            self._local_view_thread = threading.Thread(target=self._load_local_view,
                name="local-history-loader")
            self._local_view_thread.start()
        else:
            self._load_local_view()

    def _load_local_view(self):
        try:
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
                    self._state = RunState.MODULE_PAUSED
                    self._append_log("ERROR", "订单台账不可读，已停止共享业务；未恢复任何订单。")
            self._observation.enable(quotation=locals().get("startup_cfg", {}).get("v13_enabled") is True,
                                     tp=locals().get("startup_cfg", {}).get("tp_enabled") is True)
        except Exception:  # noqa: BLE001 - local display bootstrap, never raw data in diagnostics
            self._append_log("WARNING", "本地历史暂不可用，尚未执行业务操作。")
        finally:
            self._view_loading = False
            self._cache_workbench(force=True)

    def local_view_loading(self):
        return self._view_loading

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
                or self._market_actors is not None
                or self._view_loading
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
            self._site_outages.clear()
            self._site_manual_wait.clear()
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
                    actors = self._market_actors
                    if actors is not None:
                        actors.request_stop()  # thread-safe atomic transport stop, no owner release here
                    self._manual_condition.notify_all()
                self._notify()

    def _immediate_stop_requested(self):
        return self._stop.is_set() and not self._drain_due_on_stop.is_set()

    def _run(self):
        try:
            cfg = json.loads(self.production_path.read_text(encoding="utf-8"))
            self._observation.enable(quotation=cfg.get("v13_enabled") is True,
                                     tp=cfg.get("tp_enabled") is True)
            if (
                not cfg.get("spreadsheet_id")
                or not cfg.get("worksheet_titles")
            ):
                raise ProductionConfigurationError(
                    "production.json requires spreadsheet_id and worksheet_titles"
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
            web_service = build_google_web_service(
                rc.cdp.cdp_url, provider=lambda: self._google_playwright_provider(rc, cfg),
                on_read_success=lambda: self._site_recovered("Google Sheets"),
                read_guard=self._page_admission.require_open,
                stop_requested=self._immediate_stop_requested)
            reader = GoogleSheetsRowReader(web_service, retry_wait=self._stop.wait)
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
            write_service = web_service

            self._manual_reader = reader

            def get_write_service():
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
                page_admission=self._page_admission,
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
                        begin_inquiry=self._begin_duplicate_check,
                        reset=self._close_inso_order_tab,
                        wait=self._stop.wait,
                        on_success=lambda: self._site_recovered("INSO"),
                    ),
                    research_facts=ResearchExcelFactsProvider(ResearchExcelOutput(self._excel)),
                    purchase_writer=_LivePurchaseDraftWriter(
                        self._inso_operation_access,
                        session_guard_factory=self._inso_purchase_session_guard,
                        login_problem=self._manual_review,
                        store=self._v12_store,
                        observe=self._observe_stage,
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
            class AutomaticBrandUpdater:
                def update_brand(self, identity, brand):
                    from src.sheets.google_writer import GoogleSheetsBrandWriter
                    from src.workflow import SheetsSafeBrandUpdater

                    SheetsSafeBrandUpdater(
                        reader, GoogleSheetsBrandWriter(get_write_service()),
                        verify_readback=True,
                    ).update_brand(identity, brand)

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
                    brand_updater=AutomaticBrandUpdater(),
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
            self._observation.enable(quotation=self._v13_enabled, tp=cfg.get("tp_enabled") is True)
            if self._v13_enabled:
                holds = V13HoldStore(db)
                holds.migrate()
                self._v13_ledger_ready = True
                price_store = ProcurementPriceStore(db)
                price_store.migrate()
                location = quotation_location(cfg)  # Missing/unknown config stops before business.

                quotation_fx = EcbDailyUsdRmbProvider()

                def build_quotation(worksheet, *, source_store=None, source_reader=None, hold_store=None):
                    self._observe_stage("quotation", "检查采购报价与跟进", site="INSO")
                    active_reader = source_reader or reader
                    active_store = source_store or self._store
                    active_holds = hold_store or holds
                    from src.sheets.tp_brief import BriefReader
                    cached_brief = BriefReader(web_service)
                    cycle = V13QuotationCycle(reader=active_reader, store=active_store,
                        operations=self._v13_operations(rc, cfg), clock=utc_now,
                        wait=(self._closed_retry_wait if self._continuation_pump is not None else self._stop.wait),
                        stop_requested=self._stop.is_set, fx_provider=quotation_fx,
                        on_fx_success=lambda: self._site_recovered("汇率网站"),
                        on_query_success=lambda: self._site_recovered("INSO"),
                        automatic_refresh=source_store is None,
                        brief_snapshot=lambda ws: cached_brief.cached_lines(ws.spreadsheet))
                    def updater():
                        handle = self._v13_browser(rc, cfg)
                        try:
                            service = get_write_service()
                        except Exception:  # noqa: BLE001 - shared cached Sheets authorization boundary
                            raise V12Fault(FaultScope.GLOBAL_STOP,"SHEETS_AUTH_UNAVAILABLE") from None
                        return build_v13_quotation_updater(
                            service=service, source_reader=active_reader,
                            store=active_store, browser_handle=handle, location=location,
                            price_store=price_store, currency_rate=cycle.currency_rate,
                            notify_refresh_uncertain=lambda result, old, new: notify_refresh_uncertain(
                                self._v12_store, result, old, new, at=utc_now()),
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
                    return integrated
                self._quotation_factory = build_quotation
                def run_quotation(worksheet, *, source_store=None, source_reader=None, hold_store=None):
                    integrated = build_quotation(worksheet, source_store=source_store,
                        source_reader=source_reader, hold_store=hold_store)
                    for recovery in range(4):
                        try:
                            if (self._market_actor_factory is None and self._module_execute is not None
                                    and self._module_contexts[-1:] == ["quotation"]):
                                return integrated.run(worksheet,
                                    after_closed_candidate=self._yield_quotation_to_tp)
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
            self._tp = None
            if cfg.get("tp_enabled") is True:
                from .tp_composition import build_tp_cycle
                def prepare_tp(key):
                    self._begin_inso_inquiry(key)
                    prepare_research()
                self._tp = build_tp_cycle(path=db, web=web_service, reader=reader,
                    research=research, outbox=self._v12_store,
                    worker=self._v12_composition.notification_worker, now=utc_now(),
                    prepare=prepare_tp, stop_requested=self._stop.is_set,
                    retry_wait=self._stop.wait)
            self._refresh_history(force=True)
            self._set_health(("正常", "待命", "正常", "正常"), "正常")

            independent = cfg.get("v16_enabled", getattr(sys, "frozen", False)
                and Path(sys.executable).stem == "INSO_V1.6") is True
            if independent:
                configured = cfg.get("module_intervals_seconds", {})
                if not isinstance(configured, dict) or set(configured) - {"inquiry", "quotation", "tp"}:
                    raise ProductionConfigurationError("INVALID_MODULE_INTERVALS")
                periods = {"inquiry": configured.get("inquiry", 900)}
                if self._v13_enabled:
                    periods["quotation"] = configured.get("quotation", 900)
                if self._tp is not None:
                    periods["tp"] = configured.get("tp", 900)
                runtime.configure_modules(periods)
                self._module_runtime = runtime
                self._module_failures.clear()
                self._v12_composition.notification_worker.defer_delivery()

            def poll_loop():
                try:
                    if independent:
                        self._run_independent_poll(runtime, cfg, rc, web_service,
                                                   reader, worksheets, follow_up_store)
                        return
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
                            self._next_poll_at = None
                        try:
                            with web_service.poll_scope(), quotation_operation_scope(), reader.discovery_scope():
                                self._last_poll = utc_now()
                                self._cycle_id = "cycle_" + uuid.uuid4().hex
                                self._observation.begin_cycle()
                                self._notify()
                                self._begin_poll_projection()
                                self._check_site_recovery(rc, cfg)
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
                                browser_state = "已连接" if self._research_ready else "待命"
                                if not self._site_outages:
                                    self._set_health(("正常", browser_state, "正常", "正常"), "正常")
                            if self._tp is not None and not self._stop.is_set():
                                self._observe_stage("tp", "读取目标价并核验订单")
                                # Previous scope releases its three source/input slots.
                                # TP reads own operation pages on THIS same poll thread.
                                self._tp.run(cfg["spreadsheet_id"], now=utc_now())
                                if self._tp.issues:
                                    self._append_log("WARNING", f"TP 有 {len(self._tp.issues)} 条来源或价格待核对，未自动处理。")
                            # Finish execution observation; the actual wait entry
                            # publishes its own read-only plan after cleanup.
                            self._observation.end_cycle(
                                stopped=self._stop.is_set())
                            self._cache_workbench(force=True)
                            self._notify()
                        except (sqlite3.Error, V12DatabaseError):
                            raise
                        except Exception as exc:
                            if not self._defer_website_poll(exc, runtime.poll_interval):
                                raise
                        finally:
                            original_failure = sys.exc_info()[1]
                            try:
                                self._close_inso_order_tab()
                            except Exception as cleanup:
                                log_step("inso-operation-cleanup", cause=cleanup)
                                if original_failure is None:
                                    failure = V12Fault(FaultScope.GLOBAL_STOP, "INSO_OPERATION_NOT_CLOSED")
                                    failure.__cause__ = cleanup
                                    if not self._defer_website_poll(failure, runtime.poll_interval):
                                        raise
                            finally:
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
                    if independent:
                        self._v12_composition.notification_worker.bind_delivery_thread()
                    while not self._stop.is_set():
                        try:
                            BrowserHandle.drain_deferred_stops()
                            self._refresh()
                            if self._v12_composition is not None:
                                self._v12_composition.coordinator.run_notifications(now=utc_now())
                            self._release_idle_browser()
                        except Exception as exc:
                            if not self._defer_website_poll(exc, runtime.poll_interval):
                                raise
                        self._stop.wait(runtime.worker_idle_interval.total_seconds())
                except Exception as exc:  # noqa: BLE001 - local failure or proven prolonged outage
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
                self._observation.end_cycle(stopped=True,
                    reason=None if self._state is RunState.STOPPED else "业务暂停，请核对异常与健康状态")
                self._cache_workbench(force=True)
                self._notify()

    def _publish_module_plans(self):
        runtime = self._module_runtime
        if runtime is None:
            return
        for key, (due, running, paused) in runtime.module_plans().items():
            if not running:
                self._observation.module_plan(key,
                    None if paused else utc_now() + timedelta(seconds=max(0, due-monotonic())),
                    paused=paused, reason=self._module_failures.get(key, (0, None))[1])

    def _run_independent_poll(self, runtime, cfg, rc, web, reader, worksheets, episodes):
        """One browser actor, independent deadlines; existing mail worker overlaps."""
        if self._market_actor_factory is not None:
            from .business_continuations import run_business_continuations
            return run_business_continuations(self, runtime, cfg, rc, web, reader, worksheets, episodes)
        def execute(module):
            self._last_poll = utc_now()
            self._cycle_id = "cycle_" + uuid.uuid4().hex
            self._log_module_cycle(module, "begin", 0)
            self._observation.begin_module(module)
            self._publish_module_plans()
            self._notify()
            with web.poll_scope(), quotation_operation_scope(), reader.discovery_scope():
                self._check_site_recovery(rc, cfg)
                if module in {"inquiry", "quotation"}:
                    self._refresh_dashboard_counts(reader, worksheets, episodes=episodes, now=utc_now())
                if module == "inquiry":
                    self._begin_poll_projection()
                    if self._combined is not None:
                        self._combined.run_inquiry(reader, worksheets, now=utc_now())
                    else:
                        self._v12_composition.coordinator.begin_poll_cycle()
                        for worksheet in worksheets:
                            if self._immediate_stop_requested():
                                break
                            self._v12_composition.coordinator.poll_and_process(reader, worksheet, now=utc_now())
                    if not self._immediate_stop_requested():
                        self._purchase_completion.retry_saved_statuses(at=utc_now())
                        self._idle_login_tick(now=utc_now())
                elif module == "quotation":
                    self._combined.run_quotation(reader, worksheets)
                else:
                    self._observe_stage("tp", "读取目标价并核验订单")
                    self._tp.run(cfg["spreadsheet_id"], now=utc_now())
                    if self._tp.issues:
                        self._append_log("WARNING", f"TP 有 {len(self._tp.issues)} 条待核对，其他任务继续。")
        self._module_execute = execute
        try:
            while not self._stop.is_set():
                BrowserHandle.drain_deferred_stops()
                module = runtime.claim_due_module()
                if module is None:
                    self._publish_module_plans()
                    if self._wait_between_polls(runtime.module_delay()):
                        break
                    continue
                with self._poll_gate:
                    if self._stop.is_set():
                        runtime.complete_module(module)
                        break
                    self._poll_idle.clear()
                    self._next_poll_at = None
                try:
                    self._run_independent_job(module)
                finally:
                    self._poll_idle.set()
        finally:
            self._module_execute = None
            self._module_runtime = None

    def _yield_quotation_to_tp(self, _result):
        """Lend only a confirmed closed scheduled quotation boundary; never preempt."""
        runtime = self._module_runtime
        if (runtime is None or self._market_actor_factory is not None
                or self._module_execute is None or self._manual_write_service is None
                or self._module_contexts[-1:] != ["quotation"]
                or self._state not in {RunState.RUNNING, RunState.QUOTATION_RUNNING}
                or self._stop.is_set() or self._module_pause_requested is not None
                or self._manual_busy or self._manual_request is not None or self._poll_idle.is_set()
                or self._inso_session is not None or self._active_inso_inquiry is not None
                or self._keepalive_protected_targets or self._site_manual_wait):
            return
        plan = runtime.module_plans().get("tp")
        if plan is None or plan[1] or plan[2] or plan[0] > monotonic():
            return
        self._page_admission.require_open()
        # Module release never releases a source lease. Conservatively decline
        # lending while ANY existing source transaction/request remains active.
        counts = runtime.order_resource_counts()
        if counts['active'] or counts['waiting']:
            return
        # One quote cycle spans multiple worksheets. A later clean worksheet
        # cannot erase an earlier durable uncertain-effect barrier.
        if self._manual_quote is None or any(row[3] in {
                'QUOTE_INPUT_WRITE_FAILED', 'QUOTE_INPUT_READBACK_MISMATCH',
                'UPDATE_RESULT_UNCONFIRMED', 'SOURCE_STATUS_NOT_UPDATED',
        } for row in self._manual_quote[1].active()):
            return
        if not settle_quotation_operations() or not self._manual_write_service().operations_idle():
            return
        self._page_admission.require_open()
        if self._stop.is_set() or self._module_pause_requested is not None:
            return
        prior = self._observation.modules['quotation']
        self._observation.wait('quotation', '报价已安全收口，执行到期TP')
        runtime.yield_module_resource('quotation')
        try:
            with self._poll_gate:
                module = (None if self._stop.is_set() else
                          runtime.claim_due_module(exclude=('quotation', 'inquiry')))
            if module is not None:
                if self._stop.is_set():
                    runtime.complete_module(module)
                else:
                    self._run_independent_job(module)
            self._page_admission.require_open()
        except V13Stopped:
            if not self._stop.is_set():
                runtime.abort_module_resource()
            raise
        except BaseException:
            # Escaping shared/unknown faults cannot resurrect outer ownership.
            runtime.abort_module_resource()
            self._state = RunState.GLOBAL_STOP
            self._stop.set()
            raise
        finally:
            if not runtime.module_resource_failed:
                runtime.resume_module_resource('quotation')
                if self._manual_reader is not None:
                    self._manual_reader.clear_discovery_snapshot()
                self._observation.stage('quotation', prior.stage, site=prior.site,
                                        order_ref=prior.order_ref)

    def _run_independent_job(self, module, *, started=None):
        # Sync browser ownership is fixed to this thread. Only closed-row waits
        # nest here; business/session state must not be snapshotted or rolled back.
        nested = bool(self._module_contexts)
        parent = (self._cycle_id, self._last_poll, self._research_acquire_failure,
                  self._module_pause_requested)
        self._module_contexts.append(module)
        self._research_acquire_failure = None  # New execution never inherits another job's failure.
        try:
            with self._observation.module_scope(module):
                if started is None:
                    self._run_independent_job_scoped(module)
                else:
                    self._run_independent_job_scoped(module, started=started)
        finally:
            self._module_contexts.pop()
            self._module_pause_requested = parent[3]
            if nested:
                self._cycle_id, self._last_poll, self._research_acquire_failure = parent[:3]

    def _run_independent_job_scoped(self, module, *, started=None):
        runtime = self._module_runtime
        retry, paused, reason = None, False, None
        started = monotonic() if started is None else started
        outcome = "failed"
        try:
            self._module_pause_requested = None
            self._page_admission.require_open()
            try:
                self._module_execute(module)
            finally:
                self._page_admission.require_open()
            if self._module_pause_requested is not None:
                raise self._module_pause_requested
            self._module_failures.pop(module, None)
            outcome = "stopped" if self._stop.is_set() else "completed"
        except V13Stopped:
            outcome = "stopped"
            raise
        except (sqlite3.Error, V12DatabaseError):
            raise
        except Exception as exc:
            cause, seen = exc, set()
            while cause is not None and id(cause) not in seen:
                seen.add(id(cause))
                if isinstance(cause, (PageTargetCleanupError, OrderResourceOwnershipError)):
                    runtime.abort_module_resource()
                    self._state = RunState.GLOBAL_STOP
                    self._stop.set()
                    raise
                if (isinstance(cause, (sqlite3.Error, V12DatabaseError, SecurityViolation, ProductionConfigurationError))
                        or getattr(cause, "reason", "") in {"MODULE_RESOURCE_OWNERSHIP_LOST",
                            "NOTIFICATION_WORKER_OWNERSHIP_LOST", "INSO_OPERATION_NOT_CLOSED",
                            "GOOGLE_OPERATION_NOT_CLOSED", "WORKFLOW_LEDGER_UNAVAILABLE",
                            "CDP_PAGE_CLEANUP_UNCONFIRMED", "CDP_PAGE_CREATION_UNCONFIRMED",
                            "CDP_PAGE_OWNERSHIP_UNCONFIRMED"}):
                    raise
                cause = cause.__cause__ or cause.__context__
            site = _website_failure(exc)
            if site is not None:
                outcome = "deferred"
                count = self._module_failures.get(module, (0, None))[0] + 1
                retry = min(900 * 2**min(count-1, 4), 10800)
                reason = f"等待{site}恢复"
                since = self._site_outages.get(site, monotonic())
                if site != "Browser/CDP" and monotonic()-since >= 10800:
                    paused, retry, reason = True, None, f"{site}连续三小时未恢复，请人工处理"
                elif not self._defer_website_poll(exc, timedelta(seconds=retry)):
                    raise
                self._module_failures[module] = (count, reason)
            elif isinstance(exc, V12Fault) and exc.scope is FaultScope.V12_PAUSE:
                outcome = "paused"
                paused, reason = True, "模块安全暂停，请查看异常"
                self._module_failures[module] = (1, reason)
                self._append_log("ERROR", f"{module}已暂停，其他安全模块继续。")
            else:
                raise  # unknown/shared integrity or ownership fault is never swallowed
        finally:
            try:
                self._close_inso_order_tab()
            except PageTargetCleanupError:
                runtime.abort_module_resource()
                raise
            except Exception as cleanup:
                runtime.abort_module_resource()
                raise V12Fault(FaultScope.GLOBAL_STOP, "INSO_OPERATION_NOT_CLOSED") from cleanup
            finally:
                if not runtime.module_resource_failed:
                    runtime.complete_module(module, retry_after=retry, pause=paused)
                else:
                    paused, reason = True, "共享资源状态未确认，已停止共享业务"
                    outcome = "failed"
                self._observation.module_plan(module, None if paused else
                    utc_now()+timedelta(seconds=max(0, runtime.module_plans()[module][0]-monotonic())),
                    paused=paused, reason=reason)
                self._observation.finish_module(module)
                self._log_module_cycle(module, outcome, max(0, monotonic()-started))
                self._publish_module_plans()
                self._cache_workbench(force=True)
                self._notify()

    def _log_module_cycle(self, module, phase, seconds):
        runtime = self._module_runtime
        plan = runtime.module_plans()[module]
        delay = None if plan[2] else max(0, plan[0]-monotonic())
        log.info("module cycle", extra={"cycle_id": self._cycle_id,
            "scheduled_module": module, "cycle_phase": phase,
            "cycle_elapsed": seconds, "cycle_due_in": delay})

    def _pause_v12(self, fault):
        if self._module_runtime is not None:
            if self._module_pause_requested is None:
                self._module_pause_requested = fault
            return  # independent loop classifies and isolates this exact module
        self._observation.pause("inquiry", "采购暂停；报价跟进沿用原有独立策略")
        if _website_failure(fault) is not None and not self._defer_website_poll(
                fault, timedelta(minutes=15), notify=False):
            self._runtime_error(fault)
            return
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
        self._page_admission.require_open()
        for attempt in range(4):
            handle = self._browser_handle
            if handle is not None and handle.browser is not None and handle.browser.is_connected():
                bind_page_admission(handle.browser, self._page_admission)
                self._site_recovered("Browser/CDP")
                return handle
            try:
                if handle is not None:
                    handle.disconnect()
                self._browser_handle = self._browser_acquirer(rc.cdp.cdp_url,self.root,cfg,
                    probe=self.cdp_probe or probe_loopback_endpoint)
                if self._browser_handle.browser.is_connected():
                    bind_page_admission(self._browser_handle.browser, self._page_admission)
                    self._site_recovered("Browser/CDP")
                    return self._browser_handle
            except PageTargetCleanupError:
                raise
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
                self.current = quotation_operations(browser_handle=handle,login=login)
                return self.current.open(inquiry_id)
            def preserve(self):
                if self.current:
                    self.current.preserve()
            def reset(self):
                if self.current:
                    self.current.reset()
                    self.current = None
                backend._active_inso_inquiry = None
            def close(self):
                if self.current:
                    self.current.close()
                    self.current = None
                backend._active_inso_inquiry = None
        return SharedOperations()

    def _observe_quotation(self, result, key):
        self._invalidate_order_view(key)
        dto = quotation_gui(result,key)
        with self._lock:
            inquiry = result.inquiry_id or key
            self._poll_inquiries.add(inquiry)
            if result.outcome.value in {"NO_RECENT_QUOTE", "ROW_FAILED", "UPDATED_INSERTED", "UPDATED_ALREADY_EXISTS", "BASELINE_RECORDED", "PRICE_UNCHANGED", "QUOTE_AGE_EXPIRED", "QUOTE_AGE_UNVERIFIED"}:
                self._poll_quotation_completed.add(inquiry)
        if dto is not None:
            with self._lock:
                self._v13_states[key] = dto
                if result.inquiry_id is None:
                    self._v13_unbound[key] = Order(key,result.queried_mpn or "",None,0,
                        "",None,None,OrderStatus.ERROR,remark=dto.waiting_label,run_id=self._run_id or "",
                        source_sheet=result.source_worksheet.worksheet if result.source_worksheet else None,
                        source_row=result.source_row_position, module_id="quotation")
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
                if action == "tp":
                    return self._tp is not None and self._tp.store.manual_allowed(self._tp_key(inquiry_id))
                self._store.get_by_inquiry_id(inquiry_id)
                if action == "purchase":
                    return (self._state is RunState.RUNNING and self._v12_store is not None
                        and self._v12_store.manual_purchase_retry_allowed(inquiry_id))
                return action == "edit" or (action == "quotation" and self._manual_quote is not None)
            except (KeyError, sqlite3.Error, V12DatabaseError):
                return False

    def order_action_hint(self, inquiry_id, action):
        # Display only: no business lock, SQL, or cached authorization. The
        # canonical request/execute path always checks durable permissions.
        if not self._manual_idle() or self._store is None or self._manual_reader is None:
            return False
        order = next((o for o in self._view_snapshot.orders if o.inquiry_id == inquiry_id), None)
        if order is None:
            return False
        if action == "tp":
            key = order.inquiry_id if order.module_id == "tp" else order.tp_task_id
            target = next((o for o in self._view_snapshot.orders
                           if o.inquiry_id == key and o.module_id == "tp"), None)
            return (self._tp is not None and target is not None
                and target.business_status in {"MAIL_QUEUED", "FAILED"}
                and target.delivery_status in {None, "SENT", "PERMANENT_FAILURE"})
        if order.module_id == "tp":
            return False
        if action == "purchase":
            cached = self._view_state_cache.get(inquiry_id)
            dto = cached[1] if cached else None
            return (self._state is RunState.RUNNING and self._v12_store is not None
                and dto is not None and not dto.active_alerts
                and dto.business_label not in {
                    V12BusinessLabel.SUBMIT_UNCONFIRMED, V12BusinessLabel.INTERRUPTED_POSSIBLY_SENT,
                    V12BusinessLabel.STATUS_WRITE_PENDING, V12BusinessLabel.PURCHASE_SENT,
                    V12BusinessLabel.HUMAN_COMPLETED,
                }
                and order.delivery_status != "UNKNOWN")
        return action == "edit" or (action == "quotation" and self._manual_quote is not None)

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
        # Immutable reference published by the existing worker (Python 3.12).
        # GUI reads must not contend with the business lock held during SQL.
        return self._manual_result

    def _wait_between_polls(self, seconds):
        deadline = monotonic() + seconds
        self._publish_poll_wait(seconds, deadline=deadline)
        while not self._stop.is_set():
            # Give the shared browser back during idle time, on its owner thread.
            # A worker may queue teardown after this wait has already started.
            self._release_idle_browser()
            BrowserHandle.drain_deferred_stops()
            with self._manual_condition:
                if self._stop.is_set():
                    self._manual_request = None
                    self._next_poll_at = None
                    return True
                request, self._manual_request = self._manual_request, None
                if request is None:
                    remaining = deadline - monotonic()
                    if remaining <= 0:
                        self._next_poll_at = None
                        return False
                    self._manual_condition.wait(min(remaining, 0.25))
                    continue
                self._manual_busy = True
                self._next_poll_at = None
                self._poll_idle.clear()
            self._notify()
            try:
                self._observe_stage("tp" if request[2] == "tp" else "quotation" if request[2] == "quotation" else "inquiry",
                                    "核验人工操作请求", order_ref=request[1])
                self._execute_order_action(request)
            finally:
                self._close_inso_order_tab()
                with self._lock:
                    self._manual_busy = False
                    self._poll_idle.set()
                self._observation.end_cycle(stopped=self._stop.is_set(), close_round=False)
                self._invalidate_order_view(request[1])
                self._cache_workbench(force=True)
                self._notify()
            deadline = monotonic() + seconds
            if self._module_runtime is not None:
                module = {"purchase": "inquiry", "quotation": "quotation", "tp": "tp"}.get(request[2], "inquiry")
                self._module_runtime.reset_module(module)
                self._publish_module_plans()
                deadline = monotonic() + self._module_runtime.module_delay()
            self._publish_poll_wait(seconds, close_round=False, deadline=deadline)
        with self._lock:
            self._next_poll_at = None
        return True

    def _publish_poll_wait(self, seconds, *, close_round=True, deadline=None):
        # One actual wait-entry/reset deadline for UI and manual permissions.
        # Called only after TP/owned-page cleanup; the original monotonic wait
        # and poll-idle/busy/durable authorization checks remain authoritative.
        deadline = monotonic() + seconds if deadline is None else deadline
        with self._lock:
            remaining = max(0, deadline - monotonic())
            self._next_poll_at = (utc_now() + timedelta(seconds=remaining)
                if self._state in {RunState.RUNNING, RunState.QUOTATION_RUNNING}
                and not self._stop.is_set() and remaining else None)
            planned = self._next_poll_at
        self._observation.end_cycle(planned,
            stopped=self._stop.is_set(), close_round=close_round,
            recovery_site=" / ".join(tuple(self._site_outages)) or None)
        if self._module_runtime is not None and not self._stop.is_set():
            self._publish_module_plans()
        # Publish only the changed time to the existing immutable view. Calling
        # _notify here would rescan durable state at every wait boundary.
        with self._snapshot_lock:
            self._view_snapshot = replace(self._view_snapshot,
                revision=self._view_snapshot.revision + 1,
                session=replace(self._view_snapshot.session, next_poll_at=planned))

    def _execute_order_action(self, request):
        request_id, inquiry, action, field, value = request
        success, message = False, "操作未执行。"
        try:
            if action == "tp":
                from src.sheets.tp_brief import TpLocalError
                from src.workflow.tp_research import load_order
                selected = None
                try:
                    key = self._tp_key(inquiry)
                    selected = self._tp.store.get(key)
                except KeyError as exc:
                    if exc.__cause__ is not None or exc.__context__ is not None:
                        raise
                if selected is None:
                    raise TpLocalError("TP_TASK_UNAVAILABLE")
                order = load_order(selected["order_json"])
                self._tp.run(order.spreadsheet, now=utc_now(), manual_key=key)
                with self._lock:
                    self._manual_result = ManualOrderResult(request_id, inquiry, action, True,
                        "TP 专项调研已完成并进入原有邮件队列。")
                self._notify()
                return
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
                if status not in {"发给采购", "采购已报价", "已报价给客户"}:
                    raise ValueError("报价重跑要求当前Google状态为发给采购、采购已报价或已报价给客户，未修改状态。")
                runner, holds = self._manual_quote
                manual_holds = ManualRetryHolds(holds, inquiry, identity)
                for key, _, observed, reason, _ in manual_holds.matched_old:
                    if reason == "SOURCE_STATUS_NOT_UPDATED" and status == "发给采购":
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
            if self._defer_website_poll(exc, timedelta(minutes=15)):
                message = "网站暂不可用，程序等待恢复；本次手动操作未确认，不会自动重做。"
            elif exc.scope is FaultScope.GLOBAL_STOP:
                raise
            else:
                if self._combined is not None:
                    self._combined.v12_paused = True
                self._pause_v12(exc)
                message = "采购流程需要人工处理，报价轮询保持原有独立策略。"
        except (KeyError, ValueError) as exc:
            if action == "tp":
                from src.workflow.tp_research import tp_local_failure_reason
                if not tp_local_failure_reason(exc):
                    raise  # Unknown shared validation/ownership faults keep old policy.
            message = ("TP 来源、目标价或邮件发送记录需核对，本次未重复发送。" if action == "tp" else
                       str(exc) if isinstance(exc, ValueError) else "找不到订单的源表定位，未执行操作。")
        except Exception:  # noqa: BLE001 - targeted edit/read failure is shown without raw provider text
            if action != "edit":
                raise V12Fault(FaultScope.GLOBAL_STOP, "V13_INTERNAL_FAILURE" if action == "quotation" else "V12_MANUAL_RETRY_FAILED") from None
            message = "单元格同步失败或结果未确认，请重新读取表格；不会自动重复写入。"
        with self._lock:
            self._manual_result = ManualOrderResult(request_id, inquiry, action, success, message)
        self._append_log("INFO" if success else "WARNING", message)
        self._refresh()

    def _refresh_dashboard_counts(self, reader, worksheets, *, episodes, now):
        live_before = getattr(reader, "live_read_revision", None)
        counts = read_dashboard_counts(reader, worksheets, store=self._store,
                                       episodes=episodes, now=now)
        if live_before is None or reader.live_read_revision != live_before:
            self._site_recovered("Google Sheets")
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
        self._observation.finish_stage("tp" if inquiry_id.startswith("tp_") else "inquiry")
        self._observe_stage("tp" if inquiry_id.startswith("tp_") else "inquiry",
                            "处理已读来源结果", order_ref=inquiry_id)
        if result.outcome is not SourceOutcome.SOURCE_UNAVAILABLE:
            return
        code = next((str(f.value) for f in result.evidence.fields if f.key == "failure_code"), "SOURCE_UNAVAILABLE")
        inso_auth_stop = result.source is ResearchSource.INSO and code in _INSO_AUTH_STOP_CODES
        notified = self._v12_store is not None
        if notified:
            ordinary = not (isinstance(inquiry_id, str) and inquiry_id.startswith("tp_"))
            mpn = self._store.get_by_inquiry_id(inquiry_id).mpn if self._store is not None and ordinary else None
            notify_website_issue(self._v12_store, inquiry_id if ordinary else None, result.source,
                "AUTHENTICATION_REQUIRED" if inso_auth_stop else code, mpn=mpn, at=utc_now())
        login = (inso_auth_stop if result.source is ResearchSource.INSO else
                 any(token in code for token in ("LOGIN", "CREDENTIAL", "AUTHENTICATION", "VERIFICATION", "CHALLENGE", "SESSION_STALE")))
        if result.source is ResearchSource.IC_NET:
            self._manual_review(inquiry_id, "IC.net：需要人工验证" if login else "IC.net：查询不可用", notify=False)
            raise V12Fault(FaultScope.V12_PAUSE, "IC_NET_UNAVAILABLE")
        if result.source is ResearchSource.INSO and login:
            self._manual_review(inquiry_id, "INSO：" + code, notify=False)
            raise V12Fault(FaultScope.GLOBAL_STOP, "INSO_AUTHENTICATION_REQUIRED")

    def _run_inso_query(self, inquiry_id, operation, prepare):
        first_attempt = True
        last_result = None

        def prepare_attempt():
            nonlocal first_attempt
            if first_attempt:
                first_attempt = False
                return
            self._begin_inso_inquiry(inquiry_id)
            prepare()

        def read_attempt():
            nonlocal last_result
            try:
                last_result = operation()
                return last_result
            except (sqlite3.Error, V12DatabaseError, V12Fault, InsoAuthenticationError):
                raise
            except Exception:  # noqa: BLE001 - failed reads never become empty history
                last_result = None
                return None

        def succeeded(result):
            if result is None:
                return False
            code = next((str(f.value) for f in result.evidence.fields if f.key == "failure_code"), "SOURCE_UNAVAILABLE")
            if result.outcome is not SourceOutcome.SOURCE_UNAVAILABLE or "FX" in code:
                self._site_recovered("INSO")
            if result.outcome is SourceOutcome.SOURCE_UNAVAILABLE and code in _INSO_AUTH_STOP_CODES:
                self._observe_source_failure(inquiry_id, result)
            return result.outcome is not SourceOutcome.SOURCE_UNAVAILABLE or "FX" in code

        try:
            return run_inso_query(
                read_attempt, prepare=prepare_attempt, succeeded=succeeded,
                reset=self._close_inso_order_tab,
                wait=self._closed_retry_wait if self._continuation_pump is not None else self._stop.wait,
            )
        except V12Fault as exc:
            if exc.reason == "INSO_QUERY_RETRIES_EXHAUSTED" and last_result is not None:
                self._observe_source_failure(inquiry_id, last_result)
            raise

    def _run_source_query(self, inquiry_id, site, operation, reconnect):
        self._observe_stage("tp" if inquiry_id.startswith("tp_") else "inquiry",
                            "六源价格查询", site=site.value, order_ref=inquiry_id)
        from src.core.site_retry import SITE_RETRY_DELAYS, retryable_site_failure

        for attempt in range(4):
            if self._stop.is_set():
                raise V12Fault(FaultScope.V12_PAUSE, "STOP_REQUESTED")
            module = "tp" if inquiry_id.startswith("tp_") else "inquiry"
            self._observe_stage(module, "六源价格查询" if not attempt else f"价格查询重试 {attempt}",
                                site=site.value, order_ref=inquiry_id)
            result = self._run_source_query_once(inquiry_id, site, operation, reconnect)
            source = result.source_result if site is ResearchSource.IC_NET else result
            if source.outcome is not SourceOutcome.SOURCE_UNAVAILABLE:
                self._site_recovered("INSO" if site is ResearchSource.INSO else
                                     "IC.net" if site is ResearchSource.IC_NET else site.value)
            code = next((str(f.value) for f in source.evidence.fields if f.key == "failure_code"), "")
            if (source.outcome is not SourceOutcome.SOURCE_UNAVAILABLE or site is ResearchSource.INSO
                    or not retryable_site_failure(code) or attempt == 3):
                return result
            self._observation.wait(module, "等待网站重试", site=site.value)
            if self._stop.wait(SITE_RETRY_DELAYS[attempt]):
                raise V12Fault(FaultScope.V12_PAUSE, "STOP_REQUESTED")
        raise AssertionError("bounded source loop exhausted")

    def _run_source_query_once(self, inquiry_id, site, operation, reconnect):
        """Three bounded shared-CDP recoveries, independent of per-query retry."""
        for attempt in range(4):
            admission = getattr(self, "_page_admission", None)
            if admission is not None:
                admission.require_open()
            try:
                result = operation()
            finally:
                # Adapters may translate the original browser exception into a
                # generic unavailable result. Never accept that after resource
                # uncertainty, reconnect, aggregate or prepare a notification.
                if admission is not None:
                    admission.require_open()
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

    def _begin_duplicate_check(self, inquiry_id):
        self._begin_inso_inquiry(inquiry_id)
        self._observe_stage("inquiry", "检查近七天重复采购记录", site="INSO", order_ref=inquiry_id)

    def _begin_inso_inquiry(self, inquiry_id):
        self._observe_stage("tp" if inquiry_id.startswith("tp_") else "inquiry",
                            "准备订单调研会话", order_ref=inquiry_id)
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
        if protected or self._site_manual_wait:
            context, = browser.contexts
            if not any(not p.is_closed() and p.url == "about:blank" for p in context.pages):
                new_background_page(browser, context, timeout_ms=10000)
            return
        park_shared_cdp(browser)

    def _close_inso_order_tab(self, *, preserve=False):
        self._page_admission.require_open()
        session = self._inso_session
        if preserve and session is not None:
            try:
                try:
                    pages = (session.operation_access().operation_page().page,)
                except Exception:  # noqa: BLE001 - an expired lease must not discard any review page
                    pages = tuple(self._browser_handle.browser.contexts[0].pages)
                self._protect_keepalive_pages(pages)
            except Exception as exc:  # noqa: BLE001 - preserve every page if review identity cannot be pinned
                self._state = RunState.MODULE_PAUSED
                self._stop.set()
                self._set_health(("已暂停", "需要核对", "未核验", "已暂停"), "订单页面待核对")
                log_step("purchase-review-page-unconfirmed", cause=exc)
                self._append_log("ERROR", "待核对订单的页面保护尚未确认，业务已暂停；原浏览器及页面保留，禁止重发。")
        preserve |= "INSO" in self._site_manual_wait
        if not preserve and session is not None and self._state not in {RunState.MANUAL_REVIEW, RunState.MODULE_PAUSED, RunState.GLOBAL_STOP}:
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
        if not preserve and browser is not None and self._state not in {RunState.MANUAL_REVIEW, RunState.MODULE_PAUSED, RunState.GLOBAL_STOP}:
            self._park_browser(browser)

    def _complete_inquiry(self, result):
        """Settle each row before starting the next; never defer to batch drain."""
        preserve = False
        self._observe_stage("inquiry", "核验采购处理与邮件状态", order_ref=result.inquiry_id)
        try:
            log.warning("combined cycle result", extra={"cycle_id":getattr(self,"_cycle_id",None),
                "business_module":"V1.2","inquiry_id":result.inquiry_id,"stage":"purchase",
                "reason":getattr(getattr(result,"business_state",None),"value","UNKNOWN")})
            self._seen(result.inquiry_id)
            settled = self._purchase_completion.process(result, at=utc_now())
            self._v12_composition.coordinator.run_notifications(now=utc_now())
            self._invalidate_order_view(result.inquiry_id)
            if settled is False:
                preserve = True
                self._append_log("ERROR", "当前订单结果待核对，已保留页面并阻止该单重发；其他安全订单继续处理。")
            self._refresh()
            self._notify()
        finally:
            self._close_inso_order_tab(preserve=preserve)

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

        self._page_admission.require_open()
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
        if self._browser_handle.browser is not None:
            bind_page_admission(self._browser_handle.browser, self._page_admission)
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
        try:
            self._page_admission.require_open()
        except PageTargetCleanupError:
            # No generic park/close sweep when a target's creation/ownership is
            # uncertain. Detach this client only; keep every browser page.
            if handle is not None:
                handle.disconnect()
            return
        if (self._keepalive_protected_targets or self._site_manual_wait) and handle is not None:
            handle.disconnect()  # Target IDs/human wait survive detach; never close protected pages.
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
            running = self._state is RunState.RUNNING and not self._site_outages
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

    def _google_playwright_provider(self, rc, cfg):
        # Reuse canonical attach/resume when Sheets now needs Chrome before Research.
        handle = self._v13_browser(rc, cfg)
        if handle is None or handle._owner_thread != threading.get_ident():
            return None
        return self._research_playwright_provider()

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
        bind_page_admission(browser, self._page_admission)
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

    def _site_recovered(self, site):
        with self._lock:
            self._site_outages.pop(site, None)
            self._site_manual_wait.discard(site)

    def _check_site_recovery(self, rc=None, cfg=None):
        with self._lock:
            waiting = set(self._site_outages)
            manual_inso = "INSO" in self._site_manual_wait
        if "Browser/CDP" in waiting and self._inso_session is not None:
            self._close_inso_order_tab()
        if manual_inso:
            from .inso_session import authenticated_inso_shell_available
            if self._browser_handle is None and rc is not None:
                self._v13_browser(rc, cfg)
            browser = getattr(self._browser_handle, "browser", None)
            if not authenticated_inso_shell_available(browser):
                raise InsoAuthenticationError("MANUAL_VERIFICATION_REQUIRED")
            with self._lock:
                self._site_manual_wait.discard("INSO")
        if self._combined is not None and waiting & {"INSO", "IC.net"}:
            self._combined.v12_paused = False
            if self._state is RunState.QUOTATION_RUNNING:
                self._state = RunState.RUNNING

    def _defer_website_poll(self, exc, interval, *, notify=True):
        site = _website_failure(exc)
        if site is None:
            return False
        with self._lock:
            if self._stop.is_set():
                return True  # Explicit Owner stop always wins over automatic recovery.
            since = self._site_outages.setdefault(site, monotonic())
            if site != "Browser/CDP" and monotonic() - since >= 3 * 60 * 60:
                return False
            cause, visited = exc, set()
            while cause is not None and id(cause) not in visited:
                visited.add(id(cause))
                if getattr(cause, "reason_code", "") in {
                    "MANUAL_VERIFICATION_REQUIRED", "CREDENTIAL_REJECTED", "AUTHENTICATION_REQUIRED",
                    "SESSION_IDENTITY_UNVERIFIED",
                } and site == "INSO":
                    self._site_manual_wait.add(site)
                cause = cause.__cause__ or cause.__context__
            if self._state is not RunState.STOPPING_AFTER_CYCLE:
                self._state = RunState.RUNNING
            self._next_poll_at = utc_now() + interval
            detail = ("等待人工完成登录或验证，程序会自动检查恢复；不会自动重复提交。"
                      if site in self._site_manual_wait else
                      "必要操作暂未成功，等待下一轮恢复；不会自动重复提交。")
            self._health = HealthReport(tuple(
                HealthItem(name, "等待恢复" if name == site or name == "Research" else "待命", detail)
                for name in self._components()), f"等待{site}恢复")
        # Keep the existing read-exhaustion message/dedup contract.
        if notify and site == "Google Sheets" and self._defer_google_read_poll(exc, interval):
            return True
        reason = {"INSO": "INSO_WAITING_RECOVERY", "Google Sheets": "GOOGLE_WAITING_RECOVERY",
                  "IC.net": "IC_NET_WAITING_RECOVERY", "Browser/CDP": "BROWSER_WAITING_RECOVERY",
                  "汇率网站": "FX_WAITING_RECOVERY", "Findchips": "FINDCHIPS_WAITING_RECOVERY",
                  "华强": "HQEW_WAITING_RECOVERY", "立创": "LCSC_WAITING_RECOVERY",
                  "正能量": "BOM_AI_WAITING_RECOVERY"}[site]
        log.warning("Website recovery deferred", extra={
            "runtime_reason": reason, "runtime_cause": type(exc).__name__})
        if notify and self._v13_ledger_ready:
            notify_runtime_fault(self._v12_store, f"{self._run_id or 'run'}:{site}:{since}", reason, at=utc_now())
        elif notify:
            self._alert_owner_of_login(stop_reason=f"{site}等待恢复；程序未停止")
        self._notify()
        return True

    def _defer_google_read_poll(self, exc, interval):
        from src.sheets.google_reader import GoogleSheetsReadUnavailable

        cause, visited = exc, set()
        while cause is not None and id(cause) not in visited:
            visited.add(id(cause))
            if isinstance(cause, GoogleSheetsReadUnavailable):
                break
            cause = cause.__cause__ or cause.__context__
        if not isinstance(cause, GoogleSheetsReadUnavailable):
            return False
        with self._lock:
            if self._stop.is_set():
                return True
            self._next_poll_at = utc_now() + interval
            self._set_health(("等待下一轮重试", "待命", "未核验", "已暂停"), "等待Google恢复")
        log.warning("Google read retry exhausted", extra={
            "runtime_reason": "GOOGLE_READ_RETRY_EXHAUSTED",
            "runtime_cause": type(cause.__cause__).__name__,
        })
        if self._v13_ledger_ready:
            notify_runtime_fault(self._v12_store, self._cycle_id or self._run_id or "run",
                "GOOGLE_READ_RETRY_EXHAUSTED", at=utc_now())
        else:
            self._alert_owner_of_login(stop_reason="Google表格等待恢复；程序未停止")
        self._notify()
        return True

    def accept_market_fault(self, fault):
        """Original owner consumes immutable actor fault via existing stop path.

        Port only: optional actors are not enabled in production composition.
        No worker calls this method or accesses Backend state directly.
        """
        from src.workflow.market_messages import MarketFault, MarketFaultScope
        if type(fault) is not MarketFault or fault.scope is not MarketFaultScope.GLOBAL_STOP:
            raise ValueError("MARKET_GLOBAL_FAULT_REQUIRED")
        error = PageTargetCleanupError(())
        error.reason, error.failure_classes = fault.reason, fault.exception_classes
        self._page_admission.invalidate(error)
        self._runtime_error(error)

    def _runtime_error(self, exc):
        log.warning("Production runtime worker failed (%s)", type(exc).__name__)
        with self._lock:
            site = _website_failure(exc)
            prolonged = (site is not None and site != "Browser/CDP"
                         and site in self._site_outages
                         and monotonic() - self._site_outages[site] >= 3 * 60 * 60)
            page_fault, candidate, visited = None, exc, set()
            while candidate is not None and id(candidate) not in visited:
                visited.add(id(candidate))
                if isinstance(candidate, (PageTargetCleanupError, OrderResourceOwnershipError)):
                    page_fault = candidate
                    break
                candidate = candidate.__cause__ or candidate.__context__
            self._state = RunState.GLOBAL_STOP if prolonged or page_fault is not None else RunState.MODULE_PAUSED
            cause = exc
            while cause is not None:
                if isinstance(cause, V12Fault):
                    break
                if isinstance(cause, (sqlite3.Error, V12DatabaseError, InsoAuthenticationError, ProductionConfigurationError)) or type(cause).__name__.startswith("GoogleSheets"):
                    break
                cause = cause.__cause__
            self._next_poll_at = None
            self._drain_due_on_stop.clear()
            with self._poll_gate:
                self._stop.set()
                actors = self._market_actors
                if actors is not None:
                    actors.request_stop()
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
            if isinstance(cause, V12Fault) and cause.reason in {
                "SHEETS_READ_UNAVAILABLE", "SHEETS_SCHEMA_UNAVAILABLE", "GOOGLE_SHEETS_UNAVAILABLE",
            }:
                statuses = (
                    HealthItem("Google Sheets", "需要人工处理", "读取或结构确认失败；网络/授权原因尚未确定"),
                    HealthItem("Browser/CDP", "已暂停", "随共享业务暂停，未确认独立故障"),
                    HealthItem("Credential", "未核验", "此次故障不能证明凭据失效"),
                    HealthItem("Research", "已暂停", "等待Google表格恢复"),
                )
            self._health = HealthReport(statuses, "需要人工处理")
        message = (
            "需要配置：请补齐本地生产数据源与授权文件"
            if isinstance(exc, ProductionConfigurationError)
            else "相关业务已暂停，请检查运行提示；程序不会自动重复提交。"
        )
        if site is not None:
            affected = site if site in self._components() else "Research"
            self._health = HealthReport(tuple(
                HealthItem(name, "连续三小时未恢复" if prolonged and name == affected else
                           "需要处理" if name == affected else "已暂停",
                           f"{site}必要业务操作未确认；未确认其他组件独立故障。")
                for name in self._components()), "连续三小时未恢复" if prolonged else "相关业务已暂停")
        if prolonged:
            message = f"{site}必要业务操作已连续三小时未恢复，已停止共享业务；未自动重复提交。"
        self._append_log("ERROR", message)
        self._notify()
        # A shared fault is not a failure of the last historical order.
        fault_inquiry = self._active_inso_inquiry
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
        shared_fault = self._state is RunState.GLOBAL_STOP
        if page_fault is not None:
            reason = page_fault.reason
        if prolonged:
            reason = {"INSO": "INSO_OUTAGE_THREE_HOURS", "Google Sheets": "GOOGLE_OUTAGE_THREE_HOURS",
                      "IC.net": "IC_NET_OUTAGE_THREE_HOURS", "汇率网站": "FX_OUTAGE_THREE_HOURS"}[site]
        safe_reason = reason if isinstance(reason, str) and re.fullmatch(r"[A-Z_]{1,64}", reason) else "V12_INTERNAL_FAILURE"
        root_cause, visited = exc, set()
        while root_cause.__cause__ is not None and id(root_cause) not in visited:
            visited.add(id(root_cause))
            root_cause = root_cause.__cause__
        log.warning("Runtime fault", extra={
            "runtime_reason": safe_reason, "runtime_cause": type(root_cause).__name__,
        })
        # The canonical manual-login path already mailed this exact legacy pause.
        if (isinstance(exc, V12Fault) and exc.reason == "Research requires session repair"
                and self._inquiries and self._inquiries[-1] in self._manual_inquiries):
            return
        if not shared_fault and fault_inquiry not in self._manual_inquiries:
            self._record_fault_alert(fault_inquiry, "FAULT", reason)
        if (shared_fault or fault_inquiry is None) and self._v13_ledger_ready:
            try:
                notify_runtime_fault(self._v12_store,self._run_id or "run",reason,at=utc_now())
                self._v12_composition.coordinator.run_notifications(now=utc_now())
            except (sqlite3.Error,V12DatabaseError):
                self._alert_owner_of_login(stop_reason=reason)
        elif self._purchase_completion is None or fault_inquiry is None:
            self._alert_owner_of_login(stop_reason=reason)

    def _record_fault_alert(self, inquiry_id, phase, reason):
        if isinstance(inquiry_id, str) and inquiry_id.startswith("tp_"):
            return  # TP has no V1 inquiry FK; site alerts use the nullable outbox.
        if self._purchase_completion is None or inquiry_id is None:
            return
        try:
            self._purchase_completion.notify(inquiry_id, phase, reason, at=utc_now())
            if self._v12_composition is not None:
                self._v12_composition.coordinator.run_notifications(now=utc_now())
        except (sqlite3.Error, V12DatabaseError):
            self._state = RunState.MODULE_PAUSED
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
        site = "INSO" if "inso" in lower or "英索" in lower else "IC.net"
        reason = "INSO_AUTHENTICATION_REQUIRED" if site == "INSO" else "IC_NET_UNAVAILABLE"
        fault = V12Fault(FaultScope.GLOBAL_STOP, reason)
        if site == "INSO" and any(token in lower for token in (
                "需要人工验证", "验证码", "manual_verification", "credential_rejected",
                "session_identity_unverified", "没有可用的登录凭据", "captcha", "otp",
                "security_event", "credential", "verification", "interactive", "verified_session", "login_rejected")):
            self._site_manual_wait.add(site)
        with self._lock:
            self._manual_inquiries.add(inquiry_id)
        if not self._defer_website_poll(fault, timedelta(minutes=15), notify=False):
            self._runtime_error(fault)
            return
        message = (f"{site}暂不可用，程序等待恢复；需要验证时请在原Chrome完成，未停止轮询。"
                   if not self._stop.is_set() else f"{site}验证待处理；本次运行已按用户要求停止。")
        self._append_log("WARNING", message)
        if notify:
            if self._purchase_completion is not None:
                self._record_fault_alert(inquiry_id, "SESSION", reason)
            else:
                self._alert_owner_of_login(stop_reason=f"{site}等待恢复；程序未停止", inquiry_id=inquiry_id)

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
            waiting = bool(self._site_outages) and self._state in {RunState.RUNNING, RunState.QUOTATION_RUNNING}
            body = ("网站必要业务操作暂未成功，程序仍在运行，15分钟后检查恢复。\n"
                    "如需人工验证，请在原Chrome完成；不会自动重复提交采购。"
                    if waiting else _login_alert_body(stop_reason))
            if inquiry_id is not None and self._store is not None:
                item = self._store.get_by_inquiry_id(inquiry_id)
                body += (f"\n型号：{item.mpn}\n"
                         f"品牌：{item.resolved_brand or item.brand}\n数量：{item.quantity}\n"
                         "请核对本单处理状态，勿直接重发采购单。")
            result = transport.send_operator_alert(
                recipient=NotificationRecipient("owner", _LOGIN_ALERT_RECIPIENT),
                subject="【INSO】网站等待恢复" if waiting else "【INSO】询价已停止",
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
        ids = [i for i in self._inquiries if i in items][-1000:]
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
        self._cache_workbench(items=items)

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
            for record in records[:1000]
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

    def _closed_retry_wait(self, seconds):
        """Existing closed-page retry delay; progress other modules meanwhile."""
        if self._continuation_pump is None:
            return self._stop.wait(seconds)
        if not self._module_contexts:
            raise OrderResourceOwnershipError()
        runtime, module = self._module_runtime, self._module_contexts[-1]
        runtime.yield_module_resource(module)
        try:
            deadline = monotonic() + seconds
            while not self._stop.is_set() and monotonic() < deadline:
                self._continuation_pump()
                clear = getattr(self._continuation_reader, "clear_discovery_snapshot", None)
                if clear is not None:
                    clear()
                self._stop.wait(min(0.05, max(0, deadline-monotonic())))
            return self._stop.is_set()
        finally:
            if not runtime.module_resource_failed:
                runtime.resume_module_resource(module)

    def _wait_between_rows(self, seconds):
        """Expose the existing interruptible row wait without changing its policy."""
        with self._lock:
            self._row_cooldown_until = utc_now() + timedelta(seconds=seconds)
        self._observation.wait("inquiry", "订单间安全等待")
        try:
            if self._continuation_pump is not None:
                return self._closed_retry_wait(seconds)
            if self._module_runtime is not None and self._module_execute is not None:
                runtime = self._module_runtime
                runtime.yield_module_resource("inquiry")
                deadline = monotonic() + seconds
                try:
                    while not self._stop.is_set() and monotonic() < deadline:
                        other = runtime.claim_due_module(exclude=("inquiry",))
                        if other is not None:
                            self._run_independent_job(other)
                            if self._manual_reader is not None:
                                self._manual_reader.clear_discovery_snapshot()
                        else:
                            self._stop.wait(min(0.25, max(0, deadline-monotonic())))
                    return self._stop.is_set()
                finally:
                    if not runtime.module_resource_failed:
                        runtime.resume_module_resource("inquiry")
            return self._stop.wait(seconds)
        finally:
            with self._lock:
                self._row_cooldown_until = None
            self._observation.finish_stage("inquiry")

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
            from .tp_composition import tp_display_orders
            return self._results + tp_display_orders(self._tp)

    def _tp_key(self, row_key):
        if row_key.startswith("tp_"):
            return row_key
        from src.workflow.tp_research import task_key
        identity = self._store.get_by_inquiry_id(row_key).record_identity
        return task_key(identity.worksheet.spreadsheet, identity.worksheet.worksheet, identity.row_position)

    def get_result_history(self):
        with self._lock:
            from .tp_composition import tp_display_orders
            return tuple(replace(order, **self._source_overrides[order.inquiry_id])
                if order.inquiry_id in self._source_overrides else order for order in self._history) + tp_display_orders(self._tp)

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

    def start_order_mail_check(self) -> bool:
        with self._lock:
            if self._closed or (self._order_mail_thread and self._order_mail_thread.is_alive()):
                return False
            self._order_mail_report = None
            self._order_mail_stage = "RUNNING"
            self._order_mail_thread = threading.Thread(
                target=self._order_mail_worker, name="sales-header-owner-review", daemon=True,
            )
            self._order_mail_thread.start()
            return True

    def order_mail_running(self) -> bool:
        thread = self._order_mail_thread
        return bool(thread and thread.is_alive())

    def get_order_mail_report(self) -> str | None:
        return self._order_mail_report

    def get_order_mail_stage(self):
        return self._order_mail_stage

    def _notify_order_exception(self, **kwargs):
        from src.workflow.order_notifications import OrderExceptionNotifications
        if self._order_notifications is None:
            self._order_notifications = OrderExceptionNotifications(self.root)
        self._order_notifications.notify(**kwargs)

    def _order_mail_worker(self) -> None:
        from .sales_header import run_sales_header_check
        try:
            if self._order_notifications is None and (self.root / ".tmp/v14-notifications/outbox.sqlite3").exists():
                from src.workflow.order_notifications import OrderExceptionNotifications
                self._order_notifications = OrderExceptionNotifications(self.root)
            stage, text = run_sales_header_check(
                config_path=self.config_path,
                production_path=self.production_path, root=self.root, notify=self._notify_order_exception,
            )
        except Exception:  # noqa: BLE001 - never leak provider/customer data
            stage, text = "STOPPED", "订单头部检查未完成；未保存或提交，请检查配置后重试。"
        with self._lock:
            self._order_mail_stage = stage
            self._order_mail_report = text

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
        thread = self._login_all_thread
        return thread is not None and thread.is_alive()

    def get_login_all_report(self) -> SiteLoginReport | None:
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

    def _run_login_sweep(self, *, background=False, check_only=False, only_sites=None) -> tuple[SiteLoginResult, ...]:
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
            if only_sites is not None:
                options["only_sites"] = only_sites
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
            mail_thread = self._order_mail_thread
        if thread and thread is not threading.current_thread():
            thread.join()
        if login_thread and login_thread is not threading.current_thread():
            login_thread.join()
        if mail_thread and mail_thread is not threading.current_thread():
            mail_thread.join()
        local_thread = self._local_view_thread
        if local_thread and local_thread is not threading.current_thread():
            local_thread.join()
        if self._order_notifications is not None:
            self._order_notifications.close()
        with self._lock:
            self._status_callbacks.clear()
            self._log_callbacks.clear()
            self._login_all_callbacks.clear()

    def _notify(self):
        status = self.get_status()
        self._cache_workbench(session=status)
        for cb in tuple(self._status_callbacks):
            cb(status)

    def _observe_stage(self, module, stage, *, site=None, order_ref=None):
        observer = getattr(self, "_observation", None)
        if observer is not None:
            observer.stage(module, stage, site=site, order_ref=order_ref)

    def get_workbench_snapshot(self):
        # GUI path: only locks and immutable references, never SQLite/Excel/stat.
        with self._snapshot_lock:
            snapshot = self._view_snapshot
        revision, modules, started, tick, finished, timings, durations, planned, recovery = self._observation.snapshot()
        return replace(snapshot, revision=snapshot.revision + revision,
            modules=modules, cycle_started_at=started, cycle_started_monotonic=tick,
            cycle_finished_at=finished, local_loading=self._view_loading,
            timings=timings, cycle_durations=durations,
            planned_check_at=planned, recovery_site=recovery)

    def _invalidate_order_view(self, key):
        # Existing callbacks may run alongside the existing refresh worker.
        # They mark a bounded dirty key; only the projection gate mutates cache.
        with self._snapshot_lock:
            if key in self._view_state_cache and len(self._view_dirty) < 1000:
                self._view_dirty.add(key)

    def _cache_workbench(self, *, force=False, session=None, items=None):
        gate = getattr(self, "_view_gate", None)
        if gate is None or not gate.acquire(blocking=False):
            return
        try:
            if not force and monotonic()-self._view_last_refresh < 2:
                if session is not None:
                    with self._snapshot_lock:
                        self._view_snapshot = replace(self._view_snapshot, session=session)
                return
            self._view_last_refresh = monotonic()
            with self._snapshot_lock:
                dirty, self._view_dirty = self._view_dirty, set()
            for key in dirty:
                self._view_state_cache.pop(key, None)
            from src.workflow.tp_research import task_key

            from .tp_composition import tp_display_orders
            # Existing workers already load these canonical records. Read no
            # site or production state on demand from the GUI.
            if items is None:
                items = {i.inquiry_id: i for i in self._store.all_items()} if self._store else {}
            merged = {o.inquiry_id: o for o in self._results}
            merged.update({o.inquiry_id: o for o in tp_display_orders(self._tp)})
            for order in self._history:
                merged.setdefault(order.inquiry_id, order)
            orders, states = [], []
            for key, order in tuple(merged.items())[:1000]:
                if key in self._source_overrides:
                    order = replace(order, **self._source_overrides[key])
                item = items.get(key)
                identity = getattr(item, "record_identity", None)
                if identity is not None:
                    order = replace(order, source_sheet=identity.worksheet.worksheet,
                                    source_row=identity.row_position)
                    tp_key = task_key(identity.worksheet.spreadsheet,
                                      identity.worksheet.worksheet, identity.row_position)
                    target = merged.get(tp_key)
                    order = replace(order, tp_task_id=tp_key if target is not None
                        and target.module_id == "tp" and target.model == order.model
                        and target.quantity == order.quantity else None)
                cached = self._view_state_cache.get(key)
                if cached is None or cached[0] != order or force:
                    dto = self.get_v12_order_state(key) if not key.startswith("tp_") else None
                    self._view_state_cache[key] = (order, dto)
                dto = self._view_state_cache[key][1]
                if dto is not None:
                    # Bound timeline/control count; absence is never success.
                    dto = replace(dto, event_history=dto.event_history[-30:])
                    states.append(dto)
                    unsettled = bool(dto.active_alerts) or dto.business_label in {
                        V12BusinessLabel.SUBMIT_UNCONFIRMED,
                        V12BusinessLabel.INTERRUPTED_POSSIBLY_SENT,
                        V12BusinessLabel.INTERRUPTED_UNSENT,
                        V12BusinessLabel.STATUS_WRITE_PENDING,
                        V12BusinessLabel.SOURCE_CHANGED,
                        V12BusinessLabel.QUOTATION_STATUS_PENDING,
                    }
                    unknown_notification = any(a.reason_code is V12ReasonCode.NOTIFICATION_UNKNOWN
                                               for a in dto.active_alerts)
                    order = replace(order, business_status=dto.waiting_label or dto.business_label.value,
                        status=OrderStatus.ERROR if unsettled else order.status,
                        delivery_status="UNKNOWN" if unknown_notification else order.delivery_status)
                if key in self._v13_states and order.module_id != "tp":
                    order = replace(order, modules=("quotation",) if order.module_id == "quotation"
                                    else ("inquiry", "quotation"))
                orders.append(order)
            self._view_state_cache = {o.inquiry_id:self._view_state_cache[o.inquiry_id] for o in orders}
            projected_session = session or self.get_status()
            with self._snapshot_lock:
                self._view_snapshot = WorkbenchSnapshot(self._view_snapshot.revision+1,
                    projected_session, self._health, tuple(orders),
                    order_states=tuple(states), logs=tuple(self._logs[-300:]), total_orders=len(merged))
        except Exception:  # noqa: BLE001 - observation can never stop a business workflow
            log.debug("Local dashboard projection unavailable")
        finally:
            gate.release()

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
