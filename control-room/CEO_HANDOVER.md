# INSO LEO — 新 CEO 接管入口（2026-11-23 下午，V1.7 运行中；浏览器受阻会通知）

**当前权威结论：`V1_7_INSTALLED / PRODUCTION_RUNNING / REAL_PURCHASE_VERIFIED / BROWSER_BLOCK_NOTICE_ON`。**
（2026-11-23 晚已按 CEO Review 修正：通知阈值改为"同一次故障持续 45 分钟"，且不再要求存在待采购订单。）
V1.7 已成交一笔真实采购；浏览器通道连续三轮（约 45 分钟）不可用时会发一封给 Owner 的提醒。
**Owner 已明确：V1.7 暂不晋升 `main`**，`main` 保持 V1.6。

## 现场状态

| 项 | 值 |
|---|---|
| 正在运行 | `dist\\INSO_V1.7\\INSO_V1.7.exe`，PID 101176（GUI）+ 100144（watcher） |
| 已安装 EXE | SHA256 `c796b705a9fbae59314af59c846a290550349b0fb9760689c11326783174ff6e`（8,511,862 B） |
| 回退（同目录） | `INSO_V1.7.exe.prev-20261123T082603Z` + `_internal.prev-20261123T082603Z` |
| 回退（整目录） | `dist\\release-backups\\RFQ-025-pre-r6-20261123T082453Z`（程序 + 库 + `DB_VERIFY_RESULT = PASS`） |
| V1.6 | 目录未动（`9a0cb3d3…2710`）；桌面入口为"旧版，仅回退用" |
| 分支 | `develop` 含整条 V1.7 线；`main` = `d954e0a5`（V1.6）；V1.7 **未晋升（Owner 指示）** |

## 下一步

- **不要再自动晋升 `main`。** 已有真实成交也仍是前瞻版本，等 Owner 另行决定。
- 会收到的新提醒：「【需要处理】Browser/CDP业务持续受阻」，正文会写"关闭该 Chrome 的窗口"。
  收到即照做（关窗口、不强杀、不换配置、不重启程序），下一轮程序自行继续。
- 再看到「INSO 无法核验页面 / 操作未关闭」：页面问题，不需要登录或验证码，重新开始即可。

---

# 此前：V1.7 运行中；真实采购已成交（2026-11-23 上午）

**当前权威结论：`V1_7_INSTALLED / PRODUCTION_RUNNING / REAL_PURCHASE_VERIFIED`。**

V1.7 的粘贴录单已经跑出第一笔真实成交：`AMPLA1004S-R22MT` / Abracon / 60（SHAHAB 145），
11-22 23:06 完成，ERP 对账确认已保存、Sheets 回写 SETTLED、重复检查 repeated=0。
细节见 [RFQ-025/FINAL_REPORT.md](RFQ-025/FINAL_REPORT.md) 第七节与
[EXECUTION_LOG](RFQ-025/EXECUTION_LOG.md) 第 26–31 节。

## 现场状态（先看这里）

| 项 | 值 |
|---|---|
| 正在运行 | `dist\\INSO_V1.7\\INSO_V1.7.exe`，PID 102276（GUI）+ 102836（watcher） |
| 已安装 EXE | SHA256 `6674f37b55a5410ed853ff9883815769a2175b109271edaca26f9ea211d1dc03`（8,511,663 B） |
| 回退（同目录） | `INSO_V1.7.exe.prev-20261123T034618Z` + `_internal.prev-20261123T034618Z` |
| 回退（整目录） | `dist\\release-backups\\RFQ-025-pre-r5-20261123T034455Z`（程序 + 库 + `DB_VERIFY_RESULT = PASS`） |
| V1.6 | 目录未动（`9a0cb3d3…2710`）；桌面快捷方式为“旧版，仅回退用” |
| 分支 | `develop` 含整条 V1.7 线；`main` 仍 V1.6；V1.7 **未晋升** |

## 下一步

- **晋升 `main` 由 Owner 决定**，即使已有真实成交也不自行晋升。
- **观察点**：上一版在 11:22 后曾出现 22 分钟无轮次（原定 11:37 应有一轮），无故障无停止记录。
  若新构建复现，需单独排查调度线程是否被静默挂起。
- 再看到“INSO 无法核验页面 / 操作未关闭”：那是页面问题，**不需要**登录或验证码，重新开始即可。
  只有明确写“需要人工登录/验证”才需本人处理。
