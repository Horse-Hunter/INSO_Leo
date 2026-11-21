# RFQ-025 — V1.6 正式晋升 + V1.7 页面嗅探（第一轮）

**状态：`V1_6_PROMOTED_TO_MAIN / V1_7_BASELINE_READY / PASTE_SNIFF_PARTIAL / NO_BUSINESS_EFFECT`**

Owner 一句话即可复核：本文件 → [EXECUTION_LOG](EXECUTION_LOG.md) → [FINAL_REPORT](FINAL_REPORT.md)
→ 脱敏页面证据 [`docs/evidence/rfq025/paste-import-sniff.md`](../../docs/evidence/rfq025/paste-import-sniff.md)。

本轮的定性：**版本晋升与开发基线已完成并推送；粘贴录单的页面结构、字段映射与两个按钮的真实语义已查清；
但"真实点通一遍"未完成**，因为弹窗依赖登录后的 ERP 外壳，而本轮未获登录授权、且 V1.6 正在运行。
不得把本轮描述为 V1.7 开发完成。

## 1. Owner 原始要求（本轮范围）

1. 将已验收的 V1.6 晋升为正式现版本（`main`），按三分支制度保留不可变发布记录。
2. 建立 V1.7 前瞻开发基线。
3. 嗅探 INSO 原生"粘贴"录单，替换现有 AI 录单方式；本轮只嗅探，不实现、不部署、不发采购。

Owner 明确禁止：重做 RFQ-024 已结案内容；改/装/重启运行中的 V1.6；发测试采购单；改真实订单/Sheets/生产库；
删 UNKNOWN/SENT/hold；加人工确认或全局禁用开关；提前实现未验证方案；扩大改动范围。

## 2. 验收清单

| # | 要求 | 状态 |
|---|---|---|
| 1 | `main` = 已验收 V1.6，纯快进、未强推 | 完成 |
| 2 | 晋升前指针留存为不可变记录 | 完成（4 个 annotated tag，已推送） |
| 3 | `release/previous` 按 BRANCH_POLICY 处理，不冒充旧版 | 完成（保持 `NOT_VERIFIED`，理由已记录） |
| 4 | `develop` 成为真正含 V1.6 源码的 V1.7 基线 | 完成（合并，非重置/非强推） |
| 5 | 不覆盖前任工作、不删历史分支、不动脏工作树 | 完成（本地 `main` 脏工作树未触碰） |
| 6 | 粘贴按钮定位方式 | 完成（`button#product_import_`） |
| 7 | 三字段顺序、分隔符、字段映射是否需每次设置 | 完成（默认即 `型号\|数量\|品牌` + `竖线('|')`） |
| 8 | 数据预览的可靠读取方式 | 结构已查清；**真实取值路径未验证** |
| 9 | "保存数据"语义与副作用边界 | 完成（源码级证明纯客户端 + 预览闸门） |
| 10 | 与运行中 V1.6 的隔离 | 完成（自有页面，采集后关闭，进程/PID 未变，0 新增故障） |
| 11 | 真实点通 5 步 | **未完成**（需登录，见第 4 节） |

## 3. 本轮结论摘要

- **晋升**：`main` `be9d0a51`（历史 V1.1）→ `d954e0a5`（V1.6 已验收），`be9d0a51..d954e0a5` 纯快进。
- **首次对齐 ≠ 常规晋升**：晋升前 `main` 只是 V1.1 历史指针，不能当"上一正式版"。
  因此 **`release/previous` 仍留在 `d244241e` 并保持 `NOT_VERIFIED`**，
  没有按常规程序改指 V1.1 —— 那等于伪造回退关系。V1.1 指针以 tag 冻结待追溯。
- **`develop` 此前不是可用基线**：它 11-14 建于 `9ad9ccb8`，此后只走政策/文档，与 V1.6 源码线分叉
  （develop 独有 14 个文档提交，v16 独有 95 个提交）。本轮以**合并**把 V1.6 源码带入，
  冲突 5 处全为文档/证据，`src/`、`tests/` 与 `d954e0a5` 逐字节一致。
