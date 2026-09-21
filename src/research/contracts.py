"""Canonical public contracts for Research V1."""

from dataclasses import dataclass
from enum import Enum


class ResearchStatus(str, Enum):
    SUCCESS = "SUCCESS"
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
    MANUAL_REVIEW_REQUIRED = "MANUAL_REVIEW_REQUIRED"
    RETRYABLE_FAILURE = "RETRYABLE_FAILURE"


class ResearchReasonCode(str, Enum):
    NO_MATCHING_PRODUCT = "NO_MATCHING_PRODUCT"


@dataclass(frozen=True, slots=True)
class ResearchInput:
    inquiry_id: str
    mpn: str
    brand: str | None
    quantity: int


@dataclass(frozen=True, slots=True)
class ResearchResult:
    inquiry_id: str
    status: ResearchStatus
    resolved_brand: str | None = None
    reason_code: ResearchReasonCode | None = None
    remarks: str | None = None
