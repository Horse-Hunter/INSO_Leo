# Current Task

Status: ACTIVE

Goal: 完成 INSO_V1.0 Windows GUI Shell 的 CEO Final Review 修正，使 GUI Shell 可安全进入 main，并为后续 Production Launcher 接入提供稳定契约。

Business Outcome: 提供仅使用 MockBackend 的单页 GUI；金额、货量、五源展示契约、线程 dispatch、关闭清理与结果刷新符合 V1 边界，并且 Start / stop-after-cycle 在实际 INFO 日志配置下不会死锁或多跑一轮。

Acceptance:
- 当前 GUI branch 已 merge 最新 origin/main。
- 金额使用 Decimal；货量为 IC.net stock label；五源详情为展示型 SourceDetail；GUI 显示名称保持 INSO / Findchips / 华强 / 立创 / 正能量。
- Tk API 仅主线程调用；固定 Queue drain、可取消 after、worker shutdown 清理、结果增量同步。
- 重复 Start 受阻止。
- Start 在实际 logging level=INFO 且已注册 on_log listener 时不得死锁。
- “本轮结束后停止”语义严格成立：若请求发生在当前 cycle 内，完成该 cycle 后停止；若请求发生在 cycle 间隔等待期，不得再启动下一 cycle。
- Mock health 直接表达 Google Sheets / Browser-CDP / Credential / Research 的健康状态，不把某个价格源登录状态错误映射成 Research 整体状态。
- MODULE_INDEX 使用当前格式；completed task/report 不保留。
- ruff、GUI tests、完整 deterministic pytest 通过；GUI smoke 在可用 Windows Tcl/Tk 环境完成，若执行环境缺失 Tcl/Tk 则明确记录环境阻塞，不伪造通过。

Constraints: 不接真实 Sheets、Research、浏览器或生产后台；不实现 Production Launcher；不修改 Research / Sheets / Workflow 业务逻辑及价格规则；不 rebase 已推送历史或 force push；不操作上一位程序员的未知 worktree。

Done:
- 已将 origin/main merge 到 GUI branch。
- 已修正 Decimal、stock label、SourceDetail、Queue 主线程 dispatch、after cancel、worker shutdown 与 Treeview 增量刷新。
- CEO Final Review 发现两个运行时阻塞问题，需修复后重新 Review。

Current:
- BLOCKER 1：MockBackend 在持有 self._lock 时调用 _log；当主程序通过 on_log 注册 RingBuffer listener 且 logging effective level=INFO 时，RingBuffer emit -> _notify_log 会再次获取同一非重入 Lock，Start / Stop 等路径可死锁。必须避免持锁日志/回调，并加真实 INFO 级别回归测试。
- BLOCKER 2：worker 在 cycle 间隔等待期收到 request_stop_after_cycle 后，只打断 sleep，但下一次循环仍先执行 _run_cycle，再停止，导致额外多跑一轮。必须在启动下一 cycle 前检查 stop_requested；cycle 内请求仍应等当前 cycle 完成后停止。
- 同轮修正 GUI 来源显示“正能量”以及 Mock health 语义映射。

Next: Main Programmer 修复上述 Final Review findings → tests/self-review → commit/push inso-v1-gui → CEO 再 Review。

Blockers: MockBackend INFO logging lock re-entry deadlock；idle stop-after-cycle extra cycle。

Owner Decisions: NONE

Branch: inso-v1-gui

Last Good Commit: baee3df82c905d04127c46b8761cd943aff2bd93
