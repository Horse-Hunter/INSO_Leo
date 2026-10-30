"""Evidence policy at enqueue AND dispatch; no timers or external I/O."""
import json
import re
from datetime import datetime, timedelta

from .v12_contracts import NotificationKind


def review_reason(command, now):
    if command.kind is not NotificationKind.PURCHASE_EXCEPTION:
        return None
    try:
        proof = json.loads(command.review or "null")
        if not isinstance(proof, dict):
            return "EVIDENCE_MISSING"
        verified = datetime.fromisoformat(proof["verified_at"])
        if verified.tzinfo is None or not timedelta(0) <= now-verified <= timedelta(minutes=15):
            return "EVIDENCE_STALE"
        if not all(proof.get(k) is True for k in ("active", "current_business", "needs_owner", "verified")):
            return "EVENT_NOT_CURRENT"
        if not all(isinstance(proof.get(k), str) and proof[k].strip()
                   for k in ("incident_key", "module", "reason_code", "action", "original_event", "uncertainty")):
            return "EVIDENCE_INCOMPLETE"
        if not re.fullmatch(r"[A-Z_]{1,64}", proof["reason_code"]):
            return "REASON_UNVERIFIED"
        category = proof.get("category")
        from .automatic_admission import age_reason
        if not proof.get("manual") and age_reason(proof.get("inquiry_day"), now, module=proof.get("business_module", "quotation")):
            return "ORDER_AGE_EXCLUDED"
        if category == "persistent_stop":
            if not proof.get("retries_exhausted") or proof.get("completed_cycles", 0) < 3:
                return "RECOVERY_NOT_EXHAUSTED"
            if "last_success" not in proof:
                return "LAST_SUCCESS_UNVERIFIED"
        elif category == "manual_login":
            if proof["reason_code"] not in {"INSO_AUTHENTICATION_REQUIRED", "MANUAL_VERIFICATION_REQUIRED", "CREDENTIAL_REJECTED", "SHEETS_AUTH_UNAVAILABLE"}:
                return "MANUAL_REQUIREMENT_UNVERIFIED"
        elif category == "business_confirmed":
            if proof["reason_code"] not in {"MODEL_DIFFERENCE_CONFIRMED", "PURCHASE_FOLLOW_UP_REQUIRED", "SOURCE_STATUS_NOT_UPDATED"}:
                return "BUSINESS_EVENT_UNVERIFIED"
        elif category == "unknown_write":
            if proof["reason_code"] not in {"UPDATE_RESULT_UNCONFIRMED", "SAVE_OUTCOME_UNKNOWN", "UNKNOWN_WRITE_OUTCOME"}:
                return "WRITE_EVENT_UNVERIFIED"
        else:
            return "CATEGORY_UNVERIFIED"
    except (ValueError, TypeError, KeyError, OverflowError):
        return "EVIDENCE_INVALID"
    return None
