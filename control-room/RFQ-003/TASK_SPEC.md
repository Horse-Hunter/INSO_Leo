# RFQ-003 — Owner authorized V1.2 resilience closeout

Source: Owner request 2026-10-07. Branch feature/v1-2. No V1.3 implementation.
Status source: control-room/COORDINATION.md. Independent Review REQUIRED.

Executor delivery 2026-10-07: implementation and offline verification completed;
V1.2 rebuilt, backed up, overwritten and idle-launched. REVIEW_REQUIRED only,
not independently approved. Evidence: EXECUTION_LOG.md and FINAL_REPORT.md.
Owner requirements below are preserved without changing their meaning.

继续维护现有 V1.2，执行新的 RFQ-003。

本次不是开发 V1.3 报价功能，而是先完成：
“V1.2 采购模块故障隔离、恢复规则、Save-and-Send 新策略、3分钟行间冷却”。

完成后重新打包 V1.2，并覆盖当前 V1.2 部署。

工作分支：
feature/v1-2

开始前：
1. 同步远端最新 feature/v1-2。
2. 确认当前 RFQ-002 = REVIEWED_DONE。
3. 阅读：
   - AI_START_HERE.md
   - AGENTS.md
   - docs/PROJECT_BASELINE.md
   - docs/AI_WORKFLOW.md
   - docs/MODULE_INDEX.md
   - control-room/COORDINATION.md
   - RFQ-002 当前 Task Spec / Execution Log / Final Report / Review
4. 创建：
   - control-room/RFQ-003/TASK_SPEC.md
   - control-room/RFQ-003/EXECUTION_LOG.md
   - control-room/RFQ-003/FINAL_REPORT.md
5. COORDINATION 中新增 RFQ-003，初始状态 ACTIVE。

==================================================
一、总原则
==================================================

未来 V1.2=采购模块，V1.3=报价模块。

RFQ-003 暂时不要实现 V1.3，但必须把 V1.2 的故障边界改造成：

1. 单笔业务异常：
   只结束当前订单，继续下一笔。

2. V1.2 自身异常：
   可以暂停 V1.2，但不能再用“所有异常都直接杀死整个程序”的粗粒度逻辑。
   为后续 V1.3 独立运行保留明确的 module-level pause 边界。

3. 只有共享基础设施严重故障才允许 GLOBAL_STOP。

不要额外设计第二套浏览器、第二套 CDP、第二套 workflow 身份体系。

继续复用现有：
- inquiry_id
- record_identity
- workflow DB
- fixed Chrome/CDP
- notification ledger
- Sheets adapter
- INSO lower-history / Stock_VenQuote 能力

==================================================
二、V1.2 故障规则
==================================================

【1】Research 五个来源均无报价 / NO_MATCHING_PRODUCT

这是正常安全终态。

行为：
- 当前订单结束；
- 不进入采购；
- GUI 保持“调研无报价（未发采购）”；
- 现有异常提醒正常处理；
- V1.2继续下一笔；
- 不得进入全局 MANUAL_REVIEW / STOP。

--------------------------------------------------

【2】网站登录 / 人工验证问题

A. INSO：
包括登录失效、CAPTCHA、手机验证码、设备验证。

行为：
- 保留 human-needed 页面；
- V1.2 停止；
- 这是共享基础设施故障，未来 V1.3 也必须停；
- 发邮件到：
  linan229@qq.com
- 不关闭固定 Chrome/context/profile；
- 不清 cookie；
- 不继续新的 INSO 操作。

B. IC.net：

行为：
- 停止 V1.2；
- 但必须是 V1.2 module-level pause，不要设计成整个程序退出；
- 为未来 V1.3 继续运行留下边界；
- 发邮件到 linan229@qq.com，提醒人工登录。

C. 其他 Research 网站：

行为：
- 当前来源记失败；
- 继续其他来源；
- V1.2不停；
- 未来 V1.3当然不受影响；
- 网站需要人工登录/验证时发邮件到 linan229@qq.com。

