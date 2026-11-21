# RFQ-025 — 最终汇报（第二阶段：V1.7 实现与候选）

**状态：`V1_7_IMPLEMENTED / LIVE_DRAFT_VERIFIED / RELEASE_CANDIDATE_READY / READY_FOR_CEO_REVIEW`**

## 七段式

```text
正在实现什么：
把采购询价单的录单方式从 INSO 的 AI 识别换成 ERP 自带的粘贴导入，其余业务流程一点不动。

理想变化是什么：
不再依赖 AI 识别服务；型号、数量、品牌直接用我们已经确认过的数据，由 ERP 自己解析并补产品编码，更快也更可控。

以前是什么：
录单要走"AI录单"弹窗，把型号·品牌·数量交给外部 AI 服务识别，再回填。AI 服务是外部依赖，也是识别误差的来源。

现在是什么：
录单走"粘贴"弹窗：程序写入"型号|数量|品牌"，点导入让 ERP 自己解析，程序读回预览逐项核对，再点保存数据把行交给单据。AI 这条路在生产代码里已经不存在了。V1.7 候选已构建，等审核后安装。

做完了什么：
粘贴录单的完整实现、真实页面验证（单笔 + 同页连续两笔）、定向与完整回归、V1.7 版本标识、一次候选构建。过程中修掉两个真实缺陷。

测试结果：
真实环境跑通了：型号/品牌/数量回读与订单一致，ERP 自己补出了产品编码，AI 端点请求数为 0，没有生成任何 ERP 单据。完整回归结果见下方第 4 项；少数与本次无关的 TP 模块用例失败，已逐一核对来源。

你接下来需要做什么：
Review 本轮交付；确认后进入安装与真实业务试运行（那一轮才验证"保存并发送"和最终业务结果）。
```

## 六项交付（CEO 需要的技术内容）

### 1. V1.7 实际实现的功能与修改范围

分支 `workbuddy/v17-native-paste`（自 `693bd983`）。源码提交 `38341aa5`，测试/证据提交 `b3abe0a1`。

**唯一被替换的环节**：`CoordinatorPurchaseDraftWriter.prepare()` 里原 `prepare-ai-open` 起的五步。

```
open_paste_entry            # 点 button#product_import_（文本"粘贴"）
assert_paste_preview_fresh  # 解析前证明预览为空、保存数据仍禁用
set_paste_data              # 写 textarea#pasteData = 型号|数量|品牌
run_paste_import            # 点 #win_btn__dialog11（导入）→ ERP 自己解析
read_paste_preview          # 等"行数符合 + #win_btn__dialog12 解禁"，读 layui.table.cache['dg']
validate_draft_preview      # 型号/品牌/数量核对
commit_paste_entry          # 点 #win_btn__dialog12（保存数据）→ appendRow 回填
parent read-back + validate # 原有父表单四列读取与二次校验（未改）
```

| 文件 | 改动性质 |
|---|---|
| `src/inso/purchase_writer.py` | AI 面板适配器整体替换为 `PasteImportPanel` + `PlaywrightPastePreviewReader`；帧身份钉死 `product/Import.aspx`，**显式拒绝**列表批量导入 |
| `src/inso/write_safety.py` | 三个写动作改为 `SET_PASTE_DATA` / `RUN_PASTE_IMPORT` / `PASTE_ENTRY_COMMIT` |
| `src/launcher/v12_composition.py` | `prepare()` 步骤序列 |
| `src/workflow/v12_rules.py` | `build_paste_input`（`型号|数量|品牌`）+ `validate_draft_preview` |
| `src/workflow/v12_contracts.py`、`v12_flow.py` | 字段名与调用点 |
| `src/gui/app.py`、`workbench.py` | 用户可见文案改"粘贴录单" |
| `app_paths.py`、`backend.py`、spec、构建脚本 | 版本 1.6 → 1.7 |

**没有改动**：去重、七天窗口、准入规则、`save_data`、`save_and_send`、`UNKNOWN/SENT`、hold、
Sheets 读写、报价更新、TP、邮件、调度周期、代理与 CDP。`git diff --stat` 可逐条核。

### 2. 真实页面录单验证结果

用**生产代码路径**（`attach_inso_research_session → operation_page → InsoPurchaseWriter →
CoordinatorPurchaseDraftWriter.prepare`），不是临时探针。

