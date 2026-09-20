# Task Protocol

All implementation work starts from one Task Packet stored in `tasks/`. A packet is the shared contract among the requester, ChatGPT, Codex, reviewers, and Git history.

## File convention

- Recommended name: `tasks/YYYY-MM-DD-short-slug.md`
- Use one packet for one bounded outcome.
- Update the packet when verified facts, scope, or acceptance criteria change.
- Preserve unresolved items as `UNKNOWN` or explicit open questions.

## Task Packet template

```markdown
# Task: <short title>

status: proposed | ready | in_progress | blocked | complete
owner: <name or UNKNOWN>
created: YYYY-MM-DD
updated: YYYY-MM-DD

## problem
What is wrong, missing, or valuable to improve? Include observable evidence.

## goal
State the desired outcome, not an implementation wish list.

## current_facts
- Verified fact with source or repository path.
- UNKNOWN: fact that must not be guessed.

## scope
- Work explicitly included in this task.

## non_scope
- Related work explicitly excluded from this task.

## requirements
- Functional, technical, data, safety, and documentation requirements.

## acceptance
- [ ] Observable condition that must be true for acceptance.

## verification
- Command, review, test, or inspection used to prove each acceptance item.
- Record environment limitations and checks that could not be run.

## completion
- status: pending | complete | blocked
- changed: files and behavior changed
- verified: checks run and outcomes
- limitations: remaining risks, UNKNOWN items, and follow-up candidates
```

## Lifecycle

1. **Propose:** capture the problem, goal, known evidence, and unknowns.
2. **Ready:** agree on boundaries, requirements, acceptance, and verification.
3. **Implement:** make only the changes authorized by the packet; keep it current.
4. **Verify:** run applicable checks and inspect the final diff.
5. **Complete:** fill in `completion`; do not silently roll follow-up work into the task.

## Completion standard

A task is complete only when its acceptance criteria are satisfied, verification results are recorded, documentation is consistent, and the diff contains no unrelated change. If completion cannot be proven, mark the task blocked or incomplete and state why.
