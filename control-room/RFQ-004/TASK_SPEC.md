# RFQ-004 — V1.3 INSO quotation read pipeline

Executor delivery 2026-10-07: source/offline acceptance completed; REVIEW_REQUIRED only. No final CEO verdict or release. Evidence in EXECUTION_LOG.md and FINAL_REPORT.md.

Owner requirements preserved verbatim below. Status: COORDINATION.md; independent CEO Review REQUIRED.

你是新的 V1.3 Executor。

执行 RFQ-004：
“V1.3 INSO 采购报价读取模块”。

这是一个新 Codex 窗口。
不要继续在 V1.2 分支上直接开发。

==================================================
一、基线与分支
==================================================

仓库：
Horse-Hunter/INSO_Leo

V1.2 当前已经完成 RFQ-003 独立 Review。

稳定基线：

feature/v1-2
HEAD =
c8d514ed7aff2542dda685d476cd6e92ff97a85d

RFQ-003 =
REVIEWED_DONE

当前已部署 V1.2 EXE SHA256：

1A49C9650BA531F2299326FFC89761D0391CD5F2C0FE32327DDD0736BD5C3E84

本次必须：

1. fetch 最新远端；
2. 确认 feature/v1-2 HEAD 与上面稳定基线一致；
3. 从该稳定基线创建新分支：

feature/v1-3

4. 使用新的独立 worktree 开发；
5. 不回写、不重置、不覆盖 feature/v1-2。

如果远端 HEAD 已经在 CEO Review 后出现新的仅 Review/状态提交，
应以最新 REVIEWED_DONE 的 feature/v1-2 HEAD 为基础，
但必须确认没有新的未 Review 生产代码混入。

==================================================
二、开始前必须阅读
==================================================

阅读：

- AI_START_HERE.md
- AGENTS.md
- docs/PROJECT_BASELINE.md
- docs/AI_WORKFLOW.md
- docs/MODULE_INDEX.md
- control-room/COORDINATION.md

以及：

