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

## 25. 修复后的重建、重装与重启

源码变更 → 必须重建候选，不能拿旧候选冒充。

| 项 | 值 |
|---|---|
| 回归 | `4371 passed / 0 failed / 0 errors / 1 skipped`（4365 + 6 条新用例） |
| 源码 commit | `e0fba99a` |
| EXE | 8,510,928 B / SHA256 `67cede70a38e73796456b143c25d440ce74d85042ab542e30d3e65f6a6e5da05` |
| 文件数 | 2,872 |
| 清单 | `docs/evidence/rfq025/INSO_V1.7-artifact-manifest.sha256`，SHA256 `cd085807aaa08deb4897348316fd3e7fec000222e718de62736b6c0aa8b6f2c0` |
| `--self-check` / `--idle-self-check` | 退出码 0；`gui_rendered: true`，标题含 V1.7 |
| 安装方式 | **就地切换**（同一目录升级，`-PreviousExeName INSO_V1.7.exe`） |
| 安装结果 | `INSTALL_RESULT = PASS`，`installed_exe_sha256 = 67cede70…`，`installed_files_verified = 2872` |
| 回退 | `INSO_V1.7.exe.prev-20261122T063011Z` + `_internal.prev-20261122T063011Z`；另有快照目录 `dist\release-backups\RFQ-025-pre-v17fix-20261122T062633Z`（程序 + 数据库 + 校验报告） |
| 数据库 | `DB_VERIFY_RESULT = PASS`，40 条采购记录，`write_intent_state = NONE_PROVEN`，`event_age_hours = 0.31` |
| 重启 | PID 90384（GUI）+ 90508（watcher），14:31 起正常跑 quotation |

### 顺带修掉的两处跨版本硬编码

装第二遍时暴露的：`backup_running_release.ps1` 把 `INSO_V1.6.exe` 写死，导致对着 V1.7 目录做快照直接报
`No INSO_V1.6.exe`；`verify_database_backup.ps1` 的进程门禁只查 `Name='INSO_V1.6.exe'`，
**会漏掉从本安装跑的 V1.7 进程**——这正是"一个安装被判定为已停止"的假证明。

- 备份脚本改为从目录里读唯一的根级 EXE（多于一个就拒绝），不再假定版本名；
- 数据库校验改为 `Name LIKE 'INSO[_]V%.exe'`，任何版本的残留进程都算"未停止"；
- 停机文案从"INSO_V1.6"改为中性表述，避免再次误导。

安装脚本成功输出里那句"首次启动必须 `--safe-preview`"也一并改成与当前 Owner 指令一致：
从自己的目录正常启动（普通启动即完整生产模式），并且**绝不能与旧安装同时运行**（同一本台账两个调度器）。

---

# 第五阶段：真实成交、CDP 卡死、两处误报修复（2026-11-23）

## 26. 第一笔真实采购成交（V1.7 的端到端验收）

`inq_7bd2f5dbc94f50e27a474821` —— SHAHAB 第 145 行，`AMPLA1004S-R22MT` / `Abracon` / `60`。

它在 11-22 22:18 被 CDP 卡死推迟（见第 27 节），23:04 恢复后自行续跑，23:06 完成。事件链（全部来自台账）：

| 时间（UTC） | 事件 | 含义 |
|---|---|---|
| 15:04:34 | `DUPLICATE_CHECK_CONFIRMED` | 七天重复检查通过 |
| 15:04:34 | `PURCHASE_DRAFT_STARTED` | 建草稿 |
| 15:06:07 | `AI_RECOGNITION_READY` | 预览已核对通过（历史事件名，V1.7 语义为粘贴预览） |
| 15:06:07 | `SAVE_DISPATCH_ARMED` | 提交前检查完成 |
| 15:06:07 | `SAVE_CLICK_COMPLETED` | `#btnSave2`（保存并发送）点击一次 |
| 15:06:14 | `SAVE_OUTCOME_UNKNOWN` | 点击后立即置未知，等待对账 |
| 15:06:16 | `RECONCILIATION_CONFIRMED_SAVED` | **ERP 对账回读确认已保存** |
| 15:06:16 | `PURCHASE_DATA_SAVED` | 业务状态落地 `PURCHASE_RECORDED` |

旁证：

