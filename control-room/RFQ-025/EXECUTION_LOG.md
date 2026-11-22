# RFQ-025 — 执行记录（2026-11-21，第一轮：晋升 + 基线 + 嗅探）

只记可复算的事实与命令。Owner-facing 结论见 [TASK_SPEC](TASK_SPEC.md) 与 [FINAL_REPORT](FINAL_REPORT.md)。
页面结构证据见 [`docs/evidence/rfq025/paste-import-sniff.md`](../../docs/evidence/rfq025/paste-import-sniff.md)。

## 0. 起点核验（先核现场，再动手）

| 项 | 实测 |
|---|---|
| 仓库 | `Horse-Hunter/INSO_Leo` |
| 远端 `workbuddy/v16-rfq016-stabilization` | `d954e0a59ca0b31956ad306dca9dab9603acc3f2`（= CEO 核验值，命中） |
| 审核输入 HEAD | `b1b5b8151bc4468698dde93146f78a90322d32c3`（命中） |
| 审核输入之后 | 3 个提交 `c060bc9e`、`410d603d`、`d954e0a5`，只改 `control-room/CEO_HANDOVER.md`、`COORDINATION.md`、`RFQ-024/REVIEW.md`（+79 行，无业务源码） |
| 工作树 | 8 个；`main` 工作树 `D:/Program_Leo/INSO_Leo` 有 3 处未提交改动 + 大量未跟踪文件 → **未触碰** |
| `main` 本地 | `c3a597d9`（SHEETS 线，5 个该线独有提交，已在 `origin/backup/sheets-v1-before-baseline-v2` 留底） |
| `main` 远端 | `be9d0a51`（V1.1 历史） |
| `release/previous` | `d244241e`（文档已标 `NOT_VERIFIED`） |
| `develop` | `e7a1c5af`，merge-base 与 v16 为 `9ad9ccb8`（11-14） |
| 装机的 EXE | `sha256 9a0cb3d3…2710`，8,505,470 B，与 Owner 给的一致 |
| 清单 | `5bd7d7a7…63ff`，2,872 行，EXE 行哈希亦为 `9a0cb3d3…` |
| 进程 | PID 56032 / 75380，2026-11-20 14:50:55 起 |

`v16` 工作树快进到 `d954e0a5`（`git merge --ff-only`，原为 `b1b5b815`，干净）。

## 1. V1.6 晋升（首次对齐）

### 1.1 先判"这是首次对齐还是常规晋升"

`git merge-base --is-ancestor origin/main v16` → **是**，`be9d0a51` 是 `d954e0a5` 祖先，
`rev-list --left-right --count origin/main...origin/workbuddy/...` = `0 644` → 纯快进可行，无需强推。

### 1.2 不可变发布记录（annotated tag，已推送）

| tag | commit | 含义 |
|---|---|---|
| `release/v1.6-official-20261121` | `d954e0a5` | V1.6 正式现版（EXE `9a0cb3d3…`、清单 `5bd7d7a7…`、审核 RFQ-024） |
| `release/v1.1-main-superseded-20261121` | `be9d0a51` | 被取代的 `main` 指针；**明确标注：不是经 Owner 验收的上一正式版** |
| `release/previous-superseded-20261121` | `d244241e` | 晋升前 `release/previous`，仍是 `NOT_VERIFIED` |
| `preserve/sheets-v1-local-main-c3a597d9` | `c3a597d9` | 本地 `main` 停留的 SHEETS 线（5 个独有提交） |

### 1.3 执行

```
git push origin d954e0a59ca0b31956ad306dca9dab9603acc3f2:refs/heads/main
#   be9d0a51..d954e0a5  (fast-forward)
```

- 未使用 `--force`；`--dry-run` 先行确认 `be9d0a51..d954e0a5`。
- 本地 `main` 分支**故意未移动**：它在 `D:/Program_Leo/INSO_Leo` 工作树被检出且有未提交改动，
  移动它等于改写脏工作树的 HEAD。权威现版以 `origin/main` 为准，此事已在 `BRANCH_POLICY` 写明。

### 1.4 `release/previous` 为什么没有改指 V1.1

BRANCH_POLICY 常规程序第 3 步要求"先把 `release/previous` 更新到晋升前的原 `main`"，
但同一文件的"首次对齐"条款禁止把历史 V1.1 当成已核实的上一正式版。
Owner 本轮指令明确要求"不得直接将其冒充上一正式生产版本；按 BRANCH_POLICY 处理实际回退基线，
无法证明的部分如实记录"。

判定：本项目**不存在**"经 Owner 在三分支制度下验收过的上一正式版本"。
可证的只有运行级回退材料（上一装机版 EXE `fa7a8544…` / 源码 `64d3ec2c`，
实物在 `dist/INSO_V1.6/INSO_V1.6.exe.prev-20261120T065005Z`），但它同样不是"Owner 验收过的正式版"。
因此 `release/previous` **保持 `d244241e` 不变、状态 `NOT_VERIFIED` 不变**，理由写入 `BRANCH_POLICY`。

下一次晋升起，被取代者就是 `d954e0a5`，届时按常规程序走。

## 2. V1.7 开发基线（`develop`）

### 2.1 先确认 develop 到底有什么

`develop` merge-base 与 v16 = `9ad9ccb8`（2026-11-14）。此后：

- `develop` 独有 14 个提交：**全部是 docs/policy**（`e2915ff1` 建立三分支制度 … `e7a1c5af` 故障信息政策）。
- `v16` 独有 95 个提交：含 RFQ-017…024 的全部业务修复。

即：**晋升前的 `develop` 不含 V1.6 源码**，不能直接当 V1.7 基线。这是本轮的重要发现，
它和"`main` 是 V1.1"是同一类问题的两面。

### 2.2 用合并（非重置、非强推）补齐

