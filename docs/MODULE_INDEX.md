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
