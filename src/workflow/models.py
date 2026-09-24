"""Workflow V1 state and persisted work-item models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from src.sheets import SheetRecordIdentity


class WorkflowStatus(str, Enum):
    QUEUED = "QUEUED"
    RESEARCHING = "RESEARCHING"
    RETRY_WAIT = "RETRY_WAIT"
    COMPLETED = "COMPLETED"
    MANUAL_REVIEW = "MANUAL_REVIEW"
    FAILED = "FAILED"


@dataclass(frozen=True, slots=True)
class WorkItem:
    id: int
    inquiry_id: str
    record_identity: SheetRecordIdentity
    mpn: object
    brand: object
    quantity: object
    importance_raw: object
    status: WorkflowStatus
    attempt_count: int
    next_attempt_at: datetime | None
    research_status: str | None
    resolved_brand: str | None
    brand_update_status: str | None
    last_error: str | None
