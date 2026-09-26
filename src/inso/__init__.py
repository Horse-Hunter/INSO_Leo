"""INSO V1.2 contracts, safety seams, and closed-gate purchase preparation."""

from .duplicate_history import (
    DuplicateHistoryCapture,
    DuplicateHistoryFailure,
    DuplicateHistoryRecord,
    DuplicateHistoryRowValues,
    InsoDuplicateHistoryReader,
)
from .purchase_writer import (
    AiRecognitionResult,
    AiResultReader,
    InsoPurchaseWriter,
    PlaywrightAiResultReader,
)
from .session import (
    BrowserIdentity,
    BrowserOwnership,
    ContextIdentity,
    InsoOperationAccess,
    InsoSessionLease,
    LeaseState,
    OperationPage,
    PageIdentity,
    SecurityViolation,
)

__all__ = [
    "AiRecognitionResult",
    "AiResultReader",
    "BrowserIdentity",
    "BrowserOwnership",
    "ContextIdentity",
    "DuplicateHistoryCapture",
    "DuplicateHistoryFailure",
    "DuplicateHistoryRecord",
    "DuplicateHistoryRowValues",
    "InsoDuplicateHistoryReader",
    "InsoOperationAccess",
    "InsoPurchaseWriter",
    "InsoSessionLease",
    "LeaseState",
    "OperationPage",
    "PageIdentity",
    "PlaywrightAiResultReader",
    "SecurityViolation",
]
