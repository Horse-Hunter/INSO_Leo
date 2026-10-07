# RFQ-003 Final Report — 2026-10-07

## 当前 Owner 批次跟踪与修复版交付（覆盖下方历史 B1 摘要）

正在实现什么：跟踪 Owner 已启动的当前四笔真实订单，修复已确认显示问题，
覆盖 V1.2，并给 CEO 形成 V1.3 适用差异报告。不开发 V1.3。

以前是什么：S 评级按原 A/B/C 规则跳过；改为 A 后业务恢复但旧资料警报仍显示红色。
三分钟行间冷却显示“即将轮询”，被误认为卡住。

现在是什么：最小修复资料警报恢复及只读历史兼容；GUI 显示冷却/正在处理。
没有改评级、采购条件、Save-and-Send gate、通知规则或180秒策略。
原 B1 已由 CEO 在 c8d514e 基线批准；本次增量为 REVIEW_REQUIRED。

真实结果：当前四笔中三笔 PURCHASE_RECORDED，唯一点击各一次，原重要通知
各两次投递成功，源表状态均已读取确认“发给采购”。第四笔五个价格来源均无
结果，NO_MATCHING_PRODUCT / RESEARCH_FAILED，零提交，异常通知成功，源表
仍“未发”。这符合无报价不采购规则，不是四笔采购全部完成。需要 Owner 核对
第四笔型号或另行明确业务授权；执行者没有猜型号、填价格、改库或强制发送。
旧空品牌测试行不是本次四笔之一，仍按资料错误跳过，不补发。
旧真实订单没有重跑；上述是真实 Owner 循环观察，与离线验证严格分开。

验证：focused 999 passed / 1 skipped；full safe/offline 1046 passed / 11 skipped；
Ruff src tests、git diff --check PASS。现有 build/frozen self-check/staged scan、
deployed self-check PASS。通过 computer-use 正常关闭空闲应用并启动新版待命，
未点击开始询价。截图接口超时，不宣称截图验证成功；窗口/进程启动已确认。

部署：`D:\Program_Leo\INSO_Leo\dist\INSO_V1.2\INSO_V1.2.exe`

新 SHA256：`340D7F7E7E818FA74DE36B138B205F5905F320406FD8D391EF860BD052529E5F`

备份：`D:\Program_Leo\INSO_Leo\dist\release-backups\INSO_V1.2-20261007-before-input-alert-cooldown-fix`

备份旧 EXE SHA256：`1A49C9650BA531F2299326FFC89761D0391CD5F2C0FE32327DDD0736BD5C3E84`

只替换 EXE/_internal。runtime junction/DB/config/grant/profile 均保留。
CEO 同步细节：`CEO_SYNC_REPORT.md`，五个生产文件及三条新离线测试；不提交
原始客户输出、订单身份、价格、授权或生成包。本次没有实现/运行 V1.3。

你接下来需要做什么：确认第四笔无报价业务处置；CEO Review 本次增量后再同步 V1.3。
尚未证明第四笔可采购或新 EXE 真订单端到端运行，保留 UNKNOWN，不能称全部完成。

## 以下为此前 B1 修复交付历史

正在实现什么：
维护现有 V1.2，完成采购故障隔离、恢复、提交待确认和行间三分钟冷却；没有开发 V1.3。

理想变化是什么：
单行问题不拖死整批；共享故障安全停止；人工验证页保留；不重复发采购；
历史中断不自动重跑；正常下一行开始前等待三分钟，停止可以立即打断。

以前是什么：
CEO Review 指出唯一阻塞 B1：同批尚未开始的后续订单也会被重启恢复误标为处理中断。

现在是什么：
RFQ-003 为 REVIEW_REQUIRED。新版已覆盖当前 V1.2 并启动待命，未点击开始询价。
沿用唯一生产主链、原订单识别码/台账、固定 CDP、现有通知与发布基础设施。

做完了什么：

- 本次只修 B1：启动隔离和只读显示都要求真实执行证据；预入队/预建 pending 不算开始。
- 第一条处理中断时仅隔离第一条；第一条闭环后冷却退出时，后续未开始订单仍按源表顺序正常继续。
- 可能已发送的中断仍隔离、已闭环不重开，人工完成后的解除及禁止重发边界保留。

以下为此前 RFQ-003 功能，本次未重新开发：

- 无报价、重复、单行资料错误、明确提交前失败安全闭环，继续下一行。
- IC.net/采购自身异常暂停采购模块；INSO/共享表格/数据库/CDP严重故障全局停止。
- INSO 下方查询失败最多三次 fresh-tab 重试，每次可中断等待三分钟，真实空结果不混淆。
- 真正唯一点击且记录落库后，后确认失败保留独立待确认状态，尝试写发给采购、黄色提醒及229通知，绝不再发。
- 表格写回失败黄色提示人工更新，采购不重做，后续行继续；邮件失败不阻塞业务。
- 历史未闭环订单红色隔离、队列跳过；人工将源状态改为发给采购后自动解除红色且不再采购。
- 冷却只放在确实存在的下一行之前，末行和空轮询不等；人工验证页面在最终清理阶段也保留。
- 未开放单独保存或通用发送，未改变原重要/重复通知收件人。

测试结果：
Focused：996 passed / 1 skipped。完整 safe/offline：1043 passed / 11 skipped。
Ruff src tests、git diff --check 通过。build、冻结自检、干净发布扫描、部署自检通过。
通过 computer-use 正常关闭/启动最终版并保持待命；未运行真实业务，不代表线上验收。

部署路径：`D:\Program_Leo\INSO_Leo\dist\INSO_V1.2\INSO_V1.2.exe`

新 EXE SHA256：`1A49C9650BA531F2299326FFC89761D0391CD5F2C0FE32327DDD0736BD5C3E84`

本次覆盖前备份：`D:\Program_Leo\INSO_Leo\dist\release-backups\INSO_V1.2-20261007-before-rfq003-b1`

仅覆盖 EXE/_internal，runtime/数据库/config/grant/固定 profile 保留。
所有旧备份保留；新增18个参数化回归场景及实际离线数字见 EXECUTION_LOG.md。
未运行真实订单、Save/Save-and-Send、SMTP、Sheets写入或真实验证码场景。
真实新订单端到端结果仍为 UNKNOWN；不得将离线测试冒充真实提交成功。

你接下来需要做什么：
Review RFQ-003。
