# V1.5-B 工作台升级

状态：RELEASE_HOLD。最终验收 IN_PROGRESS，24 小时尚未完成，不能建议 BUILD_READY。

## 当前桌面即时验收（2026-10-26，部分完成，响应待确认）

Owner 本次明确授权不等长测、立即显示最新源码，并在条件安全时进行少量只读查询。
实际启动 SHA：`b2b4936770aad4a8cda53e5ecaf6fbee8475d17b`，分支工作树开始时干净，
应用源仍等同 CEO `9f5522d7bef41a15fc099f9ad1545120dd9565c1`，本轮未改 `src/` 或长测脚本。

**已实际启动当前 Windows 桌面窗口**，不是旧 EXE，也不是非输入隔离桌面：
标题 `INSO V1.5 最新源码 b2b4936 | MOCK 合成验收（无生产操作）`，PID **71024**，
北京时间 12:01:14 启动。复用 `gui.main`、原 app、MockBackend、原单实例锁和托盘代码；
临时注入合成投影和安全拒绝，不构造 ProductionBackend。250 条合成历史加 Mock 自带演示
循环，900 秒模拟等待；TP 配置显式 false，列表 TP 只是合成历史。标题/备注明确 Mock，
原 Mock 健康卡及“开始轮询 Google Sheets”日志也是模拟，不能当成生产健康/业务执行证明。
临时壳只给原入口注入 Mock 数据、日志和采样，不是新的业务入口/调度器，未增加依赖。

独立 `INSO_RUNTIME_ROOT`：`D:/Program_Leo/INSO_Leo/.tmp/v15-visible-acceptance`。
网络 connect、SMTP、SQLite 和后续子进程均有拒绝守卫；没有加载生产队列/凭据。
启动前 V1.4/旧 V1.5 EXE 均未见进程；原 `Local\INSO_V1.2` 不存在，Mock 启动后持有该原锁，
未绕开或另建业务单实例机制。原部署/runtime/junction/回滚文件未覆盖或清理。

当前桌面截图：[实际可见总览](docs/evidence/v15b/visible-acceptance/visible-overview.png)。
本次保持窗口供 Owner 查看；下述未通过项不能被前一节隔离桌面的六页截图替代。

| UI 项目 | 本轮实测 / 尚缺 |
| --- | --- |
| 新工作台、三模块 | HWND/标题及自身 PrintWindow 截图已验证；询价等待、报价空闲、TP 未启用可见，15 分钟倒计时在截图中正确显示剩余 13:27 |
| 六菜单/搜索/筛选/排序/分页/详情 | 合成数据及原控件已加载；**当前桌面的实际鼠标操作 NOT_VERIFIED**，不能拿先前程序调用/单元测试代替 |
| 调研/异常/历史/日志 | 合成来源、缺价、UNKNOWN/SENT 历史及日志已注入；实际逐页打开仍 NOT_VERIFIED |
| 三重跑 | 临时桩保留普通样本采购/报价、TP 样本 TP、UNKNOWN 全禁用，以及请求安全拒绝；本窗口实际点击/右键反馈 NOT_VERIFIED；真实业务授权链由本轮离线测试覆盖 |
| 设置 | 原入口加载，TP false；登录/订单邮件/文件入口仍为 Mock 或拒绝；没有测试真实开关或修改生产配置 |
| 系统菜单 | 键盘 Alt+Space 后可访问树出现系统菜单，Escape 后菜单消失 |
| 最小化/真实托盘/恢复/退出 | **NOT_VERIFIED**；鼠标工具没有成功执行最小化，未借此关闭窗口。不能把进程存活当成正常退出证明 |

**新验收阻碍需独立复核，不能宣称 UI 已通过。** computer-use 的 WGC 捕获先后报
`FrameArrived timed out`、`window capture timed out`；按指引重新选择/激活并重试一次仍失败。
不含截图的可访问树可读，但自绘控件多数是匿名窗格/图像，只有系统标题栏按钮有语义名称。
最小化按钮调用报 `coordinate input geometry is unavailable`，没有将这次尝试计为成功。
未使用原生鼠标注入/猜测坐标绕过工具失败。自身截图只用于证据，不冒充操作工具的截图。

另外，本窗口 30 秒资源回调最后写入于 **12:07:46**（391.484 秒），之后多次复查没有继续
增长；PID 存活、Windows Responding=True、stderr 为空、没有退出标记。
12:16:17–18 Mock worker 仍生成了第二轮模拟日志，但 UI 采样仍停在原处，不能仅凭后台存活
判定界面正常。
这与系统菜单工具尝试时间接近，**原因 UNKNOWN**，可能是原生模态/工具影响，也可能是
演示或 UI 响应问题，不能确认归因，更不能用低 CPU 掩盖。已请 Owner 按 Esc 并切换任务中心
核实是否恢复；截至本次记录尚无答复。未强杀/重启窗口，未改受审源码。
最小下一步：在 Owner 可见桌面确认菜单/倒计时是否继续，再在无工具干扰时复核；若仍停滞，
单独定位阻塞点供 CEO 审核。本阶段不擅自增加 UI 修复。

### 当前业务基础设施只读结果

