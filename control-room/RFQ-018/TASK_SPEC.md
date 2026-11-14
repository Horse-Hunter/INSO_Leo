# RFQ-018 — 共享页面安全保护修复与测试基线治理（2026-11-14）

**状态：`REVIEW_REQUIRED / OFFLINE_REPAIR_DONE / NOT_DEPLOYED / NOT_MERGED`。**

## Owner 目标

在 RFQ-017 只读审计和 CEO `PASS_AUDIT_SCOPE / RELEASE_HOLD` 之后，完成下一阶段的**离线**源码与测试修复：

1. 修复 Google 页面发生**未确认写入**后，跨客户端、跨服务的共享安全保护缺口，确保未知结果不能被其他写入操作绕过。
2. 修复订单邮件与销售录单模块没有完整继承统一页面准入保护的问题；安全准入失效、未绑定或资源恢复不明时，必须在取得浏览器/新建页面前退出。
3. 对 RFQ-017 剩余 21 项测试逐项核对原始安全意图，用当前架构下**等价或更严格**的保护测试承接；不得仅因接口不存在就删除、跳过或降低安全断言。
4. 优先复用现有安全机制，避免增加第二套状态管理体系；先写失败回归，再做最小修复。
5. 执行相关及全量离线测试，保留原始失败项与新结果的对应关系，报告真实失败数量，不为全绿隐藏测试。

本任务**不授权**部署、覆盖或停止当前 V1.6 EXE、操作受保护 Chrome 9222、修改生产 SQLite、清除 UNKNOWN/hold、重放 221 行采购、操作 SHAHAB/115、真实 Google 写入、INSO 采购/报价、SMTP、合并 `develop` 或晋升 `main`。

## 当前固定对象

- 工作树：`D:\Program_Leo\INSO_Leo\.worktrees\v16-rfq016-stabilization`（复用，不新建）。
- 分支：`workbuddy/v16-rfq016-stabilization`。
- 审计起点：`aad3b122`（CEO RFQ-017 Review 已 fast-forward 入本地分支；只含管理文档）。
- 业务源码基线：`b45e870e`（RFQ-016 最终 P1-E），加上 RFQ-018 本轮修改。
- 现场：EXE `E9E3DA33…`，app PID 38948 / watcher 34304；Chrome 9222 owner 24164；SQLite `dist/INSO_V1.2/runtime/production/workflow.sqlite3`。
- 真实业务保护：221 行 `rec_440fafd372440ecf9dacabf660dd155d` 不重放；SHAHAB/115 `MANUAL_REVIEW / RECONCILIATION_UNREADABLE` 保持 UNKNOWN；3 条 V13 hold 不清。

## 安全契约 A — 共享 Google 文档写入隔离

**要求（fail-closed）：**

1. 任一 Google 文档的写入处于 `UNKNOWN`、脚本/点击未结算、页面受保护或所有权不明时，该文档进入共享 hold。
2. hold 必须由**同一个共享 `PageResourceAdmission` 根对象**承载，子 admission 继承父 hold；跨客户端、跨服务、跨 sheet 的下一写者必须在**创建页面或写入任何单元格之前**被阻断。
3. 读取可以继续；其他文档的写入不应被无差别冻结。
4. hold 不自动清除。进程重启/新 runtime 是内存层解除边界；同一报价单的持久 V13 hold 仍独立有效，不得因页面层重启被绕过。
5. 覆盖路径：CDP 报价按钮/脚本、浏览器的 `GoogleSheetsWebService` fallback 写、Sheets API 写。任何路径不得以“没有共享 admission”为由默认可写；生产路径必须传入同一 admission。
6. 不新增第二个数据库、调度器或独立 hold 文件；复用现有 `PageResourceAdmission` 和现有持久 V13 hold。
7. 同一文档在途写入必须有原子 lease：同 owner 可重入，竞争 writer 在 API/页面 dispatch 前得到 busy（不是 UNKNOWN）；只有结算/关闭证据路径释放 lease，UNKNOWN 在释放 lease 前落 hold。

**验收负向测试：**

- 未确认报价写入后，关闭原 action，新客户端/新 scope 对同文档写入必须 `QuotationInputBusy`/`V12Fault`（不创建新可写页）。
- 未确认写入后，另一个 sheet（同文档）的写者也必须被阻断。
- 子 admission 的 hold 对父 admission 可见；父 hold 对子可见。
- hold 后只读操作仍可执行；其他文档写入不被误伤。
- API 写与浏览器 fallback 写都检查同一文档 hold。

## 安全契约 B — 订单邮件/销售录单完整继承页面准入

**要求（fail-closed）：**

