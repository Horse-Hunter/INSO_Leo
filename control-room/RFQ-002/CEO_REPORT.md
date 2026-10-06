# RFQ-002 — CEO Review 报告（2026-10-06）

最新空白页补充：Owner 明确允许清理固定 9222 专用上下文的旧业务标签，
每行前/正常闭环后只留一个 about:blank。既有 launcher 清理入口实现，
先保留空白再关闭其他页，绝不关闭浏览器/上下文或清登录信息；人工验证
未完成时先停住并留验证页。真实清理前后 cookies 一致，最终库存一个空白。
Focused 381 passed；full safe/offline 972 passed / 11 skipped；Ruff/diff PASS。
新 EXE 已覆盖并重启待命，SHA256
`2EEE1833FA2F2749C1DBE934010CFC0876BBE88A4E61D8783EDEF3611275EEBC`。
旧资产备份 `dist/release-backups/INSO_V1.2-20261006-before-blank-tab-update`。
未运行新订单或重跑已发订单，未提交/SMTP/写 Sheets。下方批次实测仍有效，
但其旧 EXE 指纹及“保留 Owner 旧业务页”安排已被本补充取代。

## 最新六行事件修复与实测交付（取代下方旧版本结论）

原故障已在既有生产链修复，没有重建系统。最终只读审计确认六行均为
SAVED / PURCHASE_RECORDED，Google 状态均为“发给采购”；每行累计一次
提交。新增真实提交仅四笔原未发送订单，原两笔只核对记录并补正状态。
三条符合重要规则的通知均由真实 SMTP 接受，原接收人/内容/阈值不变。

主因与修复：

- 完整下方分页的渲染等待误把双空格当未完成；仅规范显示空白，保留原始型号。
- 模糊搜索的其他型号数量为零，污染当前型号校验；复用既有精确型号策略排除，
  当前型号的无效数量仍拒绝，七天窗口/制单人/数量规则未改。
- 最终记录原始 BillID 不符合数据库不透明标识契约；现有确认器生成正确散列。
- 逐行同步收尾，状态写回/读回、通知处理及自有页面关闭后才处理下一行；
  结果不明、写回失败、通知未确认则停止，不重试采购提交。
- 同一固定 9222 CDP，每行新建并固定自己的 INSO 页；登录走原入口和业务菜单。
  旧 Owner 页不借用、不关闭；认证失败/租约失败/终态均清理自己的页。
- 统计使用业务闭环；验证码中断持久化等待恢复状态，不再显示永久处理中。
- 汇率复用当日成功的官方结果，跨日刷新；没有模拟价格或汇率。

Owner 已明确确认发送的两笔，有单独 opt-in 的只读确认恢复，普通轮询不调用：
需要原始一次 dispatch、型号/数量/时间 ±30 分钟/已发送状态的权威单一证据，
成功记录人工解决事件。未知/未找到不能重新开放发送；不伪造旧基线。
测试覆盖默认拒绝、证据不完整拒绝、显式确认成功及始终禁止第二次 dispatch。

订单定位契约仍是同一 inquiry_id：由 Google 表格 ID＋工作表名＋原行号派生，
在 workflow_items 保存原始身份/关键值快照。后续模块必须先按 inquiry_id 取
record_identity，再复用当前行重新定位、复读、防冲突和读回；不能只按型号，
也不能把历史原行号当永远不变的位置。仅本次状态转换获授权，其他模块不要
直接复用购买写入权限；具体契约和查询示例沿用下方第 3 节。

最新 EXE 已覆盖 `D:\Program_Leo\INSO_Leo\dist\INSO_V1.2\INSO_V1.2.exe`，
SHA256 `C2B46F90BBCD2AD19AC269F3F4459D72942B1B758D83F631316044BA1B44CEE5`。
旧资产备份为主项目 `dist/release-backups/INSO_V1.2-20261006-before-batch-repair`。
runtime junction/数据/授权缓存保持不变。程序已打开待命，未再启动询价。
纯程序构建/冻结依赖/安全扫描及部署自检通过；截图捕获超时，未冒称像素验证。
Focused 603 passed / 1 skipped；full safe/offline 968 passed / 11 skipped；
Ruff src/tests 和 diff check PASS。精确范围见 Execution Log；测试无真实 SMTP。

