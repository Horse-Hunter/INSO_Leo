"""Public Research V1 contracts and local output helpers."""

from .contracts import (
    ResearchInput,
    ResearchReasonCode,
    ResearchResult,
    ResearchStatus,
)
from .excel_output import (
    ExcelConsistencyError,
    ExcelOutputError,
    ExcelWriteError,
    ResearchExcelOutput,
)
from .finalize import finalize_research_result

__all__ = [
    "ExcelConsistencyError",
    "ExcelOutputError",
    "ExcelWriteError",
    "ResearchExcelOutput",
    "ResearchInput",
    "ResearchReasonCode",
    "ResearchResult",
    "ResearchStatus",
    "finalize_research_result",
]