```
git worktree add "D:/Program_Leo/INSO_Leo/.worktrees/v17-develop-baseline" develop
git merge --no-ff --no-commit origin/workbuddy/v16-rfq016-stabilization
```

冲突 5 处，**全部为文档/证据，`src/`、`tests/` 零冲突**：

| 文件 | 处理 | 理由 |
|---|---|---|
| `AGENTS.md` | 取 develop | develop 是严格超集：两条 Owner 强制规则两侧逐字节相同，develop 另有"Branch promotion is Owner-only"与"Lean Review" |
| `control-room/CEO_HANDOVER.md` | 取 v16 | v16 是当前权威（RFQ-024 结案，11-21） |
| `control-room/COORDINATION.md` | 取 v16 | 同上 |
| `control-room/RFQ-020/EXECUTION_LOG.md` | 取 v16 | v16 版含 `corrections_2026_11_15` 更正段 |
| `docs/evidence/rfq020/rfq020-build-2026-11-14.json` | 取 v16 | 同上（含更正后的观测时间） |

合并后校验：

```
git diff --stat origin/workbuddy/v16-rfq016-stabilization -- src tests   # 空
git diff --name-only origin/workbuddy/v16-rfq016-stabilization           # 仅 5 个文档
```

合并提交 `d2473a2a`；随后 `143fdadc` 同步 `BRANCH_POLICY` / `AGENTS.md` / `AI_START_HERE.md`
中"main 仍是 V1.1"的过期表述（晋升后这些句子已不成立，留着会误导下一个窗口）。

`e7a1c5af..143fdadc  develop -> develop` 已推送。

### 2.3 三条长期线现状

| 分支 | HEAD | 说明 |
|---|---|---|
| `main` | `d954e0a5` | V1.6 正式现版 |
| `develop` | 合并 `d2473a2a` + 政策同步 + 本轮记录（tip 见 `git log develop`） | V1.7 基线与集成分支（含 V1.6 源码） |
| `release/previous` | `d244241e` | 未动，`NOT_VERIFIED` |

## 3. 原 AI 录单调用链（供最小替换）

`src/inso/purchase_writer.py` 是唯一适配器（未新建第二套）。

```
src/workflow/v12_flow.py:1003   ai_input = build_ai_input(mpn, brand.strip(), quantity)
src/workflow/v12_rules.py:236   build_ai_input -> f"{mpn}{' '*6}{brand}{' '*6}{quantity}"
                                （型号 · 6 空格 · 品牌 · 6 空格 · 数量）
src/launcher/v12_composition.py:302-380
  CoordinatorPurchaseDraftWriter.prepare(PurchaseDraftCommand):
    1 prepare-new-draft   -> InsoPurchaseWriter.new_draft()
    2 prepare-customer    -> set_customer("深圳阿尔克贸易有限公司")
    3 prepare-quote-type  -> set_quotation_type()
    4 prepare-purchaser   -> set_purchaser()
    5 prepare-ai-open     -> open_ai_entry()      # button#ai_import_ "AI录单"
    6 prepare-ai-input    -> set_ai_input(text)   # textarea#paste-area
    7 prepare-ai-run      -> run_ai_recognition() # button#ai-recognize
    -- read_ai_result()   -> #preview-body > tr input[data-f=PartNo|Brand|Qty]
    -- validate_ai_recognition() -> PurchaseOutcome.AI_RECOGNIZED（否则 fail-closed）
    8 commit-ai-entry     -> commit_ai_entry()    # button:has-text("保存数据") / #win_btn__dialog11
    -- wait_for_model() + read_model/brand/quantity -> #_id_dg td[data-field=...]
    -- validate_ai_recognition() 二次校验 -> PRE_SAVE_READY
```

下游不动：`InsoPurchaseWriter.save_data()`（`#btnSave`，Write Gate 内）、`save_and_send()`
（`#btnSave2`，`OwnerAuthorizedSaveAndSendGate`）、去重、`UNKNOWN/SENT`、hold、Sheets 回写、通知、TP。

**最小替换点**：`prepare()` 里的第 5–8 步 + 两次 `read_ai_result` 读取，换成粘贴弹窗路径。
`new_draft` / `set_customer` / `set_quotation_type` / `set_purchaser` 与保存之后的一切都不变。

**可直接复用的既有能力**（不要重写）：

| 能力 | 位置 |
|---|---|
| INSO 会话/登录守卫/页面租约 | `src/launcher/inso_session.py`、`src/research/cdp_pages.py` |
| 表单 frame 解析 `iframe#winIframealert_enquiry` | `purchase_writer._FORM_SCOPE_FRAME` |
| 多选 purchaser 清空与菜单关闭 | `_PlaywrightActionPort._clear_checked_options` / `_dismiss_select_menu` |
| 控件语义白名单与门禁 | `src/inso/write_safety.py`（`SelectorRegistry` / `InsoDraftActions` / `ProductionWriteGate`） |
| 关窗/清场 | `dismiss_order_surface()`、`_close_order_window()` |
| 只读校验范式（JS handler 取源判定） | `src/launcher/v12_phase_a_readonly.py`（`_WRITE_WORDS`、`_function_source`） |

需要新增的（下一轮）：一个 `PasteImportPanel`（打开/写 `#pasteData`/点 `导入`/读预览/点 `保存数据`），
以及 `WriteAction` 里对应的语义条目。**不新增第二个 adapter、浏览器、调度器或账本。**

## 4. 页面嗅探过程（只读）

原则：只在自己新建的标签页里读；不登录；不点 `导入`、不点 `保存数据`；每轮结束关闭自有页面并复核页面数。

