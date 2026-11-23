# RFQ-025 — 最终汇报（第五阶段：真实采购已成交，V1.7 收尾完成）

**状态：`V1_7_INSTALLED / PRODUCTION_RUNNING / REAL_PURCHASE_VERIFIED / BROWSER_BLOCK_NOTICE_ON`**
（Owner 2026-11-23 决定：浏览器持续受阻要通知；V1.7 暂不晋升 `main`）

一句话：V1.7 装在 `dist\INSO_V1.7` 正常跑生产，**第一笔真实采购已于 2026-11-22 23:06 走完整条粘贴链路成交**
（ERP 对账回读确认为已保存、Sheets 回写 SETTLED、重复检查 repeated=0）；期间两次"误报"已修掉，
其中一次是登录页没加载被写成"需要验证码"，另一次是同一行单据每轮重复写"人工处理已记录"499 次。

## 七段式

```text
正在实现什么：
把采购询价单的录单方式从 INSO 的 AI 识别换成 ERP 自带的粘贴导入，收尾后装机、启动、跑真实业务。

理想变化是什么：
不再依赖 AI 识别服务；型号、数量、品牌直接用已经确认过的数据，由 ERP 自己解析并补产品编码，
流程更短、外部依赖更少、误差来源更少。

以前是什么：
录单走"AI录单"弹窗，把型号·品牌·数量交给外部 AI 识别再回填；V1.6 还在 dist\INSO_V1.6 里跑着，
粘贴路径只在代码和嗅探脚本里验证过，没有装、没有跑生产。

现在是什么：
V1.7 装在 dist\INSO_V1.7，独自占用同一个 runtime（配置、生产库、日志全沿用），
通过桌面"INSO V1.7（最新版）"启动，正在按 900 秒周期跑 inquiry / quotation / tp。
录单走"粘贴"：写"型号|数量|品牌"→导入→读预览逐项核对→保存数据交给单据。AI 路径已不在生产代码里。

做完了什么：
TP 22 条失败的根因定位与修正、粘贴两处收尾（单笔隔离、字段映射守卫）、最终全量回归、
一次最终候选构建、安装脚本跨版本适配、正式安装、正常生产启动与实盘观察。

测试结果：
全量 4365 项：0 失败 / 0 错误 / 1 跳过（上一轮那 22 条 TP 失败全部转绿，未删未跳）。
安装门禁 202 项 PASS。真实运行：三个模块各跑完至少一轮，零 ERROR、零 Sheets 故障。
真实采购：没有发生——当前没有合法待处理订单，未造单、未重发历史订单。

你接下来需要做什么：
1) Review 本轮交付与安装证据；2) 有合法待处理订单时，让它自然跑完一次"保存并发送"，
   再确认 ERP 单据与 Sheets 回写＝真正的业务验收；3) 你决定何时把 V1.7 晋升 main。
```

## 一、本轮实际实现的功能与修改范围

只换录单方式，其余业务一行未改。

| 文件 | 本轮改动（第三阶段） |
|---|---|
| `src/inso/purchase_writer.py` | 新增 `PasteImportPanel.ensure_layout()`：读 `#cmb0/#cmb1/#cmb2` 与 `#combox101` 隐藏值，默认正确时只读；不一致时用弹窗自带下拉改回并复读；改不回 fail-closed |
| `src/launcher/v12_composition.py` | `prepare()` 插入 `prepare-paste-layout` 步骤（打开弹窗之后、写数据之前） |
| `src/workflow/v12_flow.py` | `build_paste_input()` 的 `ValueError` 改走既有单笔无效输入通道，不再中断整轮 |
| `src/workflow/tp_research.py` | `_run()` 统一时间基准（`current_now`）；`run_due` 仍用调用方 `now` |
| `tests/*`、`scripts/install_release_candidate.ps1`、`scripts/test_install_gates.ps1` | 时基修正、6 条新用例、安装脚本跨版本参数化 + `-FreshInstall` |

**未改动**：去重/七天窗口/准入、`save_data`、`save_and_send`、`UNKNOWN/SENT`、hold、
Sheets 读写、报价、TP 业务规则、邮件、调度周期、代理与 CDP 修复。

## 二、真实页面录单验证

用生产同一条组合链（`attach_inso_research_session → operation_page → InsoPurchaseWriter →
CoordinatorPurchaseDraftWriter.prepare`）跑了 **两次**：加布局守卫前后各一次，结果一致。

