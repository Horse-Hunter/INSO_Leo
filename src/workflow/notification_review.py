"""Evidence policy at enqueue AND dispatch; no timers or external I/O."""
import json
import re
from datetime import datetime, timedelta

from .v12_contracts import NotificationKind

RUNTIME_SAFETY_REASONS = frozenset({
    "GOOGLE_TAB_IDENTITY_UNCONFIRMED", "GOOGLE_OPERATION_NOT_CLOSED",
    "GOOGLE_WRITE_SETTLEMENT_UNCONFIRMED", "GOOGLE_AUTHENTICATION_REQUIRED",
    "CDP_PAGE_CREATION_UNCONFIRMED", "CDP_PAGE_CLEANUP_UNCONFIRMED",
    "CDP_PAGE_OWNERSHIP_UNCONFIRMED", "PROGRAM_INTERNAL_STOP", "PROGRAM_OPERATION_STALLED",
})


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
        if category == "runtime_login":
            if (proof.get("reason_code") != {"INSO": "INSO_AUTHENTICATION_REQUIRED", "IC.net": "IC_NET_VERIFICATION_REQUIRED"}.get(proof.get("module"))
                    or proof.get("module") not in {"INSO", "IC.net"}
                    or proof.get("manual_verification_confirmed") is not True
                    or not proof.get("run_id") or command.inquiry_id is not None):
                return "MANUAL_REQUIREMENT_UNVERIFIED"
            return None
        if category == "manual_order":
            from .order_notifications import MANUAL_ORDER_CODES
            if (proof.get("module") != "sales_order" or proof.get("reason_code") != "MANUAL_ORDER_NEEDS_REVIEW"
                    or proof.get("event_code") not in MANUAL_ORDER_CODES
                    or proof.get("manual_invocation") is not True or proof.get("automatic_stopped") is not True
                    or command.command_id != "v14-exception:"+str(proof.get("invocation_id"))
                    or command.inquiry_id != "v14-notify:"+str(proof.get("invocation_id"))):
                return "BUSINESS_EVENT_UNVERIFIED"
            from .automatic_admission import age_reason
            return "ORDER_AGE_EXCLUDED" if age_reason(proof.get("invoked_at"), now, module="inquiry") else None
        if category == "service_stop":
            if (proof.get("module") != "mail_research" or proof.get("account") != "linan229@qq.com"
                    or proof.get("reason_code") not in {"IMAP_AUTH_REQUIRED", "REPORT_DELIVERY_UNKNOWN", "CDP_RESOURCE_UNCONFIRMED"}
                    or proof.get("completed_cycles", 0) < 3 and proof.get("reason_code") not in {"REPORT_DELIVERY_UNKNOWN", "CDP_RESOURCE_UNCONFIRMED"}):
                return "SERVICE_INTERVENTION_UNVERIFIED"
            return None
        if category == "runtime_stop":
            if (proof.get("module") != "business_runtime"
                    or proof.get("reason_code") != "PROGRAM_SAFETY_PAUSED"
                    or proof.get("stop_reason") not in RUNTIME_SAFETY_REASONS
                    or (proof.get("stop_reason") == "PROGRAM_INTERNAL_STOP"
                        and not isinstance(proof.get("actual_stop_reason"), str))
                    or (proof.get("stop_reason") == "PROGRAM_INTERNAL_STOP"
                        and not re.fullmatch(r"[A-Z_]{1,64}", proof["actual_stop_reason"]))
                    or (proof.get("stop_reason") == "PROGRAM_OPERATION_STALLED"
                        and not isinstance(proof.get("stall_generation"), str))
                    or proof.get("halted") is not True
                    or proof.get("stop_state") not in {"GLOBAL_STOP", "MODULE_PAUSED"}
                    or not isinstance(proof.get("run_id"), str) or not proof["run_id"]
                    or command.inquiry_id is not None):
                return "RUNTIME_STOP_UNVERIFIED"
            return None
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
            if proof["reason_code"] not in {"MODEL_DIFFERENCE_CONFIRMED", "PURCHASE_FOLLOW_UP_REQUIRED", "SOURCE_STATUS_NOT_UPDATED", "NO_MATCHING_PRODUCT", "AI_RECOGNITION_MISMATCH"}:
                return "BUSINESS_EVENT_UNVERIFIED"
            if proof["reason_code"] == "NO_MATCHING_PRODUCT" and (
                    proof.get("module") != "inquiry" or proof.get("business_module") != "inquiry"
                    or proof.get("research_status") != "EXCEPTION"
                    or proof.get("no_quote_confirmed") is not True
                    or proof.get("purchase_absent") is not True
                    or not proof.get("source_binding") or not proof.get("research_recorded_at")):
                return "BUSINESS_EVENT_UNVERIFIED"
            if proof["reason_code"] == "AI_RECOGNITION_MISMATCH" and (
                    proof.get("module") != "inquiry" or proof.get("pre_submit_confirmed") is not True
                    or proof.get("purchase_outcome") != "VALIDATION_FAILED" or proof.get("dispatch_absent") is not True
                    or not proof.get("source_binding")):
                return "BUSINESS_EVENT_UNVERIFIED"
        elif category == "unknown_write":
            if proof["reason_code"] not in {"UPDATE_RESULT_UNCONFIRMED", "SAVE_OUTCOME_UNKNOWN", "UNKNOWN_WRITE_OUTCOME"}:
                return "WRITE_EVENT_UNVERIFIED"
        else:
            return "CATEGORY_UNVERIFIED"
    except (ValueError, TypeError, KeyError, OverflowError):
        return "EVIDENCE_INVALID"
    return None