- `workflow_v12_duplicate_results`：`outcome=CONFIRMED`、`repeated=0` —— 没有重复采购；
- `workflow_write_intents`：`GOOGLE_WRITE` 于 15:06:18 建立、15:06:19 `SETTLED` —— **Sheets 回写成功且有确证**；
- `workflow_items`：第 145 行 `status=COMPLETED`，`attempt_count=1`；
- `workflow_v12_purchase_state`：41 条（装前 40 + 这 1 条），`outcome=SAVED`。

**判定：`REAL_PURCHASE_VERIFIED`。** 录单走的是粘贴路径（生产代码里已无 AI 端点，真实运行 AI 请求计数为 0），
保存并发送走的是 `#btnSave2`，不是 `#btnSave`。

## 27. CDP WebSocket 卡死（20:43 → 23:04，2 小时 21 分）

现象：`runtime fault reason=BROWSER_WAITING_RECOVERY` + `workflow step failed at login-sweep-cdp (BrowserBootstrapError)`，
inquiry/quotation 连续 `phase=deferred`，tp 仍照常（不需要浏览器）。

只读探测（与程序同一套检查项）：

| 检查 | 结果 |
|---|---|
| `GET /json/version`、`/json/list` | 正常返回（Chrome/156.0.8078.81） |
| Playwright `connect_over_cdp`，15 s | 超时于 `<ws connecting> ws://127.0.0.1:9222/devtools/browser/39afa3…` |
| 同一连接，60 s | 仍然超时 → 是**卡死**，不是慢 |

结论：Chrome 的 HTTP 调试端点活着，但浏览器级 WebSocket 握手不再被处理。程序按既有设计等待并推迟轮次
（不全局停止、不杀 Chrome、不换 profile），Owner 关闭 Chrome 窗口后 23:04 自动恢复，**订单没有丢**，
恢复后同一单继续跑完并成交。

关于"为什么没有收到告警"：程序确实生成了 `PROGRAM_OPERATION_BLOCKED` 通知，但它的证据里
`active=False`、`recovered_at` 已落地，派发前被判定 `EVENT_NOT_CURRENT` 而抑制。这是**既有策略**
（Browser/CDP 属于等待重试类，恢复后不再外发），本轮未改。代价是这次 2.5 小时无人知晓，
Owner 是自己发现的。是否要把"浏览器通道持续不可用"改成必须外发，属产品决定，留给 Owner。

## 28. 修复一：登录页没加载 ≠ 需要人工验证

11-21 23:27 那条告警的正文里写着 `InsoAuthenticationError(LOGIN_PAGE_UNAVAILABLE)` ——
登录页根本没加载出来，却被写成"ERP 会话失效或需要验证码"。原因在
`src/launcher/v13_quotation.py`：它把**任何** `InsoAuthenticationError` 都包成
`V12Fault(GLOBAL_STOP, INSO_AUTHENTICATION_REQUIRED)`，抢在模块层判定之前。

而模块层本来就会正确分类：`_website_failure` 把 `InsoAuthenticationError` 认成站点 INSO、推迟本轮，
只有 4 个真验证码/凭据码才标记人工处理（`_defer_website_poll`）。修复即让适配器不再抢先：

- 新增 `_session_failure()`：原因码属于 `INSO_LOGIN_VIOLATION_CODES`（与读取器共用同一集合）→ 全局停止；
  其余（`LOGIN_PAGE_UNAVAILABLE` 等环境类）→ 原样抛给模块层，走"等待 INSO 恢复"。
- `open()` / `_reopen()` 都改走这个判定。

测试：`test_a_login_page_that_did_not_load_is_not_a_human_challenge`（环境类不外发、不保护页面）+
4 个真验证码码参数化的 `test_a_real_login_verdict_still_stops_the_run`。

## 29. 修复二：header 行的"已跳过"原因每轮重复写（499 条）

`inq_988613911e961720d88cff52` 是 `2026` 表第 146 行，型号字段的值就是表头字 `MPN` ——
一行被误当成订单接纳的表头。`v12_flow.py` 的分支会把它标成 `INVALID_INPUT_SKIPPED` 并记录
`HUMAN_RESOLUTION_RECORDED`，注释写着"records the real reason once"。

问题：`INVALID_INPUT_SKIPPED` 本身就在 `_OWNER_RECONCILABLE_STATES` 里，所以**下一轮又满足条件**，
再记一次、再置一次 —— 从 2026-10-07 到 2026-11-23 累计 **499 条**同样的事件，GUI 上"人工处理已记录"
每隔 15 分钟重复出现一次。这既污染台账，也让真正的"人工已处理"无法辨认。