单笔（`TRJC476K016RRJ|200|Kyocera AVX`）：

| 项 | 结果 |
|---|---|
| outcome | `AI_RECOGNIZED`（历史持久值，语义"预览已核对通过"） |
| 回读 | `TRJC476K016RRJ` / `Kyocera AVX` / `200` |
| 解析请求 | 1 次 `POST /services/product/import.ashx` |
| AI 请求 | **0** |
| `#BillID` | 空 |
| 清场 | 前后均 True |

同页连续两笔（第二笔换成 `LM358DR / Texas Instruments / 500`）：**两笔都通过**。
这一项专门验证"第二单不会继承上一单的粘贴弹窗/预览"，是生产最常见的形态。

### 3. 生产路径是否已彻底移除 AI 录单

**是。** 三层证据：

1. 源码里 `src/inso/purchase_writer.py` 已无 `Import_ai.aspx`、`#ai_import_`、`ai-recognize`、`AI录单` 任何字样，
   并有专门的守卫测试（`test_the_production_draft_path_carries_no_ai_entry_anywhere`）防回潮。
2. `WriteAction` 与 `InsoDraftActions` 里不再有 AI 成员与方法。
3. 真实运行中 AI 端点请求数为 0。

保留的只有三个**持久化历史标识**：`PurchaseOutcome.AI_RECOGNIZED`、
`ReasonCode.AI_RECOGNITION_MISMATCH`、`EventType.AI_RECOGNITION_READY/MISMATCH`。
它们是 SQLite 与事件目录里的值，改名需要数据迁移；Owner 已明确允许保留必要内部名称，用户可见文案已全部改成"粘贴录单"。

### 4. 定向与完整回归结果

定向（逐项通过）：`tests/inso` 299 项、`test_v12_composition` 40 项、`test_v12_rules` 38 项、
`test_backend`/`test_manual_order`/`test_source_date_flow` 123 项、`test_workbench` 12 项。

完整回归：见 [EXECUTION_LOG](EXECUTION_LOG.md) 第 12 节（同一份 JUnit 归档在
`docs/evidence/rfq025/pytest-v17-full.xml`）。失败集合已逐条比对来源，**没有一项落在本次改动的模块**。

### 5. V1.7 候选

| 项 | 值 |
|---|---|
| 路径 | `build/windows-release-stage-1.7/dist/INSO_V1.7/INSO_V1.7.exe`（未安装，`dist/` 未被触碰） |
| 大小 | 8,508,798 B |
| SHA256 | `5707b9c598546c6476f96bfde217d712d1f7768732acf5032ef79657004af253` |
| 文件数 | 2,872（无 `runtime/`） |
| 清单 | `docs/evidence/rfq025/INSO_V1.7-artifact-manifest.sha256`，SHA256 `27d46b1cc4b7901121bf800534fb617daeb091e29a4a76d91257afaf696f3f9a` |
| 发布扫描 | `RELEASE_SCAN_OK` |
| `--self-check` | 退出码 0 |
| `--idle-self-check` | 退出码 0，`gui_rendered: true`，标题含 `V1.7` |
| 源码 | `332b8695`（其后提交仅文档/测试导入顺序） |

构建复用 V1.6 时代的 `.venv-release`，走既有 `-BuildOnly`，只产出 staging。

### 6. V1.6 当前实际状态

- **未被覆盖、未被替换、未被删除。** `dist/INSO_V1.6/` 与回退材料原样保留，本轮构建走 `-BuildOnly`，只产出 staging。
- **业务处于停止状态**（Owner 授权开发期间暂停）：停止后无新的业务轮次；进程仍在
  （已知"关窗不退出"缺陷），未擅自 kill。
- 若要恢复业务，用原 GUI 正常启动即可 —— 本轮没有改动 `dist/` 下任何文件。

### 7. 是否影响下一轮安装试运行

**无阻断。** 需要下一轮确认的只有三件事，都是流程性的：

1. 安装脚本 `install_release_candidate.ps1` 里候选目录与进程名仍写死 `INSO_V1.6`，装 V1.7 前必须按其自身门禁更新
   （本轮按 Owner 指令不动安装机制）。
2. 真实"保存并发送"与完整业务结果验收尚未做，属安装试运行阶段。
3. 生产当前是停止状态，安装前需按既有 B3/B4 程序确认停机一致性。
