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

---

# B1 Re-review — 2026-10-10

**Status:** COMPLETE  
**Verdict:** PASS / REVIEWED_DONE  
**Reviewed HEAD:** `dcb8a6266e0dc1b63d804e86aeb27a3fa75ca534`  
**Reviewed repaired Phase 1 commit:** `59d7d034589378df2168c1e0ad1ba0b2ff1ce45f`  
**Reviewed V1.3 base:** `fd7ce8665c65de3f0d1c18cf85369e8eff0a273c`

## B1 resolution

PASS.

The repaired Phase 1 commit is now directly based on the required V1.3 REVIEWED_DONE HEAD:

`59d7d034... -> fd7ce866...`

The branch therefore inherits the complete reviewed V1.3 increment set instead of the obsolete `df64762...` baseline.

Independent range review from `fd7ce866...` to the resubmitted HEAD shows that production source changes are limited to the intended Phase 1 surface:

- `src/gui/app.py`
- `src/gui/contracts.py`
- `src/launcher/backend.py`
- new `src/order_mail/`

plus Phase 1 tests/docs/control-room records.

No other V1.3 source or test file is replaced or reverted by the V1.4 increment.

## Phase 1 re-review

PASS.

### GUI

The existing login action row is split into equal weighted columns:

- left: `一键登录所有网站`
- right: `自动订单录单`

The new action is one-shot only. It does not start the V1.2/V1.3 business loop and does not add the future 15-minute V1.4 scheduler yet.

The mail check runs on its own worker thread; GUI presentation remains on the Tk main-thread polling path. Shutdown waits for the mail worker before final close.

### IMAP / credential boundary

PASS.

The receiver:

- uses `imap.qq.com:993` over TLS;
- reads credentials only through the Core Credential Provider using `site_id=imap.qq.com`;
- requires the configured username to be exactly `linan229@qq.com`;
- does not embed an authorization code in source/config/report/logging.

Existing `smtp.qq.com` sending behavior is untouched.

### Read-only mailbox boundary

PASS.

The implementation:

- opens `INBOX` with `readonly=True`;
- verifies the client reports the mailbox as read-only before searching;
- uses UID SEARCH/FETCH only;
- uses `BODY.PEEK[...]` / `BODY.PEEK[]`;
- records candidate FLAGS before content reads and compares them after;
- has no STORE/COPY/MOVE/EXPUNGE/SMTP/reply path;
- does not issue CLOSE before logout.

If read-only mode is not confirmed, it fails closed before search.

A FLAGS difference is surfaced as `FLAGS_DIFFER`; it is not silently treated as success.

### Bounded discovery / data minimization

PASS.

The inspection is intentionally bounded:

- INBOX only;
- last 30 days;
- tail window of at most 200 messages;
- at most the newest 5 candidates;
- subject must begin with exact `订单录单` before full-body inspection;
- 20 MB message cap;
- bounded attachment and Excel inspection limits.

No mailbox-wide export or persistent mail cache is introduced.

### Attachment inspection / privacy

PASS.

Excel/PDF payloads are inspected in memory only.

The public report boundary exports only sanitized structure information. Excel reporting exposes coordinates, cell type, standard label vocabulary, formulas/merge/hidden counts and dimensions, not customer cell values. PDF inspection exposes signature/page/encryption and fixed contract-structure vocabulary signals, not document text.

The implementation does not write the real attachments to production runtime, workflow DB or Git.

The two live samples remain historical evidence from the original Phase 1 probe; the B1 repair correctly did not re-read production mail merely to prove a rebase.

### Business isolation

PASS.

Phase 1 does not:

- enter INSO sales-order pages;
- operate purchase or quotation flows;
- write Google Sheets;
- write the production workflow database;
- upload contract PDFs;
- save/submit sales orders;
- send SMTP mail.

The new receiver has no workflow-state dependency in this phase.

## Regression evidence

Executor reports after the repaired baseline migration:

- focused: **534 passed**;
- full safe/offline: **1681 passed / 1 skipped**;
- Ruff: **PASS**;
- diff check: **PASS**;
- no deployment.

The branch history and range diff independently confirm that the previously reviewed V1.3 source/test set is retained and the repaired V1.4 increment is additive over `fd7ce866...`.

## Remaining Phase 2 decisions

Correctly still UNKNOWN / Owner-defined:

- authoritative contract-number source and conflict rule;
- BUYER/customer mapping into INSO;
- multiple-line-item handling;
- L/T / CONDITION / DC mappings;
- currency/tax/price/rounding rules;
- duplicate/re-send/revision semantics;
- missing/multiple attachment handling.

None of those were guessed in Phase 1.

## Release decision

**RFQ-009 Phase 1 is approved as REVIEWED_DONE.**

This approval is for the V1.4 Phase 1 development baseline and discovery implementation. It does not authorize production V1.4 deployment and does not authorize Phase 2 business mapping or INSO sales-order automation without a new Owner-defined task.

## Final state

`CHANGES_REQUESTED -> REVIEW_REQUIRED -> REVIEWED_DONE`
