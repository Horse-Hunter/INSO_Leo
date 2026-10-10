# Control Room Coordination

| RFQ | Title | Status | Branch | Review | Spec |
| --- | --- | --- | --- | --- | --- |
| RFQ-001 | V1.2 pre-save live acceptance closeout | REVIEWED_DONE | `feature/v1-2` | REQUIRED | `control-room/RFQ-001/TASK_SPEC.md` |
| RFQ-002 | V1.2 runnable Windows release closeout | REVIEWED_DONE | `feature/v1-2` | REQUIRED | `control-room/RFQ-002/TASK_SPEC.md` |
| RFQ-003 | V1.2 purchase fault isolation and recovery | REVIEWED_DONE | `feature/v1-2` | REQUIRED | `control-room/RFQ-003/TASK_SPEC.md` |

| RFQ-004 | V1.3 INSO quotation read pipeline | REVIEWED_DONE | `feature/v1-3` | REQUIRED | `control-room/RFQ-004/TASK_SPEC.md` |

| RFQ-005 | V1.3 Google quotation update pipeline | REVIEWED_DONE | `feature/v1-3` | REQUIRED | `control-room/RFQ-005/TASK_SPEC.md` |

Status is changed by the active executor/reviewer. Requirement meaning is changed only by Owner/CEO.

| RFQ-006 | V1.2 + V1.3 production integration and release | REVIEWED_DONE | `feature/v1-3-integration` | REQUIRED | `control-room/RFQ-006/TASK_SPEC.md` |

| RFQ-007 | Sync reviewed V1.2 alert/cooldown increment into V1.3 | REVIEWED_DONE | `feature/v1-3-sync-v12-increment` | REQUIRED | `control-room/RFQ-007/TASK_SPEC.md` |

RFQ-006 Owner closeout increment (2026-10-07) requires independent review. Prior reviewed
baseline2a32007 and RFQ-007 reviewed2c9f704 remain approved; RFQ-007 status is unchanged.

| RFQ-008 | GUI poll counters, source field edits and selected-row rerun | REVIEWED_DONE | `feature/v1-3-integration` | REQUIRED | `control-room/RFQ-008/TASK_SPEC.md` |

## V1.3 post-review Owner increment sync — 2026-10-08

Increment review status: REVIEWED_DONE on `codex/v13-readiness-repair`.
Scope: background Chrome, purchase-completion false alarm, fuzzy model comparison,
source B/actual-model L notification, final INSO original-full-model search.
Owner-authorized production deployment is recorded separately; CEO independent PASS is recorded in `control-room/RFQ-008/CEO_SYNC_REPORT_2026-10-08.md`.
Report: `control-room/RFQ-008/CEO_SYNC_REPORT_2026-10-08.md`.
Historical RFQ REVIEWED_DONE records above are unchanged. Existing quotation hold
in Owner's selected case remains unresolved; no automatic replay was performed.

| RFQ-009 | V1.4 one-shot order email structure inspection | REVIEWED_DONE | `codex/v1-4-order-mail-inspection` | REQUIRED | `control-room/RFQ-009/TASK_SPEC.md` |

| RFQ-010 | V1.4 sales header and Owner review | REVIEWED_DONE | `codex/v1-4-order-mail-inspection` | REQUIRED | `control-room/RFQ-010/TASK_SPEC.md` |

| RFQ-011 | V1.4 unsaved sales details and ICNET package preflight | REVIEWED_DONE | `codex/v1-4-order-mail-inspection` | REQUIRED | `control-room/RFQ-011/TASK_SPEC.md` |

| RFQ-012 | Owner single-click oldest unfilled order | REVIEWED_DONE | `codex/v1-4-order-mail-inspection` | REQUIRED | `control-room/RFQ-012/TASK_SPEC.md` |

| RFQ-013 | Owner native PDF upload after field verification | REVIEWED_DONE | `codex/v1-4-order-mail-inspection` | REQUIRED | `control-room/RFQ-013/TASK_SPEC.md` |

| RFQ-014 | All229/shawn SMTP message clarity | REVIEWED_DONE | `codex/v1-4-order-mail-inspection` | REQUIRED | `control-room/RFQ-014/TASK_SPEC.md` |

Owner2026-10-10 confirmed Review completion and authorized V1.4 packaging/deployment
of business HEAD7a5728388fc14cd685521d520e23fbfa19536988. Independent PASS is recorded
in control-room/RFQ-014/CEO_REVIEW.md (review commit3eee69a; status commitc023b60).
| RFQ-015 | Authorized V1.4 Windows release | DEPLOYED | `codex/v1-4-order-mail-inspection` | Owner authorized | `control-room/RFQ-015/TASK_SPEC.md` |
