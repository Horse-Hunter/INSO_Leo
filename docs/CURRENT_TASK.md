# Current Task

Status: READY_FOR_CEO_REVIEW

Goal: 交付 INSO_V1.1 Windows 可发布版本：从已验收 main 生产基线构建可双击启动的 Windows 桌面包，解决 frozen runtime 路径、配置发现、单实例、日志/启动错误、CDP Chrome 启动/复用与发布包 smoke；不改变已验收业务规则。

Business Outcome:
- Owner 不再需要打开终端执行 `python -m src.gui.main`，可从 Windows 发布目录双击 `INSO_V1.1.exe` 启动。
- 发布版继续使用同一 ProductionBackend / Workflow / Research，不出现“打包后另一套逻辑”。
- 发布版能稳定找到本机 Git-ignored runtime 配置、SQLite、Excel 与 OAuth client；不会把 secret/token/cookie/browser profile 打进 EXE 或提交 Git。
- 若已授权 CDP Chrome 正在运行则安全复用；若未运行且本机配置了批准的 Chrome executable/profile，则由应用启动专用 CDP Chrome。应用只关闭自己启动的浏览器，不关闭用户预先存在的 Chrome/CDP。
- 同一 Windows 用户同时只允许运行一个 INSO_V1.1 实例；第二次双击给出明确提示并退出。
- windowed EXE 没有控制台时，启动失败仍有可理解的弹窗与本地滚动日志可查。

Acceptance:
1. 版本与入口
   - Windows 窗口标题、发布目录、EXE 名统一为 `INSO_V1.1` / `INSO_V1.1.exe`。
   - Python 开发入口 `python -m src.gui.main` 继续可用，`--mock` 继续仅用于开发/演示。
   - 发布版默认 Production，不得因打包变成 Mock。
2. frozen-aware 路径
   - 新增单一 Public runtime/app-root resolver（建议 core/launcher infrastructure seam），repo 模式保持当前 repo root 语义；PyInstaller frozen 模式以 EXE 所在发布目录为 app root。
   - ProductionBackend 不再直接依赖 `Path(__file__).resolve().parents[2]` 作为唯一生产路径来源。
   - 默认配置仍为 `<app_root>/runtime/research.json` 与 `<app_root>/runtime/production.json`。
   - production/research config 内现有相对路径保持相对 app_root 解析，避免破坏已验收的 `runtime/production/workflow.sqlite3` 等配置。
   - 可选支持明确环境变量覆盖（例如 `INSO_RUNTIME_DIR`），但若实现必须有文档、测试和 fail-closed 行为；不要为了“灵活”引入复杂配置系统。
3. 发布目录
   - 首版采用 PyInstaller `onedir + windowed`，优先稳定、可排障；本阶段不追求 onefile。
   - 目标结构至少：
     `dist/INSO_V1.1/INSO_V1.1.exe`
     `dist/INSO_V1.1/_internal/...`
     `dist/INSO_V1.1/runtime/`（本地部署时创建；通用 Git/build artifact 不包含真实 secret/config/runtime 数据）
   - `dist/`、`build/`、本地 release runtime、日志继续 Git-ignored。
   - 提交可复现的 PyInstaller spec/build script（例如 `packaging/INSO_V1.1.spec` + `scripts/build_windows_release.ps1` 或等价结构）。
4. 依赖与 PyInstaller
   - 明确发布构建所需直接依赖，新增 release/build requirements 或等价可复现说明；不要只依赖某台机器“碰巧已装”。
   - spec 正确收集 customtkinter 所需 data、Google OAuth/Sheets、openpyxl、Playwright Python runtime 等实际使用依赖。
   - 不捆绑 Chromium/Chrome 浏览器二进制；Research 继续连接外部批准的本机 Chrome/CDP。
   - 不捆绑 OAuth token、client secret、credential、cookie、storage state、SQLite、Excel、browser profile。
5. 单实例
   - Windows 发布版使用 OS 级可靠 single-instance guard（优先 named mutex；可等价实现）。
   - guard 必须在 ProductionBackend/browser bootstrap 之前取得。
   - 第二实例不得启动第二套 poller/worker/CDP；显示“INSO_V1.1 已在运行”之类明确提示后退出。
   - 正常退出和异常退出后锁应由 OS 自动释放，不依赖脆弱的 stale lock file 清理。
   - Python 单元测试需能通过 injectable seam / fake 验证，不要求 CI 真创建 Windows mutex。