--------------------------------------------------

【3】Save-and-Send 已点击，但后续确认失败

这是本次非常重要的业务规则变化。

以前：
必须确认 SAVED 才允许 Google 写“发给采购”。

现在改成：

只要程序能够证明：
- durable submit state 已正确落库；
- Save-and-Send 确实执行过唯一一次 click；

那么即使后面的 INSO 上方列表确认失败/卡住/无法确定最终确认结果：

也必须：
- 永远禁止再次点击 Save-and-Send；
- Google 源状态写为“发给采购”；
- V1.2继续下一笔；
- 不进入全局停机；
- GUI 当前行淡黄色；
- GUI 文案：
  “已发采购（待确认）”
- 发邮件到 linan229@qq.com，提醒 Owner 人工确认实际发送状态。

本地 durable state 必须区分：
- SAVED
- 已点击但后确认失败（可使用清晰的 SUBMIT_UNCONFIRMED 或等价独立状态）

不能把二者伪装成完全相同的事实。

注意：
如果程序无法证明 Save-and-Send 曾经真正执行过，则绝不能直接写成“发给采购”。

--------------------------------------------------

【4】采购录单阶段失败，且尚未点击 Save-and-Send

包括但不限于：
- AI型号校验失败；
- 品牌匹配失败；
- 数量不一致；
- 采购员选择失败；
- 控件缺失；
- AI结果未就绪；
- 页面结构异常；
- 其他明确发生在 Save-and-Send 前的录单异常。

行为：
- 只结束当前订单；
- 不点击 Save-and-Send；
- 不写 Google“发给采购”；
- GUI显示当前行异常；
- 发229异常邮件；
- V1.2继续下一笔。

--------------------------------------------------

【5】采购已处理，但 Google“发给采购”写回失败

行为：
- 不重新采购；
- 不再次 Save-and-Send；
- 当前订单业务上结束；
- V1.2继续下一笔；
- GUI淡黄色；
- GUI文案：
  “采购已处理，表格状态待人工更新”
- 发邮件到 linan229@qq.com；
- 邮件明确让 Owner 人工把该行改成“发给采购”。

不要因为该 Sheets 单格写回失败而停止 V1.2。

未来 V1.3因为暂时看不到“发给采购”，自然不会处理此单；
Owner 人工改好后未来周期自然接上。

--------------------------------------------------

【6】INSO 下方“采临时询价”查询链异常

这里要严格区分：

“查清楚但没有记录”
≠
“查询本身失败”。

以下属于查询链失败：
- 请求超时；
- 页面没有settle；
- 分页异常；
- 返回结构异常；
- 无法确认查询是否完整；
- 无法可靠判断有没有历史记录。

处理：

初次失败后：
1. 关闭当前本单 INSO tab；
2. 等待 3 分钟；
3. fresh INSO tab；
4. 重新执行同一笔查询。

允许失败后重试 3 次。

即：
初次尝试 + 最多3次重试。

任意一次成功：
继续当前订单。

连续3次重试仍失败：
- 记录安全日志；
- 发229邮件；
- 进入 GLOBAL_STOP；
- 未来 V1.2 + V1.3 都必须停。

查询失败绝不能当成“没有重复订单”。

等待3分钟期间：
不要并发启动新的 INSO 操作。

--------------------------------------------------

【7】Google Sheets 整体不可用

包括：
- OAuth授权失效；
- token/grant不可用；
- spreadsheet无法读取；
- worksheet无法读取；
- 关键表结构无法可靠识别；
- API整体不可用且短暂技术重试后仍失败。

这是 GLOBAL_STOP：

- V1.2停止；
- 未来V1.3停止；
- GUI全局异常；
- 记录日志；
- 发229。

--------------------------------------------------

【8】单条 Google 订单数据异常

