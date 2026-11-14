# INSO LEO — CEO / Executor takeover card

**Updated 2026-11-14; remote-document snapshot, NOT Windows live evidence.** Start at [AI_START_HERE](../AI_START_HERE.md). Current remote development branch: `workbuddy/v16-rfq016-stabilization` (query HEAD each time); `main` is not the V1.6 working baseline.

## Active business goal

**RFQ-016**: safely complete **one** real inquiry through V1.6 using Google Sheets API, with actual receipts and no unrelated orders. See [Task Spec](RFQ-016/TASK_SPEC.md), [live-state ledger](RFQ-016/EXECUTION_LOG.md), [CEO verdict](RFQ-016/REVIEW.md), [coordination](COORDINATION.md). **NOT accepted as complete.**

Last **reported** production facts (recheck all on Windows): installed `D:\\Program_Leo\\INSO_Leo\\dist\\INSO_V1.6\\INSO_V1.6.exe` SHA256 `b357889d48e5abe6ec6504eddd610442c877e438018f156c4c932477070814f6`; backup `dist/release-backups/INSO_V1.6-header-block-20261114T021508Z`; production `google_api` absent/disabled; service account `rfq016-sheets-test@inso-509314.iam.gserviceaccount.com` reported Viewer on `INSO_QUOTE`. **All are dated reports, not current observations.**

Last reported target: `INSO_QUOTE / 2026 / physical row 221`, model `FT2232H-56Q-REEL`, Qty `105`, brand blank, status `未发`. **Inquiry pending, NOT quotation candidate**. Date, current status, customer identity and any INSO/SQLite/SMTP effect remain unverified after prior Executor quota exhaustion. GUI Start would also schedule quotation, TP and notifications; `inquiry_ids` alone does not isolate them.

## New-window takeover (CEO or Executor)

1. First inspect Git local status/worktrees/HEAD **and** Windows process/config/logs/SQLite/Sheets/INSO/SMTP if accessible. Preserve all unknown dirty state; no second process or worktree.
2. Compare pre-effect checkpoint and real external effects; an old session ending is not a proof of idle. Old program still processing means observe, not restart.
3. Check API config, key external to repo, live `--api-self-check`, production sheet read/Editor, 7-day rule (Owner single-order exemption is age only), row identity, UNKNOWN/SENT and exact single-order boundary.
4. Until the active original business is safe and scope/Editor/real effect authorization are established, only read-only work. If needed, raise **one consolidated Owner decision** with named row, workbook, whole-file Editor implications, purchases/quotation/mail and any other modules possibly affected.
5. Keep the existing `RFQ-016/EXECUTION_LOG.md` current at each meaningful boundary (pre-action intent, ack, observed effect, next action). CEO updates `REVIEW.md` and `COORDINATION.md` only on real verdict/status change.

## Protected inherited assets

- Only Chrome `127.0.0.1:9222`, profile `D:\\Program_Leo\\INSO_CDP\\chrome-profile`; older Research worktree may host the **physical** profile. Preserve junction, profile and backup.
- V1.6 `runtime` links to V1.4; SQLite may resolve through older V1.2 worktree. **Old folder names do not mean safe to delete.** See [asset audit](RFQ-016/ASSET_ARCHITECTURE_AUDIT_2026-11-02.md) and [CDP policy](../docs/CDP_SESSION_POLICY.md).
- Never clear unknown external effects, replace live EXE, force-kill a live operation or replay prior mail.
- Owner 2026-11-14 lifted the **Agent Computer Use** ban; method use still requires actual access and business effect approval. See [AGENTS](../AGENTS.md).

## Where to look only when needed

[Module index](../docs/MODULE_INDEX.md) · [Safety](../docs/SAFETY.md) · [Windows release](../docs/WINDOWS_RELEASE.md) · [Last V1.6 release receipts](../V16_RELEASE_REPORT.md) · [RFQ-016 full historic evidence](https://github.com/Horse-Hunter/INSO_Leo/blob/0db292fe0cb79d5177f436c3f8cc9b87c75288ee/control-room/RFQ-016/EXECUTION_LOG.md) · [Previous lengthy handover](https://github.com/Horse-Hunter/INSO_Leo/blob/0db292fe0cb79d5177f436c3f8cc9b87c75288ee/control-room/CEO_HANDOVER.md).

**Do not confuse:** remote HEAD, compiled source, installed SHA, last recorded live result and **current** operating state are five different facts.