- 若长时间只见 `BROWSER_WAITING_RECOVERY`：关闭 Chrome 窗口（不要强杀、不要换 profile），程序会自动重连。

---

# 此前：V1.7 运行中；误报登录故障已修（2026-11-22）

**当前权威结论：`V1_7_INSTALLED / PRODUCTION_RUNNING / FALSE_AUTH_ALARM_FIXED / REAL_PURCHASE_NOT_YET_VERIFIED`。**

11-22 早上那次“INSO 需要人工验证”是**误报**：报价读取把页面租约失效当成了登录失效，导致停止 82 分钟，
而 INSO 根本不需要验证。已按原因码区分并重装重启，详见
[RFQ-025/EXECUTION_LOG.md](RFQ-025/EXECUTION_LOG.md) 第 22–25 节。

## 现场状态（先看这里）

| 项 | 值 |
|---|---|
| 正在运行 | `dist\INSO_V1.7\INSO_V1.7.exe`，PID 90384（GUI）+ 90508（watcher） |
| 已安装 EXE | SHA256 `67cede70a38e73796456b143c25d440ce74d85042ab542e30d3e65f6a6e5da05`（8,510,928 B） |
| 回退（同目录） | `INSO_V1.7.exe.prev-20261122T063011Z` + `_internal.prev-20261122T063011Z` |
| 回退（整目录） | `dist\release-backups\RFQ-025-pre-v17fix-20261122T062633Z`（程序+数据库+`DB_VERIFY_RESULT = PASS`） |
| V1.6 | 目录未动；桌面快捷方式已改名“旧版，仅回退用” |
| 真实采购 | **仍未发生**（无合法待处理订单），不得按已验收对待 |

## 下一步

- 有合法待处理订单时让它自然跑完一次“保存并发送”，再以 ERP 单据 + Sheets 回写独立确认；
  不要为验收造单或重发。
- 晋升 `main` 由 Owner 决定。
- 若再看到“INSO 无法核验页面/操作未关闭”这类提示：那是页面问题，**不需要**做登录或验证码，
  重新开始即可；只有“INSO 需要人工登录/验证”才需要本人处理。

---

# 此前：V1.7 已安装并生产运行（2026-11-21 晚）

**当前权威结论：`V1_7_INSTALLED / PRODUCTION_RUNNING / REAL_PURCHASE_NOT_YET_VERIFIED`。**
`main` 仍是 Owner 验收的 V1.6（`d954e0a5`）；V1.7 已装进 `dist\INSO_V1.7` 并运行，
但**尚未晋升**，真实采购验收也还没发生（当前没有合法待处理订单）。

## 90 秒接管读序

1. [AI_START_HERE.md](../AI_START_HERE.md)、[AGENTS.md](../AGENTS.md)、[BRANCH_POLICY](../docs/BRANCH_POLICY.md)。
2. [RFQ-025/FINAL_REPORT.md](RFQ-025/FINAL_REPORT.md) → [EXECUTION_LOG](RFQ-025/EXECUTION_LOG.md) 第 14–21 节 →
   证据 [`docs/evidence/rfq025/`](../docs/evidence/rfq025/)。
3. 一/二阶段背景见 [TASK_SPEC](RFQ-025/TASK_SPEC.md) 与 `paste-import-sniff.md`。

## 现场状态（务必先看，别重复装）

| 项 | 值 |
|---|---|
| 正在运行 | `dist\INSO_V1.7\INSO_V1.7.exe`，PID 85452（GUI）+ 84368（watcher），业务运行中 |
| 生产 runtime | `dist\INSO_V1.7\runtime` 是 Junction → `dist\INSO_V1.4\runtime`（配置/库/日志共享） |
| 生产库 | `production.json` 里 `sqlite_path` 指向 `dist\INSO_V1.2\runtime\production\workflow.sqlite3`（历史指向，经 junction 到同一文件） |
| V1.6 | 目录未动，`INSO_V1.6.exe` = `9a0cb3d3…2710`；桌面快捷方式已改名"旧版，仅回退用" |
| 回退 | `dist\release-backups\RFQ-025-pre-v17-20261121T132826Z`（程序快照 + 数据库 + 校验报告） |

## 下一步（等 CEO 审核与 Owner 决定）

