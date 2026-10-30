# Task: RFQ-016 production trust recovery

status: in_progress
owner: Codex Executor; independent review CEO
created: 2026-10-30
updated: 2026-10-30

## problem and goal
Frozen requirements: control-room/RFQ-016/TASK_SPEC.md at be46555471cb78786437d04bf61210a3d384a74e. Stop false anomaly email, exclude expired automatic orders, show actual current customer status without clearing unknown external effects.

## scope and requirements
Reuse current V1.6 paths, preserve 7574516 and dirty work. Automatic inquiry/quotation7 Shanghai calendar days; TP/future personalized work1 calendar month; explicit Owner single-order age exemption only. Double evidence review and durable once-per-incident notification in existing outbox. Current-source projection independent from procurement history/UNKNOWN. Offline fake SMTP/Google/INSO/SQLite only. No dependency install, second CDP, Computer Use, production deployment, process kill or real test mail.

## acceptance and verification
- Correctly reproduce former failures before repair.
- Zero SMTP attempts for false/stale/recovered/old/unverified samples; one for a verified ongoing actionable incident across restart.
- Shared date/status gates cover discovery, existing queue, recovery, independent continuation and effects.
- Owner single-order authorization and all UNKNOWN/SENT guards retained.
- Source success refreshes task center; failure marks stale; UNKNOWN remains.
- Full source regression, lint and diff review required; execution evidence recorded in control-room/RFQ-016/EXECUTION_LOG.md.

## completion
Source verification complete:3272PASS/1SKIP;49 RFQ016 regressions PASS; Ruff/diff PASS. Source commit and CEO review recorded in the RFQ final report. Production remediation NOT_VERIFIED / NOT_DEPLOYED. No follow-on business task authorized.
