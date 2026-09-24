# Current Task

Status: READY_FOR_CEO_REVIEW

Goal: 完成 INSO_V1.0 Windows GUI Shell 的 CEO Final Review 修正，使 GUI Shell 可安全进入 main，并为后续 Production Launcher 接入提供稳定契约。

Business Outcome: 提供仅使用 MockBackend 的单页 GUI；金额、货量、五源展示契约、线程 dispatch、关闭清理与结果刷新符合 V1 边界，并且 Start / stop-after-cycle 在实际 INFO 日志配置下不会死锁或多跑一轮。

Acceptance:
- 当前 GUI branch 已 merge 最新 origin/main。
- 金额使用 Decimal；货量为 IC.net stock label；五源详情为展示型 SourceDetail；GUI 显示名称保持 INSO / Findchips / 华强 / 立创 / 正能量。
- Tk API 仅主线程调用；固定 Queue drain、可取消 after、worker shutdown 清理、结果增量同步。
- 重复 Start 受阻止。
- Start 在实际 logging level=INFO 且已注册 on_log listener 时不得死锁。
- “本轮结束后停止”语义严格成立：若请求发生在当前 cycle 内，完成该 cycle 后停止；若请求发生在 cycle 间隔等待期，不得再启动下一 cycle。
- Mock health 直接表达 Google Sheets / Browser-CDP / Credential / Research 的健康状态。
- MODULE_INDEX 使用当前格式；completed task/report 不保留。
- ruff、GUI tests、完整 deterministic pytest 通过；若执行环境缺失 Tcl/Tk，则明确记录环境限制，不伪造 smoke 通过。

Constraints: 不接真实 Sheets、Research、浏览器或生产后台；不实现 Production Launcher；不修改 Research / Sheets / Workflow 业务逻辑及价格规则；不 rebase 已推送历史或 force push；不操作上一位程序员的未知 worktree。

Done:
- 已将 origin/main merge 到 GUI branch。
- 已修正 Decimal、stock label、SourceDetail、Queue 主线程 dispatch、after cancel、worker shutdown 与 Treeview 增量刷新。
- 修复锁内 logging 导致 INFO listener 重入死锁，并增加 INFO + on_log listener 回归测试。
- 修复 stop-after-cycle 时序：cycle 内请求会完成当前 cycle；idle 间隔期请求会唤醒并停止 worker，不启动额外 cycle。
- 恢复 GUI 五源显示名 INSO / Findchips / 华强 / 立创 / 正能量；health 直接模拟四个 GUI 组件。
- `ruff check src tests`、`pytest tests/gui -v`、完整 deterministic pytest 通过。

Current: 运行时 blockers 已修复并 push 到 `inso-v1-gui`；等待 CEO 再次 Final Review。GUI smoke 受当前 Windows Python 缺失可用 Tcl/Tk `init.tcl` 限制，不报告通过。

Next: CEO 再次 Review；通过后由 CEO 决定是否合并 main。

Blockers: NONE（窗口级 smoke 受 Tcl/Tk 环境限制；headless 回归已通过）。

Owner Decisions: NONE

Branch: inso-v1-gui

Last Good Commit: d5689ec30d6314982a25207bdf12f4c2840a7a99