| 步 | 动作 | 结果 |
|---|---|---|
| 1 | `/json/list` 被动枚举 | 2 个 page：Google 表格 + 程序自有 `about:blank#INSO_CREATE:…` |
| 2 | 自有页 `GET login.aspx?t=islogin` | 落到登录页 → **不登录，中止** |
| 3 | 自有页 `GET /` | `login.aspx?t=reset` |
| 4 | Cookie 读名（不含值） | `erp_token` 等仍在 |
| 5 | 自有页 `GET /skins/etaoerp//InnerEnquiry/YeWuXJ/List.aspx` | 200，`1.业务询价` |
| 6 | 列表页点 `#product_add_`（`AddBill()`） | 无任何反应；`windows()` 自调用栈溢出（见证据第 2 节） |
| 7 | 列表页点 `#product_import_` | 同上，无反应 |
| 8 | 读列表页内联脚本 `粘贴` 上下文 | 得到 `product_import()` 全文与 `windows(...)` 按钮组 |
| 9 | 自有页 `GET product/Import.aspx?BillPage=Enquiry&VendorID=` | 200，`粘贴导入`，拿到全部 id/默认映射/处理器源码 |
| 10 | 自有页 `GET innerenquiry/yewuxj/Import.aspx` | 200；确认这是**列表批量**版本，`保存数据`=`Import()` |
| 11 | 自有页 `GET sale/Enquiry/Bill.aspx` | 200，`客临时询价`；`BillID` 为空（未建单）；拿到工具栏与 `ai_import()` / `product_import()` |

每次采集后：`own_page_closed`，`/json/list` 页面数回到基线；PID 56032/75380 未变；`fatal.log` 仍 0 字节。

## 4b. 真实链路实测（11:05 前后，Owner 停机并授权）

Owner 指示"1.6 已停止，可以用真实生产业务流程做嗅探"。开工前先核实：

- `Get-Process INSO_V1.6` 仍返回 PID 56032 / 75380 —— **进程没退**（已知缺陷：关窗后 Tk 主循环结束但
  非守护线程仍在）。但 GUI 窗口仍在、20 秒 CPU 增量 0、10:59:11 之后日志无新轮次 → 判定业务已停止、不跑批。
- 据此按"业务已停"执行，并全程监控日志：实测期间**没有任何新的 cycle 行**，即脚本从未与生产调度并行。

脚本 `probe_live_b.py`（一次性，不入库）在一次会话内完成并记录：

```
login.aspx?t=islogin -> 普通登录 -> 首页外壳 (after_login: https://yingsuo.alperp.cn/)
-> 业务询价 -> 新增 -> iframe#winIframealert_enquiry
   form_url = /skins/etaoerp//sale/Enquiry/Bill.aspx
   #BillID 打开后 = ""        <- 新增不建单
-> 点 button#product_import_（文本"粘贴"）
   弹窗 iframe #winIframe_dialog1 -> product/Import.aspx?BillPage=Enquiry&VendorID=&h=510
   底部按钮: #win_btn__dialog11 = 导入 (可用) | #win_btn__dialog12 = 保存数据 (disabled) | 取消
-> 填写 textarea#pasteData = "TRJC476K016RRJ|200|Kyocera AVX"，回读一致
   #combox101 = 3 / 竖线('|')；cmb0..4 = 型号/数量/品牌/品名/编码-型号
-> 点 #win_btn__dialog11 (导入)
   POST /services/product/import.ashx?action=PasteImport&VendorID=0&BillPage=Enquiry   (仅此 1 次)
   之后 #win_btn__dialog12 解除 disabled
   预览 20 列；layui.table.cache['dg'] = [{PartNo:TRJC476K016RRJ, Qty:"200",
        Brand:"Kyocera AVX", ProductID:"P1463619", ...}]
-> 点 #win_btn__dialog12 (保存数据)
   非 GET 请求数 = 0          <- 实测，不是推断
   父表单明细 cache 同上一行；单元格 = P1463619 / TRJC476K016RRJ / Kyocera AVX / 200
   #BillID 仍 = ""            <- 没有服务端单据
-> button#btnBack (goback()) 关闭表单，未保存、未发送
```

事后只读核对业务询价列表：最新单号 `XJ-261119-150055`，**无 2026-11-21 新单** —— 草稿已随表单关闭丢弃，
未在 ERP 留下任何空单据。

三个对实现有约束的实测点：

1. `Qty` 在缓存里是字符串 `"200"`，实现必须 `int()` 并校验 `> 0`。
2. 等待条件用状态：预览行数 + `#win_btn__dialog12` 解禁；禁止固定睡眠。
3. 弹窗关闭是隐藏，`Import.aspx` iframe 仍在 DOM；判断关闭看可见性。

## 5. 生产未受影响（可复核）

- 采集期间 10:43:07–10:43:10 `scheduled_module=inquiry phase=completed elapsed_s=3.438`。
- 日志中唯一 `runtime fault` 仍是 `2026-11-20 14:29:09 CDP_PAGE_OWNERSHIP_UNCONFIRMED`（已修结案）。
- 第 1 轮（V1.6 运行中，只读）：未登录、未点击导入/保存、未建单、未发采购、未写 Sheets、未碰生产库。
- 第 2 轮（Owner 停机授权后，真实链路）：登录 1 次；`新增` 空草稿 1 个，关闭后丢弃；
  `导入` 1 次（解析接口）；`保存数据` 1 次（纯客户端）；**未点 `保存`、未点 `保存并发送`、未建单**。
  事后列表核对无 11-21 新单。未写 Sheets、未碰生产库。
- 未停止、未重启、未覆盖 V1.6；未关闭他人标签页。

## 6. 改动清单

```
A docs/BRANCH_POLICY.md                     (首次对齐已完成段)
M AGENTS.md                                 (main 不再是 V1.1)
M AI_START_HERE.md                          (分支选择说明)
A control-room/RFQ-025/TASK_SPEC.md
A control-room/RFQ-025/EXECUTION_LOG.md
A control-room/RFQ-025/FINAL_REPORT.md
A docs/evidence/rfq025/paste-import-sniff.md
M control-room/COORDINATION.md
M control-room/CEO_HANDOVER.md
```