1. `run_sales_header_check(...)` 必须接收共享 `page_admission`；未提供、类型不符或 `require_open()` 失败时，**在 `acquire_cdp_browser` 之前**返回 `STOPPED`，不创建页面、不读取邮箱、不执行录单。
2. 通过后，必须把同一 admission 绑定到本次浏览器句柄，再创建后台页；`new_background_page` 的现有 `require_open()` 必须生效。
3. `ProductionBackend._order_mail_worker` 必须显式传入 `self._page_admission`。
4. 订单邮件内部后续的 Google intent/写入（`sales_intent` → `build_google_web_service`）必须继承同一 admission，不得新开第二个 root。
5. 失败信息只使用业务语言，不泄露账号、页面或客户数据。

**验收负向测试：**

- 无 admission：`run_sales_header_check` 返回 `STOPPED`，`acquire_cdp_browser` 不被调用。
- admission 已 `invalidate`：同样在取得浏览器前 `STOPPED`。
- 正常 admission：`new_background_page` 观察到 `browser._inso_page_admission is admission`。
- backend 的 order-mail worker 调用参数中 `page_admission is self._page_admission`。
- 失效 admission 下，sales intent/Google 写路径也不得创建页面或写入。

## 测试基线治理规则

- RFQ-017 的 26 个原始 nodeid 全部保留在映射表中，不得静默删除/跳过。
- 5 个确认缺口：新增负向回归；原失败项转为通过或由更严格测试承接。
- 11 个“引用不存在 API”：逐个把原安全意图映射到当前机制，改写为当前 `PageResourceAdmission` / retained identity / durable V13 hold 的等价测试；不得用 ImportError 作为 retired 理由。
- 10 个“旧 document barrier 语义”：逐个核对；能由新共享 hold 满足的保留并收紧；不能的改为当前架构下更精确的负向断言（例如“允许一次隔离恢复，但下一次写者必须被阻断”），并说明不是降低安全要求。
- 最终全量测试真实统计；任何失败如实报告，不以 deselect 冒充全绿。唯一的既有 Windows symlink skip 保留。

## 必须遵守的现场/分支约束

- 复用现有工作树与分支；不覆盖未提交内容；不新建第二工作树或第二 Chrome/profile。
- 不停止/覆盖 EXE，不操作 Chrome 9222，不写生产 SQLite/WAL/SHM，不清 hold/UNKNOWN。
- 不访问真实 Google/INSO/SMTP；所有验证用 fake/synthetic。
- 不合并 `develop`、不晋升 `main`/`release/previous`；不删除测试。
- 提交前检查 `git diff`、`git status`、`ruff`、`git diff --check`；提交并推送原 Executor 分支。

## 完成标准

- 两个安全契约有失败→通过的可复核负向回归。
- 21 项测试有“原意图 → 当前机制 → 新测试”完整映射；没有静默删除/skip/弱化。
- 相关测试与全量离线测试完成；真实失败数、跳过数、nodeid 变化全部记录。
- RFQ-018 `TASK_SPEC`、`EXECUTION_LOG`、`FINAL_REPORT`、机器可读测试证据、接管记录齐全。
- 现场/真实业务零外部效果；221、SHAHAB/115、3 条 hold 未变。

## 证据与下一步

- 执行记录：[EXECUTION_LOG.md](EXECUTION_LOG.md)
- 测试意图映射：[TEST_MAPPING.md](TEST_MAPPING.md)
- 机器可读证据：[`docs/evidence/rfq018/rfq018-test-audit-2026-11-14.json`](../../docs/evidence/rfq018/rfq018-test-audit-2026-11-14.json)
- 交付报告：[FINAL_REPORT.md](FINAL_REPORT.md)
- 下一步：CEO 独立复核；是否部署/试运行/合并均需另行授权。

## 完成结果（2026-11-14，含 CEO 第一轮 Review 补修）

- 两个安全契约均已实现：共享 Google 文档 hold（root/child 继承、写前阻断、页面关闭不是结算证据）与订单邮件/销售录单统一 admission（无/失效准入在取浏览器前 STOPPED）。
- CEO Review 的 P0-A/P0-B/P1-C 已完成：页面关闭不再自动解除未确认写 hold；API 写入必须 `require_open()` + 共享 admission，缺失共享根 fail closed；同一文档带原子 in-flight 写 lease，真实两线程/在途 API/浏览器 fallback 竞争测试覆盖。
- RFQ-017 的 **26 个原始 nodeid 全部保留并通过**：6 项未改（含 5 项确认缺口 + owner adoption），20 项按原安全意图改写为当前机制。
- 新增回归共 **26 项**（RFQ-018 原 16 + CEO Review 补 10）。
- 全量离线测试：**4188 collected / 4187 passed / 0 failed / 1 skipped / 341.54s**；唯一 skip 是既有 Windows symlink 权限限制，无 deselect、无隐藏失败。
- 未部署、未重启、未合并、未操作真实 Chrome/Google/INSO/SMTP/SQLite；221、SHAHAB/115、3 条 V13 hold 未变。