- **真实业务验收未完成。** 有合法待处理订单时，让它自然走完
  `Sheets 读取 → 调研/判断 → 草稿 → 粘贴 → 导入 → 预览核对 → 保存数据 → 保存并发送 → 回写`，
  再以 ERP 单据 + Sheets 状态独立确认。不要为了验收造单或重发。
- **晋升由 Owner 决定。** 即使试运行通过，也不得自行把 `main` 移向 V1.7。
- **V1.6 不要再启动。** 两套调度器共用同一台账；需要回退时先停 V1.7，再按回退材料恢复。
- **仍待 Owner 产品决策（沿用 RFQ-024，未变）：** 重启时中断的无写入、无 hold 任务是否自动重排。

---

# 此前：V1.7 候选已构建，待审核安装

**当前权威结论：`V1_7_IMPLEMENTED / LIVE_DRAFT_VERIFIED / RELEASE_CANDIDATE_READY / READY_FOR_CEO_REVIEW`。**
`main` 仍是 Owner 验收的 V1.6（`d954e0a5`）；V1.7 只在 `workbuddy/v17-native-paste`，未安装、未晋升。
生产程序当前处于**停止**状态（Owner 授权开发期间暂停），进程仍在但业务未运行。

## 90 秒接管读序

1. [AI_START_HERE.md](../AI_START_HERE.md)、[AGENTS.md](../AGENTS.md)、[BRANCH_POLICY](../docs/BRANCH_POLICY.md)。
2. [RFQ-025/FINAL_REPORT.md](RFQ-025/FINAL_REPORT.md)（六项交付 + 七段式）→
   [RFQ-025/EXECUTION_LOG.md](RFQ-025/EXECUTION_LOG.md) 第 8–12 节 →
   证据 [`docs/evidence/rfq025/`](../docs/evidence/rfq025/)。
3. 需要一阶段背景时再读 [TASK_SPEC](RFQ-025/TASK_SPEC.md) 与 `paste-import-sniff.md`。

## 下一步（等 CEO 审核与 Owner 指令）

- **候选 EXE 未安装。** 安装/试运行是下一轮：走既有 `install_release_candidate.ps1` 门禁，
  V1.6 目录与回退材料不得覆盖或删除。
- **真实发送未验证。** 本轮只做草稿链路；`保存并发送` 与完整业务结果验收留到安装试运行阶段。
- **生产未运行。** 若要恢复 V1.6 业务，用原 GUI 正常启动即可；本轮未改 `dist/` 下任何文件。
- **仍待 Owner 产品决策（沿用 RFQ-024，未变）：** 重启时中断的无写入、无 hold 任务是否自动重排。

---

# 此前：V1.6 已晋升 / RFQ-025 第一轮交付

**当前权威结论：`V1_6_PROMOTED_TO_MAIN / V1_7_BASELINE_READY / PASTE_SNIFF_COMPLETE / NO_BUSINESS_EFFECT`。**
`main` 已是 Owner 验收的 V1.6（`d954e0a5`），V1.1 引导陷阱关闭；V1.7 开发基线就绪；粘贴录单五步已在真实生产环境
完整跑通并实测确认"保存数据"为纯客户端回填。**没有产生任何 ERP 单据。** `src/` 至今零改动。
业务代码实现等 Owner 第二轮指令。

## 90 秒接管读序

1. [AI_START_HERE.md](../AI_START_HERE.md)、[AGENTS.md](../AGENTS.md)、[BRANCH_POLICY](../docs/BRANCH_POLICY.md)：
   权责、三条长期线、"首次对齐已完成"的现状（不要再按"main 还是 V1.1"行事）。
2. [COORDINATION.md](COORDINATION.md) 顶部 → [RFQ-025/TASK_SPEC.md](RFQ-025/TASK_SPEC.md) →
   [RFQ-025/FINAL_REPORT.md](RFQ-025/FINAL_REPORT.md) → [RFQ-025/EXECUTION_LOG.md](RFQ-025/EXECUTION_LOG.md) →
   脱敏页面证据 [`docs/evidence/rfq025/paste-import-sniff.md`](../docs/evidence/rfq025/paste-import-sniff.md)。
3. 需要 RFQ-024 的结案背景时再读 [RFQ-024/REVIEW.md](RFQ-024/REVIEW.md)、[INCIDENT-20261119.md](INCIDENT-20261119.md)、
   [INCIDENT-20261120.md](INCIDENT-20261120.md)。
