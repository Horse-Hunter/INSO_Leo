# RFQ-025 — 最终汇报（2026-11-21）

**状态：`V1_6_PROMOTED_TO_MAIN / V1_7_BASELINE_READY / PASTE_SNIFF_COMPLETE / NO_BUSINESS_EFFECT`**

## 七段式

```text
正在实现什么：
把已验收的 V1.6 升为正式现版本、备好 V1.7 开发基线，并把 INSO 原生"粘贴"录单完整跑通一遍，为下一轮替换 AI 录单做准备。

理想变化是什么：
以后录单不再依赖 AI 识别服务，改用 ERP 自带的粘贴导入，型号/数量/品牌由 ERP 自己解析补编码，流程更稳、外部依赖更少。

以前是什么：
main 还停在历史 V1.1；develop 叫"开发线"却没有 V1.6 的代码；粘贴入口只查到了页面结构，没真正点通过。

现在是什么：
main 已快进到 V1.6；develop 已真正包含 V1.6 源码，可作 V1.7 基线；粘贴录单从打开弹窗到"保存数据"回填表格，已在真实生产环境完整跑通，并且实测证明它不产生任何服务端单据。

做完了什么：
版本晋升、三分支对齐、V1.7 基线、AI 录单调用链梳理、粘贴录单五步真实链路实测、以及一份脱敏证据。业务代码零改动。

测试结果：
粘贴链路是真实跑通的（登录、开单、粘贴、导入、预览、保存数据、关闭），不是静态推断。关键一步"保存数据"用了网络监听实测：没有发出任何写请求，单据号全程为空，事后列表也没有新单。全程没有点"保存"和"保存并发送"。

你接下来需要做什么：
Review RFQ-025；确认后给我第二轮实现指令（起 v17 分支，把 AI 录单换成粘贴）。
```

## 六项汇报（CEO 需要的技术内容）

### 1. V1.6 正式晋升结果与三条长期分支 HEAD

| 分支 | HEAD | 性质 |
|---|---|---|
| `main` | `d954e0a59ca0b31956ad306dca9dab9603acc3f2` | Owner 验收的 V1.6 现版；`be9d0a51..d954e0a5` **纯快进**，未强推 |
| `develop` | 见 `git log develop`（本轮记录提交的 tip；基线合并提交 `d2473a2a`） | V1.7 基线与集成分支；**首次真正含 V1.6 源码** |
| `release/previous` | `d244241eafe564c79812f860b2491c903a4cee1e` | **未改动**，仍为 `NOT_VERIFIED` |

不可变发布记录（annotated tag，已推送）：

- `release/v1.6-official-20261121` → `d954e0a5`（EXE `9a0cb3d3…2710`、清单 `5bd7d7a7…63ff`、审核 RFQ-024）
- `release/v1.1-main-superseded-20261121` → `be9d0a51`（标注"不是已验收的上一正式版"）
- `release/previous-superseded-20261121` → `d244241e`
- `preserve/sheets-v1-local-main-c3a597d9` → `c3a597d9`

**首次对齐 vs 常规晋升（重点）：** 晋升前的 `main` 只是 V1.1 历史指针。
按 BRANCH_POLICY"首次对齐"条款 + Owner"不得冒充上一正式生产版本"的指令，
本轮**没有**执行常规程序的"先把 `release/previous` 改指原 main"，因为那会把 V1.1 伪装成回退基线。
`release/previous` 的 `NOT_VERIFIED` 状态因此如实保留。下一次晋升起，被取代者才是 `d954e0a5`。

本地 `main`（`D:/Program_Leo/INSO_Leo` 工作树，`c3a597d9`）**故意未移动**：该工作树有未提交改动，
移动分支等于改写脏工作树的 HEAD。其 5 个独有提交已在 `origin/backup/sheets-v1-before-baseline-v2`
与 `preserve/` 标签双重留底。

### 2. V1.7 开发基线与计划执行分支

