# RFQ-009 CEO Independent Review

Date: 2026-10-10  
Status: CHANGES_REQUESTED  
Reviewed branch: `codex/v1-4-order-mail-inspection`  
Reviewed HEAD: `04e1f4012084f8905f321e562090f9a2332f46ef`

## Verdict

**CHANGES_REQUESTED**

Phase 1 的功能实现本身方向正确：GUI 一次性检查入口、229 IMAP 只读边界、Vault 凭据、PEEK/FLAGS 核验、内存附件结构检查和脱敏输出均未发现新的业务安全 blocker。

但当前分支建立在过期的 V1.3 基线上，不能标记 REVIEWED_DONE，也不能作为后续 V1.4 开发/打包基线。

## B1 — V1.4 branch is based on stale reviewed V1.3

`04e1f401...` 的直接 parent 是：

`df64762ae6ad0893879814e847888246f5b5a93f`

当前 V1.3 已审核协调 HEAD 是：

`fd7ce8665c65de3f0d1c18cf85369e8eff0a273c`

从 `df64762...` 到 `fd7ce...` 还有 **18 个已审核提交**。

这些提交不是纯文档变化，包含当前生产已经依赖的关键修复，例如：

- Chrome 后台 target / 人工验证页保护；
- 采购状态写回对 `采购已报价` 的安全兼容；
- Research / 采购历史 / 报价候选统一型号比较；
- 报价输入 B 保留源型号、L 记录实际报价型号；
- 型号差异 durable notification；
- INSO 三个入口使用原表完整型号搜索，仅结果比较时规范化；
- 对应 purchase / quotation / Research / browser 安全回归。

当前 V1.4 分支没有这些代码。虽然 Phase 1 未部署，因此没有造成生产回退，但如果继续在该分支开发并最终打包 V1.4，会把已经审核通过的 V1.3 安全修复带回旧版本。

因此这是 release-blocking baseline defect。

## Required repair

不要重写 Phase 1。

只需要把 V1.4 Phase 1 增量移到当前已审核 V1.3 基线上：

`fd7ce8665c65de3f0d1c18cf85369e8eff0a273c`

推荐：

1. 从 `fd7ce866...` 建立/重置 V1.4 分支；
2. 将 `04e1f401...` 的 V1.4 Phase 1 功能安全地 cherry-pick / rebase 过去；
3. 手工解决 `src/gui/app.py`、`src/launcher/backend.py` 等与后续 V1.3 修复的冲突，禁止用旧文件整体覆盖新文件；
4. 保留当前 IMAP Phase 1 语义不变；
5. 跑 Phase 1 focused + 当前完整 safe/offline regression；
6. 确认 V1.3 已审核关键回归仍 PASS；
7. 不部署 V1.4；
8. 提交新的 REVIEW_REQUIRED HEAD 给 CEO。

## Phase 1 implementation observations

除基线问题外，本轮独立检查未发现需要重做的功能 blocker：

- IMAP 使用 `imap.qq.com:993` + TLS；
- 凭据从 Core Credential Provider 的 `imap.qq.com` site_id 读取；
- 精确限制账户为 `linan229@qq.com`；
- `INBOX` 以 readonly 模式打开，并检查 `client.is_readonly`；
- 邮件正文使用 `BODY.PEEK[]`，头部也使用 PEEK；
- 候选读取前后比较 FLAGS；
- 没有 STORE / COPY / MOVE / EXPUNGE / SMTP / reply 路径；
- logout 前不调用 CLOSE；
- 最近30天、末尾最多200封范围、最近最多5个候选，读取范围有界；
- 真实附件只在内存解析，没有写 production DB / runtime state / Git；
- Excel 只输出坐标、类型、标准字段词汇和结构，不输出原始客户值；
- PDF 只提取固定词汇结构信号，不输出合同正文；
- GUI 是一次性手动检查，没有提前实现15分钟轮询或 INSO 录单；
- 后台 worker 与 shutdown join 有测试覆盖；
- Phase 1 报告保持了合同号规则和业务字段映射 UNKNOWN，没有自行猜规则。

这些设计可以保留。

## Final state

`REVIEW_REQUIRED -> CHANGES_REQUESTED`

修复重点只有一个：**把已经完成的 V1.4 Phase 1 增量重新落到当前 V1.3 REVIEWED_DONE HEAD 上，不能继续从 df64762 开发。**
