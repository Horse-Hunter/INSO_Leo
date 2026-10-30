# Task: urgent Google tab identity pause repair

status: live_follow_up_in_progress
owner: Codex Executor
created: 2026-10-30

## Owner / scope
Owner要求尽快妥善解决导致新单暂停的bug，延续已授权正常业务与安全更新。当前新单QUEUED1，未采购，历史SENT153；00:09:08共享故障GOOGLE_TAB_IDENTITY_UNCONFIRMED。Owner已正常退出GUI并保持Chrome原样，允许必要最小只读身份定位的受控空闲窗口；不导航、刷新、关闭或写表，禁Computer Use。核对现有原Google页管理/身份及真实根因，最小修复，离线专项和全量后按原发布规程更新恢复；绝不取消身份验证、源身份、Stop、GLOBAL_STOP、SENT/UNKNOWN或采购门禁。

## Verified / UNKNOWN
仅HTTP只读目标元数据：10个targets，其中Google page2、INSO page1、blank page1、browser_ui2，另iframe2/worker2。旧/当前日志同一Google身份错误；真正触发的原始协议分支待核实，不凭页面数量猜测。

## acceptance
使用原生产调用分支复现并回归；只解析精确自有页面，非业务原生目标不应被误判为本单共享故障，自有目标身份错误/连接故障/未知写入仍阻断。受保护/人工页保留。测试/文件/源码哈希及原业务状态保护如实记录。原统一报告/JSON记录，不另造框架或额外调度；真实新单成功须原外部结果凭据，不冒充。

## Owner unattended execution authorization
Owner明确授权无人值守修复、离线验证、原流程打包覆盖和恢复原正常业务；无需普通逐阶段审批。仍禁止Computer Use、未知结果重试、降低权限或写入身份保护；Chrome绝不强杀。Owner后续明确允许必要时强杀旧INSO，仅限正常退出不可用且确认外部操作安全收口的最后手段。无法证明安全则HOLD，不用桌面控制绕过。原GUI已由Owner正常退出。当前作用于这条已入队新订单；不能承诺绝对无bug或伪报外部成功。

## Current evidence / minimum change
停机后的原只读Playwright身份复验：INSO/两Google/blank四个Page均可证明native ID；未复现瞬态Error，精确原错误协议分支UNKNOWN，不能归罪browser_ui（后者未进入Playwright Page列表）。源码对已由原工厂证明的同一Page重复建立per-page CDP会话取隐式target，容易受页面执行进程/会话变化影响。最小改为使用工厂已有native lease，在原浏览器CDP会话上显式查询同一targetId；精确匹配、文档/owner/写入settlement及GLOBAL_STOP保持。无lease跨poll fallback保留原证明，不猜ID或采纳人工页。会话detach异常也统一安全停机；固定脱敏操作步骤日志便于下次精确区分，不输出URL/账号/客户。

Owner补充允许必要时强杀旧INSO程序，仅在正常退出不可用且已确认安全收口时作为最后手段；不关闭受保护Chrome、不恢复旧账本、不重试未知外部结果。此前阶段原程序已正常退出，当时未使用强杀；本轮新增退出事实以末尾08:23收据为准。

## Canonical operator recovery, not a new production system
真实新单QUEUED/attempt0、DUPLICATE_CHECKING、仅DUPLICATE_CHECK_STARTED2，无执行/采购/派发证明。原已审核重启规则仍会将其保护为INTERRUPTED_UNSENT；不修改此安全规则，不直接重置SQL。Owner授权各环节无人值守后，使用一次性CLI操作原ProductionBackend公开API：持有同一单实例锁、同一已安装runtime、同一冻结等价源码、原start/原模块调度；只有在原can_order_action允许且原真实空闲窗口，针对这唯一新单调用一次request_order_action('purchase')。实时来源和持久化门禁由原实现再次验证；不跑第二实例，不另造调度/价格/发信/账本；迟到/UNKNOWN/安全故障不重试。完成后原request_stop_after_cycle/shutdown正常排空，退役操作脚本，启动已安装EXE留给Owner。