- **基线：`develop`。** 发现并修正一处此前没人注意的事实：`develop` 建于 `9ad9ccb8`（11-14），
  此后只走政策/文档（14 个文档提交），**完全没有 RFQ-017…024 的业务修复**，直接开发 V1.7 会基于旧代码。
  本轮以合并（非重置、非强推）把 V1.6 源码带入；冲突 5 处全为文档/证据，`src/`、`tests/` 零冲突，
  合并后与 `d954e0a5` 的 `src/`、`tests/` **逐字节相同**。
- **计划执行分支：`workbuddy/v17-native-paste`，从 `develop` 起。** 本轮未创建（空分支无意义）。

### 3. 粘贴录单五步实测结果

Owner 停机后，一次会话内完整执行、逐项记录。全程未点 `保存` / `保存并发送`。

| 步 | 实测结果 |
|---|---|
| 1 打开 | 单据工具栏 `iframe#winIframealert_enquiry` → **`button#product_import_`**（文本"粘贴"）。相邻 `button#ai_import_`（"AI录单"）id 不同，不会误点。弹窗 `#winIframe_dialog1` → `product/Import.aspx?BillPage=Enquiry&VendorID=&h=510` |
| 2 填写 | `textarea#pasteData`。`#combox101` = `3`/`竖线('|')`；字段映射 `cmb0=型号`、`cmb1=数量`、`cmb2=品牌`。**全部是默认值，不需要每次设置**；但粘贴必须严格三列。回读与输入完全一致 |
| 3 预览 | 点 `导入`（`#win_btn__dialog11`）→ **恰好 1 次** `POST /services/product/import.ashx?action=PasteImport&VendorID=0&BillPage=Enquiry`。返回 20 列 1 行；同时"保存数据"由禁用转可用。**只切"数据预览"标签不会出数据**——预览是服务端解析结果，与 Owner 描述略有差异，已按实测记录 |
| 4 保存数据 | 点 `#win_btn__dialog12` → **零个非 GET 请求**（网络监听实测）。父表单明细行写入成功：`P1463619` / `TRJC476K016RRJ` / `Kyocera AVX` / `200` |
| 5 衔接 | `btnBack`（`goback()`）关闭表单，未保存、未发送。`保存` 与 `保存并发送` 仍走原有 `#btnSave` / `#btnSave2`，未触碰 |

**关键实测值（直接决定实现写法）：**

- 预览数据源：`layui.table.cache['dg']` → `{PartNo:"TRJC476K016RRJ", Qty:"200", Brand:"Kyocera AVX", ProductID:"P1463619"}`
- **型号逐字节保持**：`PartNo` 与输入完全相同，没有截断、没有转换。
- **ERP 自动补编码**：`ProductID` = `P1463619`，输入里不存在这个值——即"编码/型号"由服务端解析回填。
- **`Qty` 是字符串** `"200"`，不是整数 → 实现必须显式转 `int` 并校验 `> 0`。
- 视觉截断是 CSS 省略；程序核对必须读表格数据，不能读渲染文本。

### 4. "保存数据"的实际行为与副作用边界

- **实际行为：** 把预览表格缓存里的行交回父表单（`returnSet`）、关闭弹窗（`windowsClose`），
  再由关窗回调 `appendRow()` 逐字段写进采购临时询价表单的明细表格。纯浏览器内操作。
- **副作用：实测为零。** 保存前后 `#BillID` 都是空，`#BillNo` 也为空；
  保存期间没有发出任何非 GET 请求；事后只读核对业务询价列表，最新单号仍是
  `XJ-261119-150055`（11-19），**没有 2026-11-21 的新单**。
- **前置闸门：** 未跑过 `导入` 时"保存数据"是禁用的；即使强行调用，ERP 也会弹
  "请先成功导入并预览数据，再保存数据。"——预览核对在机制上无法绕过。
- **结论：** 与现有 AI 录单"保存数据"属同一语义类别（客户端草稿回填），
  既有 INSO 技术契约中"原生保存数据＝客户端草稿环节"的定义**成立**，可安全纳入 V1.7。

