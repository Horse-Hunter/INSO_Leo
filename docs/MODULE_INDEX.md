# 模块注册表

本文件只维护模块职责与跨模块依赖边界，由 CEO/架构师维护；模块内部实现写在各自 module doc。

| module | path | responsibility |
| --- | --- | --- |
| `core` | `src/core/` | 公共基础能力、Credential Provider |
| `gui` | `src/gui/` | Dashboard / DTO 展示，不做业务计算 |
| `launcher` | `src/launcher/` | Runtime 组装、Chrome/CDP 生命周期 |
| `sheets` | `src/sheets/` | Google Sheets 读取与明确授权的安全写回 |
| `research` | `src/research/` | 只读市场调研、价格聚合、Research Excel |
| `workflow` | `src/workflow/` | Scheduler、状态、retry、跨模块编排 |
| `inso` | `src/inso/` | V1.2 重复检查与受控采购草稿能力 |
| `quotation` | `src/quotation/` | 后续报价模块，当前非主线 |

依赖原则：

```text
workflow -> core, sheets, research, inso, quotation
launcher -> gui, workflow, sheets, research, inso
gui -> core
sheets | research | inso | quotation -> core
```

规则：

- 跨模块只通过 Public Contract；不导入其他模块私有实现。
- GUI 不直接访问浏览器、Excel、Sheets 或业务模块内部实现。
- Research 不承担主动采购。
- INSO 主动采购不改写 Research 的价格/库存/MPN 规则。
- **一个稳定职责只能有一个 canonical owner / production path。**
- 新功能先扩展已有模块/Public Contract；禁止为了同一职责新增平行模块、平行 launcher、平行 adapter 或平行 runtime。
- 临时 discovery / live-verification helper 不得演变为长期第二生产路径；验证结论必须回收到 canonical module。
- 如果现有模块无法承载需求，必须先在 RFQ Execution Log 证明边界冲突，再升级 CEO 决定是否调整模块职责。
- 模块职责、依赖方向或跨模块 Public Contract 变化必须升级 CEO。

Owner 2026-10-08 授权共享 `core.mpn` 纯型号读取策略，由 Research、INSO 与 Workflow 复用；不扩展 source-row identity 或 purchase submission 匹配。模块依赖方向保持不变。

## V1.4 phase 1 (Owner instruction 2026-10-10)

`order_mail` (`src/order_mail/`, `tests/order_mail/`) owns bounded read-only IMAP
and order attachment structure inspection. Depends on Core Credential Provider
and existing openpyxl/standard library only. Optional pypdf is used if available;
otherwise PDF page count/encryption remains UNKNOWN. No storage or writes.
Launcher assembles it; GUI receives sanitized text through GuiBackend only.
No INSO/Sheets/SMTP/workflow-state dependency. This is the minimum new boundary
for the explicitly authorized receiver; existing SMTP sender remains unchanged.

## V1.4 Phase 2 (RFQ-010, Owner instruction 2026-10-10)

INSO owns unsaved sales-header native UI operations and readback in
`inso.sales_header`; no line/upload/save/submit API is introduced.
`order_mail.pi_orders` reads labelled PI No. in memory from the two confirmed
Excel attachments through the existing bounded read-only receiver. Launcher
assembles these public capabilities and reuses canonical CDP/InsoSessionGuard.
The ownership callback is injected into INSO; domain code does not depend on
Research. GUI receives sanitized status only. No Workflow/SMTP/Sheets/DB writes.
Boundary extension is submitted for CEO review with RFQ-010 REVIEW_REQUIRED.

## V1.4 Phase 3 (RFQ-011, Owner 2026-10-10)

`order_mail.contracts` owns strict selected-mail Excel detail parsing and authorized
lead-time rules; no network except the existing read-only mail boundary.
Research `icnet` adds a public first20 displayed-package parser using its existing
HTML tree/visibility basis; existing Research brand/stock/matching remain unchanged.
INSO `sales_details` owns native unsaved detail fields/row addition/readback only.
Launcher composes preflight and reuses Phase2 owned sales-tab/header lifecycle.
Workflow `order_notifications` composes existing V1.2 outbox/worker/1069 transport
in an isolated ignored development DB, old schema/enums only. Existing FK uses
a notification-only MANUAL_REVIEW anchor, no production/purchase/quotation state.
This Owner-authorized extension is submitted to CEO with RFQ-011 review.