本 RFQ 重新提交独立 Review；这些真实闭环不等于 CEO PASS，也不能证明未来
任意外站结构变化、人工挑战、网络故障均不会发生。发生结果不明仍禁止重发。
客户明细、原始输出、临时验证脚本、运行数据库与 EXE 不进 Git。

## 历史报告（下方旧版本指纹和旧限制不适用于最新交付）

最新复验补充：CEO B1 所列 ProductID 旧测试已按三要素规则修正，仅改 tests
及 Control Room 文档。Focused 91 passed；最新完整 safe/offline regression
946 passed / 11 skipped；Ruff src/tests、diff check PASS。两条既有发布测试
的 SMTP 尝试由保护层本机拦截，没有真实发送，详细记录见 Execution Log。
未改 src、未重新打包、未运行真实订单/提交/SMTP/Sheets 写入。
下文“旧 ProductID 测试未对齐/最新全量缺失”已由本次证据取代，其他部署及
未完成真实业务验收范围不变；等待 CEO 独立重新 Review。

## 交付结论

V1.2 已重新打包，覆盖 Owner 原路径的程序文件。本次 EXE 包含 AI 校验修复、
提交后确认修复、采购成功表格状态写回和异常邮件通知。旧程序文件已备份，
原配置、数据库、历史状态、Research 结果和 Google 授权缓存保留。
本轮没有运行订单或重新保存发送已发订单。

当前状态为 **REVIEW_REQUIRED**。旧 CEO PASS 只覆盖
`2e519e1e72b22af620b2c0d90b6e21f6b87140fa`，不覆盖后续修改。
本报告不是独立 Review PASS，也不宣称新版完整业务链已经实测通过。

## 1. 版本与部署

- 仓库：Horse-Hunter/INSO_Leo；分支：feature/v1-2。
- EXE 生产源码基线：`a1bed4094af8a834483c8f9f7852f6e7de0c7ac4`。
  此后的本轮提交仅更新文档；最终审查指针以远端分支 HEAD 为准。
- 活跃工作区：`D:\Program_Leo\INSO_Leo\.worktrees\v1-2-design`。
- Owner 程序：`D:\Program_Leo\INSO_Leo\dist\INSO_V1.2\INSO_V1.2.exe`。
- 新 EXE SHA256：
  `FDAA40FEF27AB83C7C014F2C3BC0FB5072207882DFB1F748AD08050E9597482D`。
- 旧程序备份：
  `D:\Program_Leo\INSO_Leo\dist\release-backups\INSO_V1.2-20261006-before-completion-update`。
  只备份旧 EXE 和 _internal，不移动或复制生产 runtime。
- 原 runtime junction 仍指向
  `D:\Program_Leo\INSO_Leo\.worktrees\v1-2-design\dist\INSO_V1.1\runtime`。
  V1.1 程序未覆盖。安全迁移运行数据之前不得删除/移动该工作区或 junction 目标。
- EXE、备份、授权缓存、数据库、客户明细和原始输出不进 Git。
  远端交付源码与脱敏报告，部署目录不是独立可搬走的通用分发包。

## 2. 本阶段修复与新增功能

### AI 录单校验

现场问题不是单纯等待不足：AI 已识别型号/品牌/数量，但旧代码还要求预览中
存在产品编码。Owner 明确产品编码在 AI 页面“保存数据”之后生成，不需校验。
生产主链现在只核对型号、品牌、数量，保留原品牌规则，不增加另一套录单实现。
旧产品编码兼容方法保留，生产主链不再使用其校验。

Owner 随后亲自启动新订单，三项校验通过，真实保存并发送一次；Owner 在
INSO 看到记录为“已发送”。执行者未再次提交这笔订单。

### 提交后确认

