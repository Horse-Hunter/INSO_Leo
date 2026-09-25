"""Typed, additive V1.2 public contracts.

These contracts contain business data explicitly required by the workflow.
External error text is intentionally not represented in any V1.2 result/event.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum


class ReasonCode(StrEnum):
    UNKNOWN_EXTERNAL_FAILURE = "UNKNOWN_EXTERNAL_FAILURE"
    DUPLICATE_ORDER_DETECTED = "DUPLICATE_ORDER_DETECTED"
    DUPLICATE_LOOKUP_UNAVAILABLE = "DUPLICATE_LOOKUP_UNAVAILABLE"
    DUPLICATE_LOOKUP_AMBIGUOUS = "DUPLICATE_LOOKUP_AMBIGUOUS"
    DUPLICATE_HISTORY_INVALID = "DUPLICATE_HISTORY_INVALID"
    SESSION_IDENTITY_UNVERIFIED = "SESSION_IDENTITY_UNVERIFIED"
    SESSION_STALE = "SESSION_STALE"
    PAGE_NOT_FOUND = "PAGE_NOT_FOUND"
    CONTROL_NOT_FOUND = "CONTROL_NOT_FOUND"
    CONTROL_AMBIGUOUS = "CONTROL_AMBIGUOUS"
    CONTROL_DENIED = "CONTROL_DENIED"
    ACTION_NOT_ALLOWED = "ACTION_NOT_ALLOWED"
    WRITE_GATE_DISABLED = "WRITE_GATE_DISABLED"
    AI_RECOGNITION_MISMATCH = "AI_RECOGNITION_MISMATCH"
    SAVE_OUTCOME_UNKNOWN = "SAVE_OUTCOME_UNKNOWN"
    RECONCILIATION_AMBIGUOUS = "RECONCILIATION_AMBIGUOUS"
    RECONCILIATION_UNREADABLE = "RECONCILIATION_UNREADABLE"
    NOTIFICATION_TRANSIENT = "NOTIFICATION_TRANSIENT"
    NOTIFICATION_PERMANENT = "NOTIFICATION_PERMANENT"
    NOTIFICATION_SENT = "NOTIFICATION_SENT"
    NOTIFICATION_UNKNOWN = "NOTIFICATION_UNKNOWN"
    CUSTOMER_NAME_MISSING = "CUSTOMER_NAME_MISSING"
    EVIDENCE_PATH_UNSAFE = "EVIDENCE_PATH_UNSAFE"
    SQLITE_BACKUP_INVALID = "SQLITE_BACKUP_INVALID"
    SQLITE_BACKUP_COLLISION = "SQLITE_BACKUP_COLLISION"
    SQLITE_MIGRATION_INVALID = "SQLITE_MIGRATION_INVALID"


class DuplicateOutcome(StrEnum):
    CONFIRMED = "CONFIRMED"
    UNAVAILABLE = "UNAVAILABLE"
    AMBIGUOUS = "AMBIGUOUS"
    INVALID_RESPONSE = "INVALID_RESPONSE"


class NotificationKind(StrEnum):
    IMPORTANT_ORDER = "IMPORTANT_ORDER"
    DUPLICATE_ORDER = "DUPLICATE_ORDER"


class DeliveryOutcome(StrEnum):
    PENDING = "PENDING"
    SENDING = "SENDING"
    SENT = "SENT"
    RETRYABLE_FAILURE = "RETRYABLE_FAILURE"
    PERMANENT_FAILURE = "PERMANENT_FAILURE"
    UNKNOWN = "UNKNOWN"


class PurchaseOutcome(StrEnum):
    PRE_SAVE_READY = "PRE_SAVE_READY"
    AI_RECOGNIZED = "AI_RECOGNIZED"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    UNKNOWN_WRITE_OUTCOME = "UNKNOWN_WRITE_OUTCOME"
    READ_ONLY_RECONCILIATION_REQUIRED = "READ_ONLY_RECONCILIATION_REQUIRED"
    SAVED = "SAVED"
    CONFIRMED_NOT_SAVED = "CONFIRMED_NOT_SAVED"
    MANUAL_REVIEW = "MANUAL_REVIEW"


class ReconciliationOutcome(StrEnum):
    CONFIRMED_SAVED = "CONFIRMED_SAVED"
    CONFIRMED_NOT_SAVED = "CONFIRMED_NOT_SAVED"
    AMBIGUOUS = "AMBIGUOUS"
    UNKNOWN = "UNKNOWN"


class BusinessState(StrEnum):
    QUEUED = "QUEUED"
    DUPLICATE_CHECK_PENDING = "DUPLICATE_CHECK_PENDING"
    DUPLICATE_CHECKING = "DUPLICATE_CHECKING"
    DUPLICATE_CHECK_RETRY_WAIT = "DUPLICATE_CHECK_RETRY_WAIT"
    RESEARCH_PENDING = "RESEARCH_PENDING"
    RESEARCHING = "RESEARCHING"
    RESEARCH_RETRY_WAIT = "RESEARCH_RETRY_WAIT"
    ROUTING = "ROUTING"
    DUPLICATE_STOPPED = "DUPLICATE_STOPPED"
    PURCHASE_DRAFT_PENDING = "PURCHASE_DRAFT_PENDING"
    PURCHASE_DRAFTING = "PURCHASE_DRAFTING"
    PURCHASE_EXCEPTION = "PURCHASE_EXCEPTION"
    PURCHASE_RETRY_WAIT = "PURCHASE_RETRY_WAIT"
    PURCHASE_RECORDED = "PURCHASE_RECORDED"


class BusinessLabel(StrEnum):
    PROCESSING = "处理中"
    DUPLICATE_ORDER = "重复订单"
    PURCHASE_SENT = "已发采购单"
    PURCHASE_EXCEPTION = "采购录单异常"


class AlertType(StrEnum):
    DUPLICATE_ORDER = "DUPLICATE_ORDER"
    NOTIFICATION_FAILED = "NOTIFICATION_FAILED"
    PURCHASE_EXCEPTION = "PURCHASE_EXCEPTION"
    DATA_QUALITY = "DATA_QUALITY"
    SECURITY_EVENT = "SECURITY_EVENT"


class EventType(StrEnum):
    DUPLICATE_CHECK_STARTED = "DUPLICATE_CHECK_STARTED"
    DUPLICATE_CHECK_CONFIRMED = "DUPLICATE_CHECK_CONFIRMED"
    DUPLICATE_CHECK_FAILED = "DUPLICATE_CHECK_FAILED"
    RESEARCH_STARTED = "RESEARCH_STARTED"
    RESEARCH_RETRY_SCHEDULED = "RESEARCH_RETRY_SCHEDULED"
    DUPLICATE_ORDER_DETECTED = "DUPLICATE_ORDER_DETECTED"
    IMPORTANT_ORDER_DECIDED = "IMPORTANT_ORDER_DECIDED"
    NOTIFICATION_COMMAND_CREATED = "NOTIFICATION_COMMAND_CREATED"
    NOTIFICATION_DELIVERY_FAILED = "NOTIFICATION_DELIVERY_FAILED"
    NOTIFICATION_RETRY_SCHEDULED = "NOTIFICATION_RETRY_SCHEDULED"
    NOTIFICATION_DELIVERY_SUCCEEDED = "NOTIFICATION_DELIVERY_SUCCEEDED"
    ALERT_RECOVERED = "ALERT_RECOVERED"
    PURCHASE_DRAFT_STARTED = "PURCHASE_DRAFT_STARTED"
    AI_RECOGNITION_READY = "AI_RECOGNITION_READY"
    AI_RECOGNITION_MISMATCH = "AI_RECOGNITION_MISMATCH"
    SAVE_DISPATCH_ARMED = "SAVE_DISPATCH_ARMED"
    SAVE_OUTCOME_UNKNOWN = "SAVE_OUTCOME_UNKNOWN"
    RECONCILIATION_STARTED = "RECONCILIATION_STARTED"
    RECONCILIATION_CONFIRMED_SAVED = "RECONCILIATION_CONFIRMED_SAVED"
    RECONCILIATION_CONFIRMED_NOT_SAVED = "RECONCILIATION_CONFIRMED_NOT_SAVED"
    RECONCILIATION_AMBIGUOUS = "RECONCILIATION_AMBIGUOUS"
    PURCHASE_DATA_SAVED = "PURCHASE_DATA_SAVED"
    SECURITY_CHECK_FAILED = "SECURITY_CHECK_FAILED"
    DATA_QUALITY_MISSING_CUSTOMER = "DATA_QUALITY_MISSING_CUSTOMER"
    HUMAN_RESOLUTION_RECORDED = "HUMAN_RESOLUTION_RECORDED"


@dataclass(frozen=True, slots=True)
class DuplicateCheckResult:
    inquiry_id: str
    outcome: DuplicateOutcome
    target_mpn_canonical: str
    checked_at: datetime
    repeated: bool | None = None
    historical_date: datetime | None = None
    historical_mpn: str | None = None
    historical_quantity: int | None = None
    quantity_equal: bool | None = None
    creator: str | None = None
    inso_quote: Decimal | None = None
    currency: str | None = None
    evidence_ref: str | None = None
    reason_code: ReasonCode | None = None

    def __post_init__(self) -> None:
        if self.checked_at.tzinfo is None:
            raise ValueError("checked_at must be timezone-aware")
        if self.outcome is DuplicateOutcome.CONFIRMED:
            if self.repeated is None:
                raise ValueError("confirmed result requires repeated")
            if self.repeated and self.historical_date is None:
                raise ValueError("repeated result requires historical_date")
        elif self.repeated is not None:
            raise ValueError("unconfirmed result cannot decide repeated")
        if self.historical_quantity is not None and (
            isinstance(self.historical_quantity, bool)
            or not isinstance(self.historical_quantity, int)
        ):
            raise TypeError("historical_quantity must be an integer")
        if self.historical_date is not None and self.historical_date.tzinfo is None:
            raise ValueError("historical_date must be timezone-aware")
        if self.inso_quote is not None and (
            not self.inso_quote.is_finite() or self.inso_quote < 0
        ):
            raise ValueError("inso_quote must be finite and nonnegative")


@dataclass(frozen=True, slots=True)
class NotificationRecipient:
    recipient_id: str
    address: str


@dataclass(frozen=True, slots=True)
class NotificationCommand:
    command_id: str
    inquiry_id: str
    kind: NotificationKind
    recipients: tuple[NotificationRecipient, ...]
    subject: str
    text_body: str
    html_body: str | None
    created_at: datetime
    payload_version: int = 1

    def __post_init__(self) -> None:
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")
        if self.payload_version < 1:
            raise ValueError("payload_version must be positive")
        if not self.recipients or len({item.recipient_id for item in self.recipients}) != len(
            self.recipients
        ):
            raise ValueError("notification recipients must be nonempty and unique")


@dataclass(frozen=True, slots=True)
class RecipientDeliveryResult:
    command_id: str
    recipient_id: str
    outcome: DeliveryOutcome
    attempt: int
    completed_at: datetime
    reason_code: ReasonCode | None = None
    provider_message_id: str | None = None
    next_attempt_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.attempt < 0 or self.completed_at.tzinfo is None:
            raise ValueError("delivery attempt and completion time are invalid")
        if self.next_attempt_at is not None and self.next_attempt_at.tzinfo is None:
            raise ValueError("next_attempt_at must be timezone-aware")


@dataclass(frozen=True, slots=True)
class NotificationTransportResult:
    """One adapter attempt with a closed outcome and safe reason code."""

    outcome: DeliveryOutcome
    reason_code: ReasonCode

    def __post_init__(self) -> None:
        if not isinstance(self.outcome, DeliveryOutcome) or self.outcome not in {
            DeliveryOutcome.SENT,
            DeliveryOutcome.RETRYABLE_FAILURE,
            DeliveryOutcome.PERMANENT_FAILURE,
            DeliveryOutcome.UNKNOWN,
        }:
            raise ValueError("transport result outcome must be terminal")
        if not isinstance(self.reason_code, ReasonCode):
            raise TypeError("transport reason code must be allowlisted")


@dataclass(frozen=True, slots=True)
class NotificationResult:
    command_id: str
    recipient_results: tuple[RecipientDeliveryResult, ...]
    completed_at: datetime

    def __post_init__(self) -> None:
        if self.completed_at.tzinfo is None:
            raise ValueError("completed_at must be timezone-aware")


@dataclass(frozen=True, slots=True)
class NotificationEvent:
    event_id: str
    inquiry_id: str
    command_id: str
    recipient_id: str | None
    event_type: EventType
    occurred_at: datetime
    reason_code: ReasonCode | None = None


@dataclass(frozen=True, slots=True)
class PurchaseDraftCommand:
    command_id: str
    inquiry_id: str
    customer_name: str | None
    customer_tier: str
    mpn: str
    brand: str
    quantity: int
    inventory_status: str
    estimated_total: Decimal | None
    market_minimum_reference_price: Decimal | None
    quotation_type: str
    purchaser: str
    ai_input: str


@dataclass(frozen=True, slots=True)
class PurchaseDraftResult:
    command_id: str
    outcome: PurchaseOutcome
    completed_at: datetime
    recognized_mpn: str | None = None
    recognized_brand: str | None = None
    recognized_quantity: int | None = None
    reason_code: ReasonCode | None = None
    saved_record_ref: str | None = None
    evidence_ref: str | None = None

    def __post_init__(self) -> None:
        if self.completed_at.tzinfo is None:
            raise ValueError("completed_at must be timezone-aware")
        if self.recognized_quantity is not None and (
            isinstance(self.recognized_quantity, bool)
            or not isinstance(self.recognized_quantity, int)
        ):
            raise TypeError("recognized_quantity must be an integer")


@dataclass(frozen=True, slots=True)
class ReconciliationResult:
    outcome: ReconciliationOutcome
    reconciled_at: datetime
    saved_record_ref: str | None = None
    reason_code: ReasonCode | None = None
    candidate_count: int | None = None
    verified_fields: tuple[str, ...] = ()
    authoritative: bool = False

    def __post_init__(self) -> None:
        if self.reconciled_at.tzinfo is None:
            raise ValueError("reconciled_at must be timezone-aware")
        if self.candidate_count is not None and self.candidate_count < 0:
            raise ValueError("candidate_count cannot be negative")


@dataclass(frozen=True, slots=True)
class WorkflowEvent:
    event_id: str
    inquiry_id: str
    event_type: EventType
    occurred_at: datetime
    source_module: str
    reason_code: ReasonCode | None = None
    attempt: int | None = None
    evidence_ref: str | None = None


@dataclass(frozen=True, slots=True)
class ActiveAlertDTO:
    alert_id: str
    inquiry_id: str
    alert_type: AlertType
    reason_code: ReasonCode
    raised_at: datetime
    active: bool


@dataclass(frozen=True, slots=True)
class OrderSummaryDTO:
    inquiry_id: str
    business_state: BusinessState
    business_label: BusinessLabel
    latest_active_alert: ActiveAlertDTO | None