只附着现有 Chrome 9222 的唯一 context，开始只有一个无归属原页面，没有活跃业务页冲突。
复用各站原 CDP 客户端、解析器和共享 Playwright facade；不新建 Chrome/Profile，不读取 Vault，
不登录、不调用采购或 SMTP。每个查询页由既有客户端收回，最终原页保持、新余页 0。
没有输出原始 HTML、TSV、账号、客户或业务报价内容，只保留计数/币种和已有测试型号。

| 表面 | 结果 |
| --- | --- |
| IC.net / STM32G0B0CET6 | 5.781 秒，解析 49 行；当前参考价有效，RMB。只读查询/解析通过，不是采购决策 |
| Findchips / 同型号 | 10.203 秒，9 个解析报价，USD |
| 华强 / 同型号 | 5.281 秒，40 个解析报价，RMB |
| 立创 / 同型号 | 5.250 秒，匹配产品、3 个价格档，RMB |
| BOM.AI / 同型号 | 3.125 秒，50 个解析报价，RMB |
| BOM.AI / BCM957504-N425G | 另一次已有授权型号复核：2 条 USD，币种均 confirmed；未将美元标为 RMB |
| Google Sheets | 原 Google Web 元数据读取通过，已配置文档/子表/gid 保护未放开；2026/SHAHAB 存在，共 3 个白名单子表。单元格/订单行对应 NOT_VERIFIED：原生 TSV 路径会下载整表，本次未为少量验收扫描全体订单 |
| INSO | 原 `authenticated_inso_shell_available` 只读观察为 false；没有可复用的已验证操作租约。历史报价 NOT_VERIFIED，未为凑覆盖构造生产 Backend、跳过身份保护或执行登录 |
| 真实阶段 → GUI | **NOT_VERIFIED**。上述是独立只读探针输出；没有伪装成演示窗口中的真实业务任务/日志 |

原中央 SQLite 使用 `mode=ro&immutable=1`、query_only，只读打开前确认无 WAL/journal。
quick_check=ok，仍为 **4 个 TP / 4 个 MAIL_QUEUED / 6 个 SENT 收件结果**，指纹前后相同。
没有通过应用构造器打开生产库，也没有复制真实库到测试库、迁移、补写或清理任务。

### 离线安全流转及性能初验

本轮 `tests/inso tests/workflow tests/sheets` 及既有 manual_order/tp_integration/
v13_quotation_operations：**1120 PASS、1 SKIP，44.04 秒**，SMTP 套件守卫保留，无真实发信。
复用原假适配器/独立临时数据库，包含重复采购、Save/Send/Google 写入门禁、报价状态、
TP 身份/幂等、UNKNOWN 与多收件人、人工重跑即时权限；不是实际采购或发信验收。
该独立测试库已在保存输出后退休。原测试 skip 保留，未放宽门禁或改业务算法。

可见 Mock 的 13 次资源采样覆盖 30.765–391.484 秒，含 UI/工具活动，非纯空闲基准：
排除首 60 秒后整机 CPU 均值 **0.677%**，范围 **0.289–1.528%**；
RSS **96.86–97.70 MiB**，Private **71.38–72.18 MiB**；Python 线程 2，系统线程 7–15，
句柄 579–590、GDI 136、USER 261–262，after 6、应用队列 0。
首次 60 秒只读 GetProcessTimes 观察得整机 **0.161%**（单核 2.578%），但该采样来自沙箱
桌面，其前台判定不能用于 Owner 桌面。随后用 Owner 桌面权限重测 60 秒，整机 **0.192%**
（单核 3.073%），7 个点均有有效前台句柄且为 Mock。证据分别为 `foreground-cpu.json` 和
`foreground-cpu-owner.json`，后者才可用于前台点观察；采样点不证明整段持续前台。
**资源回调停滞期间的低 CPU 不能当成正常前台空闲/响应或托盘验收通过。**
实际托盘资源和关闭后的资源释放均 NOT_VERIFIED。

实际 Mock 日志为独立目录 `mock-events.log`（200KB×3 轮转上限），13 条资源记录在
`resources.jsonl`；已有启动日志 `runtime/logs/INSO_V1.3.log` 仍空，不声称有真实业务日志。
必要合成界面、日志、资源原始值/摘要、脱敏只读统计、临时探针副本及 pytest 输出已保存至
`docs/evidence/v15b/visible-acceptance/`，不是另一份报告。在线窗口/输出仍保留供 Owner 检查。

与长测严格区分：**70956 是原 24h，71024 是可见 Mock**。长测约 49 分钟时仍健康，
8 次合成负载，0 回调/守卫异常、最大采样缺口约 60.079 秒；未停止/重启或改其源码/数据。
跟进指令已增加保护可见 Mock 目录/进程，不能收集长测时误清理。24h 依然 NOT_VERIFIED。

结论：最新源码确已可见启动，五源只读解析及离线安全测试取得证据；
**菜单/托盘/退出、停滞归因、前台空闲、Google 行对应、INSO、真实阶段传递仍未完成。**
保持 **RELEASE_HOLD**，不建议 BUILD_READY；下一步优先完成可见响应与托盘人工/工具复核，
再做经批准的只读缺项与 24h 收集。打包/安装/部署、真实写表/采购/发信仍需独立授权。

## 最终源码隔离实机验收（2026-10-26，进行中）

