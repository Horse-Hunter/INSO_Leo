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