例如：
- 型号空；
- 数量非法；
- 品牌空；
- 关键字段格式错误。

行为：
- 只跳过当前行；
- 不Research；
- 不采购；
- GUI标明当前行数据异常；
- 发229；
- V1.2继续下一行。

Owner修好Google源数据后，后续周期应可重新正常识别。

--------------------------------------------------

【9】168小时内确认重复订单

沿用现有业务规则：

- 当前单结束；
- GUI红色“重复订单”；
- 现有重复订单通知规则不变；
- 不采购；
- V1.2继续下一单；
- 不得造成模块停机。

--------------------------------------------------

【10】SQLite / workflow ledger 异常

包括：
- 数据库打不开；
- DB损坏；
- 关键状态无法持久化；
- inquiry_id / record_identity无法可靠读取；
- 无法确认历史 Save-and-Send 动作；
- durable workflow状态不可信。

这是 GLOBAL_STOP。

行为：
- V1.2停止；
- 未来V1.3停止；
- GUI全局异常；
- 日志；
- 229邮件。

--------------------------------------------------

【11】SMTP发送失败

SMTP不是业务前置条件。

行为：
- V1.2不停；
- notification ledger 保持幂等重试；
- 不因为邮件发不出去而停止采购；
- 多次失败可显示日志/GUI提醒，但业务继续。

--------------------------------------------------

【12】共享 Chrome / CDP 异常

例如：
- 127.0.0.1:9222瞬时连接失败；
- Playwright断连；
- context暂时不可用。

先自动重连，最多3次。

任意一次恢复：
继续。

连续3次仍失败：
GLOBAL_STOP。

要求：
- 不关闭固定 Chrome；
- 不删除/替换 profile；
- 不清 cookies；
- 不启动另一套临时Chrome替代生产profile。

--------------------------------------------------

【13】未分类异常

如果能够明确判断异常只属于 V1.2 自己的业务/代码路径：

- 暂停 V1.2；
- 发229；
- 保留日志；
- 不设计成整个程序直接退出；
- 为未来 V1.3 独立继续运行保留 module-level pause 边界。

只有能够判断属于共享基础设施时才升级 GLOBAL_STOP。

--------------------------------------------------

【14】处理过程中 Google 源订单被人工修改

如果只是行号移动，但可以通过：
original inquiry_id
→ workflow_store.get_by_inquiry_id
→ record_identity
→ relocate/re-read
可靠找到同一笔，则正常继续。

如果型号、数量、状态等关键字段发生冲突：
- 当前订单终止；
- 不覆盖人工数据；
- 不采购；
- GUI显示源订单已变更；
- 发229；
- V1.2继续下一笔。

--------------------------------------------------

【15】V1.2 空轮询

本轮没有任何“未发”：

这是完全正常。

立即结束本轮V1.2。

未来接入V1.3后：
必须立即进入V1.3，而不是等下一个15分钟。

RFQ-003 暂时不用实现V1.3。

--------------------------------------------------

【16】关键步骤卡住但没有明确错误

所有关键页面操作必须有 bounded timeout。

timeout后不要无限等待。

根据所在阶段转换成明确错误，再使用上述对应规则处理：

- INSO查询 → INSO查询重试规则；
- IC.net → V1.2暂停；
- 其他Research站点 → 当前来源失败后继续；
- 采购录单普通控件 → 当前订单结束后继续。

记录日志。

--------------------------------------------------

【17】程序被关闭 / 电脑重启 / EXE崩溃后的 V1.2恢复

V1.2 不自动续跑未闭环订单。

程序启动时发现历史订单未闭环：

- GUI该行标红；
- 自动队列跳过；
- 程序不重试、不续跑、不重新采购；
- V1.2从下一笔正常订单继续。

GUI文案：

如果明确知道 Save-and-Send 从未点击：
“处理中断（未发送）”

如果已经点击，或者无法可靠判断点击前/后：
“处理中断（可能已发送，请先核对）”