受测应用源码：`9f5522d7bef41a15fc099f9ad1545120dd9565c1`。从原 V1.5 分支快进至此，
开始时工作树干净；该提交相对 `bbe2743e0ba3c2f9ddcd25ec0dce7e483652db22` 仅有任务文档变更。
本次仅改任务文档、报告及手动诊断脚本，没有修改 `src/`，没有运行早期 V1.5 EXE。

复用审计：沿用 MockBackend、现有六页面 UI、只读观测 DTO、有界事件/日志、既有自身进程
Win32 采样器及 PrintWindow 截图函数。旧截图入口仍按旧版 7 项观测值解包，并模拟控件缩放，
不能作为本轮真实 DPI 验收；新增 `scripts/accept_workbench.py` 只补当前 9 项观测、有限时重复
负载、隔离守卫及证据输出，不是生产入口或新调度系统，无新增依赖。

环境：Windows / Python 3.12.10 / 16 逻辑 CPU；实际单屏 1920×1080、工作区 1920×1030，
GetDpiForWindow=120，即系统 125%。未调用控件缩放模拟，也未修改显示/电源/优先级设置。
100% 与 150% 系统 DPI：**NOT_VERIFIED**。

安全自检的早期失败：第一次脚本守卫阻断第三方主题库读取 OS 版本所需的本地子进程；
缓存 OS 信息后仍遇沙箱 Tcl 读取限制，使用已安装 Tcl、未改文件权限或部署资源。
随后普通桌面短测发现 Tk 映射会进入前台，守卫立即撤回窗口并终止（约 1.1 秒）；
此失败不撤销，也不算验收通过。之后改用 CreateDesktop/SetThreadDesktop 建立**不切换的
非输入隔离桌面**，未启动 Explorer/浏览器/业务进程。这样可以真实创建 Tk/Win32 窗口并
截取自身 HWND，避免再影响 Owner 的前台；不是在 Owner 当前桌面的人工交互验收。
恢复路径仅在诊断中抑制 lift，业务源文件保持不变。

| 检查 | 当前实测结果 / 限制 |
| --- | --- |
| 六页面 | 已截取 1280×720、1920×1080 客户区各六张，纯合成数据；人工查看小尺寸六页，未见主要按钮溢出 |
| 实际工作区 | 另检 1895×965 客户区六页；共 18 项主要按钮/筛选控件边界检查通过。1080 高客户区含外框超过 1030 工作区，不能声称物理全屏完整可见 |
| 模块/阶段/等待 | 三模块合成观测，循环运行阶段及恢复等待；并非业务 TP 已开启或真实网站异常 |
| 列表/详情/异常 | 搜索、来源/状态筛选、排序、翻页、详情反复打开关闭、UNKNOWN 提示；每页最多 200 行 |
| 三种重跑 | 普通样本采购/报价可见，TP 样本仅 TP 可见，UNKNOWN 样本全禁用；3 个启用按钮均得到假后端安全拒绝。提示由合成桩控制，不替代持久化授权测试 |
| 窗口/关闭 | 三种尺寸、隐藏/恢复及正常退出实测。真实最小化、Explorer 托盘图标/菜单/恢复：NOT_VERIFIED；隔离桌面无 shell，隐藏不等于托盘 |
| 离线回归 | `test_workbench.py` 与 `test_workbench_snapshot.py`：14 PASS，3.38 秒；Ruff / diff whitespace 通过 |
| 安全守卫 | 网络 connect、SMTP、SQLite、后续子进程及业务组合导入拒绝；通过短测守卫触发 0，回调异常 0，应用源散列不变 |
| 游戏 | 没有启动游戏或改前台/电源策略；真实 Chrome Research 的帧率影响 NOT_VERIFIED |

短测：先完成 75.078 秒/6 轮，再用最终诊断脚本完成 44.875 秒/3 轮（请求 35 秒，按采样
周期结束）。覆盖 100/500/1000 条、各轮 300 条合成日志、可见/隐藏交替。后者采样起止：
RSS 49.97→50.45 MiB、Private 31.66→32.67 MiB、句柄 353→353、GDI 57→57、USER 236→287；
这是包含初始化/不同订单数量的短测，**不是稳定趋势或泄漏结论**。
源散列、按钮结果、截图及原始短测采样见 `docs/evidence/v15b/final-acceptance/`。

| 页面 | 1280×720 | 1920×1080 |
| --- | --- | --- |
| 总览 | [截图](docs/evidence/v15b/final-acceptance/page-1280x720-0.png) | [截图](docs/evidence/v15b/final-acceptance/page-1920x1080-0.png) |
| 任务中心 | [截图](docs/evidence/v15b/final-acceptance/page-1280x720-1.png) | [截图](docs/evidence/v15b/final-acceptance/page-1920x1080-1.png) |
| 调研结果 | [截图](docs/evidence/v15b/final-acceptance/page-1280x720-2.png) | [截图](docs/evidence/v15b/final-acceptance/page-1920x1080-2.png) |
| 异常与通知 | [截图](docs/evidence/v15b/final-acceptance/page-1280x720-3.png) | [截图](docs/evidence/v15b/final-acceptance/page-1920x1080-3.png) |
| 运行记录 | [截图](docs/evidence/v15b/final-acceptance/page-1280x720-4.png) | [截图](docs/evidence/v15b/final-acceptance/page-1920x1080-4.png) |
| 设置 | [截图](docs/evidence/v15b/final-acceptance/page-1280x720-5.png) | [截图](docs/evidence/v15b/final-acceptance/page-1920x1080-5.png) |