修复：该分支只在状态还不是 `INVALID_INPUT_SKIPPED` 时写入状态与事件；数据质量告警的清理
本身幂等，仍然每轮执行（后续新告警仍能被清掉）。

测试：扩展 `test_header_row_recovery_only_clears_data_quality_alerts`，再跑两轮不得新增事件。
反证：移除守卫后该断言以 `3 != 1` 失败，说明它不是同义反复。

生产验证：新构建 11:47 跑完第一轮后，该单事件数仍为 **499**，不再增长。

## 30. 回归与候选（源码变更后重建）

| 项 | 值 |
|---|---|
| 全量回归 | `4376 passed / 0 failed / 0 errors / 1 skipped in 611.81 s` |
| 源码 commit | `6a5104cf` |
| EXE | 8,511,663 B / SHA256 `6674f37b55a5410ed853ff9883815769a2175b109271edaca26f9ea211d1dc03` |
| 文件数 | 2,872（无 `runtime/`） |
| 清单 | `docs/evidence/rfq025/INSO_V1.7-artifact-manifest.sha256`，SHA256 `2291898ca1990ac5e372f8d4b7f3971f8472e31b7c941b7f050e016822d177fb` |
| 候选校验 | `VERIFY_RESULT = PASS`（missing 0 / hash_mismatch 0 / unexpected 0） |
| `--self-check` | 退出码 0 |
| `--idle-self-check` | 退出码 0，`gui_rendered: true`，标题含 V1.7 |

`ruff check src tests` 仍只有基准的 3 条既有 F811（`test_google_quote_update.py`）。

## 31. 停机、重装、重启

停机前：`open_write_intents = 0`、`active_alerts = 0`、当日无新增采购行、`-wal` 不存在（已 checkpoint）。

| 项 | 值 |
|---|---|
| 回退快照 | `dist\release-backups\RFQ-025-pre-r5-20261123T034455Z`（`BACKUP_RESULT = PASS`，`exe_sha256 = 67cede70…`） |
| 数据库 | 同目录 `database\workflow.sqlite3`，`DB_VERIFY_RESULT = PASS`，`purchase_rows = 41`，`write_intent_state = NONE_PROVEN`，`event_age_hours = 0.39` |
| 安装 | 就地切换 `INSTALL_RESULT = PASS`，`installed_exe_sha256 = 6674f37b…`，`installed_files_verified = 2872` |
| 旧版留存 | `INSO_V1.7.exe.prev-20261123T034618Z` + `_internal.prev-20261123T034618Z` |
| 重启 | PID 102276（GUI）+ 102836（watcher），11:47 起 enquiry/quotation/tp 各跑完一轮，**零 ERROR** |

V1.6 目录仍未动（`9a0cb3d3…2710`）；`runtime` 仍是 Junction → `dist\INSO_V1.4\runtime`。

### 一处如实记录的观察

上一轮运行在 11:22:21 完成 inquiry 后不再产生任何轮次：按 900 s 周期本该在 11:37 有一轮，实际到 11:44
停机时仍无。GUI 存活、CPU 只有事件循环（约 1 s/分钟）、无 `runtime fault`、无 `ERROR`、事件流无 `stop` 记录。因无在途写入，按最保守方式直接停机重装。
新构建自 11:47 起三轮正常。**若同样现象在新构建上再出现，需要单独排查调度线程是否被静默挂起**，
本轮没有证据判定是人为停止还是程序侧问题，故只记录不结论。

---

# 第六阶段：浏览器通道持续受阻改为一封通知（2026-11-23，Owner 决定）

Owner 指令：第五阶段汇报中"浏览器卡死 2 小时 21 分无人知晓"一条**同意改**；V1.7 暂不晋升 `main`。

## 32. 为什么原来一定不会发

三条既有规则叠在一起，结果是"永远不发"：

1. `_notify_runtime_fault` 把 `*_WAITING_RECOVERY` 归为 `persistent_stop`，证据里
   `needs_owner = reason.endswith("OUTAGE_THREE_HOURS")` —— 即只有升到三小时才需要人；
2. 而 `_defer_website_poll` 与 `_runtime_error` 两处都显式写着 `site != "Browser/CDP"`，
   **Browser/CDP 被有意排除在三小时升级之外**（它是等待重试类，不该按三小时算）；