`src/`、`tests/`、配置、打包脚本：**零改动**。

## 7. 未验证

无遗留验证缺口。首轮标记的六项已在 4b 节全部实测补齐（真实链路、按钮 id、预览取值路径、
型号逐字节、父表单行值、`import.ashx` 响应与副作用）。

唯一仍未做的、也是刻意不做的：**没有点过 `保存`（`#btnSave`）与 `保存并发送`（`#btnSave2`）**。
这两步是正式建单与对外发送，属真实业务效果，不在本轮嗅探授权范围内。

---

# 第二阶段：V1.7 实现（2026-11-21）

Owner 一阶段 Review PASS，并授权直接在生产环境开发、调试、实机验证；本轮一次性完成实现、验证、回归与候选构建。

## 8. 代码改动

分支 `workbuddy/v17-native-paste`（自 `693bd983`）。提交 `38341aa5`。

| 文件 | 改动 |
|---|---|
| `src/inso/purchase_writer.py` | `AiEntryPanel`/`PlaywrightAiResultReader` 整体替换为 `PasteImportPanel`/`PlaywrightPastePreviewReader`；新增 `assert_fresh()`；三个写动作改绑；帧身份钉死 `product/Import.aspx` 并显式拒绝列表批量导入 |
| `src/inso/write_safety.py` | `WriteAction` 成员 `OPEN_PASTE_ENTRY`/`SET_PASTE_DATA`/`RUN_PASTE_IMPORT`/`PASTE_ENTRY_COMMIT`；公开方法同步改名 |
| `src/launcher/v12_composition.py` | `prepare()` 换成 7 步：new_draft → customer → quote-type → purchaser → paste-open → **paste-fresh** → paste-input → paste-import → read → validate → commit → parent read-back → validate |
| `src/workflow/v12_rules.py` | `build_ai_input` → `build_paste_input`（`型号|数量|品牌`）；`validate_ai_recognition` → `validate_draft_preview` |
| `src/workflow/v12_contracts.py` | `PurchaseDraftCommand.ai_input` → `paste_input` |
| `src/workflow/v12_flow.py` | 调用点同步 |
| `src/gui/app.py`、`src/gui/workbench.py` | 用户可见文案改为"粘贴录单" |
| `src/core/app_paths.py`、`src/launcher/backend.py`、`packaging/INSO_V1.1.spec`、`scripts/build_windows_release.ps1` | 版本 1.6 → 1.7 |

**保留的历史标识**：`PurchaseOutcome.AI_RECOGNIZED`、`ReasonCode.AI_RECOGNITION_MISMATCH`、
`EventType.AI_RECOGNITION_READY/MISMATCH`。它们是 SQLite 与事件目录里的持久值，改名需要数据迁移；
语义是"预览已核对通过"。用户可见文案已全部改为"粘贴录单"。

**未改动**：去重/七天窗口/准入、`save_data`、`save_and_send`、`UNKNOWN/SENT`、hold、Sheets 读写、
报价更新、TP、邮件、调度周期、代理与 CDP 修复。`git diff --stat` 可逐条核。

## 9. 实现过程中发现并修掉的两个真实缺陷

1. **`filter(has=<iframe handle>)` 跨帧非法。** Playwright 报
   `Inner "has" locator must belong to the same frame.`，第一次真实验证因此
   `VALIDATION_FAILED / CONTROL_NOT_FOUND`。改为"以对话框内的 `#winIframe_dialog1` 为锚点"解析，
   既合法又把对话框绑定到本帧。
2. **旧 `close()` 的页面级回退可能误关单据。** 原实现找不到帧时会点全局
   `button[title="关闭窗口"]`，而采购临时询价窗口本身就有同名按钮 —— 可能把单据关掉。
   现改为：帧不在就报告"未关闭"、不点任何全局控件，由清场流程关窗口。

## 10. 真实页面验证（生产代码路径）

脚本不做任何"探针式"绕行，直接复用 `backend._prepare_on_page()` 的同一组合：

```
attach_inso_research_session(login=..., fresh_page=True)
  -> access.operation_page()
  -> InsoPurchaseWriter(form_page=form)
  -> CoordinatorPurchaseDraftWriter(actions=writer, parent_fields=PlaywrightParentProductFields(form))
  -> prepare(command)          # 唯一的正式路径
```

结果（`TRJC476K016RRJ|200|Kyocera AVX`）：

| 项 | 实测 |
|---|---|
| outcome | `AI_RECOGNIZED`（历史持久值，语义"预览已核对通过"） |
| 回读 | `TRJC476K016RRJ` / `Kyocera AVX` / `200`，与订单一致 |
| 解析请求 | 恰好 1 次 `POST /services/product/import.ashx` |
| AI 请求 | **0**（`Import_ai.aspx`、`ai_import` 命中数为零） |
| `#BillID` | 空 —— 未创建任何服务端单据 |
| 清场 | 前后 `dismiss_order_surface()` 均 True |
| 保存/发送 | **未点击** |

多单同页复测（同一会话连开两单）与完整证据见
[`docs/evidence/rfq025/v17-live-verification.md`](../../docs/evidence/rfq025/v17-live-verification.md)。

## 11. 测试

**定向**（开发迭代期，逐项通过）：

- `tests/inso/test_v12_purchase_writer.py` 78 项；
- `tests/inso/test_v12_write_safety.py` 11 项；
- `tests/launcher/test_v12_composition.py` 40 项；
- `tests/workflow/test_v12_rules.py` 38 项；
- `tests/launcher/test_backend.py`、`test_manual_order.py`、`test_source_date_flow.py` 123 项；
- `tests/gui/test_workbench.py` 12 项。