## RFQ-012 Owner single-click receipt queue (2026-10-10)

The latest Owner rule replaces Phase2/3 development reuse for this button: every
invocation owns a new sales tab, authenticates with the canonical guard, preserves
older review tabs and releases its worker when fields verify. Launcher maximizes
the shared Chrome window before mail/business. order_mail owns bounded oldest
INBOX order-candidate metadata selection and an opaque local filled-mail receipt
ledger; email flags remain read-only. Successful full readback records processed,
failures retry, no server flag/production workflow DB state. GUI button always
returns to idle and is independent of inquiry/procurement. No Save/submit/PDF.

## RFQ-013 native order PDF (Owner 2026-10-10)

Owner extends V1.4 to native PDF attachment upload only. order_mail returns the
selected mail PDF bytes in memory and verifies unique, parseable, unencrypted
PDF using existing optional pypdf (unavailable => stop). INSO sales_attachment
owns file input/start upload/readback; launcher composes it after field checks,
before local processed receipt. No Save/review-submit/deployment is authorized.
Earlier no-PDF statements describe historical phases, superseded for this button.
Boundary extension awaits CEO independent review under RFQ-013.


## V1.6 proposed module actor Public Contract — CEO boundary decision (2026-10-27)

**Status: CONDITIONALLY APPROVED BOUNDARY ONLY / NOT IMPLEMENTED / NOT DEPLOYED.**
This records the CEO architecture decision for the existing module
responsibilities. It is NOT a permission to run concurrent business,
a new canonical scheduler, or a replacement for runtime safety review.
See `tasks/2026-10-27-v16-independent-scheduling.md` for the exact
reviewed commit, findings and blocked order-lease abort/rearm sequence.

**Trigger:** before changing a cross-module Public Contract to execute
market Research asynchronously or deploying independent market actors.

**Canonical owners and sequence:**
1. `workflow` owns one `WorkflowRuntime` bounded, fairly admitted
   scheduler and the original-source spreadsheet/sheet/physical-row FIFO
   *resource* lease. Correct its abort/rearm lifecycle first. Existing
   V12/TP/SMTP durable ledgers and fresh business identity/authorization
   checks remain the only authorities for external effects.
2. `launcher` owns assembly, runtime faults, cancellation and client
   lifecycle. It dispatches typed immutable module/cycle/source-key
   requests and receives bounded immutable result/progress/fault/terminal
   messages. It must not synchronously wait for the whole Research batch
   on its sole browser-owner scheduler thread. Error delivery from
   workers must globally close affected admissions and release active
   leases by their exact admitting scheduler owner after acknowledged
   terminal work.
3. `research` owns existing six source adapters, read-only source
   acquisition and canonical parser/aggregation/FX behavior. Two
   bounded fixed-thread market-read sync clients may use the same
   existing9222 Chrome and their own Playwright/target resources.
   No Backend-bound closure, mutable browser/Playwright object,
   credentials or existing session instance crosses worker threads.
   Client errors/unknown ownership cannot be softened to a successful
   source result. Source-site login and pacing must be serialized
   under the canonical site contract.
4. Existing original browser owner exclusively performs protected
   INSO/Google interactions and ALL external writes. It revalidates
   fresh row/snapshot/business permission and durable SENT/UNKNOWN
   before any effect; a resource lease alone is never authority.
   `gui` receives bounded immutable DTOs only.
5. STOP closes new admissions, cancels undispatched requests and
   safely drains/reconciles active leases. Preserve manual review
   pages, unknown external outcomes and120-second row cooldown.
   No new Chrome/Profile, daemon, second Research adapter, separate
   persistent queue/ledger, unbounded executor or invented order ID.

**Completion evidence / enforcement:** Before changing this status,
require offline contract/fault tests for cross-module same-row
exclusion, wrong-thread releases, abort/rearm, stop-before-dispatch,
fair admission and site auth; plus an Owner-authorized actual browser
window proving distinct parsed-source queries overlap while same
source orders serialize. Prove TP's previous454.210-second lateness
is addressed under contention and all resources remain bounded.
Independent CEO source Review and separate Owner production-install
authorization are required for the new executable. Publish evidence
in existing canonical V1.6 task/report; retire only owned temporary
test resources, never production/rollback/protected pages.
