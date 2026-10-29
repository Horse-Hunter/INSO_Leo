# Task: V1.6 desktop entry and low-impact new-order observation

status: superseded_by_identity_repair
owner: Codex Executor
created: 2026-10-30

## Owner request / scope
Owner看到桌面仅V1.4，要求补最新版入口、启动程序并观察新订单。仅指向已安装排序版00AD692E...，不构建安装或修改源码。先核验进程/程序哈希/原锁/未确认外部状态，不重复启动。可通过WScript.Shell文件接口创建V1.6快捷方式，保留V1.4回滚入口；正常GUI启动用既有--start-inquiry一次。

## Safety
只读日志、必要SQLite一致性快照、OS计数器；不连接额外Chrome/CDP，不改变页面、配置、账本/SENT/UNKNOWN，不制造订单、测试邮件、采购或写表。正常已授权业务仍由原应用执行。COMPUTER_USE_NOT_USED。

## Acceptance / observation
记录真正启动的EXE/进程及新快捷方式目标；核验原运行及新增自然业务，结果不明/安全故障及时通知Owner，不绕过保护。Owner已要求盯住新订单，使用本线程低频心跳只读跟踪，正常无变化静默，完成/异常才通知；不能把begin或本地调用当真实成功，缺外部凭据保留NOT_VERIFIED。不得自动重启、停止或补发；结束后退休本次观察心跳。

## Execution
Desktop latest shortcut created via file API; originalGUI122292 started00:05:58 then identity protection paused; Owner normal exit. Existing queued operational notice was generated prior evening, sent once on start, not historical SENT replay. This observation-only scope is SUPERSEDED by Owner unattended repair authorization in tasks/2026-10-30-google-tab-identity-fix.md. Source/live evidence retained; not a second production launch path.