3. `notification_review.review_reason` 的第一道通用门槛要求 `active / current_business /
   needs_owner / verified` 全为真，`needs_owner=False` 直接判 `EVENT_NOT_CURRENT`。

所以浏览器通道卡住时，告警永远不会进入可发送状态。11-22 那次的证据里清楚地写着
`needs_owner=False`、`completed_cycles=2`、`recovered_at` 已落地 —— 三个条件都指向"不发"。

## 33. 改法（只动 Browser/CDP，不动 Google）

| 位置 | 改动 |
|---|---|
| `backend._notify_runtime_fault` | `needs_owner` 增加 Browser/CDP 分支：该站点不再等三小时 |
| 同上 | 该站点的 `action` 文案改为"请关闭该 Chrome 的窗口（不必强杀进程，程序会自行重连），不要更换浏览器配置或另开 Chrome" |
| `fault_diagnostics.BROWSER_WAITING_RECOVERY` | 原文案第 3 条是"不要关闭该 Chrome"，与实际有效处置相反，改为"关闭窗口、保留进程、不必重启程序" |

**阈值没有放宽到"一有阻塞就发"**：通知仍要过 `review_reason` 的
`retries_exhausted` 与 `completed_cycles >= 3`（三个已完成的轮询周期，约 45 分钟），
且派发时要求该站点仍在停摆集合里 —— 也就是说：

- 只卡一两轮就自己好了 → 不发；
- 卡到第 3 轮 → 发一封（收件人只有 Owner `linan229@qq.com`）；
- 发之前已经恢复 → 取消，不补发历史。

**没有改的**：Google 的等待类故障仍按三小时规则（有用例守住）；`persistent_stop` 仍需绑定一张
在途未发订单作为受影响业务证据；收件人策略、去重键、`SENT/UNKNOWN` 保护一律未动。

## 34. 测试与反证

新增 4 条（`tests/launcher/test_runtime_safety_notice.py`，全部走真实后端 + 假 SMTP）：

| 用例 | 断言 |
|---|---|
| `test_a_persistent_browser_block_is_reported_after_three_cycles` | 第 3 轮发 1 封，收件人 Owner，正文含"关闭该 Chrome 的窗口" |
| `test_a_browser_block_that_clears_within_two_cycles_stays_silent` | 两轮内恢复 → 0 封 |
| `test_a_recovered_browser_block_does_not_mail_after_the_fact` | 派发前已恢复 → 0 封 |
| `test_google_waits_keep_their_three_hour_rule` | 同样条件下 Google 仍 0 封（作用域没被放宽） |

反证：把 `needs_owner` 里的 Browser/CDP 分支去掉，第一条立即以 `0 == 1` 失败 —— 说明测试真的在守这行。

## 35. 回归、重建、重装、重启（本轮）

| 项 | 值 |
|---|---|
| 全量回归 | `4380 passed / 0 failed / 0 errors / 1 skipped in 598 s`（4381 collected） |
| `ruff check src tests` | 基准的 3 条既有 F811 |
| 源码 commit | `871419ba` |
| EXE | 8,511,862 B / SHA256 `c796b705a9fbae59314af59c846a290550349b0fb9760689c11326783174ff6e` |
| 文件数 | 2,872（无 `runtime/`） |
| 清单 | `docs/evidence/rfq025/INSO_V1.7-artifact-manifest.sha256`，SHA256 `5e2dfe9a2f472e913a0445bacfd5235d1e2fae642875c6bc2b3ca7c503ca1e4e` |
| 候选校验 | `VERIFY_RESULT = PASS`（missing 0 / hash_mismatch 0 / unexpected 0） |
| `--self-check` / `--idle-self-check` | 均退出码 0，`gui_rendered: true` |
| 停机前 | `open_write_intents = 0`、`active_alerts = 0`、采购行 41（与上一次一致）、`-wal` 不存在 |
| 回退快照 | `dist\release-backups\RFQ-025-pre-r6-20261123T082453Z`（`BACKUP_RESULT = PASS`，`exe_sha256 = 6674f37b…`） |
| 数据库 | 同目录 `database\workflow.sqlite3`，`DB_VERIFY_RESULT = PASS`，`purchase_rows = 41`，`event_age_hours = 5.06` |
| 安装 | 就地切换 `INSTALL_RESULT = PASS`，`installed_exe_sha256 = c796b705…`，`installed_files_verified = 2872` |
| 旧版留存 | `INSO_V1.7.exe.prev-20261123T082603Z` + `_internal.prev-20261123T082603Z` |
| 重启 | PID 101176（GUI）+ 100144（watcher），16:26 起 inquiry 10 s / quotation 75 s / tp 3 s 完成，零 ERROR |

