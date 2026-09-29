# Project Baseline

## Operating model

- Work is RFQ-driven. The complete current requirement lives in Control Room, not chat.
- Any executor must be able to start from only `执行 RFQ-XXX`.
- Review is owned by CEO: Owner returns to the CEO conversation and says only `Review RFQ-XXX`.
- Git/code/tests/evidence are implementation truth; Task Spec is requirement truth; `COORDINATION.md` is status truth.
- CEO instructions must stay requirement-progress focused: business outcome, acceptance, relevant source docs, Safety boundary. No hundreds-line implementation manuals.
- If progress is slow, reread the RFQ and workflow rules and reduce scope to the shortest path that advances acceptance.
- Repeated failures become shared code/contracts/regression tests rather than repeated Owner guidance.
- Owner is not a technical message bus.

## Roles

- Owner: final business authorization.
- CEO: requirement clarification, Task Spec, business rules, architecture boundary, Safety/Write Gate, and independent RFQ review.
- Executor: implementation, debugging, tests, live verification, evidence, execution log, final report, commit/push.
- CEO Review: independently verifies implementation evidence and returns only PASS / CHANGES_REQUESTED; does not implement fixes inside the review.

## Stable project anchors

- V1.1 Research Stability: CLOSED, `release/v1.1 = 44cd4a4cdb05fc069189801d24c4710bfd9445f3`.
- V1.2 branch: `feature/v1-2`.
- Production browser: Chrome only.
- Credential source: Core Vault only.
- INSO runtime readiness is a shared capability; ordinary runtime/session recovery is not an Owner blocker.
- V1.2 Production Write Gate: CLOSED.
