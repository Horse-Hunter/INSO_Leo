# Project Baseline — reusable template

- Requirement: current RFQ Task Spec; status: Control Room; implementation: Git/tests/runtime evidence; independent acceptance: CEO Review.
- One active Executor per production task; CEO and Executor sessions are **replaceable at any time**. Preserve live worktrees/dirty state and immutable external business state.
- Mandatory pre-/post-effect checkpoint in the **existing** RFQ execution log plus durable native guards. Successor reconciles actual process, db, logs and external system; session loss never implies success, stop or permission to replay.
- Reuse stable paths/config/browser/database/adapters/packaging; no parallel implementations without justified architecture decision.
- Project-specific Owner tool/Computer Use permissions and external writes are independent; record actual method and business evidence.
- Clean only identified task-owned disposable builds/staging, preserve unknown dirty files, runtime/credentials/rollback.
- Durable rules specify trigger/owner/procedure/source/evidence/cleanup/Review; CEO mirrors cross-project rules into template source.
- Delivery over ceremony: current rules short, historical reports accessible via pinned Git revisions.