6. 启动错误与日志
   - windowed EXE 顶层启动异常不得静默消失；显示非敏感中文错误提示和日志位置。
   - 新增本地滚动日志（建议 RotatingFileHandler，有限大小/数量）到发布 app root 下可写的 runtime/logs 或等价路径。
   - 日志不得输出 secret/token/cookie/profile 内容；继续沿用现有 sanitized runtime errors。
   - 如果 app root 不可写，必须 fail closed 并给出可操作提示；不要偷偷写到未知目录。
7. CDP Chrome bootstrap / ownership
   - 在 Production Launcher 的基础设施边界实现，不放进 GUI，不复制 Research 浏览器逻辑。
   - 启动时先 probe 已配置 CDP URL：
     * reachable：attach/reuse，标记 `owned=False`，应用退出时绝不关闭它。
     * unreachable：若 production config 明确提供批准的 Chrome executable + user-data/profile dir + debug port，则启动该专用 CDP Chrome，等待 readiness，标记 `owned=True`。
     * 缺配置、启动失败或 readiness 超时：fail closed -> GUI/启动提示“需要人工处理”，不猜路径、不创建未知 profile。
   - 不硬编码 Owner 当前机器的绝对 Chrome/profile 路径进 Git；这些只存在于 Git-ignored production config。
   - 不删除、不复制、不重置现有 browser profile。
   - owned browser 在应用最终 graceful shutdown 后应尽量正常关闭并确认无残留；不得 kill 用户已有浏览器。若实现正常关闭需要 CDP Browser.close 或等价安全机制，必须只对 owned session 生效。
   - CAPTCHA / OTP / 登录 / 设备验证仍由人工完成，不自动绕过。
8. production config 扩展
   - 允许向 Git-ignored `runtime/production.json` 增加 browser bootstrap 非 secret 字段，例如 executable/profile/debug-port/timeout；命名由实现决定。
   - 旧 production.json 在 CDP 已经 reachable 的情况下仍可工作，避免无必要的强制迁移。
   - 若 CDP 不 reachable 且缺 bootstrap 字段，应明确人工处理，而不是异常 traceback。
9. 应用图标
   - 添加一个简单原创的 INSO V1.1 Windows app icon 作为发布资产；不使用第三方商标/受版权图片。
   - 本阶段图标只要求清晰、专业、在任务栏/Explorer 可识别，不做品牌设计项目。
   - icon 源资产与 `.ico` 可提交；不要把字体文件等无关大资产提交仓库。
10. 发布包运行
   - 双击 EXE 后 GUI 正常出现，无 console window。
   - GUI 的 V1.1 历史结果、重要程度、颜色、倒计时、stop-after-cycle、graceful X close 与 Python 模式一致。
   - “打开 Excel”“打开结果目录”在 frozen 模式指向发布 runtime 配置定义的真实路径。
   - OAuth protected refresh grant 继续使用 Windows CurrentUser DPAPI / LocalAppData，不因 EXE 路径变化重复 consent；client secret 路径仍由本机 config 提供。
11. 资源/退出
   - 退出时先沿用现有 GUI graceful close：当前 cycle 安全收尾、worker/poller 退出。
   - 再释放 owned browser / single-instance resources；不得先杀浏览器导致正在执行 Research 中断。
   - 关闭后无 INSO launcher/poller/worker ghost process；owned CDP Chrome 无残留；reused Chrome 不受影响。
12. deterministic tests 至少覆盖：
   - repo vs frozen app-root/runtime path resolver；
   - relative production/research paths；
   - single-instance acquire/fail/release seam；
   - second instance 不构造 ProductionBackend；
   - CDP reachable -> reuse/no close；
   - CDP unreachable + valid bootstrap -> launch/wait/owned；
   - missing bootstrap / launch timeout -> fail closed；
   - shutdown 只关闭 owned browser；
   - startup exception -> sanitized user-facing message/log path seam；
   - existing GUI/launcher/research/workflow regressions。
13. Windows release smoke
   - 在 clean release worktree 构建 `dist/INSO_V1.1/`。
   - 使用本机 Git-ignored runtime 配置完成本地部署；不得把配置提交或放入可分享的 generic artifact。
   - 从 Explorer/双击方式启动 EXE，不通过 Python。
   - 验证 production GUI、history display、runtime config discovery、OAuth silent reuse、CDP attach/launch、真实 Sheets poll 至少一轮。
   - 若有 due inquiry，允许完整处理；如没有，则真实 poll 成功即可，不伪造。
   - 测 stop-after-cycle、再次启动 dedup、运行中 X graceful close。
   - 测第二次双击只提示已有实例，不创建第二套 runtime。
   - 测 app-owned Chrome 与 pre-existing Chrome 两种 ownership：owned 随 app 安全退出；pre-existing 不被关闭。
