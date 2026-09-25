# Current Task

Status: READY_FOR_CEO_REVIEW

Goal: 交付 INSO_V1.0 Production Launcher + ProductionBackend，使 Owner 可以从 Windows GUI 一键启动现有 V1 真实自动调研、查看本次运行真实结果，并安全停止；不改变已验收的 V1 业务规则。

Business Outcome:
- GUI 的“启动自动调研”不再使用 MockBackend，而是启动真实 V1：Google Sheets -> Workflow -> Research -> 调研价格.xlsx。
- 正常运行每 15 分钟轮询既有 worksheets，继续使用现有 SQLite dedup/retry/single-worker 语义。
- GUI 只显示本次 Start 会话内实际处理过的 inquiry；金额、货量和五源文本与 Research Excel/Contract 一致。
- “本轮结束后停止”停止未来轮询，允许当前已进入处理的工作安全落盘后停止，不硬杀 Research/Excel/SQLite。
- 浏览器采集继续使用已批准的 CDP/后台页机制；正常运行不主动抬起浏览器窗口。OAuth 正常复用已保护 refresh grant。
- 登录失效、CDP 不可用、CAPTCHA/OTP/设备验证等进入“需要人工处理”并给出非敏感动作提示，不绕过验证、不泄露凭据。

Acceptance:
1. 新增稳定的 Production composition/launcher 边界；GUI 模块本身继续不直接依赖 research/sheets/workflow 内部实现。若新增 launcher/composition 模块，MODULE_INDEX 记录其职责和依赖；该模块只负责编排与展示适配，不复制价格/Sheets/Workflow业务规则。
2. ProductionBackend 实现现有 GuiBackend Contract：start、request_stop_after_cycle、status、current-run results、health、diagnostics、open Excel/results dir、shutdown。
3. 每次 Start 生成新的 run_id；重复 Start 不得启动第二套 Workflow。session 只在内存维护即可，不要求新增历史数据库。
4. current-run 结果按实际处理过的 inquiry_id 归属，不通过“Excel新增行数”猜测。可使用 launcher 层 observing/decorator seam 记录 Research 执行，再通过 Research-owned只读输出契约/窄适配读取对应 inquiry 的展示值；不得让 GUI/Workflow 复制 Research 价格逻辑。
5. GUI 主表真实显示：型号、品牌、数量、货量、市场最低参考价、预估订单总价、状态；详情真实显示 INSO / Findchips / 华强 / 立创 / 正能量及备注。金额保持 Decimal；Excel中已经格式化的展示文本不做二次价格推断。
6. 运行时沿用现有 15 分钟 poll cadence、Workflow SQLite dedup、retry 15/30/60、single Research worker。不得把 live smoke 当 daemon，也不得删除/覆盖现有真实 SQLite/Excel。
7. graceful stop：
   - stop request 后禁止开始新的 Sheets poll；
   - 已经 claim/正在执行的 Research 必须允许执行完并完成 Excel/Workflow 状态落盘；
   - 当前 cycle 已经入队且到期的工作应完成该 cycle 的安全收尾；未来 retry 不要求等待；
   - 停止完成后 worker/poller/thread/timer 全部退出，GUI 回到 STOPPED；
   - 不使用 kill/terminate 破坏 SQLite、Excel 或浏览器状态。
8. Production runtime 使用独立、稳定、非 smoke 的 SQLite 路径；Research Excel 使用正式 调研价格.xlsx 路径。运行配置保持 Git-ignored 且不含 secret。已知 spreadsheet/worksheet/OAuth client/CDP/Research 配置优先从现有 canonical/runtime 恢复，不重复询问 Owner；缺失才升级。
9. 默认不新增真实 Google Sheet 写入。Brand updater 保持当前已验收 live 行为（未明确启用时 disabled/no-op）；若要开启真实 Brand write，必须单独升级 Owner/CEO。
10. readiness/health 至少覆盖 Google Sheets authorization、Browser/CDP、Credential、Research runtime。缺失时 fail closed，GUI 显示“需要人工处理/异常”与非敏感 detail。
11. 正常状态下 Research 浏览器操作不得把 Chrome 页签主动切到前台。CAPTCHA/OTP/设备验证不得自动绕过。
12. src.gui.main 或新的正式 app entrypoint 必须有明确 production 启动方式；Mock 模式仍可保留用于开发测试，但不能让 Owner 误把 Mock 当 Production。
13. Windows 真实验收：GUI 可打开；Start 后真实读取已配置 Sheets；至少完成一轮真实 poll；如有处理订单，Excel 与 GUI 同 inquiry 一致；stop-after-cycle 正常；第二次 Start 不重复处理已 dedup 完成 inquiry；正常不重复弹 OAuth、不主动弹浏览器采集页。
14. tests：新增 ProductionBackend/launcher deterministic tests，覆盖真实 composition seam、run_id、duplicate start、session inquiry tracking、health、graceful stop、restart/dedup、资源释放、错误转 manual review。ruff 与完整 deterministic pytest 通过。
15. 完成后做适用的真实 live smoke；不得删除或覆盖已有 production Excel/SQLite，不得新增外部写副作用。