4. 查实际远端 HEAD；具备现场能力时核验本地工作树、进程、实物版本、配置；仅能读 GitHub 时明确
   Windows 现场 `NOT_INDEPENDENTLY_VERIFIED`，不能声称已读取生产库。

## 现行基线与下一步

- **三条长期线：** `main` = `d954e0a5`（V1.6 现版，EXE `9a0cb3d3…`、清单 `5bd7d7a7…`）；
  `develop`（V1.7 基线，**已含 V1.6 源码**，合并提交 `d2473a2a`，tip 见 `git log develop`）；
  `release/previous` = `d244241e`（未动，`NOT_VERIFIED`）。
- **不可变发布记录：** `release/v1.6-official-20261121`、`release/v1.1-main-superseded-20261121`、
  `release/previous-superseded-20261121`、`preserve/sheets-v1-local-main-c3a597d9`。
- **`release/previous` 为什么还是 `d244241e`：** 本项目没有"经 Owner 在三分支制度下验收过的上一正式版"，
  用历史 V1.1 顶替就是伪造回退关系。下一次晋升起，被取代者才是 `d954e0a5`。
- **V1.7 待办（Owner 已定目标）：** 用 INSO 原生"粘贴"替换 AI 录单。替换点与可复用代码已在
  [RFQ-025/EXECUTION_LOG.md](RFQ-025/EXECUTION_LOG.md) 第 3 节写清；**当前 `src/` 零改动**。
- **粘贴录单已实测闭环：** Owner 停机后，登录 → `新增` → `粘贴` → `型号|数量|品牌` → `导入` → 预览 →
  `保存数据` → 父表单行 → 关闭，全链路跑通。实测 `新增` 不建单、`导入` 只发 1 次解析 POST、
  **`保存数据` 零非 GET 请求**、型号逐字节保持、ERP 自动补 `ProductID`；事后列表无新单。
  **未点 `保存` / `保存并发送`。** 详见 [RFQ-025/FINAL_REPORT.md](RFQ-025/FINAL_REPORT.md)。
- **实现阶段的注意点：** 登录会改写共享 `erp_token`，属生产动作；现场跑通仍须停机或维护窗口，
  不得在 V1.6 跑业务时登录。
- **仍待 Owner 产品决策（沿用 RFQ-024，未变）：** 重启时中断的无写入、无 hold 任务是否自动重排。未授权前保持原策略。
- 保持正常生产 GUI、完整业务功能和准确故障说明；不增加重复审批，不以安全预览冒充正式版。
  现场状态在下次实际维护前重新只读核验。

---

# 历史交接（2026-11-21 RFQ-024 结案，结论仍有效）


**当前权威结论：`RFQ024_SOURCE_AND_EVIDENCE_PASS / PRODUCTION_RUNNING_EXECUTOR_REPORTED / NO_PENDING_QUOTE_EXECUTOR_REPORTED / REVIEW_CLOSED`。** 当前没有待修复或待发布的阻断任务；保持运行中的正式生产版，不重新启动已结案 RFQ、不重发已完成订单。

## 90 秒接管读序

1. [AI_START_HERE.md](../AI_START_HERE.md)、[AGENTS.md](../AGENTS.md)：Owner/CEO/唯一 Executor 权责、真实可用生产版以及“异常与通知”自解释红线。
2. [COORDINATION.md](COORDINATION.md) 顶部 → [RFQ-024/CEO_SYNC_20261121.md](RFQ-024/CEO_SYNC_20261121.md) → [RFQ-024/REVIEW.md](RFQ-024/REVIEW.md)。如需根因，读 [INCIDENT-20261119.md](INCIDENT-20261119.md) 第 8–10 节（最终代理根因）、[INCIDENT-20261120.md](INCIDENT-20261120.md)（外部页面租约）。
3. 查实际远端 HEAD；具备现场能力时按 AI_START_HERE 核验本地工作树、进程、实物版本、配置及安全状态；仅能读 GitHub 时明确 Windows 现场 NOT_INDEPENDENTLY_VERIFIED，不能声称已读取生产库。

## 现行生产基线与下一步

