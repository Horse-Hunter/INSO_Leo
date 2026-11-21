# RFQ-025 — 最终汇报（第一轮，2026-11-21）

**状态：`V1_6_PROMOTED_TO_MAIN / V1_7_BASELINE_READY / PASTE_SNIFF_PARTIAL / NO_BUSINESS_EFFECT`**

## 七段式

```text
正在实现什么：
把已验收的 V1.6 升为正式现版本、备好 V1.7 开发基线，并查清 INSO 原生"粘贴"录单的页面行为，为下一轮替换 AI 录单做准备。

理想变化是什么：
以后录单不再依赖 AI 识别服务，改用 ERP 自带的粘贴导入，型号/数量/品牌由 ERP 自己解析补编码，流程更稳、更少外部依赖。

以前是什么：
main 还停在历史 V1.1；develop 虽然叫"开发线"但根本没有 V1.6 的代码；粘贴入口从未查过，只知道"AI录单"。

现在是什么：
main 已快进到 V1.6（be9d0a51 → d954e0a5），develop 已真正包含 V1.6 源码可作为 V1.7 基线，晋升前的所有分针都有不可变标签留底。粘贴录单的按钮位置、字段顺序、分隔符、预览来源、"保存数据"到底做了什么，都已查清；但"真人点一遍"这一步没做完，因为它需要登录 ERP，本轮没有登录授权。

做完了什么：
版本晋升、三分支对齐、V1.7 基线、AI 录单调用链梳理、粘贴录单五步的页面与脚本级取证、以及一份脱敏证据。没有改任何业务代码。

测试结果：
未做功能测试（本轮不含实现）。已核对：V1.6 的 EXE 与清单哈希和 Owner 给的一致；晋升是纯快进未强推；合并后源码与原分支逐字节相同；嗅探期间生产程序照常完成业务轮次、零新增故障、进程未变。真实点击链路未验证。

你接下来需要做什么：
Review RFQ-025，并给一次"允许登录 INSO 做只读补测"或"进维护窗口"的授权，第二轮才能把剩下六项验证完并开始实现。
```

## 六项汇报（CEO 需要的技术内容）

### 1. V1.6 正式晋升结果与三条长期分支 HEAD

| 分支 | HEAD | 性质 |
|---|---|---|
| `main` | `d954e0a59ca0b31956ad306dca9dab9603acc3f2` | Owner 验收的 V1.6 现版；`be9d0a51..d954e0a5` **纯快进**，未强推 |
| `develop` | `143fdadcbc52e72476650fffec15c90fd824ede1` | V1.7 基线与集成分支；含 V1.6 源码（合并提交 `d2473a2a` + 政策同步 `143fdadc`） |
| `release/previous` | `d244241eafe564c79812f860b2491c903a4cee1e` | **未改动**，仍为 `NOT_VERIFIED` |

不可变发布记录（annotated tag，已推送）：

- `release/v1.6-official-20261121` → `d954e0a5`（EXE `9a0cb3d3…2710`、清单 `5bd7d7a7…63ff`、审核 RFQ-024）
- `release/v1.1-main-superseded-20261121` → `be9d0a51`（标注"不是已验收的上一正式版"）
- `release/previous-superseded-20261121` → `d244241e`
- `preserve/sheets-v1-local-main-c3a597d9` → `c3a597d9`

**首次对齐 vs 常规晋升的处理差异（重点）：** 晋升前的 `main` 只是 V1.1 历史指针。
按 BRANCH_POLICY"首次对齐"条款 + Owner"不得冒充上一正式生产版本"的指令，
本轮**没有**执行常规程序的"先把 `release/previous` 改指原 main"，
因为那会把 V1.1 伪装成回退基线。可证的运行级回退材料（上一装机版 EXE `fa7a8544…` / 源码 `64d3ec2c`，
实物 `dist/INSO_V1.6/INSO_V1.6.exe.prev-20261120T065005Z`）已在文档中记录，但同样不宣称是"正式旧版"。
`release/previous` 的 `NOT_VERIFIED` 状态因此如实保留，未伪造三分支形式。