有限时 24h 已于 **2026-10-26 11:25:25（北京时间）**启动，PID 70956。
预计最早 2026-10-27 11:25:27 后结束；启动的独立进程已复查仍存在，stderr 为空。
原始输出保留在 `D:/Program_Leo/INSO_Leo/.tmp/v15-final-acceptance-24h`，不可在运行中清理。
先空闲基线 10 分钟，再每 5 分钟执行一次负载、轮换 100/500/1000 条；通常每 60 秒采样，
操作前后另取一次资源值。采样含 CPU（单核及整机口径）、RSS/Private、系统/Python 线程、
句柄/GDI/USER、Tk after、应用事件队列、列表/值缓存、日志及 tick/操作耗时。
Tk 内部 OS 事件队列深度没有公开可靠计数，**UNKNOWN**；记录应用队列和可查询的 after，
不能把它们当作全部原生事件队列。只写有限日志/JSONL，未引入常驻监控。
本任务已设每两小时回到本线程收集状态的跟进，健康未完成时静默，完成或失败后收集证据并停止跟进。

**24 小时状态仍为 NOT_VERIFIED**。最终须检实际 elapsed≥86400 秒、最大采样缺口≤180 秒、
无回调/安全异常、应用源散列未改及正常关闭；休眠/中断不能补算成功。最终资源趋势、
异常恢复回落及整段峰值待实际完成后分析。旧基线保留于 `performance.json`（97212f4，
600 秒 idle 的整机 CPU 均值约 0.128%，RSS 74.36–88.23 MiB，Private 53.24–55.07 MiB）。
旧数据与本次桌面/负载/时长不同，只能分条件参考，不能据短测声称升级节省了多少资源。

当前建议：继续 **RELEASE_HOLD，不满足 BUILD_READY**。待真实时长证据收集及未验证项目
由 CEO 明确处置后再判断；本次未打包、安装、发信、访问生产数据或网站，没有清理四 TP/六 SENT。

## CEO 第二轮修正（2026-10-26，当前补丁）

依据审核提交 `e984f6bcf55bb56040573e9268f568fd489a90ea`，原分支从该提交继续，
未重写六页面 UI；第一轮下述 P1-A/P1-B/P2 结论保留为历史，本节说明当前最小增量。

- P1：原 `_manual_idle → can_order_action` 链路保留。移除 TP 前的截止时间赋值，
  新轮开始先清空旧值；既有等待入口/人工操作后的完整重置入口统一发布 `_next_poll_at`
  与 `planned_check_at`。两者按同一个原有单调时钟 deadline 的剩余时间计算，发布时业务锁
  即使延迟，也不能额外延长 900 秒。等待结束/停止关闭时间门禁。
  `_poll_idle`、`_poll_gate`、busy、已排队请求、运行/停止状态及持久化权限检查均保留。
  TP、页面清理和人工操作执行期间不开放窗口；没有提前触发下一轮或新增调度路径。
- P2：新增可选只读 DTO 字段 `Order.tp_task_id`。现有投影后台依据 canonical record_identity
  的 spreadsheet/sheet/row 调用既有 `task_key`，只关联已存在且完整型号、数量一致的 TP DTO。
  无 canonical 身份、仅型号相同、来源/字段冲突或 TP 未加载时不显示正向提示，不伪造 inquiry_id。
  UI 仅查看快照中的关联、business_status、delivery_status：复用现有可重跑集合
  MAIL_QUEUED/FAILED + None/SENT/PERMANENT_FAILURE；UNKNOWN、SENDING、PENDING、
  RETRYABLE_FAILURE、RESEARCHING 等明确不允许状态保守禁用。
  SENT 允许人工明确发起新一代任务，符合既有 TpStore 规则；自动幂等及 UNKNOWN 防重发不改。
  提示仍不是授权，旧 SENT 快照面对当前 UNKNOWN/SENDING/RESEARCHING 时，原实时门禁拒绝请求。

生产源码只改 `src/launcher/backend.py`、`src/gui/contracts.py` 与 `src/gui/workbench.py`。
详情差异缓存签名纳入只读提示值；关联 TP 状态变化时，普通订单内容即使不变，重跑按钮也会刷新。
提示值未变化时保留原详情控件，新增真 Tk 断言同时检查这两个方向；无新增 SQL 或布局重构。
测试修改原虚拟时间等待/真 Tk 测试并新增 `tests/launcher/test_workbench_review2.py`；
4 处替换完整等待函数的旧测试桩补调用真实入口发布步骤，原恢复/通知/停止断言未删除或放宽。
TP 组合测试新增执行/页面清理期间拒绝操作的断言。未改业务算法、月份范围、邮件队列、CDP、
六页面布局、默认 TP 配置、依赖或线程。其他业务提交仍需各自独立审核。

