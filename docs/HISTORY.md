# Historical documents — pinned revision index

This repo uses **short live documents + immutable Git history**, not ever-growing append-only Markdown. The pre-cleanup full snapshot is commit [0db292fe0cb79d5177f436c3f8cc9b87c75288ee](https://github.com/Horse-Hunter/INSO_Leo/commit/0db292fe0cb79d5177f436c3f8cc9b87c75288ee) on `workbuddy/v16-rfq016-stabilization`. That commit is in the current branch ancestry; its previous texts, reports, RFQ decisions and evidence remain traceable. Do not rewrite or drop Git history.

To inspect any older document, replace `<path>` in:
`https://github.com/Horse-Hunter/INSO_Leo/blob/0db292fe0cb79d5177f436c3f8cc9b87c75288ee/<path>`

High-value history anchors:

- [Long CEO handover](https://github.com/Horse-Hunter/INSO_Leo/blob/0db292fe0cb79d5177f436c3f8cc9b87c75288ee/control-room/CEO_HANDOVER.md); [RFQ-016 Task Spec](https://github.com/Horse-Hunter/INSO_Leo/blob/0db292fe0cb79d5177f436c3f8cc9b87c75288ee/control-room/RFQ-016/TASK_SPEC.md); [CEO Review](https://github.com/Horse-Hunter/INSO_Leo/blob/0db292fe0cb79d5177f436c3f8cc9b87c75288ee/control-room/RFQ-016/REVIEW.md); [Execution Log](https://github.com/Horse-Hunter/INSO_Leo/blob/0db292fe0cb79d5177f436c3f8cc9b87c75288ee/control-room/RFQ-016/EXECUTION_LOG.md); [Final Report](https://github.com/Horse-Hunter/INSO_Leo/blob/0db292fe0cb79d5177f436c3f8cc9b87c75288ee/control-room/RFQ-016/FINAL_REPORT.md).
- [V1.6 release report](https://github.com/Horse-Hunter/INSO_Leo/blob/0db292fe0cb79d5177f436c3f8cc9b87c75288ee/V16_RELEASE_REPORT.md); [RFQ-016 API feasibility](https://github.com/Horse-Hunter/INSO_Leo/blob/0db292fe0cb79d5177f436c3f8cc9b87c75288ee/control-room/RFQ-016/GOOGLE_API_FEASIBILITY_2026-11-13.md); [production asset audit](https://github.com/Horse-Hunter/INSO_Leo/blob/0db292fe0cb79d5177f436c3f8cc9b87c75288ee/control-room/RFQ-016/ASSET_ARCHITECTURE_AUDIT_2026-11-02.md).
- Historical RFQ-001–015 and dated `tasks/` reports are **closed evidence**, not automatic new TODOs. Access via their pinned paths only when the current task needs that evidence.
- Actual binaries, SQLite, rollback, credentials, CDP profiles, local uncommitted work and live processes **are not backed up by Git history**. Never treat this archive as a production/data backup.

**Live documents**: [AGENTS](../AGENTS.md), [AI_START_HERE](../AI_START_HERE.md), [CEO handover](../control-room/CEO_HANDOVER.md), [COORDINATION](../control-room/COORDINATION.md), active RFQ documents, module index, safety and release instructions.
