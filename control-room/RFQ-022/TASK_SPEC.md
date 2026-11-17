# RFQ-022 — 11-17 两笔未处理订单 + 全业务暂停：取证、定点修复、异常 UI 改造（待 CEO 复核）

**状态：`DELIVERED_FOR_CEO_REVIEW / INSTALLED_RUNNING / BUSINESS_VERIFIED`**
Owner 只转发一句 `Review RFQ-022`。收到这句话的 CEO 按 `AGENTS.md` 的顺序读本文件即可，不需要 Owner 复述任何上下文。

**复核所需材料（全部在 git 内）：**

| 内容 | 位置 |
|---|---|
| 需求与验收（本文件） | `control-room/RFQ-022/TASK_SPEC.md` |
| 技术记录（命令、哈希、时间线） | `control-room/RFQ-022/EXECUTION_LOG.md` → 详细证据 `control-room/RFQ-021/EXECUTION_LOG.md` 首节 |
| 当前状态 | `control-room/COORDINATION.md` 顶部 |
| 交接入口 | `control-room/CEO_HANDOVER.md` 顶部 |
| 一页式 Owner/CEO 摘要 | `control-room/RFQ-021/CEO_SYNC_20261117.md` |
| 候选文件清单（2,872 行） | `docs/evidence/rfq021/INSO_V1.6-artifact-manifest-rfq022.sha256` |
| CEO 结论（待你出具） | `control-room/RFQ-022/REVIEW.md`（尚未创建） |

## 1. Owner 原始要求

1. 查清 `2026` 表 982 行（`ADS1115IDGSR`×1500）与 983 行（`G60N100BNTD`×400）两笔 `未发` 为何没被处理，分别给出准确原因，不得笼统写"Google 异常"。
2. 查清 11-17 约三小时后全业务暂停的真正原因，找到第一个真实错误与异常类型，解释为何没有恢复；明确是否与"连续三小时升级停止"机制有关；不得凭截图猜根因。
3. **改造「异常与通知」页面**：真实故障时直接显示故障代码、发生时间、影响模块、具体原因、恢复过程、业务影响、建议操作、诊断位置；同一根因的连带暂停归并展示；重启后仍可查看；不泄露 Token/Cookie/客户隐私。
4. 定点修复 + 定向测试 + 候选构建 + 真实界面验证；涉及现场替换须保留旧 EXE/配置/数据库/回滚材料，遵循既有发布程序，不覆盖运行中的程序。
5. 不伪造订单、不改真实表格状态、不重复采购结果未知的订单；保持既有 UNKNOWN/SENT、去重、hold 与交易保护。

## 2. 本轮结论（摘要）

- **两笔订单都被正常发现并准入**，卡点是"重复检查"需要 INSO 浏览器，而 14:05 起每轮询价都在 CDP/登录巡检处失败（`BrowserBootstrapError`）。982 留下 4 次、983 留下 1 次 `DUPLICATE_CHECK_STARTED` 后中断。两笔当时**无告警、无采购事件、写意图 0 行**，从未产生外部写入。
- **全业务暂停是另一起独立故障**：报价读表时 `ssl.SSLEOFError`（TLS 中途断链），读层约 20 s 有界重试耗尽后，三处分类器把 TLS 断链判为"不可隔离" → `_defer_website_poll()` 拒绝推迟 → `_runtime_error()` → `_stop.set()`，全部业务停止且无自动恢复路径。
- **与三小时机制无关**：当日无任何 `*_OUTAGE_THREE_HOURS` 记录；落库 incident 为 `PROGRAM_SAFETY_PAUSED / PROGRAM_INTERNAL_STOP / MODULE_PAUSED`；且 `Browser/CDP` 在代码里被结构性排除在三小时规则之外。"隔三小时又崩"的观感来自退避间隔 900→1800→3600→7200 s。
- **两起故障无因果关系**：CDP 故障让订单卡住；TLS 故障结束整个运行。
- 同一 TLS 签名 **11-15 06:06:49** 已出现过（INC-20261115），属同一缺陷复发。

## 3. 代码改动范围（可 `git show aaac8c75` 逐条核）

| 文件 | 改动 | 复核要点 |
|---|---|---|
| `src/sheets/google_reader.py` | 新增 `TRANSIENT_TLS_READ_ERRORS`（`SSLEOFError`/`SSLZeroReturnError`/`SSLSyscallError`）计入 `_temporary_read_failure` | 证书类错误**不在**该集合内 |
| `src/workflow/v13_integration.py` | `is_isolated_source_read_error` 接受 TLS 中途断链 | 证书/DB/鉴权/所有权仍返回 False |
| `src/launcher/backend.py` | `_website_failure` 不再把瞬时 TLS 判为"非站点故障"；新增故障记录/恢复/水化/`_fault_cause_label`/`faults` 投影 | 证书仍返回 `None`；`get_workbench_snapshot()` 仍不取 `_lock` |
| `src/launcher/fault_diagnostics.py`（新） | `FaultDiagnostic` 投影 + 故障码中文目录 + 脱敏 | 只读 `reason_code` 与异常**类名**，从不读异常 message |
| `src/gui/workbench.py` | 「异常与通知」按故障渲染 | 无记录时不再输出"请人工核对"式空话 |
| `src/gui/contracts.py` | `WorkbenchSnapshot.faults` | 默认 `()`，旧调用方不受影响 |
| `src/workflow/v12_store.py` | `recent_fault_diagnostics()` 从既有 incident 行回读**未结清**故障 | 不新建表、不产生第二套状态 |
| `src/launcher/v13_integration.py` | 故障邮件复用同一诊断 | 界面与邮件不再互相矛盾 |