合成验证覆盖：TP 0/5/10/20 分钟后每个 0.25 秒等待切片的 UI 及 canonical 操作可用性，
到期拒绝、锁等待延迟、完整人工重置、恢复、停止和已有 UNKNOWN/采购重复保护；
无 TP 关联/有效关联、来源与型号/数量冲突、10 组 TP 状态组合，以及数据库收件人状态已变更
而快照未刷新的安全拒绝。所有测试使用临时数据库与假采集/假通知，未进行真实发信或生产操作。

验证结果：最终定向 **119 PASS / 17.53 秒**；最终完整回归 **2733 PASS / 1 SKIP / 105.02 秒**。
上述最终版本包含四种 TP 耗时下的实际 SQLite 权限门禁，以及普通行不变时的按钮更新断言。
Ruff（无缓存）及 git diff --check 通过。
最终两次运行没有 SMTP 尝试记录。纯合成结果保存在
`docs/evidence/v15b/pytest-review2-full.txt` 和 `pytest-review2-targeted.txt`。
首轮定向的 6 项旧恢复测试失败来自完整替换等待函数却仍要求预先存在计划时间的测试桩，
已补入口发布步骤，保留原安全断言。未修改原 RFQ008 测试，也未借本轮认可未审核业务改动。
中间一轮全量出现 1 FAIL / 2727 PASS / 1 SKIP（117.19 秒），为恢复场景线程未在原 10 秒
时限内退出；未延长时限。检查中移除新增等待入口的 `_notify` 同步读取，改为仅更新现有
不可变内存快照，避免额外 SQL 扫描；之后完整回归通过。不将一次超时归因为已证明的唯一原因。
锁延迟用例另明确禁止该入口调用 `_notify` / `_cache_workbench`。
本轮全部 `v15b-review2-*` 临时测试目录和中间输出在保存最终证据后退休；沿用原 V1.5
工作树，不改现有部署、回滚、生产库和 CDP 资产。状态保持 REVIEW_REQUIRED，等待 CEO 独立复审。
旧长期性能、24h、系统 DPI 和生产链路的验证边界仍有效，没有声称本轮完成新的长期测量。

## CEO 第一轮修正（2026-10-26）

审核锚点 `a7aaf615449b39f9c3b3606b61c4ffed19aa19e0`，结论 CHANGES_REQUESTED。
仅修正 P1-A、P1-B、P2；此前业务提交的独立审核状态不因本轮而改变。

- P1-A：保留 `_next_poll_at` 及其人工操作门禁。既有 `_wait_between_polls` 真正进入等待时，
  用只读 `planned_check_at` 显示实际计划时间；TP 后、清理完成前显示等待调度确认。
  仍由原单调时钟等待完整 900 秒，人工操作后仍重置完整等待，停止行为不变。
  倒计时正数向上取整，避免最后不足 1 秒提前显示时间已到。
- P1-B：同一实际等待入口结束本轮观测并关闭阶段计时，从原 `_site_outages` 提取恢复来源。
  界面显示等待该网站恢复及已知检查时间；等待时不累加执行耗时，下一轮重新开始。
  故障分类、三小时规则、恢复通知、共享资源/停机代码均未改；不是在异常尚未清理时提前宣称空闲。
- P2：详情及工作台右键菜单使用 `order_action_hint`，仅依据内存快照和已有运行标志提示
  是否可提出请求，不读 SQL、不等业务锁、不增加线程。已知发送/UNKNOWN 等状态保守禁用采购入口；
  Research 完成不等于采购已提交，不能据此禁用合法重跑。
  提交请求仍调用原 `request_order_action → can_order_action`，执行仍通过原门禁。
  旧展示提示过期时，真实提交必须被持久化权限拒绝，未缓存授权作为执行依据。

本轮变更：`src/gui/{app,contracts,workbench}.py`、
`src/launcher/{backend,workbench_snapshot}.py`、
`tests/gui/test_workbench.py`、新增 `tests/launcher/test_workbench_review.py`，以及本报告、原任务和合成测试记录。
没有改六页面视觉结构、业务算法、调度器、浏览器、依赖、生产配置或原 RFQ008 测试。

合成覆盖：TP 耗时 0/5/10/20 分钟后，分别运行原等待循环完整 900 个虚拟秒，
核对 UI 计划与实际返回；Google Sheets/INSO 各连续两轮异常、恢复后重新计时；
人工命令串行执行后重置等待；停止；旧正向提示在持久化权限改变后仍拒绝操作。
真 Tk 窗口在临时 SQLite 独占事务及业务锁被占用时打开详情，另模拟权限查询延迟 2 秒；
两种情况下都没有调用阻塞的权限查询，界面绘制回调仍完成。

验证结果：全量 **2701 PASS / 1 SKIP，104.27 秒**；最终定向 **81 PASS，11.64 秒**。
Ruff（无缓存）和 git diff --check 通过；最终两次运行均无 SMTP 尝试记录。
临时 SQLite/业务锁占用条件下，详情打开及 Tk 绘制合计 771.928 ms；模拟权限查询延迟 2 秒时
为 122.675 ms，均未调用阻塞权限查询（小于 1000 ms 的测试界限）。是本机合成测量，非生产延迟承诺。
完整证据见 `docs/evidence/v15b/pytest-review1-full.txt` 与 `pytest-review1-targeted.txt`。
首轮新增测试暴露夹具未发布运行快照、SQLite 测试连接未关闭，
并发现最后不足 1 秒提前显示到期；前两项修正测试夹具，后一项修正展示取整。
原始 80 项定向检查已通过（12.83 秒），本轮随后增强了 Research 已完成订单仍可合法重跑的断言，
并新增人工操作后重置完整等待及停止检查；上述最终 81 项及全量均含这些断言。
未重复旧版长测；下面性能表、截图及 `performance.json` 均为上一轮候选证据，不冒称本轮源码实测。
本轮仍无真实认证、网站/CDP、订单、邮件、打包或部署，24h/系统 DPI 等 UNKNOWN 保留。

