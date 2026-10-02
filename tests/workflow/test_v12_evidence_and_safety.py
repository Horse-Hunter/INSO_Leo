from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

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
    _reject_symlink,
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
    # The escape target lives under tmp_path so the test owns everything it
    # creates: a sibling of tmp_path would depend on a pristine parent that
    # pytest does not guarantee, and it would leak one directory per session.
    outside = tmp_path / "outside"
    outside.mkdir()
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    link = evidence / INQUIRY
    try:
        link.symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation not available in this test environment")
    if not link.is_symlink():
        # Some sandboxes silently downgrade symlink creation to a plain
        # directory (no reparse point). That would make the guard look broken
        # when it is fine, so only assert when a real link exists. The guard
        # itself is covered deterministically by the privilege-free unit tests.
        pytest.skip("symlink creation was silently downgraded by the filesystem")
    with pytest.raises(UnsafeEvidencePath):
        validate_existing_evidence_path(tmp_path, INQUIRY, "a" * 32 + ".png")


@dataclass
class _InspectedPath:
    """Stand-in for the Path surface that the path guard inspects.

    Creating real symlinks needs privileges on Windows, so the guard itself is
    exercised directly here instead of only through a skippable integration test.
    """

    symlink: bool = False
    present: bool = True
    attributes: int = 0
    failure: OSError | None = None

    def _inspect(self) -> None:
        if self.failure is not None:
            raise self.failure

    def is_symlink(self) -> bool:
        self._inspect()
        return self.symlink

    def exists(self) -> bool:
        return self.present

    def stat(self) -> object:
        self._inspect()
        return SimpleNamespace(st_file_attributes=self.attributes)


def test_symlink_evidence_path_is_rejected() -> None:
    with pytest.raises(UnsafeEvidencePath, match="symlink"):
        _reject_symlink(_InspectedPath(symlink=True))


def test_reparse_point_evidence_path_is_rejected() -> None:
    if os.name != "nt":
        pytest.skip("reparse points are a Windows concept")
    with pytest.raises(UnsafeEvidencePath, match="reparse point"):
        _reject_symlink(_InspectedPath(attributes=0x400))


def test_plain_evidence_path_is_accepted() -> None:
    _reject_symlink(_InspectedPath())


def test_uninspectable_evidence_path_fails_closed() -> None:
    # A path that cannot be inspected must not be treated as safe.
    with pytest.raises(UnsafeEvidencePath, match="could not be inspected"):
        _reject_symlink(_InspectedPath(failure=OSError("denied")))


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