### 附：这一轮之前那段运行的观察结果

上一版（`6674f37b`）在 11:47–16:24 之间持续运行：inquiry / quotation / tp 按 900 s 正常轮转，
**零 ERROR、零 runtime fault**；`inq_9886…` 的事件数始终是 499（header 行重复写已根治）；
采购行仍 41、open write intents 0、活动告警 0。也就是说 11:22 那次"22 分钟无轮次"没有复现。

---

# 第七阶段：CEO Review 两处边界修复（2026-11-23 晚）

CEO Review 结论：`CHANGES_REQUESTED`，只修两个实际边界，不重复开发、不回滚运行中的 V1.7。

## 36. 边界一：阈值改为"同一次故障的持续时长

**问题（属实）**：`completed_cycles` 收集的是 `self._cycle_id`，而 inquiry 与 quotation 是**不同的 cycle id**。
同一刻钟里两个模块各失败一次，就会贡献两条不同的 occurrence，`completed_cycles` 迅速到 3 ——
原本想要"连续三轮 ≈ 45 分钟"，实际可能 15~20 分钟就触发。

**改法**：

- `_notify_runtime_fault` 把该站点的**故障起始时刻**写进证据：`blocked_since`（来自 `_site_fault_since`，
  恢复时会被清掉，所以它是"这一次故障"的起点，不是历史）。
- 派发时（`_review_current_mail`）比较 `now - blocked_since >= 45 分钟`（常量
  `_BROWSER_BLOCK_NOTICE_AFTER`）；不满足则 `CURRENT_REVIEW_PENDING`（worker 会 `defer` 重试，不是永久抑制）。
- `observe_incident` 在事件仍 active 时**继承上一条的 `blocked_since`**，所以跨重启也是量故障本身，
  而不是量"本次进程启动以来"。

效果：两个模块同时失败不再提前凑数；卡满 45 分钟才发。

## 37. 边界二：不再依赖一张待采购订单

**问题（属实）**：`persistent_stop` 的证据必须绑定一张 QUEUED/RETRY_WAIT/RESEARCHING 且源表 `未发` 的订单。
浏览器卡死时如果只有报价任务、或根本没有待采购订单，`proof` 为 `None` —— 一封也发不出。

**改法**：Browser/CDP 改用**程序级**证据，不再找订单：

```
category = "resource_stop"
module = "Browser/CDP"
reason_code = "PROGRAM_OPERATION_BLOCKED"
blocked_since = <故障起始>
（无 inquiry_id）
```

- 走的仍是 `notify_runtime_fault` → 同一个 `workflow_v12_notification_commands` 账本、同一套 incident 去重、
  同一个 Owner 收件人（`linan229@qq.com`）；**没有第二套通知系统**。
- `notification_review.review_reason` 新增 `resource_stop` 分支（在"订单年龄"那道门前，因为程序级事件没有
  `inquiry_day`，不该按订单过期处理）。
- `_review_current_mail` 新增同名分支：要求该站点仍在停摆集合、时长 ≥ 45 分钟、收件人只有 Owner、无订单号。
- Google 保持原样：仍然是有订单绑定的 `persistent_stop` + 三小时规则，未放宽。

生产表 `inquiry_id` 本就可空（现存 106 条程序级通知），无需迁移。

## 38. 保持不变的约束

| 约束 | 怎么保证 |
|---|---|
| 只通知一次 | 同一 incident 行 + `SENT` 不可变（`_legacy_notice_protected`）；用例第 4 次观察仍只有 1 封 |
| 恢复后取消 | 派发时要求站点仍在 `_site_outages`；用例覆盖 |
| Google 三小时不变 | 有专门用例：同样条件下 Google 仍 0 封 |
| SENT/UNKNOWN 保护 | 未动 |
| 关窗建议不外扩 | 该文案只出现在 Browser/CDP 的证据 `action` 与 `BROWSER_WAITING_RECOVERY` 诊断条目；其他页面错误文案未动 |

## 39. 测试（可控时钟）与反证

测试全部用同一个可控时钟：后端 `utc_now`、证据 `at`、SMTP 传输三处读同一个 `_Clock`，
避免"证据时间在未来 → 传输层判永久失败"这种伪失败。