14. soak 准备
   - 本阶段只需提供可执行的 soak checklist/命令与 diagnostics 观察点，不要求一次性跑 8/24 小时。
   - 下一阶段再执行长时间 soak：内存稳定平台、线程/handle、Excel/SQLite、CDP pages/contexts、15 分钟周期。
15. 验证
   - `ruff check src tests`
   - release/launcher/gui relevant tests
   - full deterministic pytest
   - `git diff --check`
   - PyInstaller clean build success
   - Windows packaged smoke success
   - 对 build/dist 做 secret/config/runtime 扫描，确认无 token/client secret/cookie/profile/sqlite/xlsx 泄漏。

Constraints:
- 不修改已验收 Research/Workflow/Sheets 业务规则。
- 不开启 Google Sheet Brand 写回；ProductionBackend 继续 `brand_updater=None`。
- 不把实际 production config、Spreadsheet ID、OAuth client JSON、token、browser profile、SQLite、Excel、credential 写入 Git/spec/dist generic release。
- 不下载或捆绑 Chrome/Chromium。
- 不绕过 CAPTCHA/OTP/设备验证。
- 不 reset/clean/delete历史 Research worktree。
- 不做 installer/MSI、自动更新、代码签名、开机自启；这些属于后续发布增强。
- 不为了打包把 GUI/launcher/research 业务代码复制到另一个 entrypoint。

Architecture Decision:
- 新增 release/runtime infrastructure 只负责 app-root、single-instance、browser ownership、logging/startup boundary、PyInstaller packaging。
- GUI 继续只依赖 GuiBackend contract；launcher 继续是 production composition root。
- Python mode 与 frozen EXE 必须使用同一 ProductionBackend 与业务模块。
- 首版选择 onedir，不选择 onefile；先保证银行内网环境下稳定、可审计、可排障。

Done: Runtime root, single-instance guard, safe startup logging, CDP ownership and onedir packaging are implemented. The frozen Core Provider bundles only its canonical PowerShell module, never Vault data; the packaged read-only diagnostic confirms the required Site IDs without exposing credentials. Vault subprocesses remain hidden. Explorer-launched production GUI successfully polled the configured Sheets with OAuth silent reuse, wrote terminal results to matching SQLite/Excel history, displayed countdown and history, rejected a second instance, drained stop-after-cycle, preserved dedup, and closed safely on X. Dedicated-profile authenticated collection now uses normal Chrome only for due work, creates no visible startup window, keeps owned windows hidden, and closes its owned browser after the due batch drains. It does not close a reused browser. IC.net HTTP rejection is classified explicitly. LCSC initializes its authenticated home session before search, preventing a false temporary-unavailable result. `SHAHAB` schema selection is case-insensitive while the original worksheet title remains the API and identity value, so the confirmed production title reads B/D/E/F correctly. The GUI no longer displays the unreliable pending count; partial success uses normal 24-hour blue/history white coloring and exceptions remain red. No price, MPN, stock, FX, retry or Google Sheet Brand-write rule changed.

Current:
- Owner completed the approved dedicated-profile login and latest packaged smoke. Production collection has no visible Chrome or PowerShell interruption, and the latest SHAHAB pending-order discovery and GUI changes were confirmed.
- CEO Final Review's lazy-CDP retry regression is fixed. A narrow `ResearchPreparationError` now identifies failures before `ResearchService.execute()`. Workflow rolls back the transient claim and its attempt count, then lets launcher enter `MANUAL_REVIEW` and stop polling/worker without creating `RETRY_WAIT` or spending a business retry. Generic Research exceptions and `RETRYABLE_FAILURE` remain on their unchanged 15/30/60 retry path.
- Browser acquisition failure is fail-closed. If readiness cannot be proven after an owned browser is acquired, launcher closes that owned handle before entering manual handling. A packaged negative-path smoke used an isolated runtime with an unreachable CDP and no bootstrap config; the GUI showed “需要人工处理”, did not start Chrome, and its isolated queue retained zero attempts and no Research status.
- CEO Final Review found one release-build hygiene blocker that also explains the Owner-observed project growth from roughly 5 GB to 8 GB during repeated package testing. `scripts/build_windows_release.ps1` creates fresh GUID paths `build/release-dist-<id>` and `build/pyinstaller-<id>` for every build. `$stageWork` is never deleted, and `-BuildOnly` also leaves every `$stageDist` behind. Repeated clean builds therefore accumulate large PyInstaller staging trees indefinitely.