- **粘贴入口**：单据内 `#product_import_`（文本"粘贴"）与 `#ai_import_`（"AI录单"）是同一行的兄弟按钮，
  id 不同、不会误点；两者都走同一个 `windows()` 弹窗框架与"关窗回调回填父表单"的模式。
- **粘贴页**：`product/Import.aspx`，默认字段映射前三列正是 `型号/数量/品牌`，分隔符默认 `竖线('|')`，
  **不需要每次显式设置**。
- **"保存数据"= 纯客户端**：`pasteImport(1)` 只做 `returnSet()` + `windowsClose()`，再由 `appendRow()`
  写入父表单表格；无 AJAX、无 `BillID`、不发采购。且被 `importPreviewReady` 闸门强制"先预览后保存"。
  结论：**具备与 AI 录单"保存数据"相同的客户端草稿语义**，属于可验证、无真实采购效果的操作。
- **但有同名陷阱**：列表页的批量导入弹窗（`innerenquiry/yewuxj/Import.aspx`）里，"保存数据"绑的是
  `Import()`，`$.post(?action=Import)` 且要求服务端返回 `BillID` —— 会在服务端建单。
  V1.7 **必须只用单据内 `product/Import.aspx` 路径**，不得走列表批量路径。
- **数据预览是服务端解析的结果**：`导入`（`pasteImport(0)`）POST 到
  `/services/product/import.ashx?action=PasteImport`，返回预览行并启用"保存数据"。
  只切"数据预览"标签不会自己出数据。这与 Owner 描述的"点数据预览即可看"不同，属真实页面行为差异，已按实测记录。
- **截断**：预览里的 `TRJC476K01...` 是单元格宽度省略，真实值在表格数据里；程序核对必须读数据源，不能读渲染文本。

## 4. 未完成与阻碍（如实）

**阻断项：弹窗需要"登录后的 ERP 外壳"，本轮未登录。**

- 共享 profile 的 Cookie 仍在，`List.aspx`、`product/Import.aspx`、`sale/Enquiry/Bill.aspx` 都能直接只读加载；
- 但 `windows()` / `main_alertbox()` 只在登录后的首页存在。独立列表页里的 `windows()` 定义为
  `function windows(a,b,c,d,e,f,g){parent.windows(...)}`，页顶时自调用 → 栈溢出被吞 → 弹窗永不出现
  （实测点 `#product_add_`、`#product_import_` 均无反应）。
- 要真正点通，必须先登录。**本轮不登录**：登录会覆盖共享 profile 的 `erp_token`，
  而 V1.6 正在跑业务，属干扰生产登录状态，未获授权。

因此以下六项标记 `NOT_VERIFIED`，V1.7 实现前必须补齐（需一次明确授权的登录窗口）：

1. 真实 5 步点击链路；
2. 弹窗底部按钮 DOM id 与禁用态切换；
3. 预览单元格/表格数据的取值路径；
4. 型号经解析后是否逐字节保持；
5. `appendRow()` 后父表单行的最终列值；
6. `import.ashx?action=PasteImport` 的响应结构与副作用。

## 5. 代码改动

**本轮零业务代码改动。** 仅文档与发布记录：`docs/BRANCH_POLICY.md`、`AGENTS.md`、`AI_START_HERE.md`、
`control-room/*`、`docs/evidence/rfq025/*`。`src/` 与 `tests/` 无任何变更（与 `d954e0a5` 逐字节一致）。

## 6. 下一轮建议（待 Owner 指令，不自动开工）

1. `workbuddy/v17-native-paste` 从 `develop` 起分支；
2. 用一次**明确授权的登录窗口**补齐第 4 节六项，重点是预览取值路径与 `appendRow()` 后的父表单行；
3. 替换点：`CoordinatorPurchaseDraftWriter.prepare()` 的 `prepare-ai-open`…`commit-ai-entry` 五步，
   换成 `粘贴` 弹窗的 `打开 → 写入 pasteData → 导入 → 读预览 → 保存数据`，
   其余（`new_draft`/`set_customer`/`set_purchaser`/`set_quotation_type`、`save_data`、`save_and_send`、
   去重、`UNKNOWN/SENT`、hold、Sheets 回写、通知）一律不动。
4. 保留"预览核对"为程序内部自动核对，不加人工审批；核对失败即 fail-closed，不点"保存数据"。
