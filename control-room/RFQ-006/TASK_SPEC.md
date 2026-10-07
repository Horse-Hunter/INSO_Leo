# RFQ-006 — V1.2 + V1.3 production integration and release

Owner-authorized requirements, 2026-10-07. Independent CEO Review REQUIRED.

你是新的 RFQ-006 Integration Executor。

任务：
完成 V1.3 最终集成：

V1.2 + V1.3
→ 统一15分钟循环
→ 故障隔离
→ GUI状态
→ 229邮件
→ production configuration
→ read-only live acceptance
→ 最终 V1.3 Windows EXE 打包/部署

这是新的 Codex 窗口。

不要重新设计已经 CEO Review 通过的 RFQ-003 / RFQ-004 / RFQ-005。

==================================================
一、稳定基线
==================================================

仓库：

Horse-Hunter/INSO_Leo

V1.3 当前稳定分支：

feature/v1-3

最新 REVIEWED_DONE HEAD：

75b6043c3819339cbd8fe7ad38388de9d484ad1a

其中：

RFQ-003：
V1.2 failure isolation & recovery
REVIEWED_DONE

RFQ-004：
V1.3 INSO quotation read pipeline
REVIEWED_DONE

RFQ-005：
V1.3 Google quotation update pipeline
REVIEWED_DONE

当前 V1.2 已部署 EXE SHA256：

1A49C9650BA531F2299326FFC89761D0391CD5F2C0FE32327DDD0736BD5C3E84

==================================================
二、新分支
==================================================

先：

git fetch

确认：

origin/feature/v1-3 HEAD =
75b6043c3819339cbd8fe7ad38388de9d484ad1a

然后从这个 REVIEWED_DONE 基线：

新建：

feature/v1-3-integration

并使用新的独立 worktree。

不要直接继续修改：

feature/v1-3

feature/v1-3 作为已 Review 的 RFQ-004/005 基线保留。

不要修改 feature/v1-2。

==================================================
三、开始前必须阅读
==================================================

先阅读：

- AI_START_HERE.md
- AGENTS.md
- docs/PROJECT_BASELINE.md
- docs/AI_WORKFLOW.md
- docs/MODULE_INDEX.md
- control-room/COORDINATION.md

重点：

- control-room/RFQ-003/TASK_SPEC.md
- control-room/RFQ-003/EXECUTION_LOG.md
- control-room/RFQ-003/FINAL_REPORT.md
- control-room/RFQ-003/REVIEW.md

- control-room/RFQ-004/TASK_SPEC.md
- control-room/RFQ-004/EXECUTION_LOG.md
- control-room/RFQ-004/FINAL_REPORT.md
- control-room/RFQ-004/REVIEW.md

- control-room/RFQ-005/TASK_SPEC.md
- control-room/RFQ-005/EXECUTION_LOG.md
- control-room/RFQ-005/FINAL_REPORT.md
- control-room/RFQ-005/REVIEW.md

重点代码：

V1.2：
- src/launcher/backend.py
- src/launcher/v12_composition.py
- src/launcher/v12_gui.py
- src/workflow/v12_flow.py
- src/workflow/v12_faults.py
- src/workflow/v12_store.py
- src/sheets/purchase_status.py
- notification / smtp
- browser / CDP / INSO session

V1.3：
- src/workflow/v13_quotation.py
- src/workflow/v13_quote_update.py
- src/inso/quotation_read.py
- src/sheets/quotation_candidates.py
- src/sheets/quotation_input.py
- src/launcher/v13_quotation.py
- src/launcher/google_quote_update.py
- src/quotation/update_result.py

不要复制一套新的基础设施。

==================================================
四、建立 RFQ-006
==================================================

创建：

control-room/RFQ-006/TASK_SPEC.md
control-room/RFQ-006/EXECUTION_LOG.md
control-room/RFQ-006/FINAL_REPORT.md

COORDINATION 新增：

RFQ-006
V1.2 + V1.3 production integration and release
ACTIVE
feature/v1-3-integration
REQUIRED