## 00:43 follow-up: failed live receipt retained, no success claimed
8b84 source-equivalent original Backend session completed inquiry625s and TP12.8s, then quotation cleanup failed at fixed `google-target-session` step after TP return. Original Backend shut down normally; no manual retry submitted and no force kill. Exact first transient protocol cause remains UNKNOWN. Source review reveals the outer Google poll retains live Page wrappers across nested TP, although existing INSO/research recovery may replace/stop the borrowed original client. Offline original quotation->TP integration reproduces stale-client final settlement under this replacement. Minimum change: at the ALREADY-proven idle quotation boundary end original Google Page/session borrows, lend to TP with its own canonical scope, resume with fresh wrappers resolved from retained exact native IDs. Never discard unsafe surfaces or bypass owner/settlement/auth guards. New read-only scope is lazy, no extra timer/browser/profile. Stop/auth/pending surface rejection and actual quote/TP return regression32PASS. Also display canonical intake records before Research exists, retaining actual durable DTO permissions and no fabricated price/success. Live validation still REQUIRED; no claim root uniquely proven until actual follow-up.

Final handoff+intake source regression: 3168 PASS / 1 SKIP /124.41s; focused72PASS; Ruff and git diff --check PASS. Source trees recorded at commit/build receipt. No forced termination used; API session ended normally.

Final real receipt: no Google identity fault on current TP return, but INSO visibleSMSchallenge blocks quote; no target retry/purchase, originalBackend normalshutdown. InstalledGUIleftidleHOLD. See canonical report/JSON for exact receipts; no forcekill/noComputerUse. TwoGoogle transienttimeouts/693.797s latency remain unresolved; not allbugsPASS.

Owner07:50认证后已恢复运行，凌晨人工认证BLOCKER被Owner处理，当前按原日志/只读账本跟进，不重复开始或重启。原目标仍中断未发保护，原GUI闲时重跑入口需Owner操作；其他业务正常原规则不逐笔审批。当前自然完整成功尚待凭据。见原报告最新章节，不能用旧HOLD覆盖恢复事实。


## Owner 08:xx direct fix instruction: bounded download + read-only selection identity
Owner明确“有问题就修，别什么都问”，继续沿用已授权的最小修复、离线完整回归、原发布脚本、安全程序替换及原正常业务，不逐项审批。当前GUI109068已恢复并继续正常业务，开发仅在原源码树，不与生产Chrome交叠检查。
Reuse audit: existing native TSV _download uses public failure/path/delete calls with no completion timeout, unlike expect_download(start only). Existing test_read_guard_code intentionally appends valid &range=A1 and expects five failed retries: proves complete-fragment equality rejects a valid same-gid selection. Fix only explicit read-surface identity, preserving mandatory same document+single decimal gid, canonical allowed A1 range, real active worksheet gid; writes keep original strict _guard and name-box/settlement proof. Unknown fragment keys, duplicates, changed gid, auth or owner loss remain blocked. Same original Playwright client/owner; no extra client/thread/download framework. Bound vendor artifact waits through the existing bundled SyncBase dispatcher and underlying coroutine (the public synchronous Download has no timeout parameter); cancellation is only the exact owned READ download, never browser/page/write. Preserve32MiB/100000row/header/caches/fresh checks and original retry delays/count. Test hangs/cancel failure/path/delete timeout, all identity-negative cases and original write guards. Source-level defects proven; whether all historical latency came from these exact branches remainsUNKNOWN until real controlled follow-up. No promise allbugsPASS.
No production replacement while business is active/unconfirmed. Reuse original release backup/data protection, then normal shutdown if safely available; latestOwner explicitly permits force-ending oldINSO as last resort when no normal non-ComputerUse exit exists and exact program identity, idle deadline and durable effects are proven safe. Chrome never terminated. Existing interrupted order can be handled by original Backend public can_order_action/request_order_action once at original idle permission; no SQL resets or changed quarantine rules, no second concurrent Backend. Code/packaging never changes recipients, SENT/UNKNOWN or purchase authority.

Final read-boundary source:251 affectedPASS8.25s; full3200PASS/1SKIP127.03s; Ruff/diffPASS. Initial focused setup failure(temporary parent missing) corrected; initial related249PASS2FAIL exposed two old expectations intentionally rejecting valid range_after, updated only that scenario to one-pass success; changed-gid/closed/auth/write negatives retained. New tests use real bundled Playwright SyncBase dispatcher and synthetic artifact coroutines, no Chrome/CDP. No claim that all historical network latency is proven fixed. Candidate/live receipt follows after source commit.


### 本轮实际收口：新单保存、Google写回与正式GUI恢复（2026-10-30 08:54）

