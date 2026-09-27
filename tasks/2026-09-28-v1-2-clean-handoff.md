# Task: V1.2 clean handoff and pre-save gate

status: blocked
owner: Main Programmer
created: 2026-09-28
updated: 2026-09-28

## problem
`docs/CURRENT_TASK.md` contains superseded discovery history, and the launcher retains Edge compatibility although the supported browser is Chrome only. V1.2 pre-save integration still needs a complete implementation and verification pass.

## goal
Fast-forward `feature/v1-2` to the fetched remote, compact current status, remove Edge runtime compatibility, complete and verify all code/integration work before the first real Save gate, and keep Production Write Gate CLOSED.

## current_facts
- Remote `origin/feature/v1-2` fetched at `74cb518` and local branch fast-forwarded normally from `fcc842a`.
- V1.1 Research Stability is CLOSED; `release/v1.1 = 44cd4a4cdb05fc069189801d24c4710bfd9445f3`.
- V1.2 Phase A is COMPLETE: exact query and nonempty history pass; creator is not exposed by INSO; quote/currency confirmed; AI recognition/preview confirmed; parent unsaved read-back confirmed.
- Real Save, Send, SMTP and Sheets write have not occurred. Production Write Gate is CLOSED.

## scope
- Compact `docs/CURRENT_TASK.md` to current facts, stage, remaining work, latest verification, gate, and concrete blockers.
- Remove all Edge-specific runtime code, tests, config/diagnostic support, and legacy `EDGE_CDP_ATTACH_FAILED` naming; preserve Chrome behavior.
- Complete duplicate → Research → routing, persistence/state, notification/outbox fake integration, purchase draft, read-only reconciliation, GUI DTO/state integration, deterministic tests, and authorized read-only live verification as needed.
- Commit and push `feature/v1-2` when verified.

## non_scope
- Any real Save, Save-and-Send, Send, SMTP, or Google Sheets write.
- Reset, clean, force push, V1.1 resynchronization, or rollback to `42e2327` / `fcc842a`.

## acceptance
- [x] Local feature branch is a normal fast-forward of the fetched remote tip.
- [x] `docs/CURRENT_TASK.md` is about 2–3 KB and has no superseded discovery history.
- [x] No Edge runtime compatibility or legacy Edge error naming remains in code/tests.
- [ ] All pre-save integration work is implemented and deterministic tests pass. The existing deterministic integration is verified, but production parent-field and save-reconciliation adapters are absent.
- [ ] Chrome-only live read-only verification; this computer-use session exposed Edge only, and it was not used as a substitute.
- [x] Production Write Gate remains CLOSED; no prohibited external write/action occurred.
- [ ] Commit pushed to `origin/feature/v1-2` and final diff reviewed.

## verification
## verification

- `python -m pytest -q --tb=short --basetemp runtime/pytest-v12-final-20260928`: 631 passed, 11 skipped.
- `python -m ruff check src tests`: passed.
- `tests/launcher/test_release_infrastructure.py`: 17 passed.
- `git diff --check`: passed after removing trailing whitespace.
- Search found no `msedge.exe`, `is_edge`, `EDGE_CDP_ATTACH_FAILED`, or Edge-specific support in `src/` or `tests/`.
- No Chrome surface was available for live verification; no browser UI or production system was interacted with.

## completion
- status: incomplete
- changed: compacted current task, removed Edge launcher branch/test/error naming, and aligned architecture browser baseline.
- verified: full pytest, Ruff, focused launcher tests, and diff check passed.
- limitations: production parent-field writer and live save reconciler still need verified Chrome-bound implementations; Production Write Gate remains CLOSED.