完成后只能：

REVIEW_REQUIRED

不得自行：

REVIEWED_DONE

==================================================
五、RFQ-006最终业务循环
==================================================

程序点击：

开始询价

后进入统一循环。

每个 cycle：

==============================

阶段A：V1.2采购模块

扫描：

Google status == 未发

逐行执行现有 V1.2。

==============================

阶段B：V1.3报价模块

V1.2 当前 cycle 处理完可继续的订单后：

立即扫描：

Google status == 发给采购

逐行执行：

RFQ-004
→ INSO最近72小时最新报价

若：
NO_RECENT_QUOTE

→ 当前行结束
→ 下一行

若：
ROW_FAILED

→ 当前行异常处理
→ 下一行

若：
QUOTE_FOUND

→ RFQ-005
→ Google 报价输入
→ 更新报价
→ Apps Script
→ 验证采购已报价

==============================

阶段C：

当前 cycle 全部结束后：

等待直到下一次15分钟 poll。

==================================================
六、特别重要：没有额外等待
==================================================

如果当前 V1.2：

0条 未发

必须：

立即进入 V1.3。

不能：

“V1.2没单
→ 等15分钟
→ 才V1.3”。

正确：

V1.2 0条
→ 立即 V1.3
→ cycle结束
→ 再等待下一轮15分钟。

同样：

V1.2最后一条处理完

不要额外等待180秒再进入 V1.3。

V1.2 180秒 cooldown
只存在于：

相邻两个 V1.2 订单之间。

==================================================
七、V1.2 180秒规则
==================================================

保持 RFQ-003 Review 后的规则：

V1.2：

订单A真正闭环
且
后面还有下一条 V1.2

→ 等180秒

→ 订单B

包括：

- 正常采购
- duplicate
- no quote
- row bad input
- 当前行abort

只要：

当前行已经明确闭环
并且
还有下一笔 V1.2

才等待180秒。

不要在：

- 最后一笔后；
- V1.2_PAUSED后；
- GLOBAL_STOP后；
- 没有下一笔时；
- 进入V1.3前

额外sleep。

==================================================
八、V1.3无正常行间 cooldown
==================================================

V1.3：

row1
→ closed-loop

立即：

row2

不要：

180秒 cooldown。

只有 RFQ-004 的：

INSO query failure retry

仍保留：

180秒
初次 + 3 retries。

Google quotation update retry
也不使用180秒。

==================================================
九、15分钟调度
==================================================

复用现有 scheduler / launcher loop。

不要重新造另一个 daemon。

统一的业务 poll interval：

15分钟。

要求：

- shutdown可立即打断等待；
- GUI退出不遗留后台无限线程；
- 不重叠启动两个cycle；
- 上一个cycle没完成时，不启动下一cycle；
- 不并发跑两套 V1.2/V1.3。

15分钟应理解为：

一次完整 cycle 结束后，
等待到下一轮。

优先保持现有 V1.2 scheduler 语义，
不要为了 V1.3 改成复杂 cron engine。

==================================================
十、模块隔离核心规则
==================================================

必须严格实现：

--------------------------------
A. GLOBAL_STOP
--------------------------------

两边都停止。

包括：

1. INSO登录/人工验证/CAPTCHA/设备验证；
2. INSO query initial+3 retry 全失败；
3. Google Sheets整体 read/auth/schema failure；
4. Google “报价输入”整体结构/location binding失败；
5. workflow SQLite/ledger关键状态不可信；
6. shared Chrome/CDP reconnect最终失败；
7. 其他明确共享基础设施不可用。

行为：

- V1.2停止；
- V1.3停止；
- GUI显示全局异常；
- 发229邮件；
- 不再开始新业务操作。

--------------------------------
B. V1.2_PAUSED
--------------------------------

只停止 V1.2。

V1.3继续。

典型：

IC.net不可用
或
明确孤立于共享设施的未知V1.2 blocker。

行为：

V1.2暂停
→ 立即进入/保持 V1.3 polling。

