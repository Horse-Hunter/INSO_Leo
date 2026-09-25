"""Result finalization rules that depend on Excel persistence."""

from __future__ import annotations

from .contracts import (
    ResearchReasonCode,
    ResearchResult,
    ResearchStatus,
)
from .excel_output import ExcelOutputError, ResearchExcelOutput


def finalize_research_result(
    *,
    output: ResearchExcelOutput,
    inquiry_id: str,
    importance_raw: str | None,
    status: ResearchStatus,
    resolved_brand: str | None = None,
    reason_code: ResearchReasonCode | None = None,
    remarks: str | None = None,
) -> ResearchResult:
    """Persist required output before returning a terminal Research result."""

    if status is ResearchStatus.RETRYABLE_FAILURE:
        return ResearchResult(
            inquiry_id=inquiry_id,
            status=status,
            resolved_brand=resolved_brand,
            reason_code=reason_code,
            remarks=remarks,
        )

    if status is ResearchStatus.MANUAL_REVIEW_REQUIRED and not (
        remarks and remarks.strip()
    ):
        raise ValueError(
            "MANUAL_REVIEW_REQUIRED requires a persisted human-intervention reason"
        )

    try:
        output.upsert(
            inquiry_id,
            importance_raw=importance_raw,
            remarks=remarks,
            research_status=status.value,
        )
    except ExcelOutputError:
        return ResearchResult(
            inquiry_id=inquiry_id,
            status=ResearchStatus.RETRYABLE_FAILURE,
            resolved_brand=resolved_brand,
        )

    return ResearchResult(
        inquiry_id=inquiry_id,
        status=status,
        resolved_brand=resolved_brand,
        reason_code=reason_code,
        remarks=remarks,
    )