- Repo：`Horse-Hunter/INSO_Leo`；分支 `workbuddy/v16-rfq016-stabilization`。已接受修复 `64d3ec2c`、`89e931bf`，审核输入 HEAD `b1b5b8151bc4468698dde93146f78a90322d32c3`（其后的 CEO 结案提交仅文档）。
- 最终 EXE SHA256 `9a0cb3d3d2101745deb014d4fa0f4c66072dc0da295923aa927f0e0387db2710`；清单 SHA256 `5bd7d7a792d9e4c91f32058fd8ce3affb11a7c29d387168fee65294bf26263ff`；2,872 文件；最终 JUnit 4332/0/0/1（4331 passed）。源码与清单已独立审核；Windows 装机和业务状态来自 Executor。
- 截至 11-21 10:11，Executor 报告当前进程自 11-20 14:50:55 正常运行约 19 小时，今日 117 轮业务零故障、无“采购已报价”滞留行。不要把模块轮次误称订单数，不把短期稳定误称永久稳定。当前没有需主动处理的故障。
- **仅待 Owner 产品决策**：是否调整重启后中断的无写入、无 hold 任务自动重排；未授权前保持原策略。不得自动重发实际已保存或结果未确认的采购/报价、清 UNKNOWN/SENT/hold。两项非阻断代码维护建议已记 REVIEW，不另起发布。
- 保留正常生产 GUI、完整业务功能和准确故障说明；绝不以安全预览版、禁用功能冒充正式版，不增加重复审批和 Review 循环。若 Owner 提出新任务，先按真实状态确定范围，委派唯一 Executor，独立审核证据即可；避免无故打扰正常运行。

**新窗口准备动作：** 阅读上述入口，确认接管状态及待决项，用中文简要报告已准备接管，不自行启动新任务或做生产改动。不要从历史聊天重新拼凑规则。

## 以下为旧 CEO 交接历史（非当前权威状态）

# INSO LEO — CEO 复核入口（2026-11-17 生产故障结案 + 新版上线）

**一句话入口：`Review RFQ-022`。** 当前有效状态 `DELIVERED_FOR_CEO_REVIEW / INSTALLED_RUNNING / BUSINESS_VERIFIED`。
读序：[RFQ-022/TASK_SPEC.md](RFQ-022/TASK_SPEC.md)（需求 + 复核清单 + 请 CEO 判断的三件事 + 待决项）→ [RFQ-022/EXECUTION_LOG.md](RFQ-022/EXECUTION_LOG.md)（可复算命令、现场声明边界）→ [RFQ-021/EXECUTION_LOG.md](RFQ-021/EXECUTION_LOG.md) 首节（完整时间线与日志）→ [RFQ-021/CEO_SYNC_20261117.md](RFQ-021/CEO_SYNC_20261117.md)（一页摘要）。结论写进 `RFQ-022/REVIEW.md`（尚未创建）。
分支 `workbuddy/v16-rfq016-stabilization`；提交 `aaac8c75`（修复）→ `f4190cf8`（安装）→ `849ed5d7`（业务结果）→ `95669170`（CEO 材料）；现场 EXE `f2ffa44f…`。下面各段为本轮之前的历史交接，仅供追溯。

## 历史交接（2026-11-16 及更早，非当前状态）

# INSO LEO — 新 DeepSeek Executor 最终发布+真实单笔订单入口（2026-11-16）

**最新 Owner 权威授权见 [COORDINATION.md](COORDINATION.md) 顶部：不仅安装，还要真实执行一笔 inquiry；不再另设阶段性 CEO Review。** 上一版交接中“只允许安全预览/禁止真实业务”的描述已由 Owner 后续明确指令取代，不能拿历史段落阻止已经授权的单笔订单。

先读 `develop/AGENTS.md`，本分支 `RFQ-021/REVIEW.md`、`RFQ-021/INSTALL_AND_ROLLBACK.md`、`RFQ-016/TASK_SPEC.md` 与 `RFQ-016/EXECUTION_LOG.md`；保留唯一工作树。固定候选源码 `6a75cc93`，EXE `f1a0351d…`；先按真实门禁安装和安全预览，再使用**仅 inquiry 模块、唯一订单、google/inso 写入**的 `--scoped-start` 运行，批准引用 `OWNER-APPROVED:RFQ016-REAL-20261116`。221 行先核对 SAVED，已保存则不得重下，选一笔新的合法未发真实订单。异常按已有 UNKNOWN/去重门禁停止对应效果；顺利则一次性运行至真实回执确认和归档，无需再向 CEO 请求下一阶段批准。

## 前次 R5 源码放行与历史交接（仍可追溯，不是当前 Owner 业务授权范围）

# INSO LEO — CEO/Executor 交接入口（2026-11-15 R5 Final PASS）