| 用例 | 断言 |
|---|---|
| `test_a_browser_block_is_reported_once_the_outage_passes_45_minutes` | 0/15/30 分钟 0 封；46 分钟 1 封；61 分钟仍 1 封 |
| `test_two_modules_failing_in_the_same_window_do_not_shorten_the_threshold` | 0/5/10 分钟三次不同 cycle id → 0 封；46 分钟 → 1 封 |
| `test_a_browser_block_with_no_order_at_all_still_reports` | 空账本（无任何工作项）+ 46 分钟 → 1 封 |
| `test_a_recovered_browser_block_does_not_mail_after_the_fact` | 派发前恢复 → 0 封 |
| `test_a_restarted_outage_clock_earns_its_own_45_minutes` | 新故障起点 +10 分钟 → 不发 |
| `test_google_waits_keep_their_three_hour_rule` | Google 90 分钟 + 三轮 → 0 封 |

反证（各做一次，确认测试真的守在这两行上）：

- 关掉时长判断 → 前两条立即失败（提前发）；
- 把 Browser/CDP 退回"必须找订单" → 空账本条与 45 分钟条等 4 条失败。

## 40. 回归、重建、重装、重启

| 项 | 值 |
|---|---|
| 全量回归 | `4382 passed / 0 failed / 0 errors / 1 skipped in 596 s`（4383 collected） |
| 定向 | `test_runtime_safety_notice` 17、`test_fault_diagnostics`、`test_rfq016_regressions` 共 121 通过 |
| `ruff check src tests` | 基准的 3 条既有 F811 |
| 源码 commit | `e59ca657` |
| EXE | 8,512,677 B / SHA256 `a5b9e49801f7ff4afca8f0d0e749da669cdcc1f25cd32062311937e05ba22dc5` |
| 清单 | SHA256 `845fe377ffc96240434033e3644fab348e54cee9d4e7312f267a69a71d5ed79c`（2,872 行） |
| 候选校验 / 自检 | `VERIFY_RESULT = PASS`；`--self-check`、`--idle-self-check` 均 0，`gui_rendered: true` |
| 停机前 | `-wal` 存在（强停），先 `wal_checkpoint(TRUNCATE)` + `integrity_check = ok` 再备份 |
| 回退快照 | `dist\release-backups\RFQ-025-pre-r7-20261123T130656Z`（程序 + 库，`DB_VERIFY_RESULT = PASS`，41 行） |
| 安装 | 就地切换 `INSTALL_RESULT = PASS`，2,872 文件逐项复核 |
| 旧版留存 | `INSO_V1.7.exe.prev-20261123T130811Z` |
| 重启 | PID 101212（GUI）+ 104084（watcher），21:08:47 起 |

### 重启后现场：Google 走代理 502（与本次改动无关）

```
21:11 inquiry  defer（SOURCE_MAIN_SHEET_READ_DEFERRED）
21:13 GOOGLE_WAITING_RECOVERY（GoogleSheetsReadUnavailable <- TimeoutError）
21:15 quotation defer
21:15 tp 照常
```

同机复测（程序同款 urllib）：ERP `https://yingsuo.alperp.cn` **200 / 0.2 s**；
`https://sheets.googleapis.com` **URLError: Tunnel connection failed: 502 Bad Gateway**（走 7890 与直连都一样）。
即：Clash 当前节点的 Google 隧道失效，百度 200、ERP 200。程序按 Owner 规则处理（有界重试、隔离、不全局停止、
不发技术邮件），inquiry/quotation 本轮推迟，tp 不受影响。

这不是本次改动引入的：上一版在 16:26–21:03 期间零 ERROR，说明该时段 Google 通路正常；
21:11 起代理隧道开始 502，属运行环境。

---

# 第八阶段：25 小时静默停摆的根因与修复（2026-11-25）

Owner 报告：程序停了一整天没人知道，也没有邮件。

## 41. 现场

| 项 | 实测 |
|---|---|
| 停机时刻 | 2026-11-24 20:52:26（`quotation phase=failed` 之后日志再无输出） |
| Owner 发现 | 2026-11-25 22:13（**25 小时 21 分**无人知晓） |
| GUI 状态 | "采购模块暂停"，异常列表首条「未分类故障（V13_INTERNAL_FAILURE）」，原始异常 `InsoAuthenticationError(AUTHENTICATED_SHELL_UNAVAILABLE)` |
| 通知 | **存在一条记录，但被抑制**：`suppression_reason = RUNTIME_STOP_UNVERIFIED`，收件人 `SUPPRESSED`，`attempts = 0` |

