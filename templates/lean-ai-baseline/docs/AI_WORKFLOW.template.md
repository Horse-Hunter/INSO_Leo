# Workflow — reusable template

Owner defines intent → CEO writes RFQ Task Spec → one Executor implements/reuses/tests/verifies → CEO independently reviews PASS/CHANGES_REQUESTED. Requirement/status truth lives in Control Room; never solely in chat.

**Every handoff or new window:** read `AGENTS.md`, current RFQ status/spec/log/Review, inspect Git branch/HEAD/diff/worktrees **and** live processes/external effects. Preserve uncommitted work and single-Executor ownership.

**Before external effect:** durable existing RFQ checkpoint with target, authorization, pre-state, guard and intent. **After:** receipt, verified actual result/UNKNOWN and next single action. On sudden quota/context loss, successor must reconcile real state before continuing. The native business ledger/idempotency guard is indispensable; markdown alone is not a write lock. Do not infer program stopped after chat exits.

Implement minimum reuse-first changes, keep Owner-facing reports concise, store exact tests/evidence/commit and cleanup in existing RFQ records. Any temporary handoff is consumed and retired. Reusable Owner policy must define trigger, owner, procedure, source, evidence, cleanup and CEO enforcement.