Closeout:
- `scripts/build_windows_release.ps1` now uses the single marked staging root `build/windows-release-stage`; each next build replaces only this verified script-owned root. PyInstaller work is removed in `finally`; the root is retained only for a successful `-BuildOnly` artifact. A previous stage with missing ownership marker, unexpected children, a leftover work tree, or runtime-data scan findings is preserved and causes a fail-closed error. An existing deployed `dist/INSO_V1.1` is still never replaced.
- Two consecutive final-version `-BuildOnly` builds succeeded. Each passed frozen `--self-check` and `RELEASE_SCAN_OK`; after each, exactly one fixed BuildOnly artifact remained at 0.246 GiB and no work directory remained. The second build did not add a staging tree or increase staging size.
- Pre-clean project root: 12,868,357,503 bytes / 11.985 GiB. Post-clean: 6,521,603,147 bytes / 6.074 GiB. Net project-root reduction: 6,346,754,356 bytes / 5.911 GiB. `.worktrees/` went from 11.970 GiB to 6.056 GiB; active release `build/` is 4.939 GiB, deployed `dist/` is 0.246 GiB, and `.venv-release` is 0.260 GiB.
- Removed all 23 old GUID PyInstaller work trees and all 23 old GUID release staging trees after a clean artifact scan. Removed 17 source/test standard cache directories (1.61 MiB). The first cleanup attempt met a Windows access denial on DLLs loaded from two old release staging copies. No process was terminated. After Owner confirmed there was no GUI or real Research, the read-only process snapshot showed zero `INSO_V1.1.exe` processes; both remaining trees were rescanned and safely removed.
- Latest packaged process-lifecycle smoke: started the current BuildOnly EXE with `--mock` (no Sheets poll or Research), confirmed its GUI window appeared, sent the normal window-close message, observed exit code 0, waited seven seconds, then observed zero `INSO_V1.1.exe` processes. No ghost process remained. The smoke generated a sanitized startup log under the staging app's local `runtime/logs`; it was retained. The build script now refuses to replace any existing staging artifact that contains a `runtime` directory, preserving local runtime data.
- Preserved 18 ambiguous old-release/recovery entries totaling 4.41 GiB (`UNKNOWN_LARGE_DIRECTORIES`) for CEO/Owner classification. Also preserved the real deployed release, all worktrees (including the protected Research runtime worktree), `.venv-release` and its caches, generic temporary Tcl/Tk copies, test SQLite/Excel data, runtime/Vault/OAuth/profile data, and every other unknown item. No worktree was removed.
- Only PowerShell build script and this task document changed; no Python runtime/business code changed. Validation: PowerShell parser, `git diff --check`, two consecutive clean Windows PyInstaller builds with stable staging size and no work tree, frozen self-check, and `RELEASE_SCAN_OK`. Full Python test suite was not rerun because Python source was unchanged.
- No live Research smoke or production Sheets poll was run as part of this storage/build-maintenance task.

Remaining review notes:
- `UNKNOWN_LARGE_DIRECTORIES`: 18 old-release/recovery entries totaling 4.41 GiB remain because their contents may be useful and were not approved for deletion.
- The successful lifecycle smoke left a sanitized local startup log inside the fixed BuildOnly staging artifact. It was kept as runtime data; a later clean BuildOnly replacement will fail closed until that local runtime directory is reviewed.
- Commit/push this branch for CEO review; do not merge main.

Blockers:
- No remaining code blocker. The retained unknown backups and process-held staging copies are conservative cleanup boundaries documented above for CEO/Owner review.

Owner Decisions:
- 发布名称：INSO_V1.1。
- 首版 Windows 打包采用 PyInstaller onedir + windowed。
- 发布版需要单实例、可诊断启动错误、runtime 配置发现与 CDP Chrome ownership。
- 不做 MSI/installer、自动更新、签名、开机自启；先完成稳定可双击运行的发布目录。
- packaged smoke 通过后再进入长时间 soak。

Branch: feature/v1-1-windows-release

Last Good Commit: cee7804