| 项 | 实测 |
|---|---|
| outcome | `AI_RECOGNIZED`（历史持久值，语义=预览已核对通过） |
| 回读 | `TRJC476K016RRJ` / `Kyocera Avx` / `200`，与订单一致 |
| 解析请求 | 恰好 1 次 `POST /services/product/import.ashx` |
| AI 请求 | **0** |
| `#BillID` | 空 —— 未创建任何服务端单据 |
| 布局守卫 | 默认配置下**一个控件都没点**（隐藏值已是 PartNo/Qty/Brand + 3） |

见 `docs/evidence/rfq025/v17-live-verification.md`（含第 5 节第三次实测与控件结构）。

## 三、正常生产路径是否还有 AI 录单

没有。

- 源码守卫测试 `test_the_production_draft_path_carries_no_ai_entry_anywhere` 断言
  `src/inso/purchase_writer.py` 与全部控件绑定里不含 `Import_ai.aspx` / `#ai_import_` / `ai-recognize`；
- 两次真实运行的请求监听里 AI 端点命中数为 0；
- 保留的 `AI_RECOGNIZED` / `AI_RECOGNITION_MISMATCH` 只是 SQLite 与事件目录里的历史持久值
  （改名要数据迁移，Owner 已允许保留），用户可见文案已全部改为"粘贴录单"。

## 四、定向与完整回归

```
4365 collected / 4364 passed / 0 failed / 0 errors / 1 skipped in 765 s
```

- 上一轮 22 条 TP 失败**全部转绿**；没有删除、没有跳过、没有改 TP 规则或日期限制。
- 根因（与 CEO 判断一致）：TP 按"上月同日"计算截止日，夹具订单固定 `2026-10-20`，
  而省略 `now` 的调用点读墙上时钟 —— 在 `2026-11-21` 运行时截止变成 `2026-10-21`，订单被自己的夹具判过期。
  修法：`build()` 给 `TpCycle` 传 `clock=lambda: NOW`（既有参数），并让 `_run()` 全流程只用这一个时间基准。
  过程中发现并修掉一个自相矛盾：`read_orders` 认 clock、`claim` 却拿原始 `now`。
- `ruff check src tests` 仍只有基准的 3 条既有 F811。
- 顺带修掉安装门禁夹具的同类时间腐坏（事件时间固定在 11-15，72 小时新鲜度门禁必然过期）。

## 五、安装的 V1.7 与源码

| 项 | 值 |
|---|---|
| 安装目录 | `D:\Program_Leo\INSO_Leo\dist\INSO_V1.7`（全新目录，V1.6 未触碰） |
| EXE | `INSO_V1.7.exe` 8,510,418 B |
| EXE SHA256 | `6e258a5021792a1b4b88a72ca12d355064aab8c398e64eb58240ef542dece780` |
| 文件数 | 2,872（已逐文件按清单复核） |
| 清单 | `docs/evidence/rfq025/INSO_V1.7-artifact-manifest.sha256`（2,872 行） |
| 清单 SHA256 | `e148a4d22a5c2b9a7b81b484fc6228ec162cd112e896eed3aa67ace2426f5397` |
| 源码 commit | `1ce1671f`（之后只有文档提交） |
| runtime | Junction → `D:\Program_Leo\INSO_Leo\dist\INSO_V1.4\runtime`（配置/生产库/日志沿用同一份） |
| 安装结果 | `INSTALL_RESULT = PASS`，`rollback_kind = PREVIOUS_INSTALL_UNTOUCHED` |

回退材料（全部现成）：
`dist\release-backups\RFQ-025-pre-v17-20261121T132826Z`（V1.6 程序快照 + `PROGRAM-MANIFEST.sha256`）
与同目录 `database\workflow.sqlite3` + `.verify.json`（`DB_VERIFY_RESULT = PASS`，40 条采购记录）。
V1.6 目录本身一个字节未动，`INSO_V1.6.exe` 仍是 `9a0cb3d3…2710`。

## 六、实际 GUI 与生产运行状态

```
PID 102276  INSO_V1.7  「INSO LEO V1.7 — Procurement Automation Control Center」
PID 102836  INSO_V1.7  （watcher）
fatal.log 0 字节；安装 EXE = 6674f37b…dc03
```