**未动（刻意）**：UNKNOWN/SENT、采购去重、write-intent 落盘、`workflow_v13_holds`、三小时门限、`--safe-preview`/`--scoped-start` 语义、双击即完整生产。

## 4. 定向测试（可 `git show aaac8c75 -- tests` 核）

新增 18 项：TLS 断链=有界隔离且不全局停止 / 证书仍失败关闭 / 重复表头块下 982-983 的物理行与准入、超七天仍拒 / 故障记录字段与恢复标记 / 持久化只回读未结清且同码去重 / 真实 Tk 页面渲染且不含旧空话。

## 5. 现场结果（19:26–19:37，**git 无法独立验证**，见第 7 节）

983 于 19:30:57、982（Owner 单笔重跑后）于 19:35:55 均 `PURCHASE_DATA_SAVED`，源表 `未发 → 发给采购`；两笔邮件各 2 个收件人 `SENT`；3 条 Google 写意图全部 `SETTLED`；活动告警 0；本次运行零 `runtime fault`、零 `deferred`、零异常栈。

## 6. 发布与回滚

- 候选：EXE `f2ffa44f…`（8,476,327 B / 2,872 文件），清单 blob SHA256 `08b0e9f6…`（2,872 行，git 可复算，命令见 EXECUTION_LOG）。
- 安装闸门：程序快照 `BACKUP_RESULT = PASS`、库副本与生产库逐字节一致、`DB_VERIFY_RESULT = PASS`（`process_state = stopped (proven)`、`write_intent_state = NONE_PROVEN`）、`INSTALL_RESULT = PASS`（逐文件 2,872/2,872）。
- 旧版保留 `.prev-20261117T112542Z`；冷回滚按 `RFQ-021/INSTALL_AND_ROLLBACK.md` 单独批准。

## 7. 请 CEO 重点判断的三件事

1. **分级是否过宽还是过窄**：把"TLS 中途断链"归入瞬时读，是否会被用来掩盖真正的证书/中间人问题？本轮的边界是"只有 `SSLEOFError`/`SSLZeroReturnError`/`SSLSyscallError` 三类算瞬时，`SSLCertVerificationError` 等证书判定仍失败关闭"，且有专门反证测试。请判断该边界是否足够。
2. **"异常与通知"是否达到 Owner 验收口径**：故障码、时间、影响模块与连带、原因与"未确认"标注、恢复阶段、外部写入、建议操作、诊断位置是否齐全；是否存在"看起来详细但仍是猜测"的措辞。请注意：真实故障态的实机证据目前只有快照级界面用例，历史 incident 无 `diagnostic` 字段，需等下一次真实故障才在实机出现。
3. **是否接受"重启后残留的纯读阶段订单转人工"**：982 因停在 `DUPLICATE_CHECKING` 被判 `INTERRUPTED_UNSENT`，需 Owner 点一次「重跑采购流程」。这是保守保护，本轮未放宽。若认为过严，属产品决策，应另开任务。

## 8. 已知缺口与待决（不由本轮修复）

1. **TP 不跑这两笔**：TP 只认 `RFQ_BRIEF.target_price`（`tp_research.py`），而两笔客户 TP 只写在 `2026` 的 `Remark` 文本里，该列为空 → 不建 TP 任务。选项：填该列，或改 TP 取价口径（影响所有行）。
2. **`CLASS` 列耦合**：`v12_rules.py` 中 `tier == "A"` 同时决定"必发重要询价"与采购走 `FULL_PRICE`（采购员 FULL_PRICE）。改等级会同时改邮件、采购员与报价口径。
3. **遗留 3 项保护（非本轮产生、不自动重试）**：`inq_71f4a2f5…`（2026 行 219）`UPDATE_RESULT_UNCONFIRMED`、`inq_d65be9df…`（SHAHAB 行 137）`QUOTE_INPUT_WRITE_FAILED`、`unresolved:0ca37…` `SOURCE_IDENTITY_UNRESOLVED`。

## 9. 禁止事项（延续 Owner 既有红线）

不重复采购结果未知的订单；不把客户 TP 等业务数据写入 git；不以安全预览/禁用模块冒充修复；不为让测试变绿而删除或跳过用例；未获单独批准不执行冷回滚或分支晋升。

## 10. 完成标准

CEO 可仅凭本仓库回答：两笔订单为何未处理（分别是）、暂停的第一故障是什么、是否与三小时机制有关、两问题是否有因果、改了哪些文件与依据、候选与安装证据、以及仍存的风险与待决项。若以上任一无法从 git 得到答案，视为本轮交付不合格。
