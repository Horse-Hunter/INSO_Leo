# RFQ-025 — 最终汇报（第三阶段：收尾、安装与生产试运行）

**状态：`V1_7_INSTALLED / PRODUCTION_RUNNING / REAL_PURCHASE_NOT_YET_VERIFIED`**

一句话：V1.7 已装进自己的目录并正常生产运行，22 条 TP 失败查明是测试时基问题并已修正，
全量回归零失败；**没有发生真实采购**，因为当前没有合法待处理订单——这一点如实标注，不算业务验收通过。

## 七段式

```text
正在实现什么：
把采购询价单的录单方式从 INSO 的 AI 识别换成 ERP 自带的粘贴导入，收尾后装机、启动、跑真实业务。

理想变化是什么：
不再依赖 AI 识别服务；型号、数量、品牌直接用已经确认过的数据，由 ERP 自己解析并补产品编码，
流程更短、外部依赖更少、误差来源更少。

以前是什么：
录单走"AI录单"弹窗，把型号·品牌·数量交给外部 AI 识别再回填；V1.6 还在 dist\INSO_V1.6 里跑着，
粘贴路径只在代码和嗅探脚本里验证过，没有装、没有跑生产。

现在是什么：
V1.7 装在 dist\INSO_V1.7，独自占用同一个 runtime（配置、生产库、日志全沿用），
通过桌面"INSO V1.7（最新版）"启动，正在按 900 秒周期跑 inquiry / quotation / tp。
录单走"粘贴"：写"型号|数量|品牌"→导入→读预览逐项核对→保存数据交给单据。AI 路径已不在生产代码里。

做完了什么：
TP 22 条失败的根因定位与修正、粘贴两处收尾（单笔隔离、字段映射守卫）、最终全量回归、
一次最终候选构建、安装脚本跨版本适配、正式安装、正常生产启动与实盘观察。

测试结果：
全量 4365 项：0 失败 / 0 错误 / 1 跳过（上一轮那 22 条 TP 失败全部转绿，未删未跳）。
安装门禁 202 项 PASS。真实运行：三个模块各跑完至少一轮，零 ERROR、零 Sheets 故障。
真实采购：没有发生——当前没有合法待处理订单，未造单、未重发历史订单。

你接下来需要做什么：
1) Review 本轮交付与安装证据；2) 有合法待处理订单时，让它自然跑完一次"保存并发送"，
   再确认 ERP 单据与 Sheets 回写＝真正的业务验收；3) 你决定何时把 V1.7 晋升 main。
```

## 一、本轮实际实现的功能与修改范围

只换录单方式，其余业务一行未改。

| 文件 | 本轮改动（第三阶段） |
|---|---|
| `src/inso/purchase_writer.py` | 新增 `PasteImportPanel.ensure_layout()`：读 `#cmb0/#cmb1/#cmb2` 与 `#combox101` 隐藏值，默认正确时只读；不一致时用弹窗自带下拉改回并复读；改不回 fail-closed |
| `src/launcher/v12_composition.py` | `prepare()` 插入 `prepare-paste-layout` 步骤（打开弹窗之后、写数据之前） |
| `src/workflow/v12_flow.py` | `build_paste_input()` 的 `ValueError` 改走既有单笔无效输入通道，不再中断整轮 |
| `src/workflow/tp_research.py` | `_run()` 统一时间基准（`current_now`）；`run_due` 仍用调用方 `now` |
| `tests/*`、`scripts/install_release_candidate.ps1`、`scripts/test_install_gates.ps1` | 时基修正、6 条新用例、安装脚本跨版本参数化 + `-FreshInstall` |

**未改动**：去重/七天窗口/准入、`save_data`、`save_and_send`、`UNKNOWN/SENT`、hold、
Sheets 读写、报价、TP 业务规则、邮件、调度周期、代理与 CDP 修复。

## 二、真实页面录单验证

用生产同一条组合链（`attach_inso_research_session → operation_page → InsoPurchaseWriter →
CoordinatorPurchaseDraftWriter.prepare`）跑了 **两次**：加布局守卫前后各一次，结果一致。

| 项 | 实测 |
|---|---|
| outcome | `AI_RECOGNIZED`（历史持久值，语义=预览已核对通过） |
| 回读 | `TRJC476K016RRJ` / `Kyocera Avx` / `200`，与订单一致 |
| 解析请求 | 恰好 1 次 `POST /services/product/import.ashx` |
| AI 请求 | **0** |
| `#BillID` | 空 —— 未创建任何服务端单据 |
| 布局守卫 | 默认配置下**一个控件都没点**（隐藏值已是 PartNo/Qty/Brand + 3） |

见 `docs/evidence/rfq025/v17-live-verification.md`（含第 5 节第三次实测与控件结构）。

## 三、正常生产路径是否还有 AI 录单

没有。

- 源码守卫测试 `test_the_production_draft_path_carries_no_ai_entry_anywhere` 断言
  `src/inso/purchase_writer.py` 与全部控件绑定里不含 `Import_ai.aspx` / `#ai_import_` / `ai-recognize`；