进程一直活着（只是业务停止），所以"看进程还在"并不能发现问题。

## 42. 根因一：页面失败被当成全局停止

`InsoAuthenticationError` 继承 `SecurityViolation`；`_run_independent_job_scoped` 的失败边界对
**任何** `SecurityViolation` 直接 `raise` → `_runtime_error` → 停止共享业务。

而 `AUTHENTICATED_SHELL_UNAVAILABLE` 的含义是"**登录后的外壳页没拿到**"，与挑战码无关。
（11-24 的调用链是报价适配器的兜底 `except Exception` 把它包成 `V12Fault(GLOBAL_STOP,
"V13_INTERNAL_FAILURE")`，`from None` 清掉 `__cause__`，只剩 `__context__`。）

修复：边界只对 4 个真人码停止 —— `MANUAL_VERIFICATION_REQUIRED` / `CREDENTIAL_REJECTED` /
`AUTHENTICATION_REQUIRED` / `SESSION_IDENTITY_UNVERIFIED`；页面/连接族
（`LOGIN_PAGE_UNAVAILABLE`、`AUTHENTICATED_SHELL_UNAVAILABLE`、`BROWSER_TIMEOUT`、
`INSO_LOGIN_RETRY_EXHAUSTED`）交给既有的站点推迟路径（有界退避，3 小时才升级为暂停）。

**生产验证**：23:05 同一个 INSO 失败再次出现 —— 这次是
`runtime fault reason=INSO_WAITING_RECOVERY` + `quotation phase=deferred`，`tp` 照常，
程序没有停。修复前，这一条就是 25 小时停摆的起点。

## 43. 根因二：停机邮件自己不合规

停机的证据里 `actual_stop_reason` 兜底写死 `"V12_INTERNAL_FAILURE"`；通知审查要求该字段匹配
`[A-Z_]{1,64}` —— **它含数字，匹配不上**，于是永远 `RUNTIME_STOP_UNVERIFIED`。
11-14 那条 `V12_INTERNAL_FAILURE` 的历史记录也是同样被抑制的，说明这个坑从 11-14 就在。

修复：
- 兜底码改为 `INTERNAL_FAILURE_UNCLASSIFIED`（合规、且诚实地说"未归类"）；
- 当包装码本身无法记录（如 `V13_INTERNAL_FAILURE`）时，**从原因链取真实原因码**，
  本次会记成 `AUTHENTICATED_SHELL_UNAVAILABLE`，邮件直接指向页面问题而不是"内部故障"。

## 44. 根因三：INSO 受阻在"没有待采购订单"时不通知

11-25 22:42 的 INSO 推迟期间，账本里没有 QUEUED 订单，`persistent_stop` 证据建不起来，
一条通知都不产生 —— 浏览器通道已在 11-23 补过这条，ERP 通道是同一个缺口。

修复：INSO 在找不到绑定订单时退化到**程序级** `resource_stop` 证据（45 分钟、无订单也发、
每轮故障只发一次、派发前恢复则取消、收件人仅 Owner）；有订单时仍走原来的 `persistent_stop`。
Google 未动（仍是订单绑定 + 三小时规则）。

**生产验证**（23:05:02）：

```
subject = 【需要处理】INSO业务持续受阻
category = resource_stop, module = INSO, blocked_since = 23:05:02, needs_owner = true
suppression_reason = CURRENT_REVIEW_PENDING   ← 正在等 45 分钟，不是不发
recipient = linan229@qq.com  OPERATIONAL_PENDING
```

## 45. 测试、反证、回归、构建