## 基线与边界

沿用独立 worktree 和 `codex/v1-5-tp-research`，起点
`97212f40eb87cad5d0069f0c1f21c4cef71c481b`，已审核锚点
`a29c1466fc5f246636998919a2abd443960894cf`。保留锚点后的货币、邮件、完整型号搜索
和 Owner 授权发布改动；没有重置或覆盖，不能声称后续提交均已获得 CEO 审核。

本轮只改源码、执行离线/合成验证及 Git 提交。未启动生产后端、访问业务网站/CDP、
发送真实邮件、采购、改生产数据库/配置、打包或部署。已安装版本保持原样。
测试中发现旧组合夹具会尝试默认登录查询；现已注入假登录隔离，未进行真实认证，未记录凭据值。

## 复用矩阵

| 现有能力 | 直接复用 | 必要扩展 | 回归风险与验证 |
| --- | --- | --- | --- |
| CustomTkinter / ttk / app | 同一个 root、主线程、Treeview、按钮处理 | 一个 WorkbenchView，六页、详情与响应式布局 | 真 Tk、页面、尺寸/缩放、托盘循环 |
| Order / RunSession / HealthReport | 既有身份、价格、健康与业务状态 | 加法字段、不可变只读快照 | 同型号不合并；TP 保留独立任务 ID |
| 原串行工作流、来源回调 | 执行器、15 分钟截止时间和次序 | 实际阶段/站点、单调时钟、真实整轮边界 | TP 完成前不显示整轮空闲倒计时 |
| SQLite / Excel 状态转换器 | 原读取接口与安全错误分类 | 原后台线程生成有界投影；GUI 只读内存 | 重复读取不调旧 SQL/Excel 接口 |
| 事件队列、日志、系统托盘 | 原控制通道、图标与安全退出 | 状态合并、队列上限、隐藏降频 | 退出命令不丢；恢复不重放积压 |
| 人工重跑、编辑、登录、录单、文件入口 | 原 can_order_action / request_order_action 与门禁 | 详情/设置暴露同一入口，正确映射编辑列 | UNKNOWN、三种重跑、录单、关闭回归 |

## 页面及接口

- 总览：询价采购、报价跟进、目标价调研分别展示真实状态；当前任务/站点/耗时、整轮调度、
  健康与已有统计。待核对数量注明只针对已加载数据，不假装全库统计。
- 任务中心：本地型号搜索，模块/状态/来源/当前会话与历史筛选、排序、详情。
- 调研结果：共用同一列表及已取得的来源数据，不再次触发 Research。
- 异常与通知：既有告警代码、时间及安全说明。邮件 UNKNOWN 明确提示人工核对，绝不显示成功。
- 运行记录：既有安全日志；设置：既有登录、自动订单录单、打开表格/目录、模块与版本信息。
- 小窗口筛选分行，详情自动收起；总览/设置可滚动，矮窗口优先显示当前任务。
  缩放后重新计算宽度并保留控件布局，长型号通过详情/调列宽/横向滚动查看。

`GuiBackend.get_workbench_snapshot()` 是可选加法接口。ProductionBackend 返回内存不可变对象，
使用独立快照锁；报告/线程状态纯读取不再等待持有 SQL 的业务锁。快照不是业务授权依据。
原后台线程生成投影，至多每 2 秒刷新；变更标记使指定订单状态缓存失效。
本地搜索、翻页、页面切换不读网站、Excel 或数据库。

RuntimeObservation 仅记录真实调用边界；查询、重试、订单间等待及人工暂停使用单调时钟，
墙钟展示开始/结束。最多三模块及 200 段记录。阶段结束不代表业务成功，历史缺失不会补造。
TP 后才标记整轮结束，原截止时间/执行次序没移动；停止/人工任务不能篡改先前真实整轮结束时间。

默认 GUI 启动使用一次性 `local-history-loader` 读取本地历史，读完退出；载入期间不能开始业务，
关闭会等待其结束。显式 --start-inquiry 在载入完成后由既有 tick 启动一次，默认仍不自动启动。
没有新增常驻业务线程、浏览器、调度器、依赖或资源监控。
TP 源码默认 false（包括 frozen），只有现有配置显式 true 才启用；生产配置未修改。
普通 Research 1～6 月、TP 1～12 月、六源算法、ECB、SMTP、SQLite 状态机、采购/报价/写入门禁
及 UNKNOWN 防重复规则保留。

## 性能实测

旧/新候选分别完成真实 600 秒空闲、1800 秒前台及 120 秒托盘。
两个阶段使用各自独立进程，在同次会话并行测量；没有缩短或模拟持续时间。
原始采样、环境、源码 SHA256、完成标记及最终源码短测见 [performance.json](docs/evidence/v15b/performance.json)。

