# INSO LEO — Agent Rules (current)

Read [AI_START_HERE.md](AI_START_HERE.md). **Current rules here outrank historic task notes.** Original pre-compaction rules: [pinned archive](https://github.com/Horse-Hunter/INSO_Leo/blob/0db292fe0cb79d5177f436c3f8cc9b87c75288ee/AGENTS.md).

## 生产版本必须可用、功能完整（Owner 强制规则，2026-11-16）

**触发条件：** 任何版本设计、发布候选、安装、生产验收、功能风险修复和新 CEO/Executor 接管。**Owner 明确要求：以后绝不交付“安全预览不可启动业务”之类的功能受限程序冒充生产版。**

1. **产品定位不可混淆。** `--safe-preview` / `--preview-self-check` 只证明预览，不证明生产可用。带有禁用业务按钮、仅能预览、关键模块被总开关屏蔽的交付物，必须标记为 `PREVIEW_ONLY / FUNCTIONALLY_INCOMPLETE`，不得称为正式生产版、发布验收通过或真实业务完成。一次安装成功也不等于生产验收。
2. **正常业务启动必须在实际 GUI 中可达。** 正式版应提供清晰、可操作的**生产运行入口**：Owner/操作员能在界面选择正常业务模式、查看当前许可/运行范围并启动；不能要求用户发现隐藏 CLI 参数、换窗口或改源码才能用。可以“默认不自动开始真实采购”，但**不能默认只能安全预览且没有正常操作入口**。若当前安全架构尚不支持全功能 GUI，先修功能并验收，不要阉割后宣称正式交付。
3. **应有功能不得以安全为名长期删除或全面禁用。** 真实 inquiry、Google Sheets API 读写、INSO 采购、报价、TP、通知等在既定产品范围内的模块，应按功能规格能正常使用；受控单笔模式是测试/灰度手段，不是用来替代正常生产能力的永久方案。若某模块不能安全运行，必须如实标注“未完成/未验收”，修复其隔离、调度或授权实现，而不是锁死按钮后报 PASS。未经 Owner 明确同意，不得缩减正式产品功能。
4. **安全要精确，不能用“全局禁用”伪装完成。** 保留真实的权限、来源身份、去重、`SENT/UNKNOWN`、write-intent、hold 与故障失败关闭；尽可能只阻断**确实有风险的订单或具体动作**，显示可理解的理由，不要无故使其他正常业务不可用。没有授权不得自动发真实采购，但 Owner 已明确授予的具体范围不应被重复审批或新增人为流程卡住。
5. **发布验收必须验证“真的能办事”。** 在声称 `PRODUCTION_READY` 前，至少实证：正式 GUI 入口可用、应交付模块入口与后台调度正常、Google Sheets API 真实读写权限/模式、所批准的业务流程能运行、业务结果由外部系统/SQLite/回执交叉确认、异常和关闭/重启可恢复。合成测试、全绿 pytest、EXE 哈希、预览 `ok:true`、按钮禁用都**不能**替代生产功能验收。若现场无合法待处理订单，记 `REAL_BUSINESS_NOT_VERIFIED`，不伪造订单，也不把“无订单”包装成完整验收。
6. **职责与执行：** CEO 负最终产品规格与验收责任，Executor 负责实现并出具真实界面及业务证据；发布复核发现核心功能不可用，必须判 `FUNCTIONAL_RELEASE_NOT_ACCEPTED`，禁止对 Owner 报“正式版已完成”。Owner 决定是否接受功能缺项；在明确接受前只可称预览/试验版。保留现场数据与历史回执，不为凑演示修改真实订单或清理未知效果。

**当前项目教训：** 2026-11-16 的 V1.6 据 Executor 报告 `INSTALLED_PREVIEW_PASS / ORDER_NOT_DONE`、默认 GUI 为禁用业务按钮的安全预览。**该记录只证明安装和预览，不证明正式生产功能验收。** 必须提供可正常启用业务的生产操作体验，并取得真实业务证据后，才可宣称产品已按 Owner 要求完成。

## Branch promotion is Owner-only

**Bootstrap trap:** repository default `main` still contains historic V1.1. Every replacement CEO/Executor must explicitly open current `develop` entry docs before treating any branch as the project baseline. Do not auto-promote.

Three long-lived lines: `develop` (R&D + installed trial), `main` (only Owner-accepted current), `release/previous` (prior Owner-accepted current). **Packaging, installation, live operation, successful tests or elapsed time never promote a version.** Only explicit Owner approval may advance `main`; see [BRANCH_POLICY](docs/BRANCH_POLICY.md). During initial migration, `main` still contains legacy V1.1 and MUST NOT be presented as the verified current V1.6. Preserve existing DeepSeek worktree/branch.

## 故障原因必须在产品界面自解释（Owner 强制验收要求，2026-11-17）

**适用：** 生产运行故障、暂停、三小时超时、单笔任务异常、外部写入未知、登录/凭据/Sheets/CDP/Research 事件。**产品不得把 Agent 查日志作为普通用户理解故障的唯一途径。**

- “异常与通知”须直接显示：首次/最后发生时间、真实影响的模块/站点、当前阶段、可验证的 `reason_code` 与错误类别、简明中文原因及下一步用户能做什么；对于超时区分“首次故障”与“持续三小时后升级停止”。
- 明确区分**最初根因、后续连带暂停、仍未验证的猜测**，不得把 Google Sheets 暂停显示造成的 Browser/CDP 和 Credential 状态当成已证明的独立故障；未知就写“原因未确认”，附日志/事件定位方式。
- 订单/来源行仅在真实可证时关联；未确认的外部写入应标明 `UNKNOWN/SENT`、保留的保护状态和“不可盲目重试”。异常记录需可追溯并可在重启后查看未结算状态。
- 技术详情允许展示稳定故障代码和脱敏异常类型、简短安全摘要，但禁止暴露 API 密钥、Cookie、Token、完整隐私数据或原始异常可能携带的敏感字段。优先复用同一诊断/事件/告警源，不能用不同界面复制多套相互矛盾的状态。
- CEO/Executor 交付生产候选时必须实际验证异常 UI 的真实故障场景、三小时升级、恢复/重启显示；仅写“需要人工处理”或“查看日志”不达标。此要求提升可观测性，不允许顺势关闭功能、屏蔽报错或降低已有去重和交易安全机制。

## Ownership and source of truth

- **Owner** sets business intent, grants real external-effect/production permissions, decides release; **CEO** owns requirements, architecture, independent Review; **one Executor** owns implementation, tests, deployment and live business evidence.
- Requirements: `control-room/RFQ-XXX/TASK_SPEC.md`; current status: `control-room/COORDINATION.md`; handover: `control-room/CEO_HANDOVER.md`; technical record: existing `EXECUTION_LOG.md`; independent verdict: `REVIEW.md`.
- A new Executor can receive just `执行 RFQ-XXX`; a CEO can receive `Review RFQ-XXX`. Neither asks Owner to repeat context already committed.

## Lean Review / bounded execution (Owner approved 2026-11-15)

**Goal:** reduce repeated context, token use, test/build churn and R2→R3→R4-style serial discoveries; **never trade away independent safety review or live evidence**. This is an execution-efficiency rule, not an authorization to deploy.

1. **One authoritative baseline, then diff first.** On takeover still read `develop` entry/AGENTS and active `COORDINATION`, `CEO_HANDOVER`, RFQ Task Spec/last Review. Verify actual ref/HEAD, dirty worktrees and live state where relevant. Thereafter review changes against the last fixed reviewed SHA with Git Diff and trace only changed/affected call chains. Expand to full files only for risks or gaps; never rely on stale chat summaries as evidence.
2. **One bounded effect-path audit per release blocker.** Before claiming a scoped run is isolated, inventory the real startup, background/periodic, manual/GUI and recovery paths; include local SQLite/event/alert changes, Google/INSO/SMTP effects, uncertain-effect holds and rollback/installer gates. Verify scope checks **before** each possible effect, including out-of-scope historical orders. Use one consolidated negative-test matrix (in-scope/out-of-scope, permission denied, crash/restart, legacy unscoped compatibility). CEO reports all material findings of that pass together rather than knowingly spacing them over rounds.
3. **Two-stage tests, one final candidate.** During development run smallest relevant tests and targeted regressions. When source is frozen run affected suites, then one full test suite and record all failed/skipped nodeids and baseline comparison. Do not delete/deselect/skip tests to claim green. Build/sign/hash/scan **once after source freeze**; any subsequent source change invalidates the candidate and requires rebuilding and revalidation. No automatic repeat of the full suite or build just for a status update.
4. **Compact, linked reporting.** Keep one `EXECUTION_LOG.md` for checkpoints and evidence paths, one independent `REVIEW.md` (PASS / CHANGES_REQUESTED + findings + gates), and update `COORDINATION.md` only for real state changes. The Executor retains the canonical [seven reporting headings](docs/REPORTING.md) but keeps them concise: fixed SHA/changed paths, tests, candidate hash, open blockers, actual production actions, next handoff. Reference prior evidence by exact path/SHA; do not replicate long logs or rewrite historical versions.
5. **Non-negotiable gates remain.** Executor self-reported PASS is not CEO independent acceptance; hash manifests do not verify uninspected executable bytes; a dated process record is not live status. Installation, production Stop/restart, real orders and branch promotion each require their own Owner authorization and verifiable preconditions. A failed/unknown external effect stays held and is never replayed to save time.

## Interrupt-anytime / replace-any-window (Owner rule 2026-11-14)

**Trigger:** start, every task/role transfer, before/after real effects, after meaningful progress, and whenever interruption is possible. Applies equally to CEO and Executor. **Goal:** a replacement window needs only repo + live evidence, never old chat memory.

1. **Before work** read the active documents; inspect actual branch/HEAD, `git status --short`, `git diff`, `git worktree list --porcelain`; for production check running processes, config, SQLite, logs, Sheet/INSO/SMTP truth. Reuse the existing worktree; preserve uncommitted/unknown files. An expired model window does **not** imply its program stopped.
2. **Checkpoint before irreversible actions:** in the **existing** RFQ `EXECUTION_LOG.md` record exact target/scope, pre-state, authorization, live process, planned action, and potential unknown outcome; persist the original business guard/hold before dispatch. Record CEO decisions in existing `REVIEW.md` or Task Spec; update `COORDINATION.md` only for real state changes. Commit/push bounded coherent checkpoints when safe; never replace native SQLite safety with Git documentation.
3. **After each real response** reconcile the external system, record request/receipt/actual observed outcome (`DONE / NOT_DONE / UNKNOWN / WAITING_OWNER`), next single action and blockers. A request/timeout is not success. Preserve uncertain holds and stop further effects for that order.
4. **On takeover** reconcile local dirty state + live processes + all external records against last checkpoint; do not assume the last chat text, Git HEAD, old EXE hash or dated report is live proof. Confirm prior Executor is no longer initiating actions and no in-flight operation survives **before** any second start or replay. One active Executor; CEO may review independently without executing business.
5. **At interruption** no last-minute message is required for safety: pre-action durable guard + existing log checkpoint + on-site audit must suffice. Do not claim continuous monitoring after window ends. Temporary `HANDOFF*.md` only if necessary for one transfer; fold into existing record, then retire it.

**Enforcement:** CEO fails Review for missing recoverable state, duplicate/unknown external effects, or stale instructions presented as current. **Cleanup:** retire only owned disposable files; never force-delete unknown dirty worktrees, protected runtime, Chrome/CDP, SQLite/WAL/SHM, secrets, rollback or evidence. This rule is also in reusable templates.

## Safe execution and reuse

- **Computer Use permitted** by Owner 2026-11-14, including supported desktop GUI inspection/click/type. CLI, PowerShell/Python, API and existing app-owned CDP remain permitted; actual use is recorded truthfully. Tool permission **does not** grant purchase, Google Editor, quotation button, SMTP, release or other real effects. See [SAFETY](docs/SAFETY.md).
- One protected browser: profile `D:\\Program_Leo\\INSO_CDP\\chrome-profile`, port `9222`; never reset/force-kill or clone it. See [CDP policy](docs/CDP_SESSION_POLICY.md).
- Guard exact source identity, dates, status, purchase/quote/mail dedup, durable `SENT/UNKNOWN`; no blind retry or clearing holds. Before running a single order, prove other modules cannot simultaneously cause effects.
- Reuse existing stable paths, adapters, config, migrations, packaging and tests; no duplicate production implementations. Implement only proven gaps; document justified non-reuse in `EXECUTION_LOG.md`.
- No secrets in Git, report, chat or fixtures. Owner sees plain business language. Completed Executor reports use exact [seven headings](docs/REPORTING.md); CEO Review uses the short CEO format.
- Durable policy changes: CEO supplies trigger/owner/procedure/source/evidence/cleanup/enforcement in canonical docs; **project-generic** rules also update `templates/lean-ai-baseline/`. Review enforces them, not Owner reminders.