新增/改写的覆盖点：字段拼接顺序与完整性、分隔符内含字符、数量为字符串/小数/无效值、
预览空/多行/未解禁、解析超时、弹窗仅隐藏、批量导入路径拒绝、生产路径不得再引用 AI 端点。

**完整回归**：结果见第 12 节（同一份 JUnit 归档在 `docs/evidence/rfq025/`）。

## 12. 完整回归结果（源码冻结后一次）

```
4359 collected / 4336 passed / 22 failed / 0 errors / 1 skipped in 589 s
```

JUnit：`docs/evidence/rfq025/pytest-v17-full.xml`。唯一 skip 是既有的 Windows 符号链接权限条件。

### 22 个失败全部落在 TP 模块，且同一个根因

| 文件 | 失败数 |
|---|---|
| `tests/launcher/test_google_snapshot_cache.py` | 7 |
| `tests/launcher/test_tp_continuation.py` | 7 |
| `tests/workflow/test_tp_research.py` | 5 |
| `tests/launcher/test_tp_integration.py` | 2 |
| `tests/launcher/test_market_owner_recovery.py` | 1 |

失败签名统一为 `TpCycle.read_orders('test')` 返回空列表，随后
`assert 0 == 1` / `ValueError: not enough values to unpack (expected 1, got 0)`；
`test_tp_integration` 那条也是"没有工作项，所以没有派发"的连带结果。
**它们都在采购草稿写入之前就失败了，没有一条走到本次改动的代码。**

### 为什么判定与本次改动无关

1. `git diff` 里没有任何 TP / Google 模块文件：改动只在
   `src/inso/`、`src/launcher/v12_composition.py`、`src/workflow/v12_{rules,contracts,flow}.py`、
   `src/gui/{app,workbench}.py` 的文案、`src/core/app_paths.py`、`src/launcher/backend.py` 一行判定、spec 与构建脚本。
2. 在**未改动的 `develop` 工作树**上单跑 `tests/workflow/test_tp_research.py`：
   `5 failed, 69 passed` —— 与本次完全相同的 5 条，同样签名。
3. 失败发生在 `read_orders` 这一步，即 TP 从自己的数据源读不到订单；
   本轮的改动只影响"拿到订单之后如何录单"。

**没有删除、没有跳过、没有改动这些用例。** 它们是既存的失败集合，记录在此供 CEO 判断。
（V1.6 在 11-20 的全量是 4332/0/0/1，说明这 22 条是 11-20 之后由环境/数据状态引入的，
不是 V1.7 带来的；本轮没有权限也没有理由在本轮修 TP 模块。）

### 定向测试（开发迭代期，全部通过）

`tests/inso` 299、`test_v12_composition` 40、`test_v12_rules` 38、
`test_backend`/`test_manual_order`/`test_source_date_flow` 123、`test_workbench` 12。

## 13. V1.7 候选构建

用既有打包体系，`-BuildOnly`，不触碰 `dist/`：

```
scripts/build_windows_release.ps1 -BuildOnly -Version 1.7 \
  -PythonExecutable <v16 worktree>\.venv-release\Scripts\python.exe
```

复用 V1.6 时代那套已装好依赖的 `.venv-release`（PyInstaller 6.16.0 / Python 3.12.10），
没有新建第二套打包环境。

| 项 | 值 |
|---|---|
| 路径 | `build/windows-release-stage-1.7/dist/INSO_V1.7/INSO_V1.7.exe` |
| 大小 | 8,508,798 B |
| SHA256 | `5707b9c598546c6476f96bfde217d712d1f7768732acf5032ef79657004af253` |
| 文件数 | 2,872 |
| 含 runtime/ | 否 |
| 发布扫描 | `RELEASE_SCAN_OK`（脚本内建） |
| `--self-check` | 退出码 0（脚本内建，未通过则构建失败） |
| `--idle-self-check` | 退出码 0，`gui_rendered: true`，标题 `INSO LEO V1.7 — Procurement Automation Control Center`，`business_thread_started: false` |
| 清单 | `docs/evidence/rfq025/INSO_V1.7-artifact-manifest.sha256`（2,872 行），SHA256 `27d46b1cc4b7901121bf800534fb617daeb091e29a4a76d91257afaf696f3f9a` |
| 源码 commit | `332b8695`（构建时源码即此状态；其后提交只改文档与测试导入顺序，不影响产物） |

`--idle-self-check` 会往产物里写 `runtime/logs/v13-idle-self-check.json`，已删除，文件数回到 2,872。

**未做**：未安装到 `dist/INSO_V1.6`、未覆盖运行目录、未启动正常业务、未发真实采购单。

---

# 第三阶段：收尾、安装与生产试运行（2026-11-21 晚）

Owner 指令：第二阶段核心功能通过，本轮一次性完成收尾、跨版本安装适配、正式安装、正常生产启动与真实业务试运行。

## 14. TP 22 条失败的真实根因（确认 CEO 判断）

**不是** V1.7 引入的回归，是测试时基问题。

`automatic_admission.age_reason()` 对 TP 采用"上月同日"截止：`2026-11-21` 运行时截止为 `2026-10-21`。
合成订单的 `rfq_date` 固定为 `2026-10-20`（`tests/sheets/test_tp_brief.py` 的 `brief()` 默认值），
而 `TpCycle.read_orders()` 在未拿到 `now` 时回落到 `datetime.now(UTC)` —— 于是订单在自己的夹具里"过期"了。

22 条失败全部同源，证据分三类：

| 失败签名 | 含义 |
|---|---|
| `ValueError: not enough values to unpack (expected 1, got 0)` | `read_orders()` 被年龄过滤成空列表（19 条） |
| `assert cycle.issues` == `{}` | 同上，连"过期"记录都没留下 |
| `assert 'RESEARCHING' == 'FAILED'` | 手动路径读到空 → 没有任务可失败（1 条连带） |

### 修复（只动测试时基，不动业务规则）

