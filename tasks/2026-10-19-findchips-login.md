# Findchips checkbox and bounded login correction

status: REVIEW_REQUIRED
owner: Codex
created: 2026-10-19

## Owner scope / acceptance
On the existing V1.4 development branch, reuse Findchips credentials, Playwright
controls and login-outcome checks. After filling credentials, check every visible,
enabled ordinary checkbox without toggling checked ones. Confirm checked state,
wait a full five seconds, then use the existing login button. Observe the first
click briefly; only a completely unresponsive attempt may receive one extra
click. At most two clicks per login. A normal response must suppress retry.
Only Findchips code and focused offline tests change. No other sites, dependency,
browser configuration, credentials, production data, packaging or deployment.
Owner explicitly authorizes commit and push to codex/v1-4-order-mail-inspection;
delivery remains REVIEW_REQUIRED. Preserve unrelated local dirty work.

## Reuse audit
Existing ensure_findchips_signed_in owns both research and login-sweep entry.
Reuse its readiness, unique_visible_control, challenge and await_login_outcome
checks. Shared submit_login_form has no between-fill-and-click hook; keep the
site-specific checkbox/wait sequence inside Findchips rather than changing all
sites or adding a general login framework. Existing two-attempt loop retries
any unconfirmed outcome; restrict the second click to no observed response.
Existing Findchips tests cover URL refusals/readiness and mocked bounded retry.

## Verification / completion
Implemented only in src/research/findchips.py, with focused synthetic coverage
in tests/research/test_findchips.py. Ordinary visible/enabled native checkboxes
are checked and verified after credential fill, followed by wait(5.0). Observe
the initial submit for two seconds through the original outcome checker; a
document/XHR/fetch request (including one still pending), changed URL/content or
disabled submit suppresses another click and retains the existing outcome wait.
Only complete silence allows a second click; no third attempt exists.

Verification: `python -m pytest tests/research/test_findchips.py
tests/research/test_site_login.py tests/launcher/test_site_login_sweep.py -q
-p no:cacheprovider` -> **109 passed in 0.76s**. The parameterized Findchips
test exercises real login/outcome control flow with synthetic controls and clock:
two unchecked options, one already checked, hidden/disabled exclusions, exact
five-second ordering, initial success, silence/retry success, persistent silence,
pending request, changed page, busy button, delayed success and explicit refusals.
`python -m ruff check src/research/findchips.py tests/research/test_findchips.py`
and `git diff --check` -> PASS. Final scoped diff reviewed.

Live website acceptance remains UNKNOWN; no real login, credentials, browser,
runtime data, network business operations, packaging or deployment were used.
Reused existing V1.4 worktree; no worktree, release copies or owned disposable
test artifacts created. Unrelated dirty work preserved. Commit/push only these
two files and this packet to the original V1.4 branch; independent review remains
required. No follow-on business task started.

## Publication
The original local branch and origin/V1.4 have diverged before this repair.
Remote identity is confirmed by the existing remote configuration, prior push
reflog and control-room/RFQ-006/TASK_SPEC.md (Horse-Hunter/INSO_Leo). Publish only
this repair's three files as a child of the remote V1.4 tip, using a disposable
Git index; preserve the local branch/checkpoint and all unrelated working files.
The remote and local pre-repair Findchips/shared-login source and tests are
identical. No force push, merge of unrelated local commits or worktree reset.