| 稳定区间指标 | 旧界面 | 新候选 |
| --- | ---: | ---: |
| 空闲 CPU（整机均值） | 0.1276% | 0.0206% |
| 前台 CPU（整机均值 / 单核基准） | 0.1571% / 2.514% | 0.0160% / 0.256% |
| 托盘 CPU（整机均值） | 0.0930% | 0.0176% |
| 前台 RSS 范围 | 75.65–90.21 MiB | 43.69–64.68 MiB |
| 前台 Private Bytes 范围 | 55.88–56.94 MiB | 27.33–27.72 MiB |
| 前台 Python 线程 / 托盘线程 | 1 / 2 | 1 / 2 |
| 前台原生线程范围 | 6–11 | 3–6 |
| 前台句柄范围 | 543–551 | 277–285 |
| 前台 GDI / USER | 133 / 189 | 56 / 265 |
| 托盘句柄 / GDI / USER | 560 / 133 / 192 | 301 / 56 / 268 |
| tick 中位数 / P95 / 最大值 | 14.286 / 18.734 / 37.386 ms | 0.203 / 0.294 / 2.501 ms |

新界面 USER 对象更多，但循环中稳定。托盘不绘制界面、检查间隔降至 3 秒；本次新版本托盘
总 CPU 略高于前台，不能宣称进入托盘后总 CPU 必然下降。RSS 有环境波动，Private Bytes 较平稳，
不能据此证明长期无泄漏。180 次页面切换中位数 3.814 ms、P95 8.126 ms；另一空闲进程同项
P95 为 58.217 ms。表格首次布局最大 105.029 ms，详情首次打开最高 170.858 ms，
重复相同详情的缓存快路径不代表首次打开耗时。

现有 runtime diagnostics 面向退出取证、GUI helper 仅提供 RSS，未覆盖 Private Bytes、句柄、
GDI/USER；因此新增手动合成测量脚本，应用运行时不加载它，没有新增常驻监控。

环境：Windows、Python 3.12.10、16 逻辑处理器，同机合成 MockBackend，100/500/1000 条订单。
CPU 同时保存单核及整机基准；报告稳定值排除启动前 60 秒和阶段切换后 30 秒。
只采样本 Python 进程，不访问/关闭 Chrome；不能代表生产浏览器、真实账本或游戏帧率。
旧 UI 从起点 Git 对象生成源码临时副本。第一次取得完整空闲样本后提前结束（原因 UNKNOWN）；
另补完整 30 分钟前台和 2 分钟托盘，未把首次不完整前台冒称通过。

运行脚本：

```text
python scripts/measure_workbench.py --output <ignored-output>
python scripts/measure_workbench.py --source-root <git-source-snapshot> --output <ignored-output>
python scripts/verify_workbench_ui.py --output <ignored-synthetic-output>
```

## 测试及基线失败说明

上一轮审核提交全量：2693 PASS / 1 SKIP，103.07 秒。静态检查（Ruff，无缓存）与
git diff --check 通过。本轮最终测试没有 SMTP 尝试记录；跳过项按原平台条件处理。
使用已安装测试依赖，未增加依赖。测试使用合成依赖，未运行真实业务后端。

新增覆盖：整轮 TP 倒计时、墙钟回拨、三模块独立状态、有界队列/缓存、只读快照无 I/O、
业务锁占用时 GUI 仍返回、一次性历史加载及关闭、相同型号保留独立身份、UNKNOWN 非成功、
本地筛选、差异更新保留选中行、隐藏不重绘、详情继续调用原四项门禁。
合成 UI 检查为三档控件缩放 × 三种客户区像素尺寸 × 六页面，以及 90 轮异常/恢复/详情/托盘。
末次投影复核以失败测试复现了普通订单邮件 UNKNOWN 被 Research 完成状态带入“已完成”筛选的问题；
只读投影已修正，并覆盖邮件 UNKNOWN、采购提交 UNKNOWN 与核对歧义三种场景。
统一任务视图依据持久化告警/未确认业务状态进入“需核对”，原 Research 结果和业务台账不改写。
54 个页面/尺寸/缩放组合与 90 轮均通过，无 Tk 回调错误；回调数保持 5，Python 线程保持 2
（含原托盘线程），GDI 保持 57，USER 从 282 回落到 279；句柄保持 320。
Private Bytes 在前 30 轮增加约 0.262 MiB，后 60 轮持平。此短循环不替代 24 小时验证。
100/500/1000 条分别显示 100/200/200 行；实际搜索、来源/状态筛选、横纵滚动及详情的组合操作
耗时为 262.398/334.392/359.514 ms，不是单个手势延迟。日志更新及托盘恢复已断言。
额外修复缺价/零数量/跨年日期排序，并恢复详情中的库存及重要度既有字段。

完整复核曾出现 22 项失败（首个后台测试超时，随后 21 项 RFQ008 夹具级联失败）；另一轮
只剩后台停止等待超时。这些失败保留事实，不能当作通过。期间 SMTP 尝试均被本地守卫阻止，
没有真实发送。已隔离默认登录查询，并把 SMTP 守卫延伸至整个测试进程，避免失败工作线程
跨越夹具释放后绕过拦截。原 RFQ008 文件未改。新增真窗口测试使用子进程隔离原生 Tk 状态；
测试使用已安装 Python 的 Tcl，避开沙箱内冻结 Tcl 资源偶发不可读；未改部署文件或权限。