1. `tests/workflow/test_tp_research.py::build()` 给 `TpCycle` 传入 `clock=lambda: NOW`。
   `clock` 是**既有参数**，本来就是这个用途；钉住后所有省略 `now` 的调用点（`read_orders`、
   `backend._execute_order_action` 的手动路径）都用测试时基，不再读墙上时钟。
2. `TpCycle._run()` 统一时间基准：原来 `read_orders` 用 `clock`、而 `claim()` 却拿到原始 `now`——
   加了 clock 之后会出现"读到了订单，claim 又按墙上时钟判它过期"的自相矛盾（这正是 `[research]/[mail]`
   两个参数化用例改后先变红的原因）。现在 claim/recover/finish/execute_tp/complete_order 全用
   `current_now`；**`worker.run_due(now=now)` 刻意保留调用方的 `now`**，因为"到期"是调度不是准入。
3. 生产语义不变：生产不传 `clock`，`current_now` 就是 `now`，逐字节等价。

**没有**修改 TP 准入规则、没有放宽一个月限制、没有改真实订单日期、没有删除或跳过任何用例。

### 同类问题（顺带修掉，否则安装门禁跑不起来）

`scripts/test_install_gates.ps1` 的夹具数据库事件时间固定在 `2026-11-15T08:00`，而门禁要求
72 小时内 —— 2026-11-18 之后整套测试必然失败（与 TP 同一个病）。现改为相对当前时间生成；
`-Scenario` 分支原本显式传死时间，也一并改成相对值。

## 15. 粘贴录单的两处收尾

### 15.1 无法用三列表达的订单不再中断整轮

`build_paste_input()` 对含 `|` 或换行的型号/品牌抛 `ValueError`，而它在 `v12_flow.py` 构造
`PurchaseDraftCommand` 时调用，位置在采购步骤自身的异常处理**之前**——一旦命中，整轮 poll 直接抛穿，
同批其他订单一起丢。

现在改为在构造命令前先算 `paste_input`，`ValueError` 走**既有的**单笔无效输入通道：
`PURCHASE_EXCEPTION` + `PURCHASE_INPUT_INVALID`，只停这一单。
新增测试 `test_a_model_that_cannot_be_pasted_fails_only_its_own_order` 用两行夹具证明：
坏行被park、好行照常生成 `Mpn-2|8|Brand-X`。

### 15.2 字段映射与分隔符：默认只读，不默认就改回

实测结构（`product/Import.aspx`）：

| 控件 | 结构 | 默认 |
|---|---|---|
| `#cmb0/#cmb1/#cmb2` | `input type=hidden`（值 = `PartNo`/`Qty`/`Brand`）+ 兄弟 `div.select-box`（`#cmbN_text` 只显示中文 + `summary`） | 型号/数量/品牌 |
| `#combox101` | `input type=hidden`（值 `3`）+ `#combox101_text` + `summary` | `3` = `竖线('|')`（`/config/etaoerp/FenGeFu.json`） |

`#combox101_text` 的显示值可能是过期占位（实测读到 `Tab('\t')`），而 `pasteImport` 只读隐藏值——
所以守卫**只读隐藏 input**，与"不能把视觉文本当数据"同一条规则。

`PasteImportPanel.ensure_layout()`：
正常情况只读四个值、**一个控件都不点**；发现不一致时点该 `select-box` 的 `summary`，
在弹出的 `details-menu li` 里按精确文本选回目标项，再复读隐藏值确认；选不到或值没变就 fail-closed。
`prepare()` 新增步骤 `prepare-paste-layout`（放在打开弹窗之后、写数据之前），
诊断上与"弹窗打不开"区分开。

测试：4 条（默认只读、错误映射被改回、选项不出现即拒、点了但值没变即拒）；
真实环境复测一次（见 `docs/evidence/rfq025/v17-live-verification.md` 第 5 节），结果不变。

## 16. 冻结后的完整回归

```
4365 collected / 4364 passed / 0 failed / 0 errors / 1 skipped in 765 s
```

- 由 `4359 + 6`（新增布局守卫 4 条、单笔隔离 1 条、编排步骤 1 条）而来；
- **上一轮的 22 条 TP 失败全部转绿**，无删除、无跳过、无 `xfail`；
- `ruff check src tests` 仍是基准的 3 条既有 F811（`test_google_quote_update.py` 重复用例名）；
- JUnit：`docs/evidence/rfq025/pytest-v17-full.xml`。

## 17. 最终候选（源码变更后重建）

| 项 | 值 |
|---|---|
| 源码 commit | `1ce1671f`（构建后只提交过文档） |
| 路径 | `build/windows-release-stage-1.7/dist/INSO_V1.7/INSO_V1.7.exe` |
| 大小 | 8,510,418 B |
| SHA256 | `6e258a5021792a1b4b88a72ca12d355064aab8c398e64eb58240ef542dece780` |
| 文件数 | 2,872（无 `runtime/`） |
| 清单 | `docs/evidence/rfq025/INSO_V1.7-artifact-manifest.sha256`（2,872 行） |
| 清单 SHA256 | `e148a4d22a5c2b9a7b81b484fc6228ec162cd112e896eed3aa67ace2426f5397` |
| `verify_release_candidate` | PASS（2872/2872，missing 0，mismatch 0，unexpected 0） |
| `--self-check` | 退出码 0 |
| `--idle-self-check` | 退出码 0，`gui_rendered: true`，标题 `INSO LEO V1.7 — Procurement Automation Control Center`，`business_thread_started: false` |

`--idle-self-check` 会往产物写 `runtime/logs/`，已删除，文件数回到 2,872。

## 18. 安装脚本：跨版本适配

`scripts/install_release_candidate.ps1`（不改结构、不重写，只做参数化 + 一个显式模式）：

