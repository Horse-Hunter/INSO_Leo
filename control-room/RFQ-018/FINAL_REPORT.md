# RFQ-018 — Executor final report

**RFQ 状态：`REVIEW_REQUIRED / OFFLINE_REPAIR_DONE / NOT_DEPLOYED / NOT_MERGED`。**

## 正在实现什么

在 Owner 授权的离线范围内，修复两类共享页面安全缺口，并把 RFQ-017 的 26 项历史失败测试按原始安全意图接回当前架构。

## 理想变化是什么

- 一个 Google 文档发生过未确认写入后，其他客户端/其他服务不能再对同一文档发起写入；未知结果不能被绕过。
- 订单邮件和销售录单在页面安全准入未提供、已失效或未绑定时，必须在取得浏览器/新建页面前停止。
- 原有 26 项测试全部保留且通过；不靠删除、skip 或排除来制造全绿。

## 以前是什么

- Google 报价/浏览器/API 写入各自使用局部页面状态；关闭后新客户端可以打开同文档新页面，缺少共享 hold。
- 订单邮件调用销售录单时没有传统一 `page_admission`；销售前置入口可以在未证明准入时取得 CDP。
- RFQ-017 的 26 项固定失败中，20 项引用未实现的 barrier API 或旧文档 barrier 语义，5 项是确认的真实缺口。

## 现在是什么

两个安全契约均已实现，且优先复用现有 `PageResourceAdmission`，没有新增数据库、调度器、文件 hold 或第二套浏览器：

1. **共享 Google 文档写入 hold**
   - 一个 root admission 持有按文档的 hold，child/父级互相可见；
   - 写者在创建页面或写单元格前被阻断；读和其他文档不受影响；
   - 未确认点击/结果/结算、受保护页面、浏览器 fallback 脏写、API 未确认写都会落 hold；
   - 只有精确的页面关闭/已证实结算才释放该 owner 的 hold；owner 被接管或身份不明时不释放；
   - hold 是进程内状态，重启清除页面层 hold；既有持久 V13 hold 仍独立有效。

2. **订单邮件/销售录单统一准入**
   - `run_sales_header_check` 强制要求 `PageResourceAdmission`；
   - 未提供/失效准入在 `acquire_cdp_browser` 之前返回 `STOPPED`；
   - 有效准入在建页前绑定到同一浏览器；backend 显式传 `self._page_admission`；
   - 销售 intent 的 Google 写路径继承同一 admission。

## 做完了什么

- 新增 16 项离线负向回归：admission 单元 6、quote/sales/backend 7、API 2、浏览器 fallback 1。
- 先红后绿：wiring 前 **10 failed / 6 passed**；实现后 16/16 通过。
- RFQ-017 的 **26 个原始 nodeid 全部保留并通过**：
  - **6 项未改**：owner adoption、未确认写 protected/script、busy-close、order-mail、sales-no-admission；代码修复后直接通过。
  - **20 项改写**：逐项把原安全意图映射到 `PageResourceAdmission` 文档 hold、retained identity、持久 V13 hold、sales admission；没有删除、skip 或静默排除。
  - 完整映射见 [TEST_MAPPING.md](TEST_MAPPING.md)。
- 运行相关测试 426 passed；全量 `tests` 4176 collected / **4175 passed / 1 skipped / 0 failed / 320.88s**。唯一 skip 是既有 Windows symlink 权限限制。
- `ruff check src tests` 与 `git diff --check` 通过（提交前）。
- 未改生产配置、未部署、未重启、未合并、未操作真实 Chrome/Google/INSO/SMTP/SQLite；221、SHAHAB/115、3 条 V13 hold 未变。

## 测试结果

- **新负向回归：** 10 项先失败，修复后 16 项全部通过。
- **RFQ-017 原始 26 项：** 26/26 通过，0.72 秒。
- **相关文件：** 426 passed，0 failed。
- **全量离线：** 4175 passed / 1 skipped / 0 failed，320.88 秒；无 deselect、无隐藏失败。
- **真实环境验证：** 没有做。所有验证是离线 fake/synthetic；未在运行中的 EXE 上执行，未连接真实 Google/INSO/SMTP/Chrome，未修改生产 SQLite。真实部署/试运行仍为 `NOT_VERIFIED`。

## 你接下来需要做什么

Review RFQ-018

（CEO 复核后，再决定是否部署/试运行/合并；本任务不自动连锁。残余限制：共享文档 hold 为进程内、重启后页面层解除但持久 V13 hold 仍在；API transport 的跨服务保护依赖生产 builder 注入同一 admission，直接测试构造使用私有 admission，不作为生产路径。）
