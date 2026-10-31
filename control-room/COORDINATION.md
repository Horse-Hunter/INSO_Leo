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

| RFQ-016 | V1.6 production trust: source status, order age gates, false-alert elimination | DEPLOYED / BUSINESS_RUNNING | `codex/v1-6-independent-scheduling` | Owner final release authorized | `control-room/RFQ-016/TASK_SPEC.md` |

Historical RFQ-016 source-review sequence (release/subject-policy holds below superseded by Owner final2026-10-31 authorization; current status is the row above and final receipt below):

RFQ-016 is a new Owner/CEO production-correctness requirement after the unpushed local installation report `7574516f...`. The verified remote SHA at spec start was `f8f2c321...`; never infer installed source from branch. Code implementation and offline regression are authorized; *no automatic production deployment or external test email* until separate review/release authorization. Preserve current real orders and protected UNKNOWN write outcomes. No agent Computer Use.

CEO source review of `77a3e83` (documentation commit `adcff10`) identified three gating gaps: unknown quote price-baseline commit before a durable hold after a no-op alert enqueue, stale-source-backed persistent stop mail, and missing event applicability for delayed important-order mail. Details and exact corrective regression expectations in `control-room/RFQ-016/TASK_SPEC.md`. RFQ016 remains SOURCE_NOT_APPROVED / NOT_DEPLOYED; no release authorization.

Owner2026-10-30 detailed-mail/independent-IMAP extension is tracked under `tasks/2026-10-30-mail-research-upgrade.md` as part of RFQ016 source remediation. Final source `08a00cf6abacc73a4c06b7721f4dfff51fd5e373` passed 3334 offline tests with1environment skip; independent source re-review remains pending. No installation authorization.

CEO independent re-review 2026-10-31 of final application SHA `08a00cf6...`, final report SHA `e2965645...`: A/B/C quote-hold, stale alert and historical business email paths provisionally accepted; new independent IMAP latest-MPN cache freshness P0, background-first main scheduling contention P1, and exact-From header spoof risk remain. Review and acceptance tests recorded in original RFQ-016 task and `tasks/2026-10-30-mail-research-upgrade.md`; no source approval or live installation authorization.

Second-review Executor delivery: `1dd31b283ec34126637e173830dbc3c321b7c89d`,3354PASS/1SKIP; D/E fixed in source, prior A/B/C retained. Sender proposal/limitation recorded in original subtask; live IMAP-command execution SECURITY_ENABLEMENT_BLOCKED (no trustworthy QQ contract/Owner risk acceptance). CEO source re-review required; NOT_DEPLOYED; production NOT_VERIFIED.

CEO third source review of `1dd31b283ec34126637e173830dbc3c321b7c89d` (delivery `0f33b97`) provisionally accepts D/E and keeps real QQ sender authentication `SECURITY_ENABLEMENT_BLOCKED`. Single remaining material source issue: optional independent mail-research startup/resource failure indefinitely defers existing verified IMPORTANT_ORDER and PURCHASE_FOLLOW_UP_REQUIRED notifications. Original RFQ-016 task now records required bounded truthful fallback and fake-SMTP integration tests. No production install authority.

F-only Executor delivery: `55ba0f230ce4a42eeda78d4aa942e9065bfc4ba3`,39targetedPASS and3393fullPASS/1SKIP. Original important/follow-up notices use120s durable enrichment budget, then truthful fallback through unchanged final business/recipient/SENT/UNKNOWN gates. A/B/C/D/E retained; QQ security hold retained. REVIEW_REQUIRED / NOT_DEPLOYED; production NOT_VERIFIED.

CEO fourth source review of application `55ba0f230ce4a42eeda78d4aa942e9065bfc4ba3` (Executor F evidence `9d09ccde`) closes final F issue at source level: original IMPORTANT_ORDER and overdue purchase-follow-up notices wait <=120s from durable command creation for healthy six-source enrichment; fallback truthfully and only at next originally eligible dispatch without invented market prices/stock/total or bypassing original current source/event/recipient/SENT/UNKNOWN reviews. Executor reports39 targeted and3393 full PASS/1 symlink SKIP. **RFQ016 CORE SOURCE PASS / READY_FOR_SEPARATE_RELEASE_DECISION**, **IMAP real commands remain SECURITY_ENABLEMENT_BLOCKED**, **production NOT_DEPLOYED/NOT_VERIFIED**. Immutable source/test tree and independent review in original RFQ016 task. No release/install/livemail authorization; no Computer Use.

Owner final instruction authorizes subject-only IMAP activation and one controlled RFQ016 production release after tests. DEPLOYED_NATURAL_VERIFICATION; prior SECURITY_ENABLEMENT_BLOCKED/separate-release gate superseded only by this explicit authorization. Installed source4b61f521;3414PASS/1SKIP; GUI ready; all three natural inquiry/quotation/TP cycles completed; authenticated IMAP baseline established with no historical jobs. Actual new-mail report/SMTP awaiting natural trigger. See current TEST_REPORT/FINAL_REPORT/release report.
