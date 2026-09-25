"""Contained, opaque evidence-path preparation; no capture or image IO."""

from __future__ import annotations

import os
import re
import uuid
from dataclasses import dataclass
from pathlib import Path

from .v12_contracts import ReasonCode

_INQUIRY_ID = re.compile(r"^inq_[0-9a-f]{24}$")
_EVIDENCE_FILE = re.compile(r"^[0-9a-f]{32}\.png$")
_EVIDENCE_REF = re.compile(r"^evidence/inq_[0-9a-f]{24}/[0-9a-f]{32}\.png$")


class UnsafeEvidencePath(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class EvidenceMetadata:
    reason_code: ReasonCode
    capture_attempted: bool
    redaction_confirmed: bool
    relative_ref: str | None
    retention_days: int = 30

    def __post_init__(self) -> None:
        if self.retention_days != 30:
            raise ValueError("V1.2 evidence retention policy is fixed at 30 days")


def capture_is_safe(*, crop_confirmed: bool, redaction_confirmed: bool) -> bool:
    """Capture is permitted only when both crop and redaction are verified."""

    return crop_confirmed and redaction_confirmed


def new_evidence_reference(runtime_root: str | Path, inquiry_id: str) -> str:
    """Prepare an opaque relative reference after containment/symlink checks.

    This helper creates the inquiry directory only. It never captures or writes
    an image. Callers must later prove crop/redaction safety before image IO.
    """

    if not _INQUIRY_ID.fullmatch(inquiry_id):
        raise UnsafeEvidencePath("invalid inquiry identifier")
    root = Path(runtime_root).resolve(strict=True)
    evidence_root = root / "evidence"
    _reject_symlink(evidence_root)
    evidence_root.mkdir(exist_ok=True)
    evidence_resolved = evidence_root.resolve(strict=True)
    if not _inside(evidence_resolved, root):
        raise UnsafeEvidencePath("evidence root escaped runtime root")
    inquiry_dir = evidence_root / inquiry_id
    _reject_symlink(inquiry_dir)
    inquiry_dir.mkdir(exist_ok=True)
    inquiry_resolved = inquiry_dir.resolve(strict=True)
    if not _inside(inquiry_resolved, evidence_resolved):
        raise UnsafeEvidencePath("inquiry path escaped evidence root")
    filename = f"{uuid.uuid4().hex}.png"
    if not _EVIDENCE_FILE.fullmatch(filename):
        raise UnsafeEvidencePath("opaque evidence filename invalid")
    return f"evidence/{inquiry_id}/{filename}"


def validate_evidence_reference(reference: str) -> str:
    if not _EVIDENCE_REF.fullmatch(reference):
        raise UnsafeEvidencePath("evidence reference is not a safe relative path")
    return reference


def validate_existing_evidence_path(
    runtime_root: str | Path,
    inquiry_id: str,
    filename: str,
) -> Path:
    if not _INQUIRY_ID.fullmatch(inquiry_id) or not _EVIDENCE_FILE.fullmatch(filename):
        raise UnsafeEvidencePath("invalid evidence path component")
    root = Path(runtime_root).resolve(strict=True)
    candidate = root / "evidence" / inquiry_id / filename
    current = root
    for part in ("evidence", inquiry_id, filename):
        current = current / part
        _reject_symlink(current)
    resolved = candidate.resolve(strict=False)
    if not _inside(resolved, root / "evidence"):
        raise UnsafeEvidencePath("resolved evidence path escaped evidence root")
    return resolved


def _reject_symlink(path: Path) -> None:
    try:
        if path.is_symlink():
            raise UnsafeEvidencePath("symlink evidence path is not allowed")
        if os.name == "nt" and path.exists():
            attributes = getattr(path.stat(), "st_file_attributes", 0)
            if attributes & getattr(__import__("stat"), "FILE_ATTRIBUTE_REPARSE_POINT", 0x400):
                raise UnsafeEvidencePath("reparse point evidence path is not allowed")
    except OSError as exc:
        raise UnsafeEvidencePath("evidence path could not be inspected") from exc


def _inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root.resolve(strict=False))
        return True
    except ValueError:
        return False
