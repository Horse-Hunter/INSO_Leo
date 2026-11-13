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

| RFQ-016 | V1.6 production trust: source status, order age gates, false-alert elimination | CHANGES_REQUESTED / HEALTH_HOLD | `codex/v1-6-independent-scheduling` | CEO independent Review 2026-11-12: Git handover accepted; original 26 + 4 timing failures unresolved; Google cross-operation write safety, purchase root cause and real new-order closure require proof. `control-room/RFQ-016/REVIEW.md` | `control-room/RFQ-016/TASK_SPEC.md` |

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

Owner2026-11-01 requests order-association correction and controlled overwrite/run. Immutable candidate5bb8c941d8f772ea6cfb209b077a91c678b400ea; targeted172PASS, full regression in progress. Prior installed program remains running unchanged until package validation and safe normal exit. No historic report resend.

Correction5bb8c941:172 targeted PASS9.87s,3428 full PASS/1 environment SKIP319.97s; canonical build/scan/candidate self-check PASS. CandidateSHA25608a734889aaf259b01c33a2a4a1619c8de479256093fa2e6f3a0579308da0e58. BLOCKED solely by old app still running/no supported CLI exit; Owner asked for original tray Exit under no-force-kill/no-CU policy. No program replacement/data backup claimed; one needed release candidate retained, test disposables retired.

Normal-exit blocker RESOLVED by Owner original trayExit, normal code0. Correction source5bb8c941 installed/started after verified consistent backup and2875-file manifest/self-checks; startup business/config records unchanged. New GUI163608/originalobserver181684; inquiry204.562s/quotation127.563s/TP11.203s first natural cycles all completed, original900s due intervals retained. Current BUSINESS_RUNNING; real new-mail order association/recipient receipt pending natural trigger, no synthetic real send and no old report replay. Candidate stage/helper retired. Exact receipt and remaining UNKNOWNs in current TEST_REPORT/FINAL_REPORT.

Owner second correction2026-11-01: final candidateceb748a9a9b99a250d905d533b7772a331fe925b reuses confirmed/raw source-brand contract, exact intake/date fallback and truthful retained-quote inventory display. Targeted148PASS8.46s; final full regression in progress. Earlier9d5aba2 complete run3441PASS/1FAIL/1SKIP at unchanged Google test thread10s completion bound, focused full Google file subsequentlyPASS; no runtime/test timeout/notification interval changed. Previous installed5bb source still running; no new build/deploy before final fullPASS. No historical report resend.

Second correction deployed2026-11-01:source325cd19052a17c05c1d2b59a4528a2a38183b8bb;148targetedPASS/3450fullPASS+1existing environmentSKIP. Full-collection Tk font test resource deadlock RESOLVED by main-thread test GC, original deadlines/assertions/runtime intervals unchanged. Owner normal exit/verified backup/program-only swap/self-checks complete, newGUI422964/observer422044, all three natural cycles completed206.297s/85.016s/13.562s and900s due intervals.175SENT/2SUPPRESSED/two historical researchSENT preserved, no replay.35owned assets retired; actual new-mail report association/receipt still pending natural request. No more approval/Owner operation required.


RFQ-016 Owner2026-11-05 full-mail correction: source2bb0c0b7c932f75552bca6d9cccbc87853194676 pushed,127targeted/3570fullPASS+1originalOSskip, false-alert fake SMTP0; originalcanonicalpackage/selfcheck/scan/2875file/7frozen-module verificationPASS. **BLOCKED_NORMAL_EXIT / NOT_INSTALLED**: Owner normalExit received but originalPlaywright poller cannot drain, no supported safe remotecancel; forcedtermination/Chrome/UI/DB/livefileoverwrites not performed. Existing formal source97f0ac6 remains running with exitrequested; original task/evidence/release report have exact limits. No routine CEO review reintroduced; only technical safe-stop barrier. Do not reinterpret historical deployment facts as this mail repair deployed. COMPUTER_USE_NOT_USED.

RFQ016 current2026-11-05 supersedes priorBLOCKED_NORMAL_EXIT: Ownerexplicitone-off forcedstopoldGUI plus laterreadonlyCDPdiagnosis granted. Testedsource2bb0c0b installed/backedup/selfchecked/started, protected16tables/configexact beforestart and175terminalmail/1UNKNOWN/50dates unchangedafterstart. **HEALTH_HOLD**: newfirstinquiry hasnotreturned; quotation/TP/newgenuine noquoteSMTP notverified. Chrome/Googlepages immediatehealthyresponses, exactpending appcallNOT_VERIFIED. Mailrepair notcompleteproductionrecovery. No stale-source sends or additionalforcekill. SeeoriginalRFQ evidence; noextraapproval gate.


RFQ016 latest2026-11-06: e4db3fb926f7ac9f7f656a70f7d29ad77317bf7a installed after verifiedOwnernormalexit/backup and started09:48; original16tables/config identical prestart,175SENT/51intakes/1unknown preserved. Inquiry196.453sdeferred, quotation128.046sdeferred,TP9.641scomplete; no BUSINESS_RUNNING acceptance. Additional native worksheet versus SDK cached-URL race independently reproduced,126targetedPASS, final full running; new candidate not yet installed. Root retains original delivery responsibility, two internal readonly cross-reviewers only. Owner accountability report4967Chinesecharacters created; source/full result will be updated from actual release receipt. COMPUTER_USE_NOT_USED.

