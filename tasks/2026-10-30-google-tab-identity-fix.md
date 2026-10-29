# Task: urgent Google tab identity pause repair

status: in_progress
owner: Codex Executor
created: 2026-10-30

## Owner / scope
Owner要求尽快妥善解决导致新单暂停的bug，延续已授权正常业务与安全更新。当前新单QUEUED1，未采购，历史SENT153；00:09:08共享故障GOOGLE_TAB_IDENTITY_UNCONFIRMED。Owner已正常退出GUI并保持Chrome原样，允许必要最小只读身份定位的受控空闲窗口；不导航、刷新、关闭或写表，禁Computer Use。核对现有原Google页管理/身份及真实根因，最小修复，离线专项和全量后按原发布规程更新恢复；绝不取消身份验证、源身份、Stop、GLOBAL_STOP、SENT/UNKNOWN或采购门禁。

## Verified / UNKNOWN
仅HTTP只读目标元数据：10个targets，其中Google page2、INSO page1、blank page1、browser_ui2，另iframe2/worker2。旧/当前日志同一Google身份错误；真正触发的原始协议分支待核实，不凭页面数量猜测。

## acceptance
使用原生产调用分支复现并回归；只解析精确自有页面，非业务原生目标不应被误判为本单共享故障，自有目标身份错误/连接故障/未知写入仍阻断。受保护/人工页保留。测试/文件/源码哈希及原业务状态保护如实记录。原统一报告/JSON记录，不另造框架或额外调度；真实新单成功须原外部结果凭据，不冒充。

## Owner unattended execution authorization
Owner明确授权无人值守修复、离线验证、原流程打包覆盖和恢复原正常业务；无需普通逐阶段审批。仍禁止Computer Use、强杀、未知结果重试、降低权限或写入身份保护。若原应用无法安全收口/退出，保留HOLD，不用桌面控制绕过。原GUI已由Owner正常退出。当前作用于这条已入队新订单；不能承诺绝对无bug或伪报外部成功。

## Current evidence / minimum change
停机后的原只读Playwright身份复验：INSO/两Google/blank四个Page均可证明native ID；未复现瞬态Error，精确原错误协议分支UNKNOWN，不能归罪browser_ui（后者未进入Playwright Page列表）。源码对已由原工厂证明的同一Page重复建立per-page CDP会话取隐式target，容易受页面执行进程/会话变化影响。最小改为使用工厂已有native lease，在原浏览器CDP会话上显式查询同一targetId；精确匹配、文档/owner/写入settlement及GLOBAL_STOP保持。无lease跨poll fallback保留原证明，不猜ID或采纳人工页。会话detach异常也统一安全停机；固定脱敏操作步骤日志便于下次精确区分，不输出URL/账号/客户。

Owner补充允许必要时强杀旧INSO程序，仅在正常退出不可用且已确认安全收口时作为最后手段；不关闭受保护Chrome、不恢复旧账本、不重试未知外部结果。当前原程序已正常退出，未使用强杀。
