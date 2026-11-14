# V1.6 page concurrency — design reference only

This document is **historic design**, not permission to enable more concurrent tabs, a second Chrome, a second scheduler or new background workers. Current production should preserve the original one-browser `9222`/profile ownership and module safety contract.

- The optional `MarketReadActors` read-only actor/concurrency design was **not enabled by default** in earlier production evidence. Do not infer it is active now; inspect actual config and runtime.
- A performance change requires evidence of current bottleneck plus CEO architecture decision, deterministic ownership/stop/UNKNOWN tests and scoped Owner release approval. Shared CDP remains one protected session.
- New CEO/Executor after interruption must reconcile actual runtime state before experimenting; never start a duplicate browser just to recover a hung chat.

[Original full concurrency investigation/design](https://github.com/Horse-Hunter/INSO_Leo/blob/0db292fe0cb79d5177f436c3f8cc9b87c75288ee/docs/V16_PAGE_CONCURRENCY_DESIGN.md) · [CDP policy](CDP_SESSION_POLICY.md) · [Current RFQ](../control-room/RFQ-016/TASK_SPEC.md).