**当前 CEO 最终源码结论：`PASS_SOURCE_AND_OFFLINE_RELEASE_READY / RELEASE_HOLD / NOT_DEPLOYED`。** <u>不要再开 R6 或重复开发</u>；先读 `develop/AGENTS.md` 与 [RFQ-021/REVIEW.md](RFQ-021/REVIEW.md) 最新最终 R5 段和 [COORDINATION.md](COORDINATION.md)。

**固定候选：** 源码 `6a75cc93130c8b7805569edfc3131f82032e22c4`；EXE `f1a0351d…`；清单 `5dfce4c1…`。预补丁 R5 候选严禁混用。下一阶段仅在 Owner 明确授权的维护窗口进行 B4 正常停机、真正回滚材料和生产安装前门禁检查；此文档不授权任何动作。未经单独许可，任何生产进程/订单/SQLite/Chrome9222/Google/INSO/SMTP/分支晋升均不得操作。

## 历史 R5 Executor 及 CEO 阻断记录（仅追溯，不是当前许可）

# INSO LEO — RFQ-021-R5 CEO Review 交接（2026-11-15 晚）

**当前唯一有效 CEO 状态：`R5 CHANGES_REQUESTED / RELEASE_HOLD / NOT_DEPLOYED`。** 执行前先看 [CEO REVIEW R5](RFQ-021/REVIEW.md) 顶部和 [COORDINATION](COORDINATION.md)。R5 源码基线 `2c58529d`，候选哈希 `be7c0d3…` 属旧 R5 待补基线，不能在修复后沿用。仅需在 R5 内补两个 fail-closed 条件：写入意图 NULL/缺表不准 PASS，进程枚举不可确认不准当已停机；定向负测、冻结后全测、一次重建。复用唯一 Executor 工作树，禁止生产变更及版本晋升。

## R5 Executor 和此前历史交接（非最新 CEO 许可）

# INSO LEO — CEO/Executor 接管入口（2026-11-15 R5 Executor 交付，待 CEO 复核）

**当前状态：`R5 SOURCE_AND_OFFLINE_RELEASE_READY_FOR_CEO_REVIEW / RELEASE_HOLD / NOT_DEPLOYED`（Executor 自报，不是发布许可；两个 fail-closed 补丁已完成，待 CEO 复核）。** 先读 `develop/AGENTS.md` 精简规则、[CEO REVIEW](RFQ-021/REVIEW.md) 的最新结论、[COORDINATION](COORDINATION.md) 顶部与 [EXECUTION_LOG](RFQ-021/EXECUTION_LOG.md) 的 R5 段。R5 收尾补丁后的冻结源码 `6a75cc93`，唯一候选 EXE `f1a0351d…`（8,461,034 B / 2,872 文件 / 清单 `5dfce4c1…`），三种自检 0，安装门禁离线 **156** 项 PASS，全量 4,277 项 → 4,276 通过 / 0 失败 / 1 跳过（平台条件跳过）。补丁前那版（源码 `2c58529d`、EXE `be7c0d3f…`、清单 `a969a9bf…`、门禁 107 项）只作历史证据保留，不得当作新候选。