Constraints:
- 不改变 V1 Research 价格、MPN匹配、货量、来源、汇率规则。
- 不改变 Sheets pending 语义和 Workflow dedup/retry/business status 语义。
- 不实现 Future INSO 主动采购或 Quotation。
- 不引入 Redis/Celery/Docker/大型 workflow engine。
- 不把 secret/token/cookie/profile 写入 Git/log/test/evidence。
- 不绕过 CAPTCHA/OTP/设备验证。
- 不 reset/clean/stash/discard Owner 的历史 dirty checkout 或 research runtime worktree。
- 开发使用新的 clean worktree。
- 当前阶段先完成可真实运行的 Python Windows GUI；EXE/PyInstaller/开机自启属于后续阶段。

Architecture Decision:
- 保持 gui 为纯展示模块。
- launcher / composition-root 依赖 gui Public Contract 与 workflow / sheets / research Public API，负责生产对象组装、session observability、health 与 graceful lifecycle；不得承载业务规则。
- 需要读取 Research 结果给 GUI 时，优先使用 Research-owned 的只读结果读取能力或 launcher adapter，按 inquiry_id 读取 canonical Excel schema；Workflow 仍不得解析 Research Excel。

Done:
- 修复 `_Observer` 注入不匹配；Observer 在执行时登记 inquiry，并将登录/CAPTCHA/OTP/设备验证结果标到当前 run 的人工处理状态。
- stop-after-cycle 现在先封闭后续 poll admission，等待当前 poll 完成，再 drain 所有当前已到期 work；未来 retry 不等待。
- 新增真实 production `_run` composition seam 的离线 deterministic test，校验合法配置、readiness、Sheets reader、Research service、SQLite store、Workflow runtime 与 Observer wiring。
- 新增三条入队 work 的 stop/drain test，验证所有 due item 落盘和线程退出。
- `ruff check src tests`、GUI/launcher tests 与完整 deterministic pytest 通过；最终 rerun 记录见本轮验收提交。
- GUI 窗口关闭现请求 stop-after-cycle，并用 Tk `after()` 等待 backend terminal state 和 worker thread 退出后再 shutdown/destroy；关闭期间按钮进入“正在退出”状态且不会阻塞 Tk 主线程。
- GUI deterministic tests 覆盖运行中关闭、cycle 多条 due work drain、等待 worker 退出后 destroy，以及 STOPPED 立即关闭。
- Human-assisted live smoke：在 clean feature worktree 从 `python -m src.gui.main` 启动 production GUI，Owner 点击 Start / stop-after-cycle / 第二次 Start / 窗口 X；没有使用 MockBackend。
- 使用既有授权 Chrome profile 的 localhost CDP；Research readiness 与本机 Research credential prerequisites 通过。只读 Sheets OAuth 受保护 refresh grant 有效；未观察到 OAuth consent/login target，也未报告重复 OAuth 弹窗。
- production config 精确使用获批的 Spreadsheet ID、`2026` / `SHAHAB`、本机 OAuth client JSON、`runtime/production/workflow.sqlite3`；Brand updater 仍 disabled。SQLite/Excel 在 smoke 前不存在，本轮由正式路径新建，未覆盖既有生产文件。
- 真实 poll 使用配置的 `2026` / `SHAHAB` 两个 worksheet，创建 2 条持久 Workflow 记录；其中有待调研项的记录来自 `2026`。Research 完成 1 条，另一条为 future `RETRY_WAIT`。Excel 有 1 行，与 completed SQLite inquiry ID 对应；型号、数量一致，canonical 展示列存在且有值。GUI 从 backend current-run `Order` 渲染该同一 inquiry 的表格字段，详情源自同一 Excel display row。
- stop-after-cycle 后 SQLite 无 `QUEUED` / `RESEARCHING` work，保留 1 条 future retry。第二次 GUI Start 后 backend 线程恢复运行，SQLite 总记录仍为 2、inquiry ID 无重复，completed row 未重复创建。
- Owner 在第二次运行期间关闭窗口；production GUI 进程退出，无 launcher/poller/worker ghost process。SQLite `integrity_check` 正常，Excel completed row 仍在。浏览器 target 检查未发现 OAuth 登录/consent 页；Research CDP adapter 通过 background target 创建采集页，不调用前台激活。

Current:
- CEO 最终代码复审通过：production composition、stop-after-cycle drain、fail-closed runtime handling 与 GUI non-blocking graceful close 均满足代码验收。
- Human-assisted Windows GUI/V1 live smoke 已执行；SQLite/Excel 结果完整性与 close 后进程退出已核实，未启用 Sheet Brand 写回。
- 最终 deterministic verification 和 self-review 完成；尚未 merge main。

Next:
1. Main Programmer 完成最终 diff/self-review 与 Git-ignored runtime 确认。
2. commit/push `feature/v1-production-launcher`，提交 CEO Review。
3. CEO Review 后决定是否 merge main；本阶段不自行 merge。

Blockers: NONE。
Owner Decisions:
- Production GUI 第一阶段默认保持 Google Sheet Brand 写回 disabled/no-op，不新增真实 Sheet 写副作用。
- 当前阶段目标是先让 GUI 真正跑 V1；EXE 打包与开机自启放在后续阶段。

Branch: feature/v1-production-launcher

Last Good Commit: b14b9409104a7ed912cd8a2a0ca80bef7db5d8cc
