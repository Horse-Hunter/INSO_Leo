# INSO LEO — Owner 最终授权：发布 V1.6 并执行真实单笔订单（2026-11-16）

## Executor 现场执行结果（2026-11-16 01:0x +08:00）：`DEPLOYMENT_FAILED / NOT_INSTALLED / NO_BUSINESS_ACTION`

依本页 Owner 授权连续执行到安装前一步，**自有数据库门禁在真实生产账本上 FAIL**，安装器按设计只接受已证明状态，故未安装、未启动、未做真实订单、未产生任何外部效果。旧版 `e9e3da33…` 在位未变。

- **已实证 PASS：** 旧程序由自身运行记录证明干净退出（PID 38948，`exit_reason=owner_exit`，code 0，`2026-11-16 00:28:58` 本地）；候选逐文件复算 `2,872/2,872`、EXE `f1a0351d…`；旧程序/配置快照 `BACKUP_RESULT = PASS`；停机后生产库逐字节备份，哈希与源同为 `c50c3636…`，`integrity_check = ok`，源无 `WAL/SHM`。
- **唯一阻断（结构性）：** `DB_VERIFY_RESULT = FAIL` —— 账本无 `workflow_write_intents`（旧库，迁移仅 `1201`），`27 unprotected unknown order(s)`。其中 26 单实为 `SAVED` 且带真实 `saved_record_ref`（`SAVE_OUTCOME_UNKNOWN` 均早于 `SAVED` 约 6 秒，属重试后确认成功），但无活动告警/hold 挂靠；剩 1 单 `inq_99275e8e72b43fd6616fd686`（SHAHAB/115）为 `MANUAL_REVIEW`、`RECONCILIATION_UNREADABLE`、无回执、无 hold。**即使排除 26 单，SHAHAB/115 一单仍使门禁拒绝**；而把它变成"已证明"只能靠改 `purchase_state` 或补 hold，两者均为 Owner 明令禁止。
- **不触碰：** 未安装、未启新 EXE、未 `--safe-preview`、未跑真实订单、未动 Chrome 9222、未改生产库、未清理 SHAHAB/115 或任何 hold。详见 [RFQ-021 EXECUTION_LOG](RFQ-021/EXECUTION_LOG.md#rfq-021-r5--现场部署执行2026-11-16-0039010x-0800唯一-executor)。
- **待 Owner 决策：** ①授权处置 SHAHAB/115（补证为已结算，或补一条活动 hold）；②授权对安装门禁做最小修正（需新构建，Owner 已声明不要 R6）。二者之外无合法通过路径。
- **顺带更正：** 物理第 1 行外来表头 + 第 5 行真实契约表头的布局，在本冻结源码上**不会**导致 `SHEETS_SCHEMA_UNAVAILABLE`（`SOURCE_HEADER_ANCHOR_ROW=0` + `SOURCE_HEADER_WINDOW=10` 已容错）；2026-11-13 的"两种传输都要求第 1 行"结论对 `6a75cc93` 不成立。原目标第 221 行 `FT2232H-56Q-REEL` 现场为 `发给采购`，SQLite 为 `SAVED / rec_440fafd…`，已完成，不得重复采购。

**Owner 最新明确纠正：** “就是要跑真实订单啊，禁止再加阻断”。此授权**取代**此前只允许安装与 `--safe-preview` 的业务范围限制。Owner 已另行声明旧程序退出；Executor 必须以现场核实为准。**本次无需分阶段重复请求 CEO/Owner 批准**：在现有产品安全门禁真实通过后，唯一新 Executor 可连续执行：旧程序停机核验 → 真实配置/账本备份及校验 → 安装冻结 V1.6 → 新版安全预览 → **一笔真实且符合准入条件的 inquiry 订单**（Google Sheets API 读取及必要的 brand/status 写入、现有 INSO Save-and-Send 采购动作及回执核对）→ 证据归档。不得无故停在安全预览或增加额外 CEO Review。

- **授权范围：** `OWNER_AUTHORIZED_GATED_INSTALL_AND_ONE_REAL_INQUIRY / NOT_YET_VERIFIED`；`--scoped-start --scope-modules inquiry --scope-writes google,inso --scope-approval OWNER-APPROVED:RFQ016-REAL-20261116 --start-inquiry`；`--scope-inquiries` **只能是现场核准的一笔真实订单 inquiry_id**（不得使用占位符）。正常业务需要的真实 API/INSO 写入已经获得此处 Owner 一次性明确授权。
- **目标订单准则：** 先读 `control-room/RFQ-016/TASK_SPEC.md`、`EXECUTION_LOG.md`，通过真实 Sheets API + SQLite/INSO 核对。历史 `INSO_QUOTE/2026` 物理 221 行 `inq_e15970df104e170d93b4169b` 已据上一轮现场报告 `SAVED`、回执 `rec_440fafd372440ecf9dacabf660dd155d`；如最新事实仍证实保存，不得重复 Save/购买。若原目标已完成，**直接选择一笔真实、未发、来源身份唯一、当下符合准入且无历史发出/未知效果的新 inquiry**，无需额外请示；最多处理一笔。SHAHAB/115 `MANUAL_REVIEW` 与历史 hold 保持原样。
- **固定安装候选：** 源码 `6a75cc93130c8b7805569edfc3131f82032e22c4`，EXE SHA256 `f1a0351dd9837239043250fa86b9d8c921620d151eef660529d85eaecca020e2`，清单 `5dfce4c17e1583f401d78123d17378a527aeca78df356222e4d22ec954c33a64`，旧版预期 `e9e3da33417414abac53f8a88a67d9f053bcdaeab9730eae9ad8bd7870dffad0`；必须现场复核。不得新建候选或降级/绕过既有安装安全门禁。
- **业务路径：** 使用现有 Google Sheets Service Account API（实际确认 enabled、权限和唯一行身份），保留现有 INSO 业务保护及已授权 CDP 连接，不强夺/重置 Chrome9222，不启用未按订单隔离的 quotation/TP/notification/smtp 批处理。记录每次实际外部效果前/后证据、去重与 durable write intent、Google/INSO/SQLite 实际回执。一个 API 请求或按钮点击不等于 DONE。
- **自然失败而非“新增审批关卡”：** 已有安装 B3/B4、写入意图、源行身份、真实权限、采购去重、UNKNOWN/SENT 和 holds 等硬安全门禁仍按源码运行；有实质 FAIL/UNKNOWN 即停止该效果并上报可验证原因，不擅自删除或伪造业务状态。**没有问题时无需返回 CEO、无需多轮确认，直接完成单笔业务。**
- **完成定义：** 安装后真实 `INSTALLED_PREVIEW_PASS` 加 **ONE_REAL_INQUIRY_DONE**（Sheet API 写入回读/INSO 原生确认/SQLite 回执一致）；若业务确实无法完成则据实标 `NOT_DONE` / `UNKNOWN` 而非伪造完成。提交原有 `EXECUTION_LOG.md`、`COORDINATION.md`，记录唯一订单、证据与现场最后程序状态；无须再开 R6。
- **不授权：** 批量处理、重复采购历史 221、任意其他订单、自动清除 SHAHAB/115/UNKNOWN/hold、跨订单报价/邮件模块、修改安装源码规避门禁、强杀进程、任意回滚覆盖生产库、合并/晋升 `develop`/`main`/`release`。原有条款中的“禁止真实订单”仅在本次**单笔 inquiry 明确授权的范围内**被更新。

## 之前仅授权安装与安全预览的协调记录（历史；业务范围已被本次 Owner 明确更新）

# INSO LEO — RFQ-021 Owner 授权发布准备（2026-11-16）

**Owner 最新指令（聊天确认）：** “程序已退出，指挥新窗口发布吧”。Owner 自述旧程序已退出，**CEO/Executor 尚未独立验证 B4**。本条授权仅覆盖**本次**按 RFQ-021 手册执行现场核验、完整程序/配置快照、停机后当前账本一致性备份与只读校验、全部门禁 PASS 后安装固定 R5 候选，以及**新 EXE 的 `--safe-preview` 首次验收**；**不代表无条件通过、也不是实际部署已完成。**

- **当前工作状态：** `OWNER_AUTHORIZED_GATED_INSTALL_AND_SAFE_PREVIEW / RELEASE_HOLD / INSTALL_NOT_VERIFIED`。待 Executor 根据真实现场证据更新 `EXECUTION_LOG.md` 和本页；所有门禁有一项 FAIL / UNKNOWN，立即 `DEPLOYMENT_BLOCKED` 并报告，不得跳过、修改数据库业务状态、篡改报告或为达成 PASS 临时改代码。
- **固定候选，不准换版：** 冻结源码 `6a75cc93130c8b7805569edfc3131f82032e22c4`；EXE `f1a0351dd9837239043250fa86b9d8c921620d151eef660529d85eaecca020e2`；清单 `5dfce4c17e1583f401d78123d17378a527aeca78df356222e4d22ec954c33a64`；旧安装预期 `e9e3da33417414abac53f8a88a67d9f053bcdaeab9730eae9ad8bd7870dffad0`（须现场复核）。
- **执行入口：** `develop/AGENTS.md` 和 `AI_START_HERE.md`；本分支 `control-room/RFQ-021/REVIEW.md` 顶部 CEO R5 Final 与 `INSTALL_AND_ROLLBACK.md`。只允许**唯一新 DeepSeek Executor**接管；确认无旧窗口并行。检查 Git HEAD/worktree/status，核验安装来源、旧 EXE、watcher、进程、`runtime` junction、真实配置指向的 SQLite、WAL/SHM/打开句柄，任何不明即停。
- **必须保留的最终门禁：** 真实候选 2,872 文件哈希 PASS；旧程序及 watcher 均已退出且状态可证；备份旧程序/配置与账本身份一致；数据库报告 schema ≥4、业务不变量/意图/UNKNOWN 保护全部通过；安装器安装后逐文件校验；首次启动只能用 `INSO_V1.6.exe --safe-preview`，禁止任何真实业务启动。
- **此次明确未授权：** `--scoped-start`、`--start-inquiry`、任何真实订单、Google/INSO/SMTP 写入、Chrome9222 接管、UNKNOWN/hold/221/SHAHAB-115 的结算或清理、发生故障后冷回滚/回滚后重启、合并 `develop`、晋升 `main/release`。冷回滚（即使手册有步骤）及业务重启仍需 Owner 单独确认。脚本自动 `FAIL_RESTORED` 的安全恢复例外按原手册允许；若 `ROLLBACK_REQUIRED`，停工上报。
- **反馈：** 新窗口在每个实际动作后记录时间、路径、SHA、PASS/FAIL、生产副作用和日志路径；仅当现场安装与安全预览均有实证 PASS，才报告 `INSTALLED_PREVIEW_PASS / BUSINESS_HOLD`，否则说明真实阻断，禁止宣称发布成功。

## 先前 CEO R5 离线验收及历史状态（仍然有效，但已获得上述有限现场授权）

# INSO LEO — RFQ-021-R5 CEO 最终独立验收（2026-11-15 21:30+08:00）

**最新权威结论：`PASS_SOURCE_AND_OFFLINE_RELEASE_READY / RELEASE_HOLD / NOT_DEPLOYED`。** R5 两个 P0 的 fail-closed 源码及负向案例通过独立检查。**RFQ-021 离线开发阶段可以关闭；本结论不授予生产维护、安装、业务动作、分支晋升许可。**

- **唯一固定来源：** 冻结源码 `6a75cc93130c8b7805569edfc3131f82032e22c4`；候选 EXE SHA256 `f1a0351dd9837239043250fa86b9d8c921620d151eef660529d85eaecca020e2`；清单 SHA256 `5dfce4c17e1583f401d78123d17378a527aeca78df356222e4d22ec954c33a64`（CEO 对 GitHub 清单独立复算一致）。预补丁 R5 候选 `be7c0d3…` 已归档禁止安装。
- **测试证据：** GitHub JUnit 4,277 / 4,276 pass / 0 fail / 0 error / 1 conditional skip；Executor 报告隔离 PowerShell 门禁 156 项 PASS，CEO 检查了脚本和测试，但未实际运行 Windows 现场。
- **仍待 Owner：** B4 正常停止、实际备份与来源验证、真实安装/安全预览和冷回滚均 `NOT_VERIFIED`。维护窗口前先重新核对实时进程及本机真实 EXE/SQLite/junction，任何不满足停止。真实订单和所有外部写入仍不授权。详见 [CEO REVIEW 最新章节](RFQ-021/REVIEW.md)。
- **禁止动作保持：** 未经 Owner 分别确认，不得停/启程序、安装、改变生产 SQLite/WAL/SHM、接管 Chrome9222、真实 Google/INSO/SMTP、清理 221/SHAHAB-115/hold/UNKNOWN、合并 develop 或晋升 main/release。

## 以往 Executor 状态与 CEO 阻断（历史，已被上方新结论替代）

# INSO LEO — RFQ-021-R5 CEO 独立 Review（2026-11-15 晚）

**最新权威状态：`RFQ021_R5_CLOSURE_SUBMITTED / RELEASE_HOLD / NOT_DEPLOYED`（Executor 已闭环两处 P0，待 CEO 最终复核；CEO 上一次结论仍是 `R5 CHANGES_REQUESTED`）。** 两处安装安全失败关闭条件已按 R5 内定点修补完成：① 数据库缺表/查询失败/NULL 不再被当成 0——改为"确认的 0，或逐项核实过的旧库状态（UNKNOWN/SENT 仍被告警或 hold 保护），hold 只读不清"；② 进程枚举失败/权限不足/EXE 路径不可读一律拒绝，安装前最终复检同样适用。先补负测（旧脚本下红），再修复；冻结后全量 4,277 / 4,276 PASS / 0 FAIL / 1 SKIP，离线安装门禁 **156** 项 PASS。完整依据：[CEO REVIEW 顶部](RFQ-021/REVIEW.md)。**严禁自行停机、安装或真实业务。**

## R5 Executor 自测及历史状态（CEO 已复核，结论以顶部为准）

# INSO LEO — RFQ-021-R5 Executor 交付（2026-11-15 晚，含两处 P0 闭环补丁）

**最新权威状态（Executor 自报，不是发布许可）：`RFQ021_R5_SOURCE_AND_OFFLINE_RELEASE_READY / RELEASE_HOLD / NOT_DEPLOYED`。** R4 的五个集中阻断与 CEO R5 指出的两个 fail-closed 条件均已在 R5 内处理；CEO 独立结论仍以 [REVIEW.md](RFQ-021/REVIEW.md) 为准。

- **冻结源码：** `6a75cc93130c8b7805569edfc3131f82032e22c4`（其后的提交只含文档与证据；`src/` 自 `2c58529d` 起未变，补丁在脚本与门禁测试）。
- **唯一候选：** EXE `f1a0351dd9837239043250fa86b9d8c921620d151eef660529d85eaecca020e2`，`8,461,034` B，`2,872` 文件；清单自身 `5dfce4c17e1583f401d78123d17378a527aeca78df356222e4d22ec954c33a64`；逐文件复算 `PASS（2,872/2,872，0 missing / 0 mismatch / 0 unexpected）`。补丁前那版（`be7c0d3f…` / 清单 `a969a9bf…` / 门禁 107 项）只作历史证据，保留为 `*-pre-p0`，不得作为候选安装。
- **R4/R5 阻断处理：** ①快照配置绑定真实 runtime junction，并新增"账本路径取自实时配置"（本机实测：junction 指向的 `dist\INSO_V1.4\runtime` 里没有 `production\`，真实库在 `dist\INSO_V1.2\runtime\production\workflow.sqlite3`）；②切换后逐文件复算，回滚按快照逐文件恢复并验证，恢复中断报 `ROLLBACK_REQUIRED`；③数据库证明=源路径/进程状态/独占句柄/业务不变式/报告与安装目录及账本互绑；④**写入意图必须是确认的 0 或已证明的旧库状态**，缺表/查询失败/NULL 一律拒绝；⑤`_run_login_sweep(check_only=True)` 在预览与受控范围一律拒绝（断言未获取 Chrome）；⑥六项失败已定性为环境（测试临时树不可写）并给出可复现机制证据，全量 `4,277 collected / 4,276 passed / 0 failed / 0 errors / 1 skipped in 328.56 s`。
- **仍未验证：** 安装、停机、真实业务试运行、B4 干净停机均需 Owner 维护窗口；旧 EXE 血缘仍 `NOT_VERIFIED`。
- **继续禁止：** 停机/重启、生产安装、真实订单和外部写入、修改/备份生产 SQLite、接管 Chrome9222、清理 UNKNOWN/hold、合并 develop、晋升 main/release。

## R4 Executor 交付前历史协调记录

# INSO LEO — RFQ-021-R4 CEO 决定（2026-11-15）

**当前唯一有效 CEO 状态：`RFQ021_R3_CHANGES_REQUESTED / RELEASE_HOLD / NOT_DEPLOYED`。R4 仅授权离线补修与测试，未获部署或真实业务授权。**

- **独立 CEO 结论：** [RFQ-021/REVIEW.md](RFQ-021/REVIEW.md)（R3）。R3 Executor 的 `PASS_SOURCE_SCOPE` 只代表其自测报告，**不等于 CEO PASS**。
- **R4 集中待修：** ① `V12WorkflowCoordinator.initialize_run_state/discover_pending` 范围外历史订单的本地状态/事件/告警变更；② 安装脚本的旧版回滚快照完整性、身份和缺失 runtime junction 校验；③ `order_action_hint` 与后端受控权限一致。验收矩阵及证据在 CEO REVIEW。
- **Lean Review 生效：** 读取 `develop/AGENTS.md` 的 `Lean Review / bounded execution`；一次端到端效果路径审计、先定向测试、源码冻结后一次完整回归和最终构建，交付报告简洁链接证据；安全门禁不变。
- **历史和现场：** R3 源码 `1ef20c81`、候选 `faa3166d…` 已被 CEO 拒绝发布；2026-11-15 06:06 故障类别为 TLS EOF / `SHEETS_READ_UNAVAILABLE`，底层原因 `NOT_VERIFIED`；10:40 现场数据不代表实时进程。B3 完整一致回滚备份、B4 授权干净停机仍未满足。
- **绝对禁止：** 安装、重启旧生产、真实订单、Google/INSO/SMTP 写入、生产 SQLite/Chrome9222 操作、清理 UNKNOWN/hold，以及合并 `develop` / 晋升 `main` 或 `release/previous`。Owner 必须分别审批这些真实动作。

## R4 Executor 交付（2026-11-15 下午，待 CEO 独立复核）

**状态：`RFQ021_R4_SUBMITTED_FOR_REVIEW / RELEASE_HOLD / NOT_DEPLOYED`。** 自测通过不等于 CEO 通过。

- **源码**`2ad471e7b3c0101f18f6edae05d77522c6f71d47`（`557cde28` + 快照清单 BOM 修复）。
- **候选** EXE `199181856ac1430af5aa0bd0af37b6bf45a1bf17272413583b2bb6e27e679d32`，8,459,710 B，2,872 文件；清单 `docs/evidence/rfq021/INSO_V1.6-artifact-manifest.sha256`（`2de4df2f…`），逐文件 2,872/2,872 PASS。R1/R2/R3 候选与清单已归档，只认这一个。
- **三项 R4 阻断已处理：** 协调器 `initialize_run_state`/`discover_pending` 的范围过滤；安装脚本的快照完整性 / 旧版身份 / junction 目标 / 独立数据库校验；`order_action_hint` 与执行守卫一致。
- **审计另发现并修复：** 跨站点登录巡检在按钮之外还有三个自动入口；故障证据会挂到范围外订单；备份脚本写的清单带 BOM 导致好快照不可验证。
- **测试如实：** 4,260 项 / 4,253 通过 / 6 失败 / 1 跳过；6 个失败均在本轮未改动的 launcher 用例，单独运行各 5/5 通过，捕获原因为测试临时库只读；未删除或跳过任何测试。详见 [EXECUTION_LOG](RFQ-021/EXECUTION_LOG.md)。
- **仍未做：** 安装、停机、重启、真实业务、生产 DB/Chrome 一律未动；安装脚本的"通过路径"未在真实装机上跑过（生产在运行，末道门按设计拒绝）。


## R3 Executor 阶段记录（历史，不构成 CEO 通过）

**当前状态：`RFQ021_R3_PASS_SOURCE_SCOPE / RELEASE_HOLD / NOT_DEPLOYED`；事件 `INC-20261115 FAULT_CLASS_CONFIRMED / UNDERLYING_CAUSE_NOT_VERIFIED`。**

- **R3 第 1 条（P0-A 背景效果）已修**：`PurchaseCompletionActions` 现在接收范围订单集，`retry_saved_statuses` 与 `process()` 都按范围过滤；范围外 SAVED 订单即使 `google` 是已授权目标也不会触发 Google 写入或本地状态变更。显式 `inquiry_ids` 与 `RunScope` 冲突时直接拒绝（`SCOPE_INQUIRY_IDS_CONFLICT`）。
- **R3 第 2 条（P0-C）已修**：`start_login_all_sites` 在预览或任何受控范围下**一律拒绝**，与 google 权限无关；新增 `_action_in_scope` 逐个审计手动动作（`edit` 需 google、`purchase` 需 inso+google，报价/TP 因模块不可隔离永远拒绝）。
- **R3 第 3/4 条（证据与安装）已处理**：手册源码 SHA 更正为 `1ef20c81`、只用当前一个候选；R1 JSON 归档；R2 通过数由 4235 更正为 4234；安装脚本改为失败关闭（回滚快照逐文件复算 + 数据库备份文件头校验 + 显式确认），删除"旧 EXE 支持 `--safe-preview`"的错误假设；冷回滚与回滚后业务重启是两个独立审批。
- **新候选**：源码 `1ef20c81`，EXE 8,459,010 B / `faa3166d…`，2,872 文件，清单 `accd463a…`（r1/r2 已归档）；三种自检全 0，逐文件复算 2,872/2,872 PASS。
- **测试**：完整套件 4,248 项 → 4,245 通过 / 2 失败 / 1 跳过；两处失败与未修改的父提交基线相同（同一 nodeid，测试临时目录只读），未删除未跳过。新增 11 项 R3 负向/集成测试。
- **事件（第 5 条）**：`FAULT_CLASS_CONFIRMED`（`SSLEOFError` → `SHEETS_READ_UNAVAILABLE` → `MODULE_PAUSED`）、`UNDERLYING_CAUSE_NOT_VERIFIED`（为何那一刻断网）。10:40 只读复核：旧 EXE `e9e3da33…` 未变、日志停在 06:06:49、进程无 443 外连（未偷偷重试）、Google 现在可建连（302/0.40 s）、3 条 hold 与 0 活动告警未变、故障后 0 条业务事件。
- **仍未做**：未安装、未停机、未重启、未碰生产 SQLite/Chrome9222、未合并或晋升。B3/B4 仍需维护窗口。

## RFQ-021-R2 定点补修（保留记录，2026-11-15 上午）

**当前状态：`RFQ021_R2_PASS_SOURCE_SCOPE / RELEASE_HOLD / NOT_DEPLOYED`；事件 `INC-20261115 ROOT_CAUSE_CONFIRMED`。**

- **早间事件（只读取证，已结案为单一故障）**：正在跑的是旧 EXE `E9E3DA33…`（PID 38948 `--start-inquiry` + watcher 34304，2026-11-14 13:47 启动）。06:06:28 报价模块开始，06:06:48 失败（19.3 s），06:06:49 `SHEETS_READ_UNAVAILABLE / SSLEOFError` → `MODULE_PAUSED`。**不是崩溃**（fatal.log 为空、无 Windows 应用错误事件）。**无未确认外部效果**（失败在读取阶段；故障后 0 条业务事件；采购状态、3 条 V13 hold、0 活动告警均未变）。详见 [INCIDENT-20261115](INCIDENT-20261115.md)。
- **CEO 三个 P0 全部属实并已修复**：范围绑定到 `compose_v12_production`（此前传 None＝全量）；邮件服务改为 `may_start_process_services()` 双层把关；邮件/登录/单笔动作在预览与越界订单上双层拒绝。详见 [REVIEW_FOLLOWUP](RFQ-021/REVIEW_FOLLOWUP.md)。
- **能力收窄（刻意）**：报价/TP/通知无法按订单隔离，现在直接拒绝（`SCOPE_MODULE_NOT_ISOLATABLE`），`smtp` 也不能作为写入目标。受控试运行当前只支持 `inquiry` 模块 + 指定订单。
- **新候选**：源码 `1314da5d`，EXE 8,457,679 B / `74586eb2…`，2,872 文件，清单 `74ae29c7…`（旧候选 `63bcd6ce…` 与清单已归档为 `-r1`）；三种自检全 0，逐文件复算 2,872/2,872 PASS。
- **测试**：完整套件 4,237 项 → 4,235 通过 / 2 失败 / 1 跳过；两处失败与未修改的父提交基线相同（同一 nodeid），捕获原因为测试临时目录写入被拒，非本轮引入，未删除未跳过。
- **仍未做**：未安装、未停机、未重启旧程序、未碰生产 SQLite/Chrome9222、未合并或晋升。B3 完整回滚快照与 B4 干净停机仍需维护窗口。
- **下一步**：CEO 复核 RFQ-021-R2。旧程序当前仍处于"采购模块暂停"，是否重启恢复属业务动作，需 Owner 单独授权（建议先确认到 Google 的连通性）。

## RFQ-021-R1 首次交付（保留记录，2026-11-15 凌晨）

**当前状态：`RFQ021_READY_FOR_CEO_RELEASE_REVIEW / NOT_DEPLOYED / NOT_MERGED / B5-B6-B7_CLOSED_IN_SOURCE`。** 最新执行证据：[FINAL_REPORT](RFQ-021/FINAL_REPORT.md)、[EXECUTION_LOG](RFQ-021/EXECUTION_LOG.md)、[安装与回滚](RFQ-021/INSTALL_AND_ROLLBACK.md)、[JSON](../docs/evidence/rfq021/rfq021-final-candidate.json)、[候选清单](../docs/evidence/rfq021/INSO_V1.6-artifact-manifest-r1.sha256)、[JUnit](../docs/evidence/rfq021/pytest-report.xml)。

- **B7 关闭（源码+测试）**：普通双击＝安全预览，不调 `start_process_services`、不迁移、不读 IMAP、不发 SMTP、不连 CDP，开始按钮显示「安全预览（不启动业务）」且禁用；`--start-inquiry` 缺范围直接拒绝。候选 `--preview-self-check` 真机跑两轮全绿。
- **B5 关闭（源码+测试）**：`RunScope` 限制订单/模块/写入目标，写入需 `OWNER-APPROVED:` 审批串；Google 写入在唯一租约处拦截，INSO 写入在既有门外面加一层拒绝，范围只收窄不放宽；无范围不启动，不会退回 full Start。
- **B6 关闭（源码+测试）**：`workflow_write_intents` 在外部请求前落盘；进程崩溃后残留的 PENDING/UNKNOWN 会阻断同一文档的后续写入；账本不可读/不可写一律 fail closed；没有自动清理路径。
- **候选**：源码 `8cded532`，EXE 8,455,788 B / `63bcd6ce…`，2,872 文件、无 `runtime/`；清单 `d5cc3d4c…` 经脚本逐文件复算 2,872/2,872 一致。RFQ-020 的 `b358f687…` 不再作为本轮证据。
- **测试**：新增 35 项负向测试全绿；受影响模块 2,886 项全绿；完整套件 4,223 项中 4,220 通过、2 失败、1 跳过，两处失败与**未修改的父提交基线完全相同**（同一测试、同一现象），非本轮引入，未删除任何测试。
- **未做**：未安装、未停机、未正常 GUI、未业务 Start、未碰生产 SQLite/Chrome9222，未合并 `develop`、未晋升分支。B3 完整回滚快照与 B4 干净停机仍需 Owner 单独批准的维护窗口。
- **保护不变**：221 SAVED `rec_440fafd372440ecf9dacabf660dd155d` 不重下；SHAHAB/115 `MANUAL_REVIEW` 未证真实采购；3 条 V13 报价 hold 保留。
- **下一步**：CEO 复核 RFQ-021。通过后仍分三步，各自单独授权：①维护窗口内做停机+完整回滚快照；②安装候选并只做安全预览验收；③受控业务启用。

## RFQ-020 CEO Review（保留记录，2026-11-14）

**当前状态：`RFQ020_PASS_BUILD_AND_ISOLATED_SELF_CHECK / RELEASE_HOLD / NOT_INSTALLED / RFQ019_PREP_PASS / RFQ018_SOURCE_PASS`。** 最新审核：[RFQ-020 CEO Review](RFQ-020/REVIEW.md)，执行证据：[EXECUTION_LOG](RFQ-020/EXECUTION_LOG.md)、[JSON](../docs/evidence/rfq020/rfq020-build-2026-11-14.json)、[完整 SHA256 清单](../docs/evidence/rfq020/INSO_V1.6-artifact-manifest.sha256)。

- **候选存在且 staging 自检 PASS（仅按 Executor 实测）**：固定代码 `25894efa`，离线 Python3.12.10/Tk8.6.15/PyInstaller6.16.0，`-BuildOnly` 生成候选 `build/windows-release-stage-1.6/dist/INSO_V1.6`，EXE 8,436,056 B / `b358f687…`、2,872 文件、无 `runtime/`；`--self-check=0`、`--idle-self-check=0`（3秒/停止/无业务线程），扫描通过。CEO 从 GitHub 校验清单 2872 无重复文件路径，并独立重算 manifest SHA256 `c8806aea…` 匹配。**CEO 未验证 Windows EXE 实物字节，也未实机执行自检。**
- **现场不变要限时表达**：Executor 比对 22:38–22:45 自检窗口生产 EXE/PID/SQLite size+mtime/Chrome15页不变；稍后自报生产 DB mtime 和 Chrome 页数变化，属于继续运行环境的动态观察，**不能称整个 RFQ 全程无变化或独立证明变动原因**。记录中的 23:00 观测时间早于其 22:50 Git 提交不合时序，正式发布前澄清。
- **B1/B2 阶段性关闭，B3/B4/B5/B6/B7 仍发布阻断**。无完整当前旧版程序+配置+一致 DB 回滚备份、无授权干净 Stop；正常 GUI 启动带 DB/IMAP/SMTP 副作用，full Start 不限单笔，重启丢 process-local document hold，禁止安装/正常 GUI/真实业务 Start。当前旧 EXE `E9E3DA33…` 仍为旧生产候选；其源码血缘不可证。
- **保护**：221 SAVED `rec_440fafd372440ecf9dacabf660dd155d` 不重下；SHAHAB/115 `MANUAL_REVIEW/RECONCILIATION_UNREADABLE` 未证真实采购；3 条 V13 报价 hold 保留。不能操作 Chrome9222、生产 SQLite/WAL/SHM、外部 Google/INSO/SMTP 或晋升分支。
- **接管纠正**：RFQ019 REVIEW 在 Executor 分支和 develop 均存在；`docs/BRANCH_POLICY.md` 只在 develop 存在。下一个窗口明确逐分支读取，不据旧工作树缓存判断仓库全局文件缺失。候选 manifest 可检不代替真实 staging 文件 re-hash。
- **下一步建议**：一次性有界推进 B5/B6/B7 的离线受控启动保护设计与测试，**需 Owner 新授权才能改源码**；届时因源码新 SHA 需重新 build 候选。B3 回滚备份和 B4 停机另按 Owner 维护窗口批准，不自动连锁。