--------------------------------
C. V1.3 ROW_FAILED
--------------------------------

只结束当前报价订单。

例如：

- SOURCE_IDENTITY_UNRESOLVED
- SOURCE_IDENTITY_AMBIGUOUS
- SOURCE_MPN_UNAVAILABLE
- SOURCE_CHANGED
- QUOTE_INPUT_WRITE_FAILED
- QUOTE_INPUT_READBACK_MISMATCH
- UPDATE_RESULT_UNCONFIRMED
- SOURCE_STATUS_NOT_UPDATED

行为：

- GUI当前行红色；
- log；
- 229邮件；
- 下一条 V1.3；
- 不暂停 V1.3；
- 不暂停 V1.2；
- 不GLOBAL_STOP。

==================================================
十一、网站故障隔离
==================================================

保持 Owner 已确认规则。

INSO：

任何真正 INSO 登录/人工验证/关键查询问题
→ shared
→ 两边GLOBAL_STOP。

IC.net：

问题
→ 仅 V1.2 pause
→ V1.3继续。

其他 Research website：

问题
→ 当前source失败
→ 使用剩余sources
→ 两边继续。

任何网站出现登录/验证/不可用问题：

都发邮件到：

linan229@qq.com

提醒 Owner 人工登录/检查。

不要因为普通 Research source失败
就停 V1.3。

==================================================
十二、V1.2 Save-and-Send特殊规则
==================================================

完全保留 RFQ-003。

如果明确：

Save-and-Send click 已发生

但最终保存状态无法确认：

- 不重发；
- 内部保持 SUBMIT_UNCONFIRMED；
- Google source仍更新 发给采购；
- GUI浅黄色：
  已发采购（待确认）
- 229邮件人工确认；
- V1.2继续；
- V1.3允许后续查询；
- 不GLOBAL_STOP。

绝对不要为了 RFQ-006
重新做第二次 Save-and-Send。

==================================================
十三、V1.2 Google发给采购写回失败
==================================================

保持现有：

采购已处理
但 Google 发给采购 写回失败：

- 不重新采购；
- GUI黄色：
  采购已处理，表格状态待人工更新
- 229邮件；
- V1.2继续；
- V1.3继续；
- Google状态仍未发时 V1.3自然看不到；
- Owner人工改为发给采购后，V1.3下一轮处理。

不要恢复旧的“整批停止”。

==================================================
十四、V1.2 crash/restart
==================================================

完全保留 RFQ-003 Review 规则。

只有真正开始过且未闭环的 V1.2 row：

重启：

标红
处理中断

可能已发送：
处理中断（可能已发送，请先核对）

明确未发送：
处理中断（未发送）

该行自动skip。

后面的预入队、未真正开始订单：

必须继续正常处理。

不要让 RFQ-006 scheduler
重新引入 RFQ-003 B1。

Owner将人工处理红行后：

Google状态改：

未发 → 发给采购

下一轮：

V1.2不再碰它
V1.3开始处理报价。

==================================================
十五、V1.3 crash/restart
==================================================

V1.3 与 V1.2 不同。

不要做永久 interruption quarantine。

程序重启：

如果 source：

采购已报价

→ 不进入V1.3。

如果：

发给采购

→ 正常重新走：

RFQ-004
→ RFQ-005。

如果上一次实际上已经成功更新，
Script已有报价：

下一次：
已有报价1行

→ 正常闭环。

这是 Owner 已确认的幂等设计。

==================================================
十六、V1.3成功/等待/异常GUI
==================================================

整合到现有 GUI，
不要重做UI框架。

尽量复用现有订单行展示。

至少支持以下用户可理解状态。

V1.3：

NO_RECENT_QUOTE：

建议显示：

等待采购报价

或：

采购暂未报价

普通/中性颜色。

--------------------------------

QUOTE update成功：

UPDATED_INSERTED
或
UPDATED_ALREADY_EXISTS

建议：

采购已报价

绿色/已完成语义。

--------------------------------

ROW_FAILED：

红色。

用户可读：

报价处理异常，需人工处理