RFQ016 2026-11-12 delivery handover (Executor switched to a new window; handover recovery only, no business change): the workspace's 62 uncommitted items were reviewed and committed as `d244241eafe564c79812f860b2491c903a4cee1e` (63 files, +6993/-464) and pushed fast-forward to `codex/v1-6-independent-scheduling` (`635ddfef..d244241e`); GitHub was re-fetched and returned the same commit. The installed formal EXE `00ac7d68d88e1a27eb52e3b7457b4192b699211df1b1f5e3efe0be406eef30bd` is byte-identical to the preserved build copy: 130/130 source Python files, identical `packaging/` and `scripts/`, and all 2875 installed files hash-match the candidate stage. Test-tree to binary correspondence is `NOT_VERIFIED` (the build copy holds no tests). The historical 2026-11-12 run's 26-failure list, aggregate (3920 passed / 26 failed / 11 skipped in 603.42s) and command were recovered verbatim from the executor session transcript; its full stdout is `NOT_RETAINED`. A new full offline run gives 3932 passed / 30 failed / 1 skipped in 566.12s, reproducing all 26 historical failures plus 4 load-sensitive backend tests (3 pass alone, 1 alternates). Runtime logs read-only since the 21:19 install show 6 inquiry / 6 quotation / 6 TP cycles completed with no ERROR; no new-order closure, no mail, no production write. Status at handover was REVIEW_REQUIRED / HEALTH_HOLD; this was superseded by CEO 2026-11-12 independent Review: CHANGES_REQUESTED / HEALTH_HOLD. Git handover is accepted; overall RFQ-016 is not PASS. See `control-room/RFQ-016/REVIEW.md`. COMPUTER_USE_NOT_USED.

## Owner escalation — 2026-11-13: end-to-end production reliability P0

**Priority: P0, Owner-reported, not yet independently diagnosed.** Owner reports **two additional recent unexpected V1.6 stops** and that **almost no real order completes its intended full workflow without some error**. A screenshot was supplied in conversation, but no incident timestamp/order anchor/root-cause evidence was independently correlated with log/database yet. Do not promote a user's qualitative incident report into a fabricated diagnosed cause or claim it is fixed.

**CEO scheduling change:** Pause expanding the Google SA / Sheets API migration, further feature batches and cosmetic-only fixes. Preserve completed Cloud-console/SA feasibility and previous test evidence; no cancellation of committed resources without inspection. This incident takes precedence over the deferred pooled-CDP read-page cleanup and other RFQ-016 work. Current installed EXE `00ac7d68d88e1a27eb52e3b7457b4192b699211df1b1f5e3efe0be406eef30bd` (last Executor-reported, verify locally), frozen source branch `codex/v1-6-independent-scheduling` `4d3c3493fd5b47df68efab0007790043e91b6d42`, shared Chrome CDP/profile, SQLite/WAL/SHM, original state and outbox receipts remain intact. Development and diagnostics only on `workbuddy/v16-rfq016-stabilization`. No unattended production edits, controlled restart/kill, real Google writes, purchase commits, quote clicks, or email sends are authorized by this escalation.

**First executor tranche — FORENSICS ONLY (STOP before coding):**
1. Passively preserve/inspect the exact two most recent production-stop episodes: timestamps, process exit vs application `GLOBAL_STOP` vs `MODULE_PAUSED` vs hung UI, logs around incidents, last successful work, Windows process exit/event evidence if present, original backend health/diagnostics, and exit/restart behavior. No live site navigation or destructive experiments. Distinguish definitive log evidence from hypotheses.
2. Correlate 5–10 recent real order identities (minimized/redacted in reports) across **source read → inquiry eligibility → research → purchase/duplicate checks → external commit/Google status → quote eligibility/input/Update quote CDP click/result → TP/report/notifications when applicable**. Build one order-by-order stage matrix: expected step, observed outcome, exact failure/gap, persisted SENT/UNKNOWN/hold/ledger evidence, and whether this step was actually due/applicable. Do not assume every order should execute every optional module. Never replay historic orders.
3. Separate infrastructure-wide stop from module-specific faults; timeouts, CDP navigation/error tabs/ownership, source rows/age/status misclassification, Google false notifications, GUI truthfulness, SMTP exact durable receipt, and cross-module scheduler/liveness. Prioritize shared root causes with actual reproductions and corrected causal chain over scattershot patches.
4. Report a **ranked cause/evidence table** for both stops and failed-order classes; list precise source locations and smallest scoped testable fixes. Any real unknown write/dispatch must remain protected; no forced success flags, suppression of genuine alerts, blindly retrying purchases/quote scripts or resetting SQLite.
5. Deliver the evidence and a *minimal proposed repair plan* for CEO Review **before altering production logic**. Existing 30 baseline test failures must be accounted for, not silently hidden. When implementation is separately authorized, use deterministic offline incident regressions and end-to-end simulated order lifecycles, not pass-count alone; later obtain Owner-approved, bounded natural business acceptance with correct final states, no duplicates/false stop/false mail before release.

**Release acceptance is not the count of passing unit tests:** verify that representative real order paths can complete their **applicable** life cycle with correct persisted source/status/receipt and without false `GLOBAL_STOP`, no accidental replay and truthful GUI. No claim of production success until source, tests, built artifact and live acceptance are independently reviewed. New code or deployment **NOT AUTHORIZED** by this triage instruction. Overall RFQ-016 remains `CHANGES_REQUESTED / HEALTH_HOLD`.