以正式生产模式启动（`--start-inquiry` 就是「开始运行」调用的同一个 `backend.start()`），
首轮三个模块全部完成且零 ERROR：inquiry 11.1 s / quotation 71.8 s / tp 0.5 s。
上一版（`67cede70…da05`）在 11-22 14:31–11-23 11:22 期间持续运行，期间完成过真实成交，
`ERROR` / `SHEETS_*` / `fault` 命中数 0。

## 七、真实采购结果：已成交

`inq_7bd2f5dbc94f50e27a474821` —— SHAHAB 第 145 行，`AMPLA1004S-R22MT` / `Abracon` / `60`，
2026-11-22 23:06（本地）完成：

| 环节 | 证据 |
|---|---|
| 七天重复检查 | `outcome=CONFIRMED`、`repeated=0`（没有重复采购） |
| 录单 | `PURCHASE_DRAFT_STARTED` → 粘贴 → `AI_RECOGNITION_READY`（预览核对通过） |
| 保存并发送 | `SAVE_DISPATCH_ARMED` → `SAVE_CLICK_COMPLETED`，控件为 `#btnSave2` |
| 结果确认 | `SAVE_OUTCOME_UNKNOWN` → `RECONCILIATION_CONFIRMED_SAVED`（**ERP 对账回读确认**） |
| Sheets 回写 | `GOOGLE_WRITE` 15:06:18 建立、15:06:19 `SETTLED` |
| 台账 | purchase 行 41 条、`outcome=SAVED`；工作项 `COMPLETED`，`attempt_count=1` |

这一单在成交前曾被 CDP 卡死推迟（20:43–23:04，见下节），恢复后自行续跑完成，
说明"推迟 → 恢复 → 继续"这条路径也是通的，且订单没有丢。

## 七点五、2026-11-22 早上那次"需要人工验证"：误报，已修

**现象**：07:27 报价轮次失败 → `runtime fault reason=INSO_AUTHENTICATION_REQUIRED` → 全局停止 82.5 分钟；
GUI 提示"INSO 需要人工登录/验证"。Owner 到 INSO 看过，**不需要验证**。

**三条反证**：日志里登录尝试 0 次（无 `session is being established by logging in`、无
`INSO_LOGIN_RETRY_EXHAUSTED`）；08:49 恢复后同一个会话读完同样的 47 条，结果与故障前一致；
进程 PID 未变（进程内停止 → 重新开始）。

**根因**：`InsoQuotationReader` 把**任何** `SecurityViolation` 都翻译成"登录失效"。而这条路径上的
违规全部来自租约/页面身份 —— `verified shell page is closed`、`page identity changed`、
`browser or context is stale`、`operation identity is required`。页面问题冒充登录问题，
于是提示 Owner 去做一件根本不存在的事。

**修复**：
- 只按原因码判登录失效（`MANUAL_VERIFICATION_REQUIRED` / `CREDENTIAL_REJECTED` /
  `AUTHENTICATION_REQUIRED` / `SESSION_IDENTITY_UNVERIFIED`）；其余变成既有的
  "本次读取未结算、单独重试"，不再影响整轮；
- `_reopen()` 遇到页面类违规不再停全世界，改走 `open()` 已有的全新页面路径；
- `close()` 无法核验页面时**仍然**保留该页、**仍然**停止（页面归属 fail-closed 不变），
  但原因码改为 `INSO_OPERATION_NOT_CLOSED`；`preserve()` 记住原因，下一阶段报真实原因；
- 诊断文案新增该码，明确写"这**不需要**你去做登录或验证码"。

**没有放宽的东西**：真验证码/密码被拒仍全局停止（CAPTCHA / 手机验证码 / 设备验证三例覆盖）；
页面保留策略、写入门禁、UNKNOWN/SENT/hold 一律未动。

**重装**：源码变更 → 重建 `67cede70…da05`（清单 `cd085807…f2c0`）→ 就地切换
`INSTALL_RESULT = PASS` → PID 90384/90508 重新开始，14:31 起 inquiry/quotation 正常、零 ERROR。

**顺带**：装第二遍时暴露 `backup_running_release.ps1` 与 `verify_database_backup.ps1` 各自写死
`INSO_V1.6.exe`；后者会**漏掉** V1.7 进程，等于能出具假的"已停机"证明。两处都改成按目录/按版本族识别。

## 七点六、2026-11-23：CDP 卡死与两处误报