可根据 reason 增加简短说明，
但不要把内部异常堆栈直接显示。

==================================================
十七、V1.2 GUI保持
==================================================

已有：

重复订单红色
调研无报价
已发采购
已发采购（待确认）
采购已处理，表格状态待人工更新
处理中断
全局错误

这些已 Review 行为不得因为V1.3集成而消失。

不要大规模改GUI布局。

==================================================
十八、229邮件整合
==================================================

继续复用现有：

notification ledger
SMTP transport
idempotency

收件人：

linan229@qq.com

不要另写第二套 SMTP。

RFQ-006 新增 V1.3 row failure邮件。

标题/正文保持简洁。

至少包含：

- 模块：V1.3报价
- inquiry_id
- worksheet
- source row（作为定位信息，不作为业务身份）
- MPN
- 固定 reason
- Owner建议动作

例如：

SOURCE_STATUS_NOT_UPDATED

说明：

“更新报价结果已确认，但源订单状态未变为采购已报价，请人工检查。”

UPDATE_RESULT_UNCONFIRMED：

“更新报价多次无法确认，请人工检查该订单；程序已跳过并继续其他订单。”

不要把：

Google provider raw error
cookie
token
OAuth secret
页面完整HTML

写进邮件。

==================================================
十九、SMTP失败
==================================================

保持现有规则：

SMTP失败
→ 不影响 V1.2
→ 不影响 V1.3
→ notification ledger保留待重试
→ log

绝不能：

邮件发不出去
→ GLOBAL_STOP业务。

==================================================
二十、V1.3红行人工解除
==================================================

Owner 已确认：

不需要额外GUI按钮。

如果 V1.3 ROW_FAILED：

程序本地可以记录：

manual/error state

后续自动扫描时，
只要 Google source 仍是：

发给采购

就不要自动无限重试该“已明确失败”的行。

Owner人工处理完：

把 source 改：

采购已报价

下一轮自然消失。

注意：

这条是针对 RFQ-005 operational ROW_FAILED。

不要把：

NO_RECENT_QUOTE

放入红行/人工hold。

NO_RECENT_QUOTE：

下一轮15分钟必须继续自动查询。

需要一个轻量 durable V1.3 exception/hold ledger
或复用现有安全持久层。

要求：

- 不新建第二套复杂 workflow DB；
- 可以在现有SQLite中增加极小的V1.3 durable state；
- schema migration必须向后兼容；
- DB故障属于GLOBAL_STOP；
- V1.3 crash本身不是红行；
- 只有已经明确产出 ROW_FAILED 的订单进入hold。

如果已有机制可以安全复用，优先复用。

==================================================
二十一、V1.3 hold解除规则
==================================================

对于本地已有 ROW_FAILED hold：

Google source仍：

发给采购

→ GUI保持红色
→ 自动skip
→ 不重复发送同一故障邮件。

Google source变：

采购已报价

→ 认为 Owner已人工完成
→ 清除/关闭hold
→ GUI恢复完成态
→ 不再处理。

如果该source row被删除/无法定位：

保留安全日志，
不要猜另一条订单。

==================================================
二十二、V1.3邮件去重
==================================================

每个：

inquiry_id
+
failure episode/reason

不要每15分钟发一次相同邮件。

复用 notification ledger/idempotency。

只有：

首次进入人工失败
或
reason发生实质变化

才创建新通知。

SMTP失败按原机制后续retry。

==================================================
二十三、production configuration
==================================================

RFQ-005 当前 live-only UNKNOWN：

- 生产 gid；
- input header row；
- input first row；
- first column；
- 实际14列表头布局；
- Google 更新报价按钮实际 role/DOM；
- popup实际DOM；
- Script刷新延迟；
- Google登录/session。

RFQ-006 负责尽可能通过：

READ-ONLY ACCEPTANCE

确认可确认的项目。

禁止猜值。

==================================================
二十四、允许的 READ-ONLY live acceptance
==================================================

可以在 Owner 当前现有生产环境：

仅做读取/观察。