另：本地 `main` 分支（`D:/Program_Leo/INSO_Leo` 工作树，`c3a597d9`）**故意未移动** ——
该工作树有未提交改动，移动分支等于改写脏工作树的 HEAD。其中 5 个该线独有提交已在
`origin/backup/sheets-v1-before-baseline-v2` 与 `preserve/` 标签双重留底。

### 2. V1.7 开发基线与计划执行分支

- **基线：`develop` @ `143fdadc`。**
  发现并修正了一处此前没人注意的事实：`develop` 建于 `9ad9ccb8`（11-14），此后只走政策/文档
  （14 个文档提交），**完全没有 RFQ-017…024 的业务修复**，直接拿来开发 V1.7 会基于 11-14 的旧代码。
  本轮以合并（非重置、非强推）把 V1.6 源码带入；冲突 5 处全为文档/证据，`src/`、`tests/` 零冲突，
  合并后与 `d954e0a5` 的 `src/`、`tests/` **逐字节相同**。
- **计划执行分支：`workbuddy/v17-native-paste`，从 `develop` 起。** 本轮未创建（空分支无意义），
  下一轮第一步创建。

### 3. 粘贴录单各步骤的嗅探结果

| 步 | 结果 | 证据等级 |
|---|---|---|
| 1 打开粘贴录单 | 单据内 `iframe#winIframealert_enquiry` → **`button#product_import_`**（文本恰为"粘贴"，唯一/可见/可用）。相邻的 `button#ai_import_`（"AI录单"）id 不同，不会误点。打开的是同一个 `windows()` 框架弹窗，标题"粘贴导入"，1050×600，内容页 `product/Import.aspx?BillPage=…&VendorID=…` | 实读 DOM + 客户端源码 |
| 2 填写粘贴数据 | 文本框 `textarea#pasteData`。字段映射 `#cmb0..cmb24` **默认前三位就是 型号/数量/品牌**；分隔符 `#combox101` 值 `3` = `竖线('|')`。**两者都是固定默认值，不需要每次设置**（但可显式校验一次）。注意：粘贴必须**严格三列**，第 4 列起会被当品名/编码 | 实读 DOM |
| 3 数据预览 | 标签 `li#tabs_li2` → `div#tabs_2`，表格容器 `div#dg_div` / `div#import_div`。**预览行不是本地算的**：`导入`（`pasteImport(0)`）POST `/services/product/import.ashx?action=PasteImport`，返回行并置 `importPreviewReady`、启用"保存数据"、自动切到预览标签。只切标签不会出数据 | 源码级确定；真实取值路径未验证 |
| 4 保存数据 | `pasteImport(1)`：**纯客户端** —— `returnSet(DetailData)` + `windowsClose()`，行取自 `table.cache['dg']`，再由关窗回调 `appendRow()` 写进父表单表格。无 AJAX、无 `BillID`、不发采购 | 源码级确定 |
| 5 衔接 | `appendRow()` 写入后，父表单的 `#btnSave` / `#btnSave2` 与后续一切不变；本轮未点"保存并发送" | 未点 |

**预览截断：** Owner 截图里的 `TRJC476K01...` 是单元格宽度省略，真实值在表格数据里。
程序核对必须读数据源（`table.cache['dg']`），不能读渲染文本 —— 否则会把视觉截断误判成型号错误。

**必须避开的同名陷阱：** 列表页的批量导入（`innerenquiry/yewuxj/Import.aspx`）标题也叫"粘贴导入"，
但它的"保存数据"绑 `Import()`，`$.post(?action=Import)` 且要求返回 `BillID` —— **会在服务端建单**。
V1.7 只允许走单据内的 `product/Import.aspx`。

### 4. "保存数据"的实际行为与副作用边界

- **实际行为：** 把预览表格当前缓存的行交回父表单，关闭弹窗，由 `appendRow()` 逐字段写进
  采购临时询价表单的明细表格（纯浏览器内操作）。