误判原因是上方查询页码读取错误及筛选后保留的旧总数，不代表 INSO 发送失败。
复用原查询，证明上方首页已结算后，只看最新首行：准确型号、新单据编号
（与提交前基准不同）和本次提交时间；Owner 允许时间误差前后 **30 分钟**。
不再用陈旧总数要求首页代表完整历史，响应/缓存/DOM 身份与顺序核对仍保留。

只读复查原已发送记录的首页结算通过，没有重新提交。下方**采临时询价**
七天重复检查仍完整分页并读取真实制单人，不能与上方提交确认混用。
无法确认仍提示人工核实，不能自动再次点击提交。

### 采购成功后写表状态

只有流程结果与持久化采购状态都为 SAVED 才自动写回；Research 完成、
按钮点击或 GUI 完成计数不是采购成功证明。

- 复用 Sheets 唯一快照定位、写前重读、RAW 单格更新与读回。
- 只改标准表 A / SHAHAB B 状态格：“未发”→“发给采购”；其他格不动。
- 已为“发给采购”不重复写；其他状态、零/多候选阻止写入。
- 写回失败保持采购成功，告警后只重试表格状态，绝不重发采购单。

Owner 授权对已人工确认发送成功的原订单验证状态更新。写后第一次读回遇
Google 502；重试确认已为“发给采购”，再次调用无第二次写入。
未伪造采购台账为 SAVED，未调用 INSO 提交。

### 异常邮件

新增异常通知只发 `linan229@qq.com`，包含内部识别码、型号、品牌、数量、
来源工作表/原行号、失败阶段及安全的具体原因。覆盖采购录单/校验、提交
不明、重复查询不可确认、Research 异常和状态写回失败；既有登录告警补订单
信息。原重要/重复订单通知仍沿用原触发规则与收件人，不被替换。

提交不明明确提示“可能已经发送，请查 INSO，禁止直接重跑”。
复用既有命令/收件人台账和 SMTP worker，同一订单/阶段/原因去重，
SENT 收件人不重发。真实验证使用明确标记的合成测试通知，QQ SMTP 接受，
再次入队无重发；SMTP 接受不等于已证明收件箱展示。

### Google 授权

Owner 已亲自完成写入授权，使用原 CurrentUser DPAPI 加密缓存，保存在仓库外。
普通重启/版本更新/打包不删除缓存或更换 OAuth client。
生产写回 `allow_interactive=False`，仅复用/刷新 grant，不在 worker 重复弹授权。
真实撤销、缺失或损坏须明确失败告警，不能承诺授权永不失效。

## 3. 后续模块如何定位同一行的内部识别码

### 定义与存储

当前计算在 `src/workflow/store.py`：

```python
key = "\x1f".join((spreadsheet_id, worksheet_name, str(original_row_number)))
inquiry_id = "inq_" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]
```

输入是 Google 表格 ID、工作表原名称、读取入队时的原行号；不含型号、品牌、
数量或状态。修改状态不会改变已保存识别码。它不同于 INSO 单据编号 BillID
和产品编码 ProductID。

摘要不能反解为表格/行号。Workflow 的 `workflow_items` 保存唯一 inquiry_id
及 `record_identity_json`，后者含表格、工作表、原行号和识别快照。
具体客户订单识别码已私下给 Owner，不发布到 Git 报告。

### 后续模块接入顺序

1. 在任务/事件中接收并保存原 inquiry_id，使用同一 Workflow 数据库。
2. 使用已有公开查询，不按现在的行号重新计算识别码：

   ```python
   item = workflow_store.get_by_inquiry_id(original_inquiry_id)
   identity = item.record_identity
   # 向 Sheets 传递 opaque identity，执行明确授权的状态转换。
   ```

3. 由 Sheets 按工作表映射重读并确定当前唯一目标行。原行号只是线索；
   插行/排序后可能变化。现有非品牌定位快照：标准表核对状态、重要程度、
   型号、数量；SHAHAB 核对状态、型号、数量。其他模块不复制定位逻辑。
4. 明确当前阶段允许的“预期当前状态 → 下一状态”，写前重读、只改目标格、
   写后读回。内容改变、零/多候选失败关闭，不按型号或原行号猜测。