允许：

- Google spreadsheet metadata读取；
- 查找 title = 报价输入；
- 获取真实 sheetId/gid；
- 读取报价输入表头；
- 确认第一条输入区位置；
- 读取/观察当前Google页面；
- 确认“更新报价”按钮存在及实际可定位方式；
- 检查登录/session；
- INSO只读查询页面结构；
- 查看现有未改变的页面DOM/role；
- 截图/诊断。

禁止：

- 写真实报价输入；
- 点击真实“更新报价”；
- 执行真实Apps Script；
- Save；
- Save-and-Send；
- 修改真实Google业务状态；
- 发真实业务提交。

如果 read-only discovery 可以确认：

gid
header row
input row
first column

则把真实值写入正式 production config。

不要 hardcode到Python源码。

==================================================
二十五、无法只读确认的东西
==================================================

例如：

只有点击“更新报价”后
才会出现的真实 popup DOM。

如果无法在不提交业务的情况下确认：

保持：

LIVE_SELECTOR_ACCEPTANCE = PARTIAL / UNKNOWN

不要编造。

生产代码必须：

fail closed
+
保留明确日志。

如果最终真实运行前需要一次受控业务验收，
在 FINAL_REPORT 中单独列：

“需要 Owner 授权的一次 live acceptance 操作”

不要擅自执行。

==================================================
二十六、报价输入真实geometry
==================================================

Owner最新明确：

真实 worksheet title：

报价输入

不是：

报价输入子表

必须通过 metadata确认：

title == 报价输入
真实 sheetId == 配置 gid

然后读取真实表头。

必须确认14列：

日期
型号
品牌
数量
币种
供方返点
报价
供方未税价
平台数量
批号
货期
备注
备注2
制单人

找到：

header_row
first_column

并确定：

第一条报价输入行 input_row。

不能凭历史截图直接猜。

如果只能确认表头不能确认输入行：

不要猜，
明确 report blocker。

==================================================
二十七、统一浏览器
==================================================

V1.2 + V1.3 必须继续共用：

同一 fixed Chrome
同一 CDP：
127.0.0.1:9222
同一 profile
同一 cookies/session

不能：

启动两套Chrome。

V1.2 INSO：
fresh operation tab / row。

V1.3 INSO：
fresh operation tab / row。

V1.3 Google update：
fresh owned Google operation tab / attempt。

共享：

BrowserHandle/context/profile。

==================================================
二十八、空闲浏览器状态
==================================================

保持 RFQ-002 / RFQ-003 已 Review 规则。

普通业务完全settled：

固定浏览器可以 park 到：

恰好一个 about:blank。

但如果存在：

INSO manual verification page
或
Google human-needed auth page

必须保留该页面。

不能为了“空闲清理”把人工验证页面关掉。

==================================================
二十九、shared CDP断线
==================================================

保持现有策略：

短暂断线：

自动reconnect。

最多3次恢复。

恢复成功：

两模块继续。

最终失败：

GLOBAL_STOP
+
229。

不要：

- close固定Chrome；
- 新建profile；
- 清cookie；
- 删除profile。

==================================================
三十、V1.3与V1.2循环顺序
==================================================

一个 cycle 内：

优先：

V1.2

再：

V1.3。

但是如果：

V1.2_PAUSED

不要阻塞V1.3。

例如：

IC.net failure
→ V1.2_PAUSED
→ 同cycle立即运行V1.3。

如果：

GLOBAL_STOP

则：

V1.3也不能继续。

==================================================
三十一、V1.2未知异常
==================================================

保持 Owner规则：

如果明确局限于 V1.2业务链，
且不是：

Google
INSO
CDP
DB

共享设施：

→ V1.2_PAUSED
→ 229
→ V1.3继续。

不要为了“保险”全部GLOBAL_STOP。

==================================================
三十二、V1.3未知异常
==================================================

如果能明确是：

当前 V1.3 row内部业务/adapter异常

→ 当前row ROW_FAILED
→ 229
→ 下一条。

如果来源是：