| 项 | 值 |
|---|---|
| 新增测试 | 11 条分类（4 真人码仍停、4 瞬时码不停、无关停机不受影响、原因码从链上取、兜底码合规）+ 5 条通知（未归类停机必发、链上真实码出现在正文、INSO 无订单 46 分钟发一封、30 分钟不发、不发第二次） |
| 反证一 | 兜底码改回 `V12_INTERNAL_FAILURE` → 未归类停机那封立刻 0 封 |
| 反证二 | 关掉 INSO 程序级退化 → 空账本两条立刻失败 |
| 全量回归 | `4398 passed / 0 failed / 0 errors / 1 skipped in 610 s` |
| `ruff` | 基准的 3 条既有 F811 |
| 源码 commit | `75ba2dd4`（其后仅文档） |
| EXE | 8,514,010 B / `4f3f86ba2956eb7a2964a7bf0d905d041b7abfc0844ecc3ecbc842a745164f80` |
| 清单 | `18b08d7631507e6bc578533c59d3767a110997c2afca332fd9ba2d2aa3ae90`（2,872 行） |
| 安装 | 就地切换 `INSTALL_RESULT = PASS`，2,872 文件；旧版 `.prev-20261125T150205Z` |
| 回退 | `dist\release-backups\RFQ-025-pre-r9-20261125T150104Z`（程序 + 库，`DB_VERIFY_RESULT = PASS`，41 条采购） |
| 重启 | PID 140236（GUI）+ 141460（watcher），23:02 起 |

## 46. 23:15 的现场补充：ERP 会话已过期

只读核对（python urllib，与程序同款）：

```
GET .../InnerEnquiry/YeWuXJ/List.aspx
  200 -> https://yingsuo.alperp.cn/home/checking?gourl=%2Fskins%2Fetaoerp%2F...
  页面含 login.aspx，不含 _id_dg / DetailFieldValue / select_btns
```

即：ERP 会话已失效，列表页被重定向去登录。程序每轮都在重试（`force_login=True`），目前拿到的是
`INSO_WAITING_RECOVERY`（页面/会话未能证明），不是挑战码，所以它推迟而不是停。

**给 Owner 的直接处置**：在那台机器上用程序专属的 Chrome 登录一次 INSO（账号已保存），
下一轮会自己继续；若登录时要求验证码，那才是真正需要本人完成的一步。

**已知诊断缺口（本轮未改，留待下一轮）**：报价适配器的兜底 `except Exception` 用
`from None` 把真实异常藏在 `__context__`，所以在"推迟"路径上界面只能看到
`INSO_WAITING_RECOVERY`，看不到底层是登录页、超时还是凭据。停机路径本轮已能取到真实原因码
（见第 43 节），推迟路径还没有。今晚不再重建，先让 45 分钟的通知在真实环境里发出去。

## 47. 45 分钟通知的真实验证（23:50:04）

```
created 2026-11-25T15:05:02Z  subject 【需要处理】INSO业务持续受阻
  before: suppression_reason = CURRENT_REVIEW_PENDING, recipient OPERATIONAL_PENDING, attempts 0
  after : suppression_reason = None, recipient SENT / NOTIFICATION_SENT, attempts 1, at 15:50:04Z
```

即：从故障起点算起**整 45 分钟**才发出，只发一次，收件人只有 Owner。旧逻辑下这条要么根本不存在（无待采购订单），
要么被 `RUNTIME_STOP_UNVERIFIED` 抑制。

## 48. 顺带发现的两个"又会让你蒙在鼓里"的问题（今晚未改，留待下一轮）

1. **标签误导。** 同一轮登录保活把 INSO 判成 `SiteLoginOutcome.NO_CREDENTIAL`，界面显示
   "**缺少登录凭据**"。但底层原因是 `AUTHENTICATED_SHELL_UNAVAILABLE`（外壳页没拿到），
   被 `_NO_CREDENTIAL_CODES` 这批码"因为名字里有 AUTHENTIC"归进去的。它不是"没配账号"，
   是"登录后的页面没证明出来"。这句提示会把人引向错误的方向。
2. **保活通知被吞。** 两条 `网站登录保活异常`（Findchips 登录失败、INSO ERP 缺凭据）在账本里
   `suppression_reason = EVIDENCE_MISSING`，`review_json` 为空 —— 也就是这条路径压根不带证据，
   按"无证据不外发"的规则永远发不出去。

## 49. 当前 ERP 状况与处置（23:52 只读核对）

```
GET .../InnerEnquiry/YeWuXJ/List.aspx -> 200 -> /home/checking?gourl=...
页面含 login.aspx，不含 _id_dg / DetailFieldValue / select_btns
```

ERP 会话已失效，列表页被要求登录；程序每轮重试但拿不到外壳页，所以持续 `INSO_WAITING_RECOVERY`。
**处置**：在那台机器上用程序专属 Chrome 登录一次 INSO。登录后下一轮会自动继续；
若登录要求验证码，那才是真正需要本人完成的一步（届时会按 `MANUAL_VERIFICATION_REQUIRED` 立即发信）。
