# RFQ-017 — CEO 独立 Review（2026-11-14）

**Review 结论：`PASS_AUDIT_SCOPE / RELEASE_HOLD / NOT_DEPLOYED / NO_TEST_RETIREMENT_AUTHORIZED`.** 本结论只**接受 26 项失败的只读审计工作及其可复核的初步归因**。CEO **不采纳** Executor 报告中“21 项已确定无需保护”“整体 MEDIUM 因而不阻断受控真实试运行”的放行推论。任何生产现场部署、外部效果、源码合入或正式版晋升，仍无授权。

独立审核对象：原 Executor 分支 `workbuddy/v16-rfq016-stabilization` 的审计提交 `f790d5ad60b03205727e38823bd25b50b279306d`、nodeid 正规化提交 `38e482f965b9768567b42b3bbd8df5bdffa054f4`；[审计报告](AUDIT_REPORT.md)、[执行记录](EXECUTION_LOG.md)、[机器可读证据](../../docs/evidence/rfq017/rfq017-test-audit-2026-11-14.json)。通过 GitHub **实际读取**材料及部分关键生产源码/测试，查看 [`d244241e`](https://github.com/Horse-Hunter/INSO_Leo/commit/d244241eafe564c79812f860b2491c903a4cee1e) 的提交信息与测试文件列表，核对当前分支相对 RFQ-016 最终 Review **仅新增本 RFQ 文档/JSON，未改 src/tests**。CEO **没有**亲自运行 Windows pytest、访问实时 EXE/Google/INSO/SMTP 或更改生产数据。Git 历史中每个测试的 `git blame` 归属、全部 Git 分支 `-S` 输出和 26 个完整 pytest traceback 是 Executor 报告的检查结果，不冒充 CEO 独立复现。

## 可接受的已证明/已提交证据

1. 提交了 26/26 的 `nodeid`、逐项分类、报告、任务说明、执行记录、对照 JSON；`nodeid` 已归一为 RFQ-016 原有的 dotted 形式。本次测试范围是 Executor 报告的 **26 failed in 4.76s**，与排除 26 项后的全树 **4133 passed / 1 skipped / 26 deselected / 0 failed in 332.76s**；该对照**并不意味着原始全量测试全绿**。测试数量 4160=4133+1+26。
2. 报告的失败类型为 7 `ImportError`、1 `ModuleNotFoundError`、3 `AttributeError`、15 行为断言；此前 26 项并非随机环境抖动的说法有明确测试证据，故**暂接受“环境故障 0”作为本次离线测试范围的观察**。
3. `d244241e` 确实将涉事 tests/launcher 多个文件连同源代码快照一并提交，并在提交信息中明确承认 **tests 与当时已安装 EXE 的构建源码对应性未证明**。缺失符号 `_document_barrier`、`_GoogleDocumentBarrier`、`google_resource_barrier`、`google_resource_holds` 等确实未出现在本次审查的生产源码接口中。**这支持共同根因的诊断方向，但不能单凭“API 从未存在”判定安全合同已作废。**
4. 关键缺口直接得到代码印证：
   - `src/launcher/google_quote_update.py:479-530,969-1015`：防护大量基于当前 action 实例、当前页面、刷新标志和 `_ACTIVE_QUOTE_TARGETS`；跨客户端单一 Google 文档的全局、持久隔离未由此保证。执行者报告第 13/14/15 项对应未确认脚本/受保护页面关闭后，另一写者仍可开新页面。
   - `src/launcher/backend.py:4131-4142`：`_order_mail_worker` 未将 `self._page_admission` 显式传给 `run_sales_header_check`；`src/launcher/sales_header.py:98-131` 没有该参数，进入 `acquire_cdp_browser` 前也没有强制统一 `require_open`。虽 `src/research/cdp_pages.py:378-404` 会在 **browser 已绑定同一准入对象时** 检查，但该入口没有证明每次已绑定或故障时 fail-closed。这与第 21/26 项的失败相符。
   - 因此 **5 项不是“只因测试旧了而失败”**：按已提交测试/源码，这里至少存在两类明确的保护范围缺口：**跨客户端 Google 写入隔离**、**销售/订单邮件页面准入传播**。尚未复现真实重复采购/报价/邮件，既不能声称事故已发生，也不能据此批准真实效果测试。

## CEO 对原分类/风险判断的限定

| Executor 类别 | 本次审核处理 | 安全含义 |
| --- | --- | --- |
| 11 项“引用不存在 API” | **接受机械失败原因；不批准视为安全要求不存在或无风险** | 测试引用失效与该测试守护的行为是否仍必需是不同问题。要求将缺失 API 对应的业务安全意图映射到当前保护措施，才能合理重写或淘汰测试 |
| 10 项“旧 document barrier 语义” | **接受现有测试与实现契约不一致；替代保护等价性 `NOT_VERIFIED`** | “允许隔离恢复”“API 主读写”不能自动证明跨窗口、fallback、写入未知时拥有等价的 fail-closed 保障 |
| 5 项真实防御纵深缺口 | **确认需单独治理；未接受不阻断真实业务试运行的主张** | 当前证据没有构建实际持久隔离/销售准入的等价保护链，不能仅凭“没有已发生事故”降低发布风险 |
| 0 项环境问题 | **就提交的离线假环境复现而言接受** | 不能外推为 Windows/网络/受保护 Chrome 真实运行环境已验收 |

**发布门槛裁决：`RELEASE_HOLD`。** 不允许依据本审计直接打包覆盖运行中 EXE、启用真实自动采购/报价/Google 写入/销售录单或宣称全量回归绿。允许继续 **无外部效果的离线测试、模拟 UI 演示、只读取证**。如 Owner 未来考虑有真实外部效果的受控试运行，至少需先完成缺口治理、可验证的跨路径防护测试、完整发布包追溯与专项授权；具体门槛另行 Review。风险级别暂定为 **`NOT_VERIFIED_FOR_RELEASE`**，不采纳自动 `MEDIUM → 可试运行` 的换算。

## 后续唯一技术任务建议（建议 RFQ-018；不自动创建或授权真实效果）

1. **先审业务安全契约，再决定代码形状。** 独立为两类缺口制定 fail-closed 要求：① 某个 Google 文档/写入处于 UNKNOWN、忙碌或受保护时，跨客户端/跨服务是否必须阻止下一写者及什么时候可以有证据解锁；② 订单邮件/销售录单在统一准入失效、未绑定或资源恢复不明时，必须在取得浏览器/新建页面前退出。避免盲目复制一个遗弃的 `_GoogleDocumentBarrier` 实现。
2. 为实际行为写**离线负向回归**，覆盖同文档未确认写、跨 sheet 异常 busy、关闭后的新客户端、无准入/失效准入的销售预检及 order-mail 传播。以最小单一防护机制修复缺口，**不可删除/skip 26 项以做“假全绿”**。
3. 对其余 21 项逐一建立 **原测试意图 → 现有机制 → 等价负向测试/明确不再支持的经过批准的理由** 表，再由 CEO Review 是否替换其接口，不得仅以 ImportError 作为 retired 理由。原 26 nodeid 在此之前保持可追溯、不得降级成静默排除。
4. 在任何打包试运行前，验证候选固定 Git SHA ↔ 构建/EXE SHA ↔ 运行配置 ↔ 回滚资产；复核不属于本 RFQ 的 SHAHAB/115 UNKNOWN、3 条历史 V13 报价 hold、221 行原有成功 receipt 和进程/Chrome/SQLite-WAL-SHM 保护，另行申请 Owner 的严格范围授权。

## 当前业务/分支隔离

RFQ-016 的 P0/P1 源码安全专项 Review 仍为 **`PASS_SOURCE_SAFETY_SCOPE`**；RFQ-017 不改其已接受结果。最近 Executor 只读现场报告旧 EXE `E9E3DA33…` app PID38948/watcher34304，Chrome9222 owner24164；这不是 CEO 实时核对。221 行原采购 `rec_440fafd372440ecf9dacabf660dd155d` 不重放。SHAHAB/115 的采购结果 `MANUAL_REVIEW/RECONCILIATION_UNREADABLE`、原生 INSO `NOT_VERIFIED`；3 条 V13 hold 不清、不改单、不重发。源码仍在原 `workbuddy/v16-rfq016-stabilization`；`develop` 只同步管理文档/证据；`main` 是历史 V1.1，`release/previous` 是未完成验收的回退候选。无任何代码合并、EXE 部署或版本晋升授权。

**结论解释：RFQ-017 的“只读审计任务”`PASS`；其“非阻断真实试运行建议”`NOT_APPROVED`；发布依然 `HOLD`。** [任务说明](TASK_SPEC.md) · [原 Executor 审计报告](AUDIT_REPORT.md) · [机器可读证据](../../docs/evidence/rfq017/rfq017-test-audit-2026-11-14.json)。