共享 Sheets
ledger
INSO
CDP
Google auth/schema

→ GLOBAL_STOP。

不要 broad except 全部 global。

==================================================
三十三、V1.3 no quote
==================================================

这是正常状态：

INSO query成功
+
72小时内0条

→ NO_RECENT_QUOTE

行为：

- 不发邮件；
- 不红；
- 不hold；
- Google保持 发给采购；
- 下一15分钟cycle重新查。

==================================================
三十四、V1.3 update failure hold
==================================================

这些：

QUOTE_INPUT_WRITE_FAILED
QUOTE_INPUT_READBACK_MISMATCH
UPDATE_RESULT_UNCONFIRMED
SOURCE_STATUS_NOT_UPDATED

属于：

人工处理状态。

进入 durable hold。

下一轮：

状态仍发给采购
→ skip自动重试。

这与 crash/restart不同。

如果只是进程：

在RFQ-005中途crash
而没有产出最终 ROW_FAILED

不要自动hold。

重启后：

可重新正常处理。

==================================================
三十五、RFQ-004 source row failure hold
==================================================

这些：

SOURCE_IDENTITY_UNRESOLVED
SOURCE_IDENTITY_AMBIGUOUS
SOURCE_MPN_UNAVAILABLE
SOURCE_CHANGED

如果 RFQ-004 已经明确形成：

ROW_FAILED

同样进入V1.3人工hold。

不要下一轮自动重复撞同一问题。

Owner处理后改成采购已报价
→ 清除。

==================================================
三十六、GUI启动 / 停止
==================================================

保留现有：

开始询价

用户点击后：

统一V1.2/V1.3 scheduler启动。

不要新增：

“开始V1.3”

第二按钮。

停止/退出：

必须停止：

当前安全边界之后的新业务动作
+
scheduler等待。

如果正在：

不可安全中断的提交确认阶段

遵循现有安全逻辑。

不要强杀导致重复提交。

==================================================
三十七、GUI模块状态
==================================================

建议只增加轻量状态，不大改界面。

例如总状态可表达：

运行中
V1.2暂停 / V1.3正常
全局暂停
等待下一轮

不要向Owner暴露：

FaultScope枚举
内部class name
stack trace。

==================================================
三十八、日志
==================================================

必须能够区分：

cycle_id
module：
V1.2 / V1.3
inquiry_id
stage
result/reason

但不要日志泄露：

OAuth token
cookies
Google provider原始敏感内容
客户敏感整表数据
完整页面HTML。

==================================================
三十九、测试：combined scheduler
==================================================

必须新增组合测试。

至少：

1.
V1.2 0条
→ 同cycle立即执行V1.3。

2.
V1.2 1条
→ 完成后立即V1.3
→ 没有180秒尾部sleep。

3.
V1.2 2条
→ 中间180秒
→ 第二条
→ V1.3
→ 没有额外180秒。

4.
V1.2 duplicate/no quote等闭环
→ 如果还有下一条V1.2才180秒。

5.
V1.2 PAUSED
→ V1.3仍执行。

6.
GLOBAL_STOP
→ V1.3不执行。

7.
V1.3 NO_RECENT_QUOTE
→ 下一15分钟cycle仍再次查询。

8.
V1.3 ROW_FAILED
→ 同cycle下一row继续。

9.
V1.3 held red row
→ 下一cycle source仍发给采购
→ skip
→ 不重复mail。

10.
Owner改采购已报价
→ hold自动解除。

==================================================
四十、测试：fault isolation
==================================================

至少：

11. IC.net fail：
V1.2 pause
V1.3 continue。

12. other Research source fail：
V1.2继续
V1.3继续。

13. INSO auth：
both stop。

14. Sheets整体auth：
both stop。

15. workflow DB：
both stop。

16. shared CDP最终fail：
both stop。

17. SMTP fail：
both continue。

18. V1.3 input row fail：
下一V1.3继续
V1.2状态不受影响。

19. V1.3 update unconfirmed：
hold当前行
下一行继续。