Owner会人工从头检查/处理该订单。

不要新增“人工恢复”“重新执行”等按钮。

--------------------------------------------------

【18】人工完成中断订单后的自动解除

Owner人工处理后会修改Google状态。

如果中断订单仍然是“未发”：
- GUI保持红色处理中断；
- V1.2继续跳过。

如果Owner把它改成“发给采购”：
- 程序自动识别人工处理完成；
- 红色中断状态解除；
- V1.2永久不再采购这条；
- 后续V1.3自然可以按“发给采购”处理。

Google状态就是业务事实来源。

==================================================
三、新增：V1.2每行闭环后固定冷却3分钟
==================================================

这是 Owner 新增的明确要求。

目的：
防止 V1.2 连续采购/发送过快，提高网页触发验证码或风控的概率。

规则：

V1.2同一批次中：

第1行完整闭环
→ 等待180秒
→ 第2行

第2行完整闭环
→ 等待180秒
→ 第3行

以此类推。

“闭环”包括：
- 正常采购完成；
- Save-and-Send待确认但已按新规则闭环；
- 重复订单；
- Research无报价；
- 单行数据异常；
- 采购录单失败；
- 其他已经得到明确最终处理结果的单行终态。

边界：

1. 只有“确实还有下一条V1.2订单要处理”时才等待3分钟。

2. 本轮最后一条V1.2闭环后：
   不额外等3分钟。

3. V1.2空轮询：
   不等待3分钟。

4. 这180秒等待必须可被 stop/shutdown 立即打断；
   禁止硬 sleep 导致程序无法正常退出。

5. INSO查询失败后的“3分钟重试等待”
   与
   “V1.2相邻订单3分钟冷却”
   是两套独立规则。

   同一笔订单还没闭环时，不叠加行间冷却。

6. 未来V1.3不使用这个行间3分钟节流。
   V1.3只是INSO查询/报价搬运，逐行连续即可。

==================================================
四、GUI / 状态要求
==================================================

至少支持清晰区分：

- 重复订单 → 红色
- 处理中断（未发送） → 红色
- 处理中断（可能已发送，请先核对） → 红色
- 已发采购（待确认） → 淡黄色
- 采购已处理，表格状态待人工更新 → 淡黄色
- 调研无报价（未发采购） → 现有正确状态
- 全局基础设施故障 → 明确全局错误

不要只靠颜色，必须有文字。

==================================================
五、邮件
==================================================

本 RFQ 新增/调整的人工异常提醒统一发：

linan229@qq.com

尤其：
- INSO人工验证；
- IC.net人工登录；
- 其他网站人工登录/验证；
- 单笔采购录单异常；
- Save-and-Send后确认失败；
- Google“发给采购”写回失败；
- Google/DB/CDP/INSO全局故障；
- V1.2未知内部异常。

继续复用现有 notification ledger / SMTP worker。

必须幂等。

不要改变已有：
- 重要订单通知收件人；
- 重复订单通知收件人；
除非 Owner 已明确修改。

==================================================
六、实现原则
==================================================

1. 最小修改。
2. 复用现有状态机、store、notification、browser/CDP、Sheets逻辑。
3. 不创建第二套生产链。
4. 不重构与本RFQ无关代码。
5. 不实现V1.3。
6. 不删除RFQ-002已经验证过的安全边界。
7. 不允许重新发送任何历史真实采购订单。
8. 不用真实验证码做测试。
9. 所有新增重试必须bounded。
10. 所有业务写动作保持可追踪和幂等。

特别注意：
RFQ-002刚刚修复的
“MANUAL_VERIFICATION_REQUIRED 必须保留 fresh human-needed INSO page”
不得回归。

==================================================
七、测试要求
==================================================

先补/调整离线 regression，至少证明：

