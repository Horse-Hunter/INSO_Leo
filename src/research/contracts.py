"""Canonical public contracts for Research V1."""

from dataclasses import dataclass
from enum import Enum


class ResearchStatus(str, Enum):
    SUCCESS = "SUCCESS"
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
    EXCEPTION = "EXCEPTION"
    RETRYABLE_FAILURE = "RETRYABLE_FAILURE"


class ResearchReasonCode(str, Enum):
    NO_MATCHING_PRODUCT = "NO_MATCHING_PRODUCT"
    SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"


class InvalidResearchInput(ValueError):
    """A deterministic input contract violation; retrying cannot change it."""


@dataclass(frozen=True, slots=True)
class ResearchInput:
    inquiry_id: str
    mpn: str
    brand: str | None
    quantity: int
    importance_raw: str | None

    def __post_init__(self) -> None:
        # A worksheet row can carry a column legend or a blank cell where a
        # quantity belongs. Rejecting it here keeps that data problem at the
        # contract boundary instead of surfacing as a deep arithmetic
        # conversion error inside price aggregation. Numeric values keep their
        # existing downstream handling.
        if isinstance(self.quantity, bool) or not isinstance(self.quantity, (int, float)):
            raise InvalidResearchInput("quantity must be a number")


@dataclass(frozen=True, slots=True)
class ResearchResult:
    inquiry_id: str
    status: ResearchStatus
    resolved_brand: str | None = None
    reason_code: ResearchReasonCode | None = None
    remarks: str | None = None