**R5 处理了 R4 五个阻断：** 回滚快照配置绑定真实 runtime junction，且备份/安装的账本路径改为取自实时配置（本机 junction 指向的 `dist\INSO_V1.4\runtime` 里没有 `production\`，真实库在 `dist\INSO_V1.2\runtime\production\workflow.sqlite3`）；切换后逐文件复算、回滚按快照逐文件恢复并验证，恢复中断报 `ROLLBACK_REQUIRED`；数据库证明＝配置源路径＋独占句柄停机一致性＋业务不变式＋报告与安装目录/账本互绑，存在未结算写入意图直接拒绝；`_run_login_sweep(check_only=True)` 与手动执行器末端的范围复检；六项全量失败定性为环境（测试临时树不可写）并加会话级 WAL 探针。详见 EXECUTION_LOG R5 段与 [候选 JSON](../docs/evidence/rfq021/rfq021-final-candidate-r5.json)。

**仍未做：** 未安装、未停机、未重启、未执行业务试运行、未碰生产 SQLite/Chrome9222。B3 现场安装/冷回滚与 B4 干净停机仍需 Owner 维护窗口。没有 Owner 单独授权，禁止停/启旧程序、安装、业务写入或晋升分支。

## R4 CEO Review 历史交接

**R4 权威结论（历史）：`R4 CHANGES_REQUESTED / RELEASE_HOLD / NOT_DEPLOYED`。** 固定 R4 源码 `2ad471e7`、候选 `19918185…` 仅作历史离线证据，已被 R5 取代（清单保留为 `…-manifest-r4.sha256`）。

## R4 Executor 历史交接（待审标注已被 CEO 结论覆盖）

**当前唯一 CEO 结论：`RFQ-021-R3 CHANGES_REQUESTED / RELEASE_HOLD / NOT_DEPLOYED`；R4 执行结果待独立复核。** [独立审核及 R4 验收范围](RFQ-021/REVIEW.md)；[当前指挥状态](COORDINATION.md)。R3 Executor 的 `PASS_SOURCE_SCOPE` 是历史自测记录，R4 的执行记录同样是自测，二者都不是发布许可。

**R4 已提交待审：`2ad471e7` → 候选 `19918185…`（8,459,710 B / 2,872 文件 / 清单 `2de4df2f…`，逐文件 2,872/2,872 PASS），三种自检 0，安装门禁离线 13 项 PASS。**差异、审计矩阵与失败 nodeid 见 [EXECUTION_LOG](RFQ-021/EXECUTION_LOG.md) 的 R4 段。**R4 自测 PASS 不等于 CEO 通过，也不构成部署授权。**

**高效接管顺序：** 先显式读 **`develop`** 的 [AI_START_HERE](https://github.com/Horse-Hunter/INSO_Leo/blob/develop/AI_START_HERE.md)、[AGENTS（Lean Review）](https://github.com/Horse-Hunter/INSO_Leo/blob/develop/AGENTS.md) 和 [BRANCH_POLICY](https://github.com/Horse-Hunter/INSO_Leo/blob/develop/docs/BRANCH_POLICY.md)；再读本分支本文件、`COORDINATION.md`、`RFQ-021/REVIEW.md` 和执行日志最新 R3 记录。先比对固定源码 `1ef20c81` 的差异与关键效果路径，不重复通读历史文件。恢复原 Executor 工作树前核实本地 HEAD/status/diff/worktree，不清理未知改动。

**R4 仅允许离线修改和测试：** 集中修复协调器启动/轮询对范围外订单的本地状态、事件、告警影响；强制旧版回滚快照完整与有效 runtime junction；同步 `order_action_hint`。迭代时定向测试，冻结代码后一次完整测试及一次最终构建，真实结果写原 `EXECUTION_LOG.md`。任何源码变更须重建候选，不可沿用 R3 EXE 哈希。

**事故和生产：** 06:06 `SSLEOFError` → `SHEETS_READ_UNAVAILABLE` → `MODULE_PAUSED` 为确认故障类别，底层网络原因未知。10:40 旧 EXE `e9e3da33…` 与 PID 38948/34304 的读取证据有时间边界，不能宣称此刻仍然运行。B3/B4 未完成，未经 Owner 另行授权不得停机、重启、安装、真实订单/写入、碰 Chrome9222/生产 DB、清理 hold/UNKNOWN 或移动 `develop/main/release`。

## R3 Executor 历史交接（保留证据，非最新 CEO 决定）

**先访问 `develop`，不要默认 `main`**：[AI_START_HERE](../AI_START_HERE.md)、[AGENTS](../AGENTS.md)、[BRANCH_POLICY](../docs/BRANCH_POLICY.md)、[COORDINATION](COORDINATION.md)、[RFQ-021 REVIEW_R3](RFQ-021/REVIEW_R3.md)、[INC-20261115](INCIDENT-20261115.md)、[安装与回滚](RFQ-021/INSTALL_AND_ROLLBACK.md)。新窗口先 fetch 最新 develop，再核对本地 git HEAD/status/worktree 与运行中的进程。**只保留一个 Executor 工作树，不得关闭正在运行的生产程序。**

**最新结论：`RFQ-021-R3 PASS_SOURCE_SCOPE / RELEASE_HOLD / NOT_DEPLOYED`；`INC-20261115 FAULT_CLASS_CONFIRMED / UNDERLYING_CAUSE_NOT_VERIFIED`。**
源码 `1ef20c81`，候选 EXE `faa3166d41db5a738348dc57f6adebbfcda0b3dbf29eb99f3549cf0d0d2596c1`（8,459,010 B，2,872 文件），清单 `accd463a…` 已逐文件复算 2,872/2,872。**只以这一个候选为准**；r1（`63bcd6ce…`）、r2（`74586eb2…`）与各自清单已归档为历史。

**R3 修了什么**：①后台 `retry_saved_statuses`/`process()` 按范围过滤——范围外 SAVED 订单即使 google 授权也不会写 Google 或改状态；显式 `inquiry_ids` 与范围冲突直接拒绝。②一键登录在预览/受控范围下无条件拒绝（与写入权限无关）；手动动作按模块与写入族逐个审计，`edit` 需 google、`purchase` 需 inso+google。③手册源码 SHA、单一候选、R2 计数更正；安装脚本失败关闭（回滚快照复算 + DB 备份文件头 + 显式确认），不再假设旧 EXE 支持 `--safe-preview`；冷回滚与回滚后业务重启分两次审批。

**今早事件**：旧 EXE `e9e3da33417414abac53f8a88a67d9f053bcdaeab9730eae9ad8bd7870dffad0` 仍在运行（PID 38948 + 34304，11-14 13:47 启动）。06:06:49 `SSLEOFError` → `SHEETS_READ_UNAVAILABLE` → `MODULE_PAUSED`；非崩溃、无未确认外部效果。10:40 复核：日志停在 06:06:49、无 443 外连、Google 现在可建连、3 条 hold 与 0 活动告警未变、故障后 0 条业务事件。**重启旧程序属业务动作，需 Owner 单独授权。**

**测试**：4,248 项 → 4,245 通过 / 2 失败 / 1 跳过；两处失败与未修改父提交基线相同（测试临时目录只读），未删除未跳过。

**仍未做**：未安装、未停机、未重启、未碰生产 SQLite/Chrome9222、未合并或晋升。B3 完整回滚快照、B4 干净停机仍需维护窗口。

## RFQ-021-R2 定点补修（保留记录，2026-11-15 上午）

## RFQ-021-R1 首次交付（保留记录，2026-11-15 凌晨）

**结论：`RFQ-021 READY_FOR_CEO_RELEASE_REVIEW / NOT_DEPLOYED / NOT_MERGED`**。源码 `8cded532`，候选 EXE `63bcd6ce…`（8,455,788 B，2,872 文件），清单 `d5cc3d4c…`；`--self-check` / `--idle-self-check` / `--preview-self-check` 全 0。完整套件 4,223 → 4,220 通过 / 2 失败 / 1 跳过，两处失败与父提交基线相同。**未安装、未停机、未启用业务。**

## RFQ-020 CEO Review（保留记录，2026-11-14）

**结论：`RFQ-020 PASS_BUILD_AND_ISOLATED_SELF_CHECK / RELEASE_HOLD`**。使用 `workbuddy/v16-rfq016-stabilization` 原工作树，固定源码 `25894eface6ea622153d1573c19d0ca6b9ad72aa`（RFQ-018 PASS），PyInstaller BuildOnly 候选 EXE `b358f68715f9e1dadeae19d5ad5b0f517664756105ebf1fcea1b843dc482d29c`（8,436,056 B，2,872 文件，无 runtime），manifest `c8806aea…`。CEO 已从 GitHub 独立重算清单哈希并接受，但未验证 Windows EXE 实物字节、未实机执行自检。**未安装、未停机、未合并。**

**生产不变的时间边界**：22:38–22:45 自检窗口内旧 EXE/SHA/PID/SQLite/Chrome 15 页未变；之后运行中的旧版继续处理业务，DB mtime 与页数自行变化。原记录中的「23:00 观测」已在本轮更正为约 22:47（早于其提交），属记录时序错误，不涉及未授权动作。CEO 未实机归因。

**保留旧业务**：221 行 INSO SAVED `rec_440fafd372440ecf9dacabf660dd155d` 不重放；SHAHAB/115 `MANUAL_REVIEW/RECONCILIATION_UNREADABLE` 原生 INSO `NOT_VERIFIED` 不冒称成功；3 个旧 V13 quote holds 不清。最近 Executor 报告旧 EXE SHA `E9E3DA33…` app PID38948/watch34304，Chrome9222 PID24164，生产 SQLite `dist/INSO_V1.2/runtime/production/workflow.sqlite3`；均需现场重新只读确认。**不允许**无授权停旧 EXE、生产数据库备份/修改、接管 Chrome、正常 GUI、业务 Start、真实 Google/INSO/SMTP 写入、合入 develop/晋升 main 或 release。