1. NO_MATCHING_PRODUCT只结束当前单，下一单继续；
2. IC.net故障只产生V1.2暂停，不走global stop；
3. 其他Research站点故障不会停止整个V1.2；
4. INSO人工验证仍GLOBAL STOP并保留页面；
5. Save-and-Send已经点击但确认失败：
   - 不再点击第二次；
   - 内部记录独立状态；
   - Google尝试写“发给采购”；
   - GUI淡黄色；
   - 229 command；
   - 后续V1.2订单仍可继续；
6. Save-and-Send前录单失败不会写“发给采购”；
7. “发给采购”写回失败不会重新采购，也不会停V1.2；
8. INSO查询异常：
   - fresh tab；
   - 180秒逻辑可 fake clock；
   - 初次失败+最多3次重试；
   - 恢复后继续；
   - 全部失败才global stop；
9. 单条数据错误只跳过当前行；
10. workflow DB异常global stop；
11. SMTP失败不阻塞业务；
12. CDP最多3次恢复，最终失败global stop；
13. 未分类V1.2内部异常不会自动升级整个程序退出；
14. 历史未闭环订单：
    - 启动后标红；
    - 自动跳过；
    - 不自动续跑；
15. Google改为“发给采购”后历史中断标记自动解除；
16. 两条及以上V1.2订单：
    - 第一条闭环后等180秒才开始第二条；
    - 最后一条后不额外等待；
    - 空轮询不等待；
    - stop可以中断等待；
17. RFQ-002 manual-verification page preservation regression继续PASS。

时间相关测试必须使用fake clock/event/wait seam，不允许真实等3分钟。

==================================================
八、验证
==================================================

执行：

- 与本RFQ相关 focused pytest
- full safe/offline pytest
- python -m ruff check src tests
- git diff --check

不得为了测试运行：
- 真实订单；
- 真实Save；
- 真实Save-and-Send；
- 真实SMTP；
- 真实Google Sheets写入；
- 真实验证码；
- 真实受保护业务操作。

==================================================
九、重新打包并覆盖当前 V1.2
==================================================

因为本RFQ会修改生产 src，测试全部通过后必须重新打包。

继续使用现有、已经验证的 V1.2 build/deploy pipeline。

版本仍然是：
INSO_V1.2

部署目标仍然是现有 V1.2 路径：
D:\Program_Leo\INSO_Leo\dist\INSO_V1.2\INSO_V1.2.exe

部署前：
- 备份当前 EXE/_internal 到新的 release-backups 目录；
- 不碰 runtime；
- 不碰 workflow DB；
- 不碰 OAuth/grant；
- 不碰 config；
- 不碰固定Chrome profile；
- 不移动/删除 v1-2-design runtime target；
- 不清 cookies。

只替换正常发布流程允许替换的：
- EXE
- _internal / frozen assets

执行：
- build
- frozen self-check
- clean staged release scan
- deployed self-check
- idle launch

可以正常重启新版GUI待命。

禁止点击：
“开始询价”

禁止运行真实业务订单。

重新记录：
- 新 EXE SHA256
- backup path
- build/self-check/scan结果
- idle launch结果

==================================================
十、完成流程
==================================================

完成后：

1. 更新：
   - RFQ-003/TASK_SPEC.md
   - RFQ-003/EXECUTION_LOG.md
   - RFQ-003/FINAL_REPORT.md

2. commit + push。

3. COORDINATION：
   RFQ-003 → REVIEW_REQUIRED

4. 不要自己标 REVIEWED_DONE。

5. 确认 remote HEAD 与本地一致。

最后汇报只需要：

- commit SHA
- 主要生产文件改动
- focused测试结果
- full safe/offline测试结果
- Ruff
- git diff --check
- 新 EXE SHA256
- backup path
- build/self-check/scan结果
- idle launch是否成功
- 明确：
  “未运行真实订单、Save/Save-and-Send、SMTP、Sheets写入或真实验证码场景”
- 最后一句：
  “RFQ-003 已提交 CEO Review。”
