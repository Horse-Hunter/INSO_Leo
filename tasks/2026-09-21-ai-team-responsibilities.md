# Task: Document AI team responsibilities

status: complete
owner: Codex
created: 2026-09-21
updated: 2026-09-21

## problem

The repository does not yet record the confirmed AI collaboration roles, decision hierarchy, fact priority, and chat handoff practice.

## goal

Add a concise durable AI team guide and link it from the repository map.

## current_facts

- The Human Owner, Architecture Chat, Module Chats, and Codex roles have distinct decision and execution responsibilities.
- GitHub `main` is the highest-priority source of formal project facts.
- Pre-existing uncommitted Credential Vault and reference-file work is outside this task.

## scope

- Create `docs/AI_TEAM.md`.
- Add its entry to the `docs/AI_START_HERE.md` repository map.
- Record and verify this task.

## non_scope

- Module architecture, product baseline, business code, new modules, or pre-existing worktree changes.

## requirements

- Keep the team guide concise, approximately one page or less.
- Preserve the confirmed role hierarchy, decision ownership, fact priority, and handoff sequence.
- Commit and push only this task's three files.

## acceptance

- [x] `docs/AI_TEAM.md` contains all confirmed roles and decision principles.
- [x] The fact-priority order and three-step chat handoff are explicit.
- [x] `docs/AI_START_HERE.md` links the new document.
- [x] The scoped diff contains no business or module architecture change.

## verification

- Check required headings, roles, priority statements, handoff steps, file length, and repository-map entry.
- Run scoped `git diff --check` and review the complete scoped diff.
- Verify staged and committed file scope before pushing.

## completion

- status: complete
- changed: added the concise AI team guide and its repository-map entry
- verified: role, decision, priority, handoff, length, protected-file, scoped diff, and formatting checks passed
- limitations: none