- **副作用边界：无外部持久化、无采购发送、无 IM 通知、不产生 `BillID`。**
- **前置闸门：** `if (!importPreviewReady)` 直接弹"请先成功导入并预览数据，再保存数据。"
  → "预览核对"在机制上不可能被绕过。
- **结论：** 与现有 AI 录单弹窗的"保存数据"属同一语义类别（客户端草稿回填），
  因此已有 INSO 技术契约中"原生保存数据＝客户端草稿环节"的定义**成立**。
- **但本轮仍未点击它。** 原因是它需要登录后的弹窗才能出现，而不是因为它有风险。
  下一轮补齐一次真实点击即可结案。

### 5. 原 AI 录单调用链、最小替换范围、可复用代码

调用链（单一适配器 `src/inso/purchase_writer.py`）：

```
build_ai_input(mpn, brand, qty)  ->  "型号      品牌      数量"（6 空格分隔）
CoordinatorPurchaseDraftWriter.prepare()          [src/launcher/v12_composition.py:302]
  new_draft -> set_customer -> set_quotation_type -> set_purchaser
  -> open_ai_entry()      # ai_import() -> windows('AI智能录单', product/Import_ai.aspx, [保存数据])
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
（`src/inso/purchase_writer.py` 增加一个粘贴面板适配器；`src/launcher/v12_composition.py` 调整步骤序列）。
上游 `build_ai_input` 需要改成 `型号|数量|品牌`（顺序也变了：AI 是 型号·品牌·数量）。

**可直接复用（禁止另建）：** INSO 会话/登录守卫/页面租约、`iframe#winIframealert_enquiry` 解析、
purchaser 多选清空与菜单关闭、`write_safety.py` 的控件语义白名单与门禁、关窗清场、
`v12_phase_a_readonly.py` 的"读 handler 源码判定副作用"范式。

**不构建**第二套 INSO 适配器、浏览器、调度器或账本。

### 6. 尚未验证的事项与真实阻碍

**唯一阻碍：** 粘贴弹窗只能由登录后的 ERP 外壳创建。
共享 profile 的 Cookie 仍在（`List.aspx`、`product/Import.aspx`、`sale/Enquiry/Bill.aspx` 都能直接只读加载），
但 `windows()` 定义为 `function windows(a,b,c,d,e,f,g){parent.windows(...)}`，在独立页里页顶自调用 → 栈溢出被吞 →
弹窗永不出现（实测点 `#product_add_`、`#product_import_` 都无反应）。
要真正点通必须先登录；登录会覆盖共享 profile 的 `erp_token`，而 V1.6 正在跑业务，属干扰生产登录状态，未获授权。

未验证六项：

1. 真实 `粘贴 → 导入 → 预览 → 保存数据` 点击链路；
2. 弹窗底部按钮的实际 DOM id 与禁用态切换；
3. 预览单元格/表格数据的可用取值路径（`table.cache['dg']` 字段名）；
4. 型号经服务端解析后是否逐字节保持原样（不截断、不转换）；
5. `appendRow()` 后父表单明细行的最终列值；
6. `import.ashx?action=PasteImport` 的响应结构与是否存在副作用。

另有两点记录在案、不影响本轮结论：

- 当前生产环境的 `Import_ai.aspx` 已是**新版 AI 识别页**（有"极速识别""载入示例"等控件），
  与代码里注释描述的旧版细节不完全一致；`#preview-body`、`#ai-recognize`、`#ai_import_` 仍在，未影响运行。
- 现运行的 V1.6 本轮全程未被触碰：10:43:07–10:43:10 仍完成 inquiry 轮次，`fatal.log` 0 字节，
  唯一 `runtime fault` 仍是 2026-11-20 14:29 那条已修结案的。

## 采集边界声明

本轮在 Windows 现场执行，读到的是真实仓库、真实 EXE 哈希、真实进程与真实 ERP 页面。
真实"点击跑单"未执行 —— 该边界已在上面逐条列明，未以静态分析冒充运行验证。
