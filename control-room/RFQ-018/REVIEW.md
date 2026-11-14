# RFQ-018 — CEO 第二轮独立 Review（2026-11-14）

**结论：`PASS_SOURCE_SAFETY_SCOPE / RELEASE_HOLD / NOT_DEPLOYED / NOT_MERGED`。** RFQ-018 指定安全修复的**源码/离线测试证据审核通过**，但**不是生产 EXE 验收、自动部署或现版晋升授权**。

本轮独立审核对象：原 Executor 分支 `workbuddy/v16-rfq016-stabilization` 固定源码提交 [`25894eface6ea622153d1573c19d0ca6b9ad72aa`](https://github.com/Horse-Hunter/INSO_Leo/commit/25894eface6ea622153d1573c19d0ca6b9ad72aa)，前轮 CEO Review [`67f2a283`](https://github.com/Horse-Hunter/INSO_Leo/blob/67f2a283fb5db1254361c12cbed420e192b8a634/control-room/RFQ-018/REVIEW.md)。CEO 使用连接的 GitHub **实际审读**改动、关键完整源码、测试函数、[Executor 执行记录](EXECUTION_LOG.md)、[最终报告](FINAL_REPORT.md)、[机器可读证据](../../docs/evidence/rfq018/rfq018-test-audit-2026-11-14.json)。**未在 Windows 亲自运行 pytest、操作真实 Chrome/Google/INSO/SMTP，也未实机核对旧 EXE 进程。**

## 结论依据：三项补修全部接受

### P0-A — 未确认写入 hold 不因页面关闭而消失：**PASS**

- `src/research/cdp_pages.py:228-242` 的 `document_hold()` 已删除以 `page.is_closed()` 为条件自动 `pop(owner)` 的代码；保留的 hold 仅走指定 `release_document(document, owner)`。
- `src/launcher/google_quote_update.py` 原 click/result/受保护页面未确认路径仍发布 shared hold；恢复流程要求已观测结算并经过 owner 核查后才走 release。原有 owner-adoption/来源不明拦截仍保留。
- 新增完整页面已关闭却继续阻断 root/child、同文档跨 sheet 的回归（`tests/research/test_shared_document_admission.py::test_unconfirmed_write_hold_survives_the_held_page_closing`、`tests/launcher/test_rfq018_shared_safety.py`）。页面关闭不再等同于业务写入结算证据。
- **剩余已知边界**：`allow_closed=True` 的成功结算+关闭路径属于专用 owner 恢复；真实浏览器中并发人工作业/归属变化未实测。不得把离线 PASS 写作外部系统行为已证明。

### P0-B — Sheets API 真实写入必须共享/有效 admission：**PASS**

- `src/sheets/google_api_service.py:211-219,359-403` 不再自动给缺失 admission 的可写客户端创建私有 root；实际 `_write_range()` 在 API 请求前检查非空共享 admission、`require_open()` 以及文档保护和新 atomic write lease。
- `src/launcher/backend.py:_google_api_service` 注入 `self._page_admission`。新增/更新 `tests/sheets/test_google_api_service.py` 的无 admission、失效 admission negative，明确断言 `FakeApi.calls == []`，同 root hold 可阻断写入。
- 直接构造的只读/假客户端不因此自动取得生产写入许可；其他非标准生产构造路径必须在真实发布评估中重新核实，不可自动宣称都已实机覆盖。

### P1-C — 同文档原子在途写入互斥：**PASS**

- `src/research/cdp_pages.py:184-227` 新增 root-admission 原子 `begin_document_write/end_document_write`，同 owner 有界重入，其他 owner 在同文档在途时得到 `DocumentWriteBusy`；busy 不被伪装为 UNKNOWN。
- `src/sheets/google_api_service.py` 覆盖整个 API request/response receipt 确认期；`src/launcher/google_web.py` 覆盖 fallback 写入期；`src/launcher/google_quote_update.py` 在 native 报价 click dispatch 前取得 lease，结算或关闭时释放。未确认写在释放 lease 之前先发布 shared hold。
- 旧 `tests/launcher/test_google_quote_update.py::test_document_write_admission_serializes_threads_but_allows_same_owner_nesting` 已恢复成真正的双线程 `Event` 竞争；`tests/research/test_shared_document_admission.py`、`tests/sheets/test_google_api_service.py`、`tests/launcher/test_google_web.py` 有竞争 writer / in-flight HTTP fake 负向测试，第二个请求在第一请求完成之前未发送；其他文档不被误阻断。
- 原 21 项测试接口/语义治理记录保留在 [TEST_MAPPING](TEST_MAPPING.md)；纯只读失败可有界隔离，**未确认写入必须先 hold** 的两类处理不可混淆。原 26 nodeid 仍逐一可追溯。

## 测试证据、适用边界

| 对象 | Executor 报告、CEO 核对 |
| --- | --- |
| 原 RFQ-017 26 项 nodeid | **26/26 PASS**，原列表全部保留（6 原样、20 依据当前机制改写） |
| 本 RFQ 新增保护性测试 | 合计 **28 项**（首轮16 + 本轮12），报告全部通过 |
| 相关测试 | **478 PASS / 0 FAIL** |
| 全树 `python -m pytest tests -q --tb=short -p no:cacheprovider` | **4188 collected、4187 passed、1 skipped、0 failed，341.54 秒**；没有 deselect；既有 Windows symlink 权限 1 SKIP |
| 风险限制 | **仅离线 fake/synthetic**；没有执行真实 Google、原生 INSO、SMTP 或已安装 EXE 的完整回归 |

CEO 静态审核确认 `25894efa` 相对上一轮仅改指定安全路径、保护性测试及本 RFQ 文档/JSON；**无需继续针对 P0-A/P0-B/P1-C 追加 RFQ-018 补丁**。未来新证据可另作有界缺陷任务，不能拿本轮 PASS 作零风险保证。

## 独立生产发布闸门仍 HOLD

1. **进程内共享 hold 有边界。** 新文档 hold 与在途 lease 不持久化，重启可解除页面层保护；已存在的 per-order 持久 V13 hold 保留但不等于所有跨服务 Google 写入 UNKNOWN 的持久阻断。发布前必须制定 **断电/重启/中断 UNKNOWN 清单与隔离恢复方案**，不能以重启清内存 hold 为“已经结算”的证明。
2. **真实部署与版本追溯尚未完成。** 当前 Executor 分支上的 `25894efa` 源码尚未合并 `develop`，未打包/安装对应候选 EXE，缺少源码 SHA→构建文件 SHA→配置→回滚包→实际启动的证据。最近 Executor 只读快照旧 EXE `E9E3DA33…` app PID38948/watcher34304，Chrome 9222 PID24164；不是本次 CEO 实时观察。任何停止/覆盖旧 EXE 需 Owner 单独批准及安全运行窗口。
3. **旧业务 UNKNOWN 不因测试全绿消失。** Google/INSO SHAHAB 第 115 行 `inq_99275e8e72b43fd6616fd686` purchase `MANUAL_REVIEW / RECONCILIATION_UNREADABLE`、无 `saved_record_ref`，原生 INSO 收据 `NOT_VERIFIED`，旧版曾清告警；不可重放或冒称已采购。221 行 SAVED 原生 `rec_440fafd372440ecf9dacabf660dd155d` 不得重复下单。3 条 V13 报价 hold 保留。
4. **旧 GUI 及操作稳定性**：报价重试拒绝原因、`inq_d65be9df…` 持续失败、GUI 停刷、退出挂起、Chrome 残留页面等仍是独立验收风险。未获真实试运行/生产发布授权，`main` 仍历史 V1.1、`release/previous` 不动。

## 下一步：发布准备评估，而不是继续无限修 RFQ-018

进入**单独发布准备与恢复策略评估**（建议 `RFQ-019`，先只读/离线）：锁定固定源码 SHA、隔离重启未知效果的恢复要求、真实 EXE/配置/运行中进程/Chrome/SQLite/WAL-SHM 的切换和回滚计划、非业务效果的候选构建验证及 GUI 已知问题风险评估。提出清晰的 Owner 授权清单后才允许集成 `develop`、部署试运行或恢复真实外部写入，**不自动连锁批准**。

**最终裁决：`PASS_SOURCE_SAFETY_SCOPE / RELEASE_HOLD / NO_AUTOMATIC_DEPLOYMENT / OWNER_APPROVAL_REQUIRED`.**