20. V1.3 source status not updated：
hold当前行
下一行继续。

==================================================
四十一、测试：restart
==================================================

至少：

21.
V1.2 active row crash
+
后续queued rows

→ 只active红
→ 后续继续。

22.
V1.2 cooldown crash

→ 后续queued不红。

23.
V1.3 crash before最终结果

→ restart重新处理
→ 不hold。

24.
V1.3明确ROW_FAILED后crash

→ restart保持hold。

25.
V1.3 update实际已成功，
source采购已报价

→ restart不处理。

==================================================
四十二、测试：邮件
==================================================

至少：

26.
V1.3首次ROW_FAILED
→ 创建1封229通知。

27.
15分钟后仍同reason
→ 不重复创建通知。

28.
SMTP发送失败
→ 业务继续
→ notification pending。

29.
新的failure reason episode
→ 可生成新通知。

30.
共享GLOBAL_STOP
→ 229通知。

==================================================
四十三、测试：GUI
==================================================

至少：

31.
NO_RECENT_QUOTE：
显示普通等待态。

32.
UPDATED：
显示采购已报价。

33.
ROW_FAILED：
红色。

34.
SUBMIT_UNCONFIRMED：
保持现有黄色。

35.
V1.2 writeback pending：
保持现有黄色。

36.
GLOBAL_STOP：
显示全局错误。

37.
V1.2 pause + V1.3 active：
不要显示成整个程序已死。

==================================================
四十四、live read-only discovery
==================================================

如果本机当前 production environment 可安全访问：

允许用 read-only 方式确认：

Google：

- spreadsheet ID
- title 报价输入
- sheetId/gid
- header row
- input row
- first column
- 按钮存在
- login状态

不要点击：

更新报价。

INSO：

仅检查已 Review reader 所需页面仍可读取。

不要提交任何业务。

所有真实发现记录进：

EXECUTION_LOG

明确标：

READ_ONLY_LIVE_ACCEPTANCE

==================================================
四十五、production config
==================================================

如果 read-only discovery 得到真实：

gid
header_row
input_row
first_column

写入现有正式 production config机制。

要求：

- 不另造第二个配置文件体系；
- 不把值硬编码src；
- 不提交token/secret；
- 配置缺失时 fail closed；
- deployed runtime可读取。

如果未能确认：

不要猜。

FINAL_REPORT中写：

BLOCKED LIVE CONFIG

不要因此擅自提交真实数据。

==================================================
四十六、最终打包前
==================================================

在 source/offline tests全部PASS后：

执行：

- full safe/offline pytest
- Ruff
- git diff --check
- frozen/build self-check
- clean release scan

然后才能准备：

V1.3 EXE。

==================================================
四十七、最终发布名称
==================================================

这次是新版本。

不要覆盖 V1.2 目录。

建议正式输出：

D:\Program_Leo\INSO_Leo\dist\INSO_V1.3\INSO_V1.3.exe

保留现有：

D:\Program_Leo\INSO_Leo\dist\INSO_V1.2\INSO_V1.2.exe

作为可回滚版本。

不要删除 V1.2。

==================================================
四十八、发布备份
==================================================

打包/部署前：

创建明确 release backup。

至少保留：

当前 V1.2
+
本次 V1.3 pre-release / prior build（若有）。

不能覆盖旧 backup。

记录：

backup path
EXE SHA256。

==================================================
四十九、运行时资产
==================================================

不得破坏：

- production config；
- OAuth config/grant；
- runtime SQLite DB；
- existing workflow history；
- fixed Chrome profile；
- cookies/session；
- user runtime data；
- logs；
- research output；
- notification state。

升级 V1.3 必须兼容已有 V1.2 runtime。

如果新增SQLite schema：

必须 migration
+
向后兼容
+
自动升级测试。

==================================================
五十、打包后验证
==================================================

最终 EXE：

执行：

1. frozen self-check；
2. deployed self-check；
3. clean staged scan；
4. idle launch；
5. GUI显示正常；
6. 不点击“开始询价”进行真实业务；
7. fixed Chrome/profile不被重建；
8. V1.2旧EXE仍存在。