- 两次真实运行的请求监听里 AI 端点命中数为 0；
- 保留的 `AI_RECOGNIZED` / `AI_RECOGNITION_MISMATCH` 只是 SQLite 与事件目录里的历史持久值
  （改名要数据迁移，Owner 已允许保留），用户可见文案已全部改为"粘贴录单"。

## 四、定向与完整回归

```
4365 collected / 4364 passed / 0 failed / 0 errors / 1 skipped in 765 s
```

- 上一轮 22 条 TP 失败**全部转绿**；没有删除、没有跳过、没有改 TP 规则或日期限制。
- 根因（与 CEO 判断一致）：TP 按"上月同日"计算截止日，夹具订单固定 `2026-10-20`，
  而省略 `now` 的调用点读墙上时钟 —— 在 `2026-11-21` 运行时截止变成 `2026-10-21`，订单被自己的夹具判过期。
  修法：`build()` 给 `TpCycle` 传 `clock=lambda: NOW`（既有参数），并让 `_run()` 全流程只用这一个时间基准。
  过程中发现并修掉一个自相矛盾：`read_orders` 认 clock、`claim` 却拿原始 `now`。
- `ruff check src tests` 仍只有基准的 3 条既有 F811。
- 顺带修掉安装门禁夹具的同类时间腐坏（事件时间固定在 11-15，72 小时新鲜度门禁必然过期）。

## 五、安装的 V1.7 与源码

| 项 | 值 |
|---|---|
| 安装目录 | `D:\Program_Leo\INSO_Leo\dist\INSO_V1.7`（全新目录，V1.6 未触碰） |
| EXE | `INSO_V1.7.exe` 8,510,418 B |
| EXE SHA256 | `6e258a5021792a1b4b88a72ca12d355064aab8c398e64eb58240ef542dece780` |
| 文件数 | 2,872（已逐文件按清单复核） |
| 清单 | `docs/evidence/rfq025/INSO_V1.7-artifact-manifest.sha256`（2,872 行） |
| 清单 SHA256 | `e148a4d22a5c2b9a7b81b484fc6228ec162cd112e896eed3aa67ace2426f5397` |
| 源码 commit | `1ce1671f`（之后只有文档提交） |
| runtime | Junction → `D:\Program_Leo\INSO_Leo\dist\INSO_V1.4\runtime`（配置/生产库/日志沿用同一份） |
| 安装结果 | `INSTALL_RESULT = PASS`，`rollback_kind = PREVIOUS_INSTALL_UNTOUCHED` |

回退材料（全部现成）：
`dist\release-backups\RFQ-025-pre-v17-20261121T132826Z`（V1.6 程序快照 + `PROGRAM-MANIFEST.sha256`）
与同目录 `database\workflow.sqlite3` + `.verify.json`（`DB_VERIFY_RESULT = PASS`，40 条采购记录）。
V1.6 目录本身一个字节未动，`INSO_V1.6.exe` 仍是 `9a0cb3d3…2710`。

## 六、实际 GUI 与生产运行状态

```
PID 85452  INSO_V1.7  「INSO LEO V1.7 — Procurement Automation Control Center」
PID 84368  INSO_V1.7  （watcher）
run_id edc94a2c…，fatal.log 0 字节
```

以正式生产模式启动（`--start-inquiry` 就是「开始运行」调用的同一个 `backend.start()`），
三个模块都按 900 s 跑起来且零故障：inquiry 9.6 s / quotation 77.5 s / tp 1.2 s，
21:47 第二轮 inquiry 4.1 s 完成。日志中 `ERROR`、`SHEETS_*`、`fault` 命中数 0。

## 七、真实采购结果

**没有发生，且不是故障。** 最新业务状态全为 `PURCHASE_RECORDED` / `HUMAN_COMPLETED`，
询价模块两轮都无单可做；purchase 行数 40（与装前备份一致），最后一条采购是 11-19，
活动 hold 3 条原样保留，open write intents 0。

按 Owner 指令，不造单、不重发历史订单，故标注 `REAL_PURCHASE_NOT_YET_VERIFIED`。
真正的业务验收（保存并发送 → ERP 单据 → Sheets 回写）要等出现合法待处理订单时自然发生。

## 八、尚未验证 / 未完成

1. **真实"保存并发送"与最终业务结果**：本轮无合法待处理订单，未验证。
2. **安装后程序内实测粘贴路径**：尚未有订单触发；现有证据是"同一份源码的真实运行 + 装机二进制与候选逐字节一致"。
3. **数据库路径**：`production.json` 的 `sqlite_path` 仍指向 `dist\INSO_V1.2\runtime\production\...`
   （历史遗留指向，经 junction 解析到同一文件）。本轮未改，属独立清理项。
4. 既有现象（非本次引入）：`inq_d65be9df3c7cc40b65cbffaa` 的 `QUOTE_INPUT_WRITE_FAILED`、
   `inq_71f4a2f5ef8678223385b6e2` 的 `UPDATE_RESULT_UNCONFIRMED`，自 11-20 起每轮同签名出现。
