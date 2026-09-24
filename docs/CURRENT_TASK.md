# Current Task

Status: ACTIVE

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
- `ruff check src tests`、launcher tests 与完整 deterministic pytest 通过；未运行 live smoke（本轮明确不要求）。

Current: 本轮 CEO Review 提出的确定性 blocker 与 graceful-stop cycle 缺陷均已修复，等待 CEO Review。

Next: CEO Review；不 merge main。

Blockers: NONE（live smoke 未运行，依本轮要求暂不执行。）
Owner Decisions:
- Production GUI 第一阶段默认保持 Google Sheet Brand 写回 disabled/no-op，不新增真实 Sheet 写副作用。
- 当前阶段目标是先让 GUI 真正跑 V1；EXE 打包与开机自启放在后续阶段。

Branch: feature/v1-production-launcher

Last Good Commit: 944c0624f935cd808f2d45f8fc6c01fcedb3e236