原公开入口08:50:12仅接受一次purchase重跑；原持久化权限和来源鲜检均保留。真实新单一次attempt完成六源调研（PARTIAL_SUCCESS，不宣称六站全有报价）。INSO保存点击后先记UNKNOWN，再由原只读对账确认SAVED及非空外部record reference，最终PURCHASE_RECORDED；未再次点击保存、未重发采购。08:52:47原follow-up episode确认本单Google状态发生写入并已鲜读回，不只是本地SUCCESS。08:52:56原Backend返回manual_success=true、PURCHASE_SENT并正常shutdown/释放锁。
原自然询价636.391秒、报价397.016秒、嵌套TP11.938秒均结束；包含一次Google读取超时后恢复，不能宣布所有读取故障已消除。Google/INSO历史故障并非同一根因。
仅退休本次原Backend新建、精确native ID且已证实空闲的3个Google页；0个历史页面关闭，0个保护页面关闭，其他历史11个Google页保留。未强杀Chrome。单次CLI辅助已退出，不留第二生产Backend。
08:54:24正式EXE BC7970…启动一次--start-inquiry；实际GUI145364、原观察器139324；08:54:26 gui_ready，08:54:28实际询价begin，响应正常，原单实例锁持有。启动中的previous_abnormal_exit是08:23授权强制退出的历史凭据，不作新的业务故障或静默清除。
SQLite integrity ok；历史125条不可变命令、156条SENT完整行及4个历史TP任务不变（其中原6条TP-SENT保留）。SAVED由23增24；无新增SMTP收据，无UNKNOWN残留。SMTP发信和供应商后续报价不能凭采购保存冒充完成；目标单是否满足TP由原自然轮次判断，不制造TP任务或邮件。原900/120秒及双Actor关闭保持不变。
正式程序2875文件再次逐项哈希相等，原单实例检查通过。当前BUSINESS_RUNNING / V16_REVIEW_REQUIRED；继续低干扰跟进，真实长期稳定、DPI和游戏影响NOT_VERIFIED。COMPUTER_USE_NOT_USED。无需Owner再点重跑或开始。

最终资源/清理补充：正式GUI122秒短测0.30449%host CPU、RSS114.6~118.4MiB、线程12~18、句柄1086~1318；非长期稳定结论。已退休本次构建暂存2876文件/268036144字节、兼容副本843776字节及8个一次性脚本；保留正式程序、回滚及仅日志/只读账本跟进工具。原“Owner需右键重跑”已SUPERSEDED，新单一次原API重跑已成功收口，Owner无需重复操作。


## Owner追加：Google历史页面增长诊断与最小收口（2026-10-30）
Owner要求自行分析并决定处理，不反复询问。仅HTTP现有目标清单元数据（无调试会话/页面操作）确认14个Google页，其中11个在本次正式进程前已存在、3个后续工作页；不是已证明每轮无限创建。源码四页registry仅服务内存，正常poller停止未退休已确认空闲的自有页，跨进程旧页按原安全规则不认领。复用原native target证明、Page所有权、认证/DOM未完成检查和close接口，在原poller线程退出时退休仅其registry内且证实空闲的页；保护/未知/人工页保留。必要重新attach仅原CDP，不启动Chrome、无写表/邮件/改账本。四页跨正常轮次照常复用，不在每轮结束清理。离线验证及原全量回归；不为本次清理而立即强杀/重启正在处理业务的旧EXE，避免又添一组旧页。候选随下一次真正必要的安全程序更新使用，不自行清理历史未知页。


Lifecycle candidate verification:22 focusedPASS0.46s;198 affectedPASS4.74s;
final full3221PASS/1SKIP125.84s;Ruff(no-cache)/diffPASS. Initial test parent missing
caused22setup errors before execution; initial focused20PASS2FAIL used unsupported
fake auth/dirty attributes, corrected to original login_markers and synthetic unsafe
predicate port (original real-JS predicate tests retained); no product safety rule
weakened. Original real Backend production composition is tested in both legacy and
independent modes, proving retirement occurs on production-sheets-poller, not GUI
shutdown thread. HTTP metadata09:49:36 and09:58:36 Shanghai:14pages both,0new/0closed,
11present before current formal run+3subsequent working pages. No debugger sessions,
page actions, download, credentials or customer data. This is not 24h stability or
safe ownership proof for historical pages. No current production replacement,
restart, Chrome action, SQL/config/Vault/SENT change, purchase or mail. Normal-stop
fix does not promise cleanup after force termination; unknown historical pages stay.
Owner autonomous decision: preserve live business, keep candidate for next necessary
safe update; do not force-restart merely to clear tabs and generate another group.
COMPUTER_USE_NOT_USED. Candidate and installed application SHA recorded separately.