5. 状态失败与 INSO 不可逆提交分开；不能因表格失败重发采购。

识别码不会自动追随 Google 行移动；重新使用同一行号可能与旧队列身份冲突。
它是本地 Workflow 记录身份，不是 Google 原生永久行 ID。不能用重新计算的
摘要、型号或行号单独定位旧订单。

当前 `write_purchase_status_safely` 仅支持“未发/已发给采购”的幂等转换，
不是任意状态 setter。后续其他状态须单独授权，复用原身份查询、Sheets
定位和单格写回，定义当时的预期状态；不能用原快照“未发”覆盖后续状态。
本轮只记录接入方式，不实施未来模块。

## 4. 复用与安全

继承 V1.1/WorkBuddy 的配置、Sheets/OAuth、Research、Workflow、Vault、GUI、
数据库、Chrome/CDP 和同一发布脚本/spec；无新增依赖、第二启动链或迁移。
自动采购截图仍已删除。唯一 CDP 为 127.0.0.1:9222，profile 为
`D:\Program_Leo\INSO_CDP\chrome-profile`，本轮未操作它。

默认 ProductionWriteGate 仍关闭；已批准客临时询价最终提交为窄例外。
AI 窗口内导入保存与普通对外单独 Save 不能混同；普通 Save、generic send/
submit 未开放。Sheets 仅开放上述成功状态转换，未开放任意写入。

## 5. 验证与未验证范围

| 验证 | 结果 | 范围限制 |
| --- | --- | --- |
| 上轮新状态/通知与相关离线检查 | 152 passed，8.48 秒 | 不是最新全仓库回归 |
| 上轮真实状态更新/读回 | 通过，重复调用无第二次写 | Owner 已确认发送的订单；未执行 INSO |
| 上轮真实异常邮件 | SMTP 接受，去重通过 | 合成测试通知，只发 Owner |
| 本轮 Ruff src/tests | PASS | 使用已有开发 Python；发布环境未安装 Ruff |
| 本轮 git diff --check | PASS | 文档提交前检查 |
| 同一发布脚本 -Version 1.2 -BuildOnly | 成功 | 干净 staging，源码 a1bed40 |
| 冻结依赖自检 | exit 0 | staging 与覆盖后的 EXE，不运行订单 |
| 干净产物扫描 | RELEASE_SCAN_OK | 关联私有 runtime 前 |
| 本轮 GUI 启动 | 未完成 | Computer Use app approval timeout；没有绕过或点击开始 |
| 新 EXE 完整订单链 | 未运行 | 留给 Owner 下一笔真订单，不重跑旧单 |

早前 921 passed / 11 skipped 不覆盖 10 月 6 日修改。AI/确认修复按当时 Owner
指示未跑自动测试，部分旧 ProductID 合约测试尚未对齐；不将专项检查或
打包成功称为最新完整回归通过。原订单的本地采购结果仍待人工确认，未
伪造为 SAVED；人工确认及表格补写不会自动改历史采购台账。
供应商实际收件没有证据。

## 6. CEO Review 重点与阅读入口

审查 `e585e88`、`c30e96a`、`a1bed40` 及执行记录，重点核对：

- AI 三要素、下方完整七天历史与上方首页确认的不同边界。
- 时间 ±30 分钟、新首行编号、精确型号、结算证据及未知结果不重发。
- 提交前落未知状态、单次 dispatch、旧单防补发和重启安全不退化。
- durable SAVED 才写表、定位冲突不误写、状态重试不触发采购提交。
- Owner-only 异常邮件、台账去重、grant 复用和 protected runtime/CDP。
- 最新全量回归尚缺；如要求执行先修过期 ProductID 测试，不重跑已发订单。

阅读：Task Spec 最新授权 → 本报告 → Execution Log → 实际源码 diff →
Final Report。REVIEW.md 旧 PASS 是历史检查点，等待 CEO 独立新结论。
本轮未自动向 CEO chat 发消息，Owner 可让 CEO 从远端读取本报告。