- control-room/RFQ-001/*
- control-room/RFQ-002/*
- control-room/RFQ-003/TASK_SPEC.md
- control-room/RFQ-003/EXECUTION_LOG.md
- control-room/RFQ-003/FINAL_REPORT.md
- control-room/RFQ-003/REVIEW.md

重点阅读现有模块：

- INSO
- Sheets
- Workflow
- Launcher / browser/CDP
- V1.2 duplicate/history query
- 下方“采临时询价”读取逻辑
- Stock_VenQuote / lower-history 等现有能力
- inquiry_id / record_identity 实现

不要看到名字是 V1.2 就直接复制一套。

RFQ-004 的核心原则是：

“复用成熟基础设施，新增独立 V1.3 业务模块。”

==================================================
三、建立 RFQ-004 控制文件
==================================================

创建：

control-room/RFQ-004/TASK_SPEC.md
control-room/RFQ-004/EXECUTION_LOG.md
control-room/RFQ-004/FINAL_REPORT.md

COORDINATION 新增：

RFQ-004
V1.3 INSO quotation read pipeline
ACTIVE
feature/v1-3
REQUIRED

本窗口是 Executor。

不要自己做最终 CEO Review。
完成后只能进入 REVIEW_REQUIRED。

==================================================
四、RFQ-004 的业务目标
==================================================

本阶段只实现：

Google 源表
状态 = “发给采购”
        ↓
逐行读取
        ↓
使用该行型号 MPN
        ↓
fresh INSO operation tab
        ↓
业务询价
        ↓
下方“采临时询价”
        ↓
执行现有查询
        ↓
寻找最近滚动72小时记录
        ↓
若多条，选择时间最新一条
        ↓
提取该行：
“日期” → “制单人”
        ↓
返回结构化 V1.3 quotation result
        ↓
关闭当前 operation tab
        ↓
下一行

本阶段到这里结束。

==================================================
五、本 RFQ 明确不做什么
==================================================

RFQ-004：

禁止实现：

- 写 Google“报价输入子表”；
- 点击 Google“更新报价”；
- Apps Script 操作；
- 修改源状态为“采购已报价”；
- V1.2 + V1.3 总调度；
- 正式15分钟生产集成；
- V1.3 GUI最终集成；
- V1.3 邮件最终集成；
- V1.3 EXE正式发布；
- 覆盖当前 V1.2 EXE。

以上属于后续：

RFQ-005 / RFQ-006。

尤其注意：

本次不允许覆盖：

D:\Program_Leo\INSO_Leo\dist\INSO_V1.2

当前 V1.2 是已 Review 稳定版本，
RFQ-004 不得影响其部署。

==================================================
六、Google 源订单读取
==================================================

V1.3 的待处理队列来源：

Google 源表状态：

“发给采购”

只读取，不修改。

不要改变现有 V1.2：

“未发”

扫描逻辑。

要求新增 V1.3 自己清晰的 read-only 查询入口，
但尽量复用现有：

- Sheets service
- worksheet schema
- row parsing
- SheetRecordIdentity
- canonical identity
- inquiry_id
- record relocation

不要复制第二套完整 Sheets 基础设施。

==================================================
七、订单身份
==================================================

V1.3 必须继续使用已经成熟的：

inquiry_id
+
record_identity

不能根据当前 row number 创建新的业务身份。

行移动不是新订单。

如果源表行移动，但现有 identity 能可靠 relocate：

继续使用原订单身份。

不要做模糊匹配。

不要创建：

V1.3自己的随机订单ID
或
按当前行号重新生成的新业务ID。

后续 RFQ-005 / 006 需要使用同一身份完成报价闭环。

==================================================
八、每行独立 closed-loop
==================================================

每一条“发给采购”必须独立处理。

一条订单：

fresh INSO operation tab
→ 查询
→ 读取
→ 形成结果
→ 关闭该 operation tab

然后下一条。

禁止一张订单页面同时承载多笔订单状态。

继续遵守现有 fixed Chrome / CDP / profile 规则。

禁止：

- 创建第二套 Chrome；
- 创建第二个生产 profile；
- 清 cookie；
- 删除 profile；
- 随意关闭 Owner 的固定 Chrome；
- 修改固定 CDP 端口策略。

==================================================
九、INSO 查询必须复用现有能力
==================================================

现有 V1.2 已经能够：

业务询价
→ 下方“采临时询价”
→ 输入型号
→ 查询历史
→ 分页/settlement
→ 读取结果

RFQ-004 必须首先找到并理解现有实现。

优先复用：

- existing lower-history reader
- existing Stock_VenQuote query
- existing page/session guard
- existing pagination settlement
- existing exact MPN normalization/filter
- existing fresh-tab lifecycle
- existing query timeout/retry infrastructure

不要因为 V1.3 又重写一套：

- Playwright selector；
- pagination；
- table parser；
- login handling；
- CDP连接器。

如果现有类/函数命名带 V1.2，
但逻辑实际上是共享 INSO infrastructure：

本 RFQ 优先通过小的 adapter/service 复用。

不要为了改名字做大重构。

共享基础设施的正式抽象整理可以留给 RFQ-006。

==================================================
十、型号查询规则
==================================================

查询型号来自当前 Google：

“发给采购”源订单的 MPN。

使用现有规范化规则进行查询/精确型号判断。

不能因为 INSO 返回相似型号就选进去。

但是注意：

“精确型号”只是为了确定查询结果属于当前订单。

这不代表做报价内容验证。

==================================================
十一、72小时窗口
==================================================

V1.3 的“3天内”正式定义：

滚动 72 小时。

时区：

Asia/Shanghai

不是：

- 3个自然日；
- 今天+前两天；
- 按电脑本地未知时区；
- UTC直接比较。

逻辑应类似：

query_time
↓
转换/解释为 Asia/Shanghai
↓
cutoff = now_shanghai - 72 hours
↓
只接受：
record_time >= cutoff
且
record_time <= now_shanghai

时间比较逻辑必须集中，
不要散落多个文件。

测试必须覆盖：

- 71小时59分 → 接受
- 正好72小时 → 接受
- 72小时+极小量 → 排除
- 跨午夜
- 跨月份
- 跨年份

测试使用固定时钟。

禁止依赖真实当前时间做不稳定测试。

==================================================
十二、没有3天记录
==================================================

如果查询本身成功，
但最近72小时内：

0 条

这是完全正常的业务结果。

含义：

“采购暂时还没有报价。”

必须返回清晰的正常结果，例如等价语义：

NO_RECENT_QUOTE

它不是：

- ERROR
- RETRY
- MANUAL_REVIEW
- PURCHASE_EXCEPTION
- GLOBAL_STOP

不发邮件。

不标红。

不修改 Google。

后续正式 V1.3 接入后，
下一轮15分钟会再次查询。

本 RFQ 只需把这个结果表达正确。

==================================================
十三、多条记录
==================================================

如果同型号在最近72小时内有多条：

只选择：

时间最新的一条。

不是：

- 第一条随便拿；
- 最贵；
- 最便宜；
- 数量最匹配；
- 品牌最匹配；
- 制单人特定；
- 批号最新。

唯一业务选择条件：

“日期/时间最新”。

必须写测试：

- 1条 → 返回该条；
- 2条不同时间 → 返回最新；
- 多页记录 → 仍选择全量结果中的最新；
- 旧于72小时的记录不能参与竞争。

如果原 INSO reader 已经保证完整分页，
直接复用其结果。

不要为了“最新”只读取第一页就猜。

==================================================
十四、报价内容：绝对不要业务校验
==================================================

这是 Owner 已确认的重要要求。

当最近72小时内找到了最新一条记录以后：

不要验证其业务内容。

不要因为以下情况拒绝：

- 品牌为空；
- 品牌与Google不同；
- 数量不同；
- 数量为空；
- 币种奇怪；
- 供方返点为空；
- 报价为空；
- 供方未税价为空；
- 平台数量为空；
- 批号为空；
- 货期为空；
- 备注为空；
- 备注2为空；
- 制单人为空；
- 文本格式特殊。

V1.3 此阶段不是 AI 审核器。

Owner规则：

“找到最近3天最新一条以后，INSO是什么就搬什么。”

RFQ-004 虽然暂时不写 Google，
但返回 DTO 时必须保留这个“原样搬运”能力。

==================================================
十五、必须提取的字段
==================================================

从选中的 INSO 行提取：

1. 日期
2. 型号
3. 品牌
4. 数量
5. 币种
6. 供方返点
7. 报价
8. 供方未税价
9. 平台数量
10. 批号
11. 货期
12. 备注
13. 备注2
14. 制单人

即：

INSO“日期”列
到
“制单人”列

完整连续区间。

不要带入后面的：

- 平台来源
- 品名
等本阶段不需要字段。

==================================================
十六、字段原样保留
==================================================

建议建立明确的数据对象，例如语义等价：

V13QuotationRow

它应包含：

- inquiry_id
- record_identity / source identity
- queried_mpn
- quote_record_time（用于技术选择）
- 原始14字段 payload

关键要求：

用于72小时比较的 parsed datetime
和
将来写 Google 的原始“日期”显示值

要分开。

不要为了时间比较而把：

“日期”

字符串重格式化后覆盖原始 payload。

其他13个字段同样：

尽可能保留 INSO 表格实际读到的文本值。

不要：

- Decimal 自动格式化；
- 去掉前导零；
- 自动补币种；
- 自动改日期格式；
- 自动 trim 掉有业务意义的备注；
- 把空字符串变成 0；
- 把空字段变成 None 后未来无法原样写回。

可以做安全的技术读取规范化，
但必须同时保留未来可原样回填的值。

==================================================
十七、V1.3 查询异常
==================================================

必须严格区分：

A：

查询成功
+
72小时内没有记录

=
正常 NO_RECENT_QUOTE

B：

查询本身无法可靠完成，例如：

- timeout；
- 页面没有settle；
- pagination异常；
- response/table structure异常；
- 无法确认全量结果；
- 无法判断是否真的没有记录。

=
INSO_QUERY_FAILURE

不能把 B 当成 A。

RFQ-004 必须复用 RFQ-003 已经确定的 INSO 查询恢复原则：

初次失败
↓
关闭当前 operation tab
↓
等待180秒
↓
fresh INSO tab
↓
重新查询同一订单

最多：

初次尝试 + 3次重试

任意一次恢复：
继续当前订单。

全部失败：
抛出/返回现有共享语义的 GLOBAL_STOP 故障。

由于 RFQ-004 尚未接总调度，
本阶段只需要把 typed result/fault 边界实现正确。

不要在 RFQ-004 再造一套不同的 retry engine。

等待必须可被 shutdown/stop 打断。

测试必须 fake wait，
禁止真的等3分钟。

==================================================
十八、INSO登录 / 人工验证
==================================================

继续沿用 RFQ-002 / RFQ-003 已确认规则。

如果发现：

- INSO登录失效；
- CAPTCHA；
- 手机验证码；
- 设备验证；
- MANUAL_VERIFICATION_REQUIRED；

这是共享 INSO 故障。

必须：

- 不把它解释成“没报价”；
- 保留 human-needed page；
- 不关闭该人工处理页面；
- typed GLOBAL_STOP；
- 不清 profile/cookie；
- 不新开临时Chrome绕过。

RFQ-004 不需要新发一套邮件，
最终邮件/总调度在 RFQ-006 接。

但不能破坏现有 fault signal。

==================================================
十九、V1.3 不使用 V1.2 的180秒行间冷却
==================================================

Owner已明确：

V1.2：

每行订单闭环后，
如果还有下一条 V1.2，
等待180秒。

原因：
降低连续采购发送触发验证码/风控概率。

但是 V1.3：

不使用这个“行间180秒冷却”。

V1.3只是：

INSO查询
+
读取

可以：

第1行闭环
→ 立即第2行
→ 立即第3行

不要把 V1.2 的 row cooldown 误复用到 V1.3。

注意：

INSO QUERY FAILURE 后的180秒重试等待仍然存在。

这两个概念完全不同：

V1.3正常相邻订单：
0秒额外冷却

V1.3 INSO查询失败重试：
180秒

==================================================
二十、RFQ-004 推荐模块边界
==================================================

不要机械照抄此命名，
但代码职责最好清楚分为：

A. V1.3 source candidate reader

只负责：

Google read-only
status == 发给采购
→ V1.3 candidates

B. V1.3 INSO quote reader

只负责：

MPN
→ lower Stock_VenQuote
→ 完整结果

C. recent/latest selector

纯函数：

records
+ now Asia/Shanghai
→
NO_RECENT_QUOTE
或
latest record

D. V1.3 quotation DTO

保存：

identity
+
raw 日期→制单人字段

E. RFQ-004 cycle/service

串行：

candidate1
→ fresh tab
→ query
→ result
→ close tab
→ candidate2

但暂时不接 production 15-minute scheduler。

==================================================
二十一、不要污染现有 V1.2
==================================================

本次开发必须确保：

现有 V1.2 行为完全不变。

尤其不能改变：

- V1.2 未发扫描；
- 168h duplicate；
- Research五源；
- AI录单；
- Save-and-Send；
- 发给采购写回；
- SUBMIT_UNCONFIRMED；
- RFQ-003 fault isolation；
- V1.2 180秒行间冷却；
- startup interruption quarantine；
- fixed Chrome/CDP；
- RFQ-002人工验证页保护。

V1.3新增代码尽量：

additive
+
shared infrastructure reuse

而不是改写 V1.2 核心业务流程。

==================================================
二十二、测试要求
==================================================

必须新增 V1.3 专属离线测试。

至少覆盖：

1. 只扫描状态“发给采购”；
2. “未发”不进入V1.3；
3. “采购已报价”不进入V1.3；
4. 保留原 inquiry_id / record_identity；
5. 行移动可通过现有 identity 可靠处理；
6. 一行一个 fresh INSO operation tab；
7. 正常相邻 V1.3 行没有180秒 cooldown；
8. exact MPN query/filter；
9. 72小时内0条 = NO_RECENT_QUOTE；
10. 72小时边界；
11. 多条选择最新；
12. 跨分页仍选择全量最新；
13. 日期→制单人14列全部提取；
14. 空字段允许；
15. 奇怪文本允许；
16. 品牌/数量不同不阻止结果；
17. 原始字段不被业务清洗；
18. query failure 不能变成0条；
19. query初次+最多3次retry；
20. retry使用fresh tab；
21. retry wait使用fake 180秒；
22. shutdown可中断retry wait；
23. retries exhausted → GLOBAL_STOP typed fault；
24. INSO manual verification → GLOBAL_STOP；
25. manual verification page仍保留；
26. RFQ-002 / RFQ-003现有相关回归继续PASS；
27. V1.2现有测试全部PASS。

==================================================
二十三、时间/数据测试要求
==================================================

所有时间测试使用：

fixed aware datetime

明确：

ZoneInfo("Asia/Shanghai")

禁止：

- datetime.now()直接写进纯逻辑测试；
- naive datetime参与业务比较；
- 用电脑当前时区猜；
- wall-clock sleep 180秒。

==================================================
二十四、安全测试边界
==================================================

RFQ-004 是 read-side 开发。

禁止真实：

- Save；
- Save-and-Send；
- Google写；
- 报价输入写入；
- 更新报价；
- Apps Script；
- 源状态变更；
- SMTP；
- 历史订单重放。

原则上不要用真实生产订单做开发验证。

优先：

- fake Sheets rows；
- fake INSO rows；
- existing captured fixtures；
- existing parser/unit seams；
- offline integration。

如果现有代码不足以确定 live selector，
不要擅自探索生产写路径。

记录 UNKNOWN，
提交 CEO Review。

==================================================
二十五、验证
==================================================

完成后执行：

V1.3 focused tests

以及现有完整：

python -m pytest -q tests

safe/offline only。

并执行：

python -m ruff check src tests

git diff --check

所有 V1.2 regression 必须继续通过。

==================================================
二十六、本 RFQ 不打正式生产包
==================================================

RFQ-004 完成后：

不要重新覆盖 V1.2 EXE。

不要发布所谓 V1.3 EXE。

不要动：

D:\Program_Leo\INSO_Leo\dist\INSO_V1.2

正式 V1.3 打包和总集成留到 RFQ-006。

本 RFQ 的交付物是：

- 源代码；
- tests；
- RFQ文档；
- 可 Review 的 commit。

==================================================
二十七、完成标准
==================================================

完成时必须能够用离线测试证明：

输入一组“发给采购”订单，

对于每一条：

如果 INSO 最近72小时无报价：
→ 明确 NO_RECENT_QUOTE

如果有一条：
→ 返回该条日期→制单人原始字段

如果有多条：
→ 返回最新一条

如果查询本身失败：
→ 绝不伪装成无报价
→ 使用现有 retry / GLOBAL_STOP fault boundary

整个过程：

- 不采购；
- 不Save；
- 不Send；
- 不写Google；
- 不改源状态。

==================================================
二十八、完成流程
==================================================

完成后：

1. 更新：
   control-room/RFQ-004/TASK_SPEC.md
   control-room/RFQ-004/EXECUTION_LOG.md
   control-room/RFQ-004/FINAL_REPORT.md

2. TASK_SPEC 必须保留本任务 Owner/CEO 原始要求，
   不要自行缩减业务范围。

3. commit。

4. push feature/v1-3。

5. COORDINATION：
   RFQ-004 → REVIEW_REQUIRED

6. 不要自己写 REVIEW PASS。

7. 不要标 REVIEWED_DONE。

8. 确认：
   local HEAD == remote feature/v1-3 HEAD

==================================================
二十九、最后汇报格式
==================================================

完成后只汇报：

- commit SHA
- branch / remote HEAD
- 新增主要生产文件
- 复用了哪些现有 V1.2 / INSO 基础设施
- V1.3“发给采购”扫描实现位置
- 72小时/latest实现位置
- 日期→制单人 DTO/提取实现位置
- INSO retry复用方式
- focused测试结果
- full safe/offline测试结果
- Ruff
- git diff --check
- 明确：
  “未执行真实 Save、Save-and-Send、Google写入、更新报价、SMTP或真实业务提交”
- 明确：
  “未覆盖当前 V1.2 EXE”
- 当前仍 UNKNOWN 的 live-only 事项

最后一句：

“RFQ-004 已提交 CEO Review。”