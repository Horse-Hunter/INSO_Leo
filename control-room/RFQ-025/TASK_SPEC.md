# RFQ-025 — V1.6 正式晋升 + V1.7 页面嗅探

**状态：`V1_6_PROMOTED_TO_MAIN / V1_7_BASELINE_READY / PASTE_SNIFF_COMPLETE / NO_BUSINESS_EFFECT`**

Owner 一句话即可复核：本文件 → [EXECUTION_LOG](EXECUTION_LOG.md) → [FINAL_REPORT](FINAL_REPORT.md)
→ 脱敏页面证据 [`docs/evidence/rfq025/paste-import-sniff.md`](../../docs/evidence/rfq025/paste-import-sniff.md)。

本轮的定性：**版本晋升与开发基线已完成并推送；粘贴录单的五步已在真实生产环境完整跑通，
按钮标识、字段映射、预览取值路径、两个按钮的真实语义与副作用边界全部实测确认。** 业务代码仍未改动，
`src/` 未新增任何实现，等第二轮实现指令。

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
| 8 | 数据预览的可靠读取方式 | 完成（`layui.table.cache['dg']`，实测取到完整型号） |
| 9 | "保存数据"语义与副作用边界 | 完成（**实测零非 GET 请求** + 源码 + 预览闸门） |
| 10 | 与运行中 V1.6 的隔离 | 完成（第 1 轮只读期间进程/PID 未变、0 新增故障） |
| 11 | 真实点通 5 步 | **完成**（Owner 停机授权后全链路跑通，未建单、未发送） |

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
- **数据预览是服务端解析的结果**：`导入`（`pasteImport(0)`）**实测恰好一次 POST**
  `/services/product/import.ashx?action=PasteImport&VendorID=0&BillPage=Enquiry`，返回 20 列、1 行预览，
  同时把"保存数据"由禁用变为可用。只切"数据预览"标签不会自己出数据。
  这与 Owner 描述的"点数据预览即可看"不同，属真实页面行为差异，已按实测记录。
- **截断**：预览里的 `TRJC476K01...` 是单元格宽度省略，真实值在表格数据里；程序核对必须读数据源，不能读渲染文本。
  实测同一行渲染文本与缓存值一致（本机列宽足够），但契约按"读缓存"执行。

## 4. 真实链路实测结果（Owner 停机授权后完成）

一次会话内完整执行：登录 → 业务询价 → `新增`（空草稿）→ `粘贴` → 写示例 → `导入` → 读预览 →
`保存数据` → 读父表单行 → `返回列表` 关闭。**全程未点 `保存` / `保存并发送`。**

| 验收点 | 实测结果 |
|---|---|
| 弹窗归属 | `#winIframe_dialog1` → `product/Import.aspx?BillPage=Enquiry&VendorID=&h=510` |
| `导入` 控件 | `#win_btn__dialog11` |
| `保存数据` 控件 | `#win_btn__dialog12`，**初始 `disabled`**，解析成功后转可用 |
| `新增` 是否建单 | **否**：`#BillID` 与 `#BillNo` 全程为空 |
| 型号是否逐字节保持 | **是**：缓存 `PartNo` = 输入 `TRJC476K016RRJ` |
| ERP 自动补编码 | **是**：`ProductID` = `P1463619`（输入中不存在） |
| 数量类型 | 缓存里是**字符串** `"200"` → 实现时必须显式转 `int` 并校验 `>0` |
| `保存数据` 网络行为 | **零个非 GET 请求**（实测监听，非推断） |
| `保存数据` 后父表单 | 明细行写入成功，单元格含 `P1463619` / `TRJC476K016RRJ` / `Kyocera AVX` / `200` |
| `保存数据` 后 `#BillID` | 仍为空 → **没有产生服务端单据** |
| 事后核对 | 业务询价列表最新单号仍为 `XJ-261119-150055`，**无 11-21 新单** |
| 收尾 | `btnBack`（`goback()`）关闭表单，未保存、未发送 |

**结论："保存数据"具备与 AI 录单"保存数据"完全相同的客户端草稿回填语义，无外部持久化，可安全纳入 V1.7。**

## 4b. 遗留（不影响结论）

1. **弹窗关闭是隐藏而非移除**：`保存数据` 后 dialog 置为隐藏，`Import.aspx` iframe 仍留在 DOM。
   判断"关了"必须看可见性，不能看存在 —— 与既有 INSO 契约一致，实现时不要用 `count()==0`。
2. **可靠等待条件**：`导入` 后应同时满足 (a) `layui.table.cache['dg']` 行数符合预期，
   (b) `#win_btn__dialog12` 不再 `disabled`，再读数据；任一不成立 fail-closed，不点保存。禁止固定睡眠。
3. **登录是生产动作**：第 1 轮之所以没做，正是因为登录会覆盖共享 profile 的 `erp_token`。
   实现阶段若需要现场跑通，仍须按"Owner 停机或维护窗口"处理，不得在 V1.6 跑业务时登录。

## 5. 代码改动

**本轮零业务代码改动。** 仅文档与发布记录：`docs/BRANCH_POLICY.md`、`AGENTS.md`、`AI_START_HERE.md`、
`control-room/*`、`docs/evidence/rfq025/*`。`src/` 与 `tests/` 无任何变更（与 `d954e0a5` 逐字节一致）。

## 6. 第二阶段：V1.7 实现（2026-11-21，Owner 现场授权）

Owner 指令：`RFQ-025 第一阶段 Review PASS`，允许 V1.6 暂停、直接在现有生产环境完成 V1.7 开发、
调试与实机验证；一次性完成开发、验证、回归与候选构建。

### 6.1 实现范围（只换录单方式）

| 文件 | 改动 |
|---|---|
| `src/inso/purchase_writer.py` | AI 面板适配器整体替换为 `PasteImportPanel` + `PlaywrightPastePreviewReader`；三个写动作改为 `SET_PASTE_DATA` / `RUN_PASTE_IMPORT` / `PASTE_ENTRY_COMMIT`；帧身份钉死 `product/Import.aspx` 并**显式拒绝** `innerenquiry/yewuxj/Import.aspx` |
| `src/inso/write_safety.py` | `WriteAction` 的 AI 成员换为粘贴成员；公开方法改名 |
| `src/launcher/v12_composition.py` | `prepare()` 的五个 AI 步骤换为 `open → assert_fresh → set_data → import → read → validate → commit` |
| `src/workflow/v12_rules.py` | `build_ai_input` → `build_paste_input`（`型号|数量|品牌`）；`validate_ai_recognition` → `validate_draft_preview` |
| `src/workflow/v12_contracts.py` | `PurchaseDraftCommand.ai_input` → `paste_input` |
| `src/workflow/v12_flow.py` | 调用点同步 |
| `src/gui/app.py`、`src/gui/workbench.py` | 用户可见文案由"AI 识别"改为"粘贴录单" |
| `src/core/app_paths.py`、`src/launcher/backend.py`、`packaging/INSO_V1.1.spec`、`scripts/build_windows_release.ps1` | 版本标识 1.6 → 1.7 |

**刻意保留的内部名称：** `PurchaseOutcome.AI_RECOGNIZED`、`ReasonCode.AI_RECOGNITION_MISMATCH`、
`EventType.AI_RECOGNITION_READY/MISMATCH`。它们是 SQLite 与事件目录里的历史标识，
改名需要数据迁移；Owner 明确允许保留必要内部名称。语义是"预览已核对通过"，用户可见文案已改。

**未改动：** 去重、七天窗口、准入规则、`save_data`、`save_and_send`、`UNKNOWN/SENT`、hold、
Sheets 读写、报价更新、TP、邮件、调度周期、代理与 CDP 修复。

### 6.2 三个关键设计（都有实测依据）

1. **先证明"空"再解析**：`assert_paste_preview_fresh` 在点 `导入` 之前要求预览为空且"保存数据"仍禁用，
   这样后面读到的行只可能来自本次解析，不可能是上一单残留。
2. **按状态等待，不按时间**：同时满足"缓存行数符合预期"与"`#win_btn__dialog12` 解禁"，否则 fail-closed。
3. **数量只接受 ASCII 纯数字**：`"200.0"` / `"2e2"` 一律拒绝而不是截断 —— 截断正是让错误数量通过的方式。

### 6.3 真实页面验证与回归

见 [EXECUTION_LOG](EXECUTION_LOG.md) 第 8 节与
[`docs/evidence/rfq025/v17-live-verification.md`](../../docs/evidence/rfq025/v17-live-verification.md)。

### 6.4 交付边界

候选 EXE 交 CEO 审核；**未安装、未覆盖 `dist/INSO_V1.6`、未重启生产、未发送任何真实采购单**。
V1.7 仍是前瞻版本，未经 Owner 验收不得晋升 `main`。

## 7. 下一轮（待 Owner 指令，不自动开工）

1. `workbuddy/v17-native-paste` 从 `develop` 起分支；
2. 实现替换点：`CoordinatorPurchaseDraftWriter.prepare()` 的 `prepare-ai-open` … `commit-ai-entry`，
   换成 `粘贴` 弹窗的 `打开 → 写入 #pasteData → 点 #win_btn__dialog11 → 读 layui.table.cache['dg'] → 点 #win_btn__dialog12`；
   其余（`new_draft` / `set_customer` / `set_purchaser` / `set_quotation_type`、`save_data`、`save_and_send`、
   去重、`UNKNOWN/SENT`、hold、Sheets 回写、通知）一律不动；
3. 输入改为 `型号|数量|品牌`（注意：AI 旧格式是 `型号·品牌·数量`，**顺序也变了**）；
4. 预览核对为程序内部自动核对、不加人工审批；型号/品牌逐字节比对、数量转 `int` 后比对，
   任一不符即 fail-closed，不点"保存数据"；
5. 等待条件用状态而非睡眠：预览行数符合预期 + `#win_btn__dialog12` 解除禁用；
6. 只用单据内 `product/Import.aspx` 路径，**禁止**走列表页批量导入（那是服务端建单）。
