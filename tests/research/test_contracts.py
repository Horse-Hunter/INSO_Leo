from dataclasses import fields

from src.research.contracts import (
    ResearchInput,
    ResearchReasonCode,
    ResearchResult,
    ResearchStatus,
)


def test_research_input_contract_is_exact() -> None:
    assert [field.name for field in fields(ResearchInput)] == [
        "inquiry_id",
        "mpn",
        "brand",
        "quantity",
        "importance_raw",
    ]


def test_research_result_contract_has_no_output_ref() -> None:
    assert [field.name for field in fields(ResearchResult)] == [
        "inquiry_id",
        "status",
        "resolved_brand",
        "reason_code",
        "remarks",
    ]


def test_status_catalog_is_exact() -> None:
    assert {status.value for status in ResearchStatus} == {
        "SUCCESS",
        "PARTIAL_SUCCESS",
        "MANUAL_REVIEW_REQUIRED",
        "RETRYABLE_FAILURE",
    }


def test_reason_code_catalog_is_minimal() -> None:
    assert {reason.value for reason in ResearchReasonCode} == {
        "NO_MATCHING_PRODUCT",
        "SOURCE_UNAVAILABLE",
    }
