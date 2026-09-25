from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from src.gui.contracts import (
    OrderAlertDTO,
    V12AlertCode,
    V12BusinessLabel,
    V12ReasonCode,
)
from src.workflow.v12_contracts import ReasonCode
from src.workflow.v12_evidence import (
    EvidenceMetadata,
    UnsafeEvidencePath,
    capture_is_safe,
    new_evidence_reference,
    validate_evidence_reference,
    validate_existing_evidence_path,
)
from src.workflow.v12_safety import V12SafeLogger

INQUIRY = "inq_0123456789abcdef01234567"
CANARY = "SECRET_CANARY_9F8C"


def test_evidence_reference_is_opaque_relative_and_uses_validated_inquiry(tmp_path: Path) -> None:
    reference = new_evidence_reference(tmp_path, INQUIRY)
    assert reference.startswith(f"evidence/{INQUIRY}/")
    assert Path(reference).name.endswith(".png")
    assert validate_evidence_reference(reference) == reference
    with pytest.raises(UnsafeEvidencePath):
        new_evidence_reference(tmp_path, "../escape")
    with pytest.raises(UnsafeEvidencePath):
        validate_evidence_reference("../../secret.png")


def test_existing_path_rejects_symlink_escape_when_supported(tmp_path: Path) -> None:
    outside = tmp_path.parent / f"{tmp_path.name}-outside"
    outside.mkdir()
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    link = evidence / INQUIRY
    try:
        link.symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation not available in this test environment")
    with pytest.raises(UnsafeEvidencePath):
        validate_existing_evidence_path(tmp_path, INQUIRY, "a" * 32 + ".png")


def test_external_exception_logger_records_only_reason_code() -> None:
    observed = []
    logger = V12SafeLogger(
        observed.append,
        clock=lambda: datetime(2026, 9, 25, tzinfo=UTC),
    )
    code = logger.record_external_error(
        "notification", TimeoutError(CANARY + " raw response")
    )
    assert code is ReasonCode.NOTIFICATION_TRANSIENT
    assert len(observed) == 1
    assert observed[0].reason_code is code
    assert CANARY not in repr(observed)


def test_evidence_metadata_has_no_untrusted_message_field() -> None:
    metadata = EvidenceMetadata(
        ReasonCode.EVIDENCE_PATH_UNSAFE,
        capture_attempted=False,
        redaction_confirmed=False,
        relative_ref=None,
    )
    assert CANARY not in repr(metadata)
    assert not hasattr(metadata, "message")
    assert metadata.retention_days == 30
    assert not capture_is_safe(crop_confirmed=True, redaction_confirmed=False)
    assert capture_is_safe(crop_confirmed=True, redaction_confirmed=True)


def test_gui_alert_dto_rejects_free_form_external_exception_text() -> None:
    with pytest.raises(TypeError):
        OrderAlertDTO(
            "alert-1",  # type: ignore[arg-type]
            CANARY,
            V12ReasonCode.UNKNOWN_EXTERNAL_FAILURE,
            datetime(2026, 9, 25, tzinfo=UTC),
            True,
        )
    safe_alert = OrderAlertDTO(
        "alert-1",
        V12AlertCode.NOTIFICATION_FAILED,
        V12ReasonCode.NOTIFICATION_TRANSIENT,
        datetime(2026, 9, 25, tzinfo=UTC),
        True,
    )
    assert CANARY not in repr(safe_alert)
    assert V12BusinessLabel.PURCHASE_SENT.value == "已发采购单"
