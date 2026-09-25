# Current Task

Status: NONE

Goal: 等待 Owner / CEO 启动下一阶段。

Business Outcome: INSO_V1.0 Production Launcher + ProductionBackend 已完成并通过 deterministic review 与 Windows human-assisted live smoke。当前 GUI 默认进入 production mode，可真实执行 Google Sheets -> Workflow -> Research -> 调研价格.xlsx，并支持本次运行结果展示、安全停止、persistent dedup 与安全关闭。

Acceptance: NONE

Constraints:
- 保持已验收 V1 Research / Sheets / Workflow 业务规则不变。
- Production GUI 默认不启用真实 Google Sheet Brand 写回。
- runtime/research.json、runtime/production.json、OAuth grant、SQLite、浏览器 profile 与其他本机运行文件继续 Git-ignored；不得提交 secret/token/cookie。
- CAPTCHA / OTP / 设备验证继续人工处理，不绕过。
- 不 reset/clean/delete 历史 Research runtime worktree。

Done:
- ProductionBackend / launcher composition 已接入真实 Sheets、Workflow、Research runtime。
- GUI 默认 production；--mock 仅用于开发演示。
- 每次 Start 独立 run_id；重复 Start 不启动第二套 runtime；本次运行 inquiry 显式跟踪，不依赖 Excel 行差异猜测。
- 15 分钟 poll、Workflow SQLite dedup/retry、single Research worker 保持原语义。
- stop-after-cycle 会封闭新 poll、等待当前 poll 完成并 drain 本轮已到期工作；future retry 不等待。
- GUI 窗口 X 使用非阻塞 graceful close，等待当前 cycle 与后台线程安全退出后再销毁窗口。
- 登录/CDP/runtime异常 fail closed 到“需要人工处理”；正常 OAuth refresh grant 静默复用。
- Windows live smoke 已完成：真实 poll 覆盖 2026 / SHAHAB；生成 2 条持久 Workflow inquiry，其中 1 条完成并写入 Excel，1 条进入 future RETRY_WAIT；completed Excel 行与 SQLite inquiry 一致。
- stop 后无 QUEUED / RESEARCHING；第二次 Start SQLite 总记录仍为 2、无重复 inquiry；completed row 未重复创建。
- 运行中关闭窗口后 GUI 与 launcher/poller/worker 进程均退出；SQLite integrity_check 正常；Excel 结果保留。
- Brand updater 保持 disabled；未产生新的 Google Sheet 写副作用；未遇到 CAPTCHA / OTP / 设备验证。
- 最终验证：ruff 通过；GUI + launcher 36 passed；完整 deterministic pytest 358 passed；git diff --check 通过。

Current: NONE

Next:
- Windows 发布阶段：EXE/PyInstaller、应用图标、双击启动、运行目录与 Git-ignored runtime 配置发现、单实例、发布包 smoke。
- 随后做长时间 soak / 资源稳定性验收，再决定是否加入开机自启。

Blockers: NONE

Owner Decisions:
- Production GUI 第一阶段 Google Sheet Brand 写回保持 disabled/no-op。
- V1 Production Launcher 已验收，可作为后续 Windows 发布版基线。

Branch: NONE

Last Good Commit: dd7a480dfc5edec81b23aa5dd29c6c8ffd30712e
