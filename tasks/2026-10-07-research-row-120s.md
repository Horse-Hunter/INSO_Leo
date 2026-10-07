# Task: Research row cooldown120 seconds

status: complete
owner: Integration Executor
created: 2026-10-07
updated: 2026-10-07

## problem / goal
Owner requests normal Research row spacing reduced from180 to120 seconds, with matching
GUI countdown. Apply on current feature/v1-3-integration without new branch or architecture.

## current_facts
Canonical normal row cooldown is V12FlowCoordinator._before_next_row in workflow/v12_flow.py.
Backend wrapper projects the supplied interval; GUI countdown derives its absolute deadline.
Owner expanded scope during execution: all fixed180-second waits become120, including
INSO read/duplicate/history/quotation query retries. V1.3 normal quotation spacing remains0s.

## scope / requirements
Change normal V1.2 Research/purchase row spacing and shared INSO query retries to120. Display cold start02:00 and
elapsed countdown through existing deadline. Preserve original interruptible Event.wait,
no final-row tail wait, V1.3 isolation, four-attempt retry/close-before-wait policy,15min scheduler and approved fixes.
No production access, real SMTP, order replay or installed release replacement.

## acceptance / verification
Update existing row-spacing/stop/restart/combined/backend/GUI regressions rather than duplicate
coverage. Focused, safe/offline full suite, Ruff, diff check, canonical BuildOnly/frozen check.
Commit/push current branch, clean local==remote; provide CEO report in code block.

## completion
Implementation complete; independent review REQUIRED before installation.
Changed two canonical production wait sites plus existing regression expectations/docs.
Focused289 PASS12.18s; full1394 PASS/1 SKIP58.08s; Ruff/diff PASS.
BuildOnly/frozen self-check/release scan PASS; installed release unchanged.
Existing CEO review files untouched. No production or SMTP acceptance; no new dependencies.