如果 Owner没有另行明确授权：

禁止通过最终EXE：

真实采购
真实报价更新。

==================================================
五十一、不要擅自做真实更新报价
==================================================

即使 RFQ-006 最终代码全部完成：

没有 Owner 明确授权时，

不要：

写真实“报价输入”
点击真实“更新报价”
执行Apps Script。

read-only discovery可以做。

真正提交行为不属于默认授权。

==================================================
五十二、Review边界
==================================================

Executor完成后：

只允许：

REVIEW_REQUIRED。

不要自行：

PASS
REVIEWED_DONE。

CEO会独立检查：

- combined scheduler；
- module isolation；
- V1.3 hold；
- notifications；
- GUI；
- config；
- read-only acceptance证据；
- packaging；
- EXE；
- V1.2 regression。

==================================================
五十三、验证结果最低要求
==================================================

必须汇报：

- RFQ-006 focused
- combined scheduler focused
- V1.3 integration focused
- full safe/offline
- Ruff
- git diff --check
- build
- frozen self-check
- clean release scan
- deployed self-check
- idle launch

==================================================
五十四、提交
==================================================

完成后：

commit
push：

feature/v1-3-integration

COORDINATION：

RFQ-006 → REVIEW_REQUIRED

确认：

local HEAD
==
remote feature/v1-3-integration HEAD

==================================================
五十五、最终汇报格式
==================================================

最后只汇报：

- commit SHA
- branch / remote HEAD
- 新增/修改主要生产文件
- combined scheduler实现位置
- V1.2/V1.3 fault isolation实现位置
- V1.3 durable hold实现位置
- V1.3 GUI状态实现位置
- V1.3 229通知实现位置
- 15分钟cycle实现
- V1.2 180秒 cooldown验证
- V1.3无cooldown验证
- read-only live acceptance结果
- 确认到的生产：
  gid
  header row
  input row
  first column
  （若无法确认明确写UNKNOWN/BLOCKED，不猜）
- focused测试
- combined测试
- full safe/offline测试
- Ruff
- git diff --check
- build/self-check/scan结果
- V1.3 EXE SHA256
- V1.3部署路径
- backup path
- V1.2 EXE仍保留确认
- 明确：
  “未执行未经Owner授权的真实采购、真实报价写入或更新报价”
- 仍存在的live-only UNKNOWN
- 是否存在必须由Owner授权才能完成的一次live acceptance

最后一句：

“RFQ-006 已提交 CEO Review。”

## Owner correction / CEO repair — 2026-10-07
Supersedes earlier header/geometry UNKNOWN assumptions: 报价输入 intentionally has no header.
QUOTE_INPUT_GEOMETRY CONFIRMED: gid=489913321, input_row=1, first_column=1, target A1:N1.
header_row is absent; header NONE / NOT APPLICABLE. QUOTATION_COLUMNS is the INSO raw14 order,
not Google header text. Revalidate unique metadata title/gid before each write and UI opening.
Strict hold relocation remains first; on conflict only the original worksheet/position is a
human-status safety anchor (never business identity). Sent blocks that position; quoted closes
the hold; missing/unknown status retains it and unrelated rows continue.
Unknown V1.3 operation/reader/updater exceptions GLOBAL_STOP V13_INTERNAL_FAILURE without hold;
only typed row-local failures and reviewed retry exhaustion may become ROW_FAILED.
Every website SOURCE_UNAVAILABLE enqueues one sanitized, deduplicated owner229 alert via existing
ledger/worker. INSO authentication is global; IC.net pauses V1.2; other sites continue.
Rebuild, backup/deploy V1.3 assets and own config; preserve V1.2 executable/config bytes.
Read-only metadata/DOM only. No business write/click/Script/Save/Send or actual procurement.
Real button DOM and live popup/status/delay remain UNKNOWN unless safely read-only verified.
Final status REVIEW_REQUIRED; REVIEW.md is CEO-owned and must remain unchanged.