- **两个 EXE 名分开**：`-PreviousExeName`（默认 `INSO_V1.6.exe`，被替换的那个）与
  `-CandidateExeName`（默认空 = 从候选清单里读，必须恰好一个根级 EXE）。
  旧实现把 `INSO_V1.6.exe` 写死在十余处（快照比对、切换、post-copy 校验、回滚、进程门禁、仅校验模式）。
- **进程门禁同时查新旧两个名字**：一次切换前后，任何一侧的残留进程都是同一台账上的第二个调度器。
- **回滚路径同步**：恢复时先删掉失败切换留下的 *候选* EXE（名字可能不同），再放回旧 EXE。
- **新增 `-FreshInstall`**：装进自己的目录，V1.6 目录**一个字节都不动**。要求目标为空、
  候选不带 `runtime`、创建并复验 `runtime` **Junction**、跑 `Assert-DatabaseReport`、
  新旧两个安装目录都不得有活进程；失败时只删本次创建的东西并报 `FAIL_CLEANED`。
- **数据库门禁抽成 `Assert-DatabaseReport`**，两种模式共用：切换模式要求报告属于本安装，
  全新安装模式不要求（报告属于共享 runtime 的那套安装），但仍要求报告描述的就是配置里那个台账。

`scripts/test_install_gates.ps1` 新增 3 组用例（跨版本切换、跨版本切换失败回滚、全新安装 + 拒绝覆盖），
`checks = 202 / GATE_TEST_RESULT = PASS`。

## 19. 正式安装

前置（全部实测）：

| 项 | 证据 |
|---|---|
| V1.6 是否真的停 | 日志最后一条 `10:59:11`；两进程 CPU 零增量；无窗口；`-wal` 不存在（台账已 checkpoint） |
| 停止残留进程 | PID 56032 / 75380 已终止（窗口早已销毁，无正常停机入口；业务已静默 10.5 h） |
| 回退快照 | `dist\release-backups\RFQ-025-pre-v17-20261121T132826Z`，`BACKUP_RESULT = PASS`，`exe_sha256 = 9a0cb3d3…2710` |
| 数据库回退 | 同目录 `database\workflow.sqlite3`，`DB_VERIFY_RESULT = PASS`，`purchase_rows = 40`，`write_intent_state = NONE_PROVEN`，`event_age_hours = 10.51` |

安装（`-FreshInstall`，未触碰 V1.6）：

```
INSTALL_RESULT = PASS
install_dir = D:/Program_Leo/INSO_Leo/dist/INSO_V1.7
installed_exe_sha256 = 6e258a5021792a1b4b88a72ca12d355064aab8c398e64eb58240ef542dece780
installed_files_verified = 2872
runtime_junction = D:/Program_Leo/INSO_Leo/dist/INSO_V1.4/runtime
rollback_kind = PREVIOUS_INSTALL_UNTOUCHED
rollback_previous_install = D:/Program_Leo/INSO_Leo/dist/INSO_V1.6
```

配置继承：`dist\INSO_V1.7\runtime` 是 **Junction** → `dist\INSO_V1.4\runtime`，
`production.json`（`tp_enabled=True`、`v16_enabled=True`、`google_api.enabled=True`）、
`research.json`、生产 SQLite 全部沿用同一份，没有复制、没有新建第二套配置。

V1.6 目录未被改动：`INSO_V1.6.exe` 仍是 `9a0cb3d3…2710`。

启动入口：桌面 `INSO V1.7（最新版）.lnk` 指向 `dist\INSO_V1.7\INSO_V1.7.exe`
（由原 V1.6 快捷方式按同长度替换生成，815 B 结构不变）；原 `INSO V1.6（最新版）.lnk`
改名为 `INSO V1.6（旧版，仅回退用）.lnk`，保留可回退但不会再被误点。

## 20. 正常生产启动与业务观察

启动方式：正式生产模式（非 `--safe-preview`、非 `--scoped-start`），
`INSO_V1.7.exe --start-inquiry` —— 该开关就是 GUI「开始运行」按钮调用的同一个 `backend.start()`，
所以业务是"点过开始运行"的状态，不是受限预览。

```
PID 85452  INSO_V1.7  CPU 22.4s  窗口：INSO LEO V1.7 — Procurement Automation Control Center
PID 84368  INSO_V1.7             （watcher，observer.json 已记录 target/observer 对应关系）
runtime-run_id = edc94a2c5c684066ae0b3eea8a3d28a5，fatal.log = 0 字节
```

三个模块都按 900 s 周期跑起来了，且**零故障**：

| 时间 | 模块 | 用时 | 结果 |
|---|---|---|---|
| 21:31:58 | inquiry | 9.6 s | completed，无采购动作（无待处理订单） |
| 21:32:07 | quotation | 77.5 s | 47 条处理完毕，全部为既有的年龄/无新报价类结果 |
| 21:33:29 | tp | 1.2 s | completed，既有 5 条 TP 任务仍为 `MAIL_QUEUED` |
| 21:47:07 | inquiry（第二轮） | 4.1 s | completed，同样无采购动作 |

今日日志里 `ERROR` / `SHEETS_*` / `fault` / `exception` 命中数 **0**；Google Sheets 读取正常
（否则询价模块不会枚举出 47 条历史询价）。

**没有产生任何真实采购**：

| 项 | 值 |
|---|---|
| `workflow_v12_purchase_state` 行数 | 40（与装前备份一致） |
| 最后一条采购 | `inq_17724bfe8d738fdd3bd0f166` / `SAVED` / 2026-11-19 |
| 活动 hold | 3（原样保留，未清未改） |
| open write intents | 0（报告 `NONE_PROVEN`） |

**原因不是故障，是没有合法待处理订单**：`workflow_v12_inquiry_state` 最新状态全是
`PURCHASE_RECORDED` / `HUMAN_COMPLETED`，询价模块两轮都无事可做。
按 Owner 指令"没有合法待处理订单时不制造订单、不重发历史订单"，本轮如实标注
`REAL_PURCHASE_NOT_YET_VERIFIED`。