纯合成截图和检查记录位于 `docs/evidence/v15b/`：`synthetic-overview.png`、
`synthetic-small-high-scale.png`、`synthetic-task-unknown.png`、`ui-checks.json`、
`performance.json`、`pytest-final.txt`。最后一项保留最终完整测试输出。
已退休本轮全部 v15b-* 临时副本、采样目录和测试目录；仅保留上述必要证据与可复用诊断脚本。
测试进程已退出，未新建第二个工作树，保留原 V1.5 开发工作树与现有部署/回滚/CDP 资产。

原先两项 CDP 恢复参数场景失败的处理发生于本任务之前的
`ea537060a42c8b8b53c4472034ff7df4e387189c`，涉及
`test_unsettled_manual_attempt_preserves_durable_old_hold_and_automatic_barrier`：
旧停止预期与已审核恢复策略冲突，原提交调整预期并替换通知副作用。
本轮没有改 `test_rfq008_hold_lifecycle.py`，该文件仍参加回归；历史失败事实不撤销，前述改动待 CEO 独立复核。
既有 GUI 预期仅更新过时轮询文字、设置入口位置、明确要求的 TP 默认值及启动测试桩参数；
原启动错误类型与脱敏断言未放宽。

## 文件清单

| 文件 | 变更 |
| --- | --- |
| src/gui/app.py | 新布局委托、缓存 tick、托盘降频、编辑列/关闭兼容；复用处理函数 |
| src/gui/workbench.py（新增） | 六页、筛选/分页/差异渲染、详情/告警/计时、尺寸适配 |
| src/gui/contracts.py | 加法 DTO、可选快照接口 |
| src/gui/resources.py | 有界事件交接及退出优先 |
| src/gui/main.py | 默认入口一次性后台历史加载；启动/重复运行提示使用产品名 |
| src/gui/tray.py | 产品名称；保留原托盘实现 |
| src/launcher/backend.py | 轻量观测、缓存/失效、历史展示上限、TP 默认关闭 |
| src/launcher/workbench_snapshot.py（新增） | 无 I/O/线程的阶段时间观测 |
| src/launcher/tp_composition.py | 既有 TP 状态的来源、独立身份及邮件字段 |
| scripts/windows_release_entry.py | 原空闲自检匹配新标题；未执行构建 |
| scripts/measure_workbench.py、verify_workbench_ui.py（新增） | 手动合成诊断及自身窗口截图 |
| tests/gui/test_workbench.py、tests/launcher/test_workbench_snapshot.py（新增） | 投影、队列、真 Tk、时间/线程/加载 |
| tests/gui/test_gui_contracts.py、test_rfq007_cooldown.py、test_order_mail.py | 本任务的文字/入口预期 |
| tests/launcher/test_tp_integration.py、test_release_infrastructure.py | TP 默认 false、构造测试桩 |
| tests/gui/test_startup.py | 明确启动指令在历史载入期间排队，载入后只执行一次 |
| tests/launcher/conftest.py（新增） | 组合测试使用假登录，隔离默认凭据查询 |
| tests/conftest.py、tests/workflow/test_v12_smtp_transport.py | 全测试进程 SMTP 阻断及其边界测试 |
| 本报告、tasks/2026-10-25-v15b-workbench.md | 设计、证据、Review 交接 |
| docs/evidence/v15b/ | 纯合成截图、检查与自身进程性能记录，无真实业务数据 |

## 限制与后续验收

- 24 小时合成稳定性：NOT_VERIFIED，后续验收条件，不能用短测推断。
- 三档 Windows 系统 DPI 切换：NOT_VERIFIED；控件缩放与实际像素窗口组合不能代替真实多显示器/DPI 验收。
- 生产浏览器/网络/登录、邮件、采购、报价现场链路：本阶段未授权实测，仅假实现回归。
  Chrome 消耗、GPU、磁盘吞吐及游戏帧率均未归因或测量。
- 工作台最多载入 1000 条，每页 200 条；更老记录通过原 Excel/结果目录查看。没有删历史数据。
  业务账本/恢复所需集合保留，不能承诺整个业务栈所有缓存都已变为有界。
- TP 历史逐源报价未完整持久化，明确显示不可用；默认关闭时不虚构活跃 TP cycle/历史明细。
  无可靠来源位置的旧 Excel 记录保留“来源未载入”，不凭型号关联。
- 时间线只覆盖本进程已观测阶段，不补造重启前历史；本轮模块耗时为已记录阶段之和。
- Mock 性能测试不执行生产 Backend，也不能证明 1000 条真实账本的后台投影生成成本。
  长时间采样版本早于最后的排序、两个详情字段、UNKNOWN 投影、启动提示和排队启动小修。
  不宣称最终源码完成同样 30 分钟实测：证据保留散列差异、窗口代码差异和最终源码短测。
  54 组合及 90 循环针对最后排队启动小修之前的界面；最终排队启动另由回归与短测覆盖。

完成后保持 REVIEW_REQUIRED，等待 CEO 源码和合成截图审核；不自行打包或发布。