**必须避开的同名陷阱（重要）：** 列表页的批量导入弹窗（`innerenquiry/yewuxj/Import.aspx`）标题也叫"粘贴导入"，
但它的"保存数据"绑的是 `Import()`，`$.post(?action=Import)` 且要求服务端返回 `BillID` —— **会在服务端建单**。
V1.7 只允许走单据内的 `product/Import.aspx`。

### 5. 原 AI 录单调用链、最小替换范围、可复用代码

```
build_ai_input(mpn, brand, qty) -> "型号      品牌      数量"（6 空格分隔）
CoordinatorPurchaseDraftWriter.prepare()            [src/launcher/v12_composition.py:302]
  new_draft -> set_customer -> set_quotation_type -> set_purchaser
  -> open_ai_entry()      # button#ai_import_ -> windows('AI智能录单', product/Import_ai.aspx)
  -> set_ai_input()       # textarea#paste-area
  -> run_ai_recognition() # button#ai-recognize  （AI 服务，外部依赖）
  -> read_ai_result()     # #preview-body > tr input[data-f=PartNo|Brand|Qty]
  -> validate_ai_recognition() -> AI_RECOGNIZED（否则 fail-closed）
  -> commit_ai_entry()    # 保存数据 #win_btn__dialog11 -> pasteImport() -> returnSet + ai_appendRow
  -> wait_for_model() / 读 #_id_dg 四列 -> 二次校验 -> PRE_SAVE_READY
下游：save_data(#btnSave, Write Gate) / save_and_send(#btnSave2, Owner 门禁)
      去重、UNKNOWN/SENT、hold、Sheets 回写、通知、TP —— 全部不动
```

**最小替换范围：** 只换 `prepare()` 里的第 5–8 步与两处 AI 预览读取，共 2 个文件
（`src/inso/purchase_writer.py` 增加粘贴面板适配器；`src/launcher/v12_composition.py` 调整步骤序列）。
上游 `build_ai_input` 要改成 `型号|数量|品牌`——**注意顺序也变了**（AI 是 型号·品牌·数量）。

**可直接复用（禁止另建）：** INSO 会话/登录守卫/页面租约、`iframe#winIframealert_enquiry` 解析、
purchaser 多选清空与菜单关闭、`write_safety.py` 的控件语义白名单与门禁、关窗清场、
`v12_phase_a_readonly.py` 的"读 handler 源码判定副作用"范式。

**不构建**第二套 INSO 适配器、浏览器、调度器或账本。

### 6. 尚未验证的事项与真实阻碍

**没有遗留验证缺口。** 首轮标记的六项（真实链路、按钮 id、预览取值路径、型号逐字节、
父表单行值、`import.ashx` 副作用）已全部实测补齐。

刻意没做的只有两件，都不属于"未验证"，而是不在本轮授权范围：

1. **没有点 `保存`（`#btnSave`）与 `保存并发送`（`#btnSave2`）。** 那两步是正式建单与对外发送，
   属真实业务效果，本轮只做嗅探。
2. **没有在 V1.6 运行期间登录。** 登录会改写共享 profile 的 `erp_token`，属生产动作；
   第 1 轮因此只做了只读取证，第 2 轮等你停机后才跑真实链路。

另外两点记录在案：

- 当前生产环境的 `Import_ai.aspx` 已是**新版 AI 识别页**（有"极速识别""载入示例"等控件），
  与代码注释描述的旧版细节不完全一致；`#preview-body`、`#ai-recognize`、`#ai_import_` 仍在，未影响运行。
  替换后这条外部依赖整体消失。
- 你停机后进程并未真正退出（PID 56032/75380 仍在，符合已知"关窗后线程不退出"缺陷）。
  本轮据此确认业务已停（GUI 闲置、CPU 20 秒零增量、日志无新轮次）后才动手，实测期间没有任何新的调度轮次。

## 采集边界声明

本轮在 Windows 现场执行，读到的是真实仓库、真实 EXE 哈希、真实进程与真实 ERP 页面，
并在 Owner 授权下完成了真实点击链路。**没有任何一步是以静态分析冒充运行验证的。**