既有现象（未变、非本次引入，如实记录）：`inq_d65be9df3c7cc40b65cbffaa` 的
`QUOTE_INPUT_WRITE_FAILED` 与 `inq_71f4a2f5ef8678223385b6e2` 的 `UPDATE_RESULT_UNCONFIRMED`
在 11-20 的日志里每一轮都以同样签名出现，属报价输入表的历史条件，不在本次改动范围内。

## 21. 本轮结束时的状态

`V1_7_INSTALLED / PRODUCTION_RUNNING / REAL_PURCHASE_NOT_YET_VERIFIED`

- V1.7 已装进独立目录并正常生产运行；V1.6 目录、回退快照、数据库备份、hold 全部原样保留；
- 正常生产路径不含 AI 录单（源码守卫测试 + 两次真实运行的 AI 请求计数为 0）；
- 真实"保存并发送"与最终业务结果**尚未验证**，等有合法待处理订单时自然发生；
- `main` 仍是 V1.6，`release/previous` 未动，V1.7 未晋升。

---

# 第四阶段：误报"INSO 需要人工验证"导致全局停止（2026-11-22）

Owner 报告：早上报过一次"INSO 需要人工验证"并全局停止；本人到 INSO 看过，**并不需要验证**。

## 22. 现场证据

日志（`dist\INSO_V1.4\runtime\logs\INSO_V1.3.log`）：

```
07:25:47  INFO  scheduled_module=quotation phase=begin            （正常开始）
07:26:53  WARNING ... stage=quotation result=QUOTE_AGE_EXPIRED      （前 47 条照常处理）
07:27:05  INFO  scheduled_module=quotation phase=failed elapsed_s=77.766
07:27:07  WARNING runtime fault reason=INSO_AUTHENTICATION_REQUIRED cause=V12Fault
   ……82.5 分钟无任何调度……
08:49:40  INFO  scheduled_module=inquiry phase=begin                （Owner 重新开始后恢复）
08:49:50  WARNING ... stage=quotation result=QUOTE_AGE_EXPIRED      （同样 47 条，正常读完）
```

三条关键反证：

1. **全程没有任何登录尝试**：`the INSO session is being established by logging in` 与
   `INSO_LOGIN_RETRY_EXHAUSTED` 在日志里命中数为 0。会话守卫根本没有被触发。
2. **恢复后没有登录**：08:49 起直接沿用同一个会话读完了同样的 47 条，结果与故障前一致。
3. **进程从未重启**：PID 85452 自 11-21 13:31 起未变，属"进程内停止 → 重新开始"。

## 23. 根因

`src/inso/quotation_read.py` 把**任何** `SecurityViolation` 都翻译成"登录失效"：

```python
except SecurityViolation:
    raise InsoQuotationAuthenticationError("INSO_AUTHENTICATION_REQUIRED") from None
```

而这条读取路径里的 `SecurityViolation` 全部来自**租约/页面身份**，与登录无关：

- `InsoSessionLease._assert_identity()`：`verified shell page is closed`、`page identity changed`、
  `browser or context is stale`、`session lease is not active`；
- `InsoOperationAccess.operation_page()`：`operation identity is required`。

其中任何一条 → `InsoQuotationAuthenticationError` → `v13_quotation` 抛
`V12Fault(GLOBAL_STOP, "INSO_AUTHENTICATION_REQUIRED")` → 停止整轮，GUI 按
`INSO_AUTHENTICATION_REQUIRED` 显示"INSO 需要人工登录/验证，ERP 会话失效或需要验证码"。
Owner 于是去查了一个并不存在的验证码。

**判定不是"页面出错就不该停"，而是"页面出错不能冒充登录失效"**：假诊断让 Owner 做无效操作，
也让真正的登录问题淹没在假告警里。

## 24. 修复（只改判定与文案，不改安全边界）

1. `quotation_read.py`：按**原因码**区分。只有
   `MANUAL_VERIFICATION_REQUIRED` / `CREDENTIAL_REJECTED` / `AUTHENTICATION_REQUIRED` /
   `SESSION_IDENTITY_UNVERIFIED` 才转成登录失效；其余 `SecurityViolation` 转成
   `InsoDuplicateHistoryError(QUERY_SETTLEMENT_UNCONFIRMED)` —— 走既有的"本次读取未结算、单独重试"通道。
2. `v13_quotation.py`：
   - `_reopen()` 遇到非登录类的 `SecurityViolation` 不再整轮停止，而是丢掉这个租约、走
     `open()` 已有的全新页面路径（这与"菜单丢失"的既有恢复方式一致）；
   - `close()` 无法核验页面时依旧保留该页、依旧停止（页面归属 fail-closed 不变），
     但原因码改为 `INSO_OPERATION_NOT_CLOSED`；
   - `preserve()` 记录保留原因，下一阶段 `open()` 报出**真实**原因，不再一律报登录失效。
3. `fault_diagnostics.py`：新增 `INSO_OPERATION_NOT_CLOSED` 文案 ——
   "INSO 页面无法核验（不是登录问题）…这**不需要**你去做登录或验证码"。

**未改**：真正的挑战/密码被拒仍然全局停止（`test_actual_rfq002_authentication_keeps_human_page_in_v13_cycle`
覆盖 CAPTCHA / 手机验证码 / 设备验证三种）；页面保留策略、写入门禁、UNKNOWN/SENT/hold 一律未动。

测试变化：`test_midquery_session_guard_failure_keeps_existing_owned_page` 原名与断言都固化了
"租约失效=登录失守"这一误判，已改名为
`test_midquery_lost_shell_identity_is_not_reported_as_a_login_problem` 并改断言真实原因码；
新增 4 条读取器分类用例与 1 条"保留页面后下一阶段报页面问题"用例。