**CDP WebSocket 卡死（20:43–23:04，2 h 21 min）**：`/json/version` 与 `/json/list` 都正常返回，
但 Playwright 浏览器级 WS 握手 15 s 超时、放宽到 60 s 仍超时 —— 是卡死，不是慢。
程序按设计把轮次推迟（不全局停止、不杀 Chrome、不换 profile），Owner 关闭 Chrome 窗口后自动恢复。
那段时间**没有外发告警**：程序生成了 `PROGRAM_OPERATION_BLOCKED`，但其证据里 `active=False`、
`recovered_at` 已落地，派发前被 `EVENT_NOT_CURRENT` 抑制 —— 这是既有策略（Browser/CDP 属等待重试类），
本轮未改；是否要改成必须外发，请 Owner 决定。

**修复一：登录页没加载 ≠ 需要人工验证。** 11-21 23:27 那条告警正文其实写着
`InsoAuthenticationError(LOGIN_PAGE_UNAVAILABLE)`，却被表述成"需要验证码"。原因是报价适配器把任何
`InsoAuthenticationError` 抢先包成全局停止，压过了模块层本来正确的分类。现在只有 4 个真验证码/凭据码
才全局停止，其余交回模块层走"等待 INSO 恢复"。

**修复二：header 行的"已跳过"原因每轮重复写。** `inq_9886…` 是 `2026` 表第 146 行、型号字段就是表头字
`MPN`；`INVALID_INPUT_SKIPPED` 本身在可对账集合里，导致每 15 分钟重复记一次
`HUMAN_RESOLUTION_RECORDED`，累计 **499 条**。现在只记一次，告警清理仍每轮执行。
生产实测：新构建跑完首轮后该单事件数仍为 499。

## 七点七、浏览器通道持续受阻：现在会通知（2026-11-23 下午）

**原设计为什么一定不发**：`*_WAITING_RECOVERY` 属于 `persistent_stop`，其 `needs_owner`
只在三小时升级时为真；而 Browser/CDP 被显式排除在三小时之外；`review_reason` 的第一道门槛
又要求 `needs_owner` —— 三者相加，通知永远停在 `EVENT_NOT_CURRENT`。11-22 那条记录的字段正是
`needs_owner=False`、`completed_cycles=2`、`recovered_at` 已落地。

**改法（只动 Browser/CDP）**：该站点的 `needs_owner` 不再等三小时；通知仍受
`completed_cycles >= 3`（约 45 分钟）与"派发时仍在停摆"约束 ——
卡一两轮就好的不发，发之前已恢复的取消。收件人仍只有 Owner，Google 等待类仍按三小时规则。

**文案纠正**：原建议写着"不要关闭该 Chrome"，而实际清掉 11-22 那次卡死的正是关闭窗口；
邮件与诊断现在都写"关闭该 Chrome 的窗口（不必强杀进程、不要换配置），程序下一轮自行继续"。

**证据**：4 条新用例（真实后端 + 假 SMTP），去掉 `needs_owner` 那行后第一条以 `0 == 1` 失败；
全量 `4380 passed / 0 failed / 1 skipped`；新 EXE `c796b705…ff6e`（8,511,862 B，
清单 `5e2dfe9a…1e4e`），`INSTALL_RESULT = PASS`，16:26 起三个模块各一轮、零 ERROR。

## 八、尚未验证 / 未完成

1. **`main` 晋升**：Owner 2026-11-23 明确"暂不晋升"。`main` 保持 V1.6，`release/previous` 未动。
2. **一处待观察现象**：上一版在 11:22:21 之后 22 分钟没有新轮次（原定 11:37 应有一轮），
   GUI 存活、CPU 只有事件循环、无故障无停止记录。无在途写入，故直接停机重装；新构建首轮正常。
   **若在新构建上复现，需要单独排查调度线程是否被静默挂起**，本轮无证据判定原因。
3. **数据库路径**：`production.json` 的 `sqlite_path` 仍指向 `dist\INSO_V1.2\runtime\production\...`
   （历史遗留指向，经 junction 解析到同一文件）。本轮未改，属独立清理项。
4. 既有现象（非本次引入）：`inq_d65be9df3c7cc40b65cbffaa` 的 `QUOTE_INPUT_WRITE_FAILED`、
   `inq_71f4a2f5ef8678223385b6e2` 的 `UPDATE_RESULT_UNCONFIRMED`，自 11-20 起每轮同签名出现。
