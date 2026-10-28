# V1.6 unified release and initial production verification

## 最新正式发布：四页常驻审核版本 / 2026-10-28

**已实际安装并恢复原业务，BUSINESS_RUNNING；非整体V1.6 PASS。**
CEO审核 `b473888ddd45d19db9de5fb929704f223964c523`；
应用 `c24d686096b1f6b5157ac1e443167be5662f6b54`；
src树 `81ab97bbbff5f220e70ae2ad73f8c5ff4e497f8f`。
本次未改应用源码，沿用已审核3054PASS/1SKIP，不重复开发/全量离线测试。

### 实际构建及数据保护

原唯一发布脚本 `build_windows_release.ps1 -Version 1.6 -BuildOnly`，既有发布Python；
候选自检及RELEASE_SCAN_OK通过，冻结七个关键模块与审核源码编译对象一致。
候选/安装EXE SHA256：
`C92F48E1380A90A747300CD7BDADFBD410C6A8D8352304C1B4D6DA438C7F28CE`。
2875个程序文件逐一匹配。安装目录仍
`D:/Program_Leo/INSO_Leo/dist/INSO_V1.6`，仅替换EXE/_internal。
Owner托盘正常退出旧PID86248；原退出收据10:32:12(+08)code0，
独占锁释放后安装，无强杀。新鲜程序回滚：
`D:/Program_Leo/INSO_Leo/dist/release-backups/INSO_V1.6-retained-20261028T023242Z/program`。
旧EXE `745BEC95F0426673C82ED4AB76EE38DCAB442F2922FAEF124D7B040F947F51CE`，
回滚自检/资产匹配通过。备份含指定配置、加密Vault及验证SQLite备份；
兼容性仅在副本验证，无模式/数据变化，生产未迁移。不得恢复旧业务账本。
安装/空闲自检前后全表一致、配置/Vault/runtime链接及V1.4/V1.5资产不变。
新GUI PID86788、观察器84332，10:34:13(+08)启动，gui_ready/Responding、
原跨版本单实例锁持有；启动未传--start-inquiry。
截图通道超时、控件文字不可用，不冒充完整UI/托盘自动验收。

### 真实只读四页验收及一次交叠失败

最初业务10:34:22已开始，检查10:35:06开始，执行者未在检查前再次核对实际
轮次日志，发生交叠。因此这次窗口不能作为隔离PASS：业务累计12次
GOOGLE_WEB_READ_ARTIFACT_LOST、2次耗尽；只读检查最终在google-open-sheet
出现原生Error/GOOGLE_WEB_READ_UNCLASSIFIED。未出现原三页数量拦截。
仅能说明时段交叠，不能断言所有下载故障根因已解决。Owner已安全停止保留GUI。
第一检查已结束，仅按精确身份关闭自己创建且已确认空闲的页，未清理历史/人工页。

确认停止后10:40:43—10:43:36(+08)，用同一审核Google服务、原9222，
不初始化Backend、账本或邮件，增加新业务轮次出现即停止检查的临时守卫。
**隔离实机只读PASS**：2个原页面保留不接管，加4个当前自有页，总数6；
跨轮次/多个CDP重新连接保持4个原生身份；仅关闭自有空闲SHAHAB后按需补开，
其他3个身份不变；原页面从未作为关闭目标。三个来源表在有效60秒内各仅下载1次，
报价输入两次查询下载2次；真实60秒到期后三来源各再下载1次；
有效缓存内强制2026鲜检仍独立下载。最终下载2026=3、SHAHAB=3、Brief=2、输入=2，
分别含误关补开/到期/强制鲜检，不能当作普通缓存一分钟频率违规。
本隔离轮错误0；结束仅退休本检查自有4页，生产后续建立自身页面池。
没有Google写入、采购/测试邮件、放宽认证/弹窗/归属/未知写入保护。
真实写入的鲜检和读回未制造业务验证；仍依据审核源码及既有自然业务取证。

Owner确认再次点击开始运行，10:48:54.698(+08)真实询价begin；
所有独立浏览器检查连接已结束，后续仅读日志/账本摘要和原生进程计数。
报价10:50:59.234开始、10:58:56.086完成，476.860秒；
询价开始到嵌套报价124.536秒，未缩短原120秒安全间隔。报价31条无近期价、
1条价格未变、1条来源身份未确认，未将周期completed说成成功发出报价。
询价2条SOURCE_CHANGED安全拦截，无新采购SAVED。初次11:06:06取证尚未见收口；**后续已实证**：询价11:07:04.251完成
（1089.547秒）；TP11:07:04.326开始、11:07:16.173完成（11.844秒）。
TP首次开始距离本次恢复1089.628秒，串行资源等待仍存在，不能判定准时。
不将历史四TP/六SENT或只读Brief验证冒充新TP业务成功。
恢复后11:06:22出现1次google-download-read/TimeoutError，
GOOGLE_WEB_READ_UNAVAILABLE；按原重试恢复，随后询价/TP均completed，
没有恢复后的重试耗尽或新故障通知，不能写成恢复后绝无Google错误。
仍无新增采购SAVED、
实际发送报价或新TP邮件的外部成功凭据，未制造测试业务。

### 历史状态与资源

安装基线146SENT/116不可变命令/4TP及6TP-SENT。最初自然业务运行后149SENT：
1条原PENDING已由原队列发送，2条新运行故障通知SENT；原146SENT全行不变，
原116命令及4TP全行不变，无清空、重置或重发；SMTP接受不等于最终投递。
采购SAVED仍23，无新采购/报价成功凭据。只读隔离验证期间这些摘要不变。

资源短测：初次业务+检查交叠60.70s，GUI0.29280%整机CPU，
RSS121.90MiB/private91.54MiB/1468句柄/12线程；不能写为空闲。
Chrome同期稳定15进程CPU1.52194%整机、RSS2966.47MiB/private2665.60MiB/
11319句柄，另有2新进程，CPU只计两端存活者，不是完整Chrome峰值或长期结论。
确认停止后的133.72s，GUI0.00292%整机、RSS124.36MiB/private95.14MiB/
1704句柄/6线程，观察器0%/20.78MiB/128句柄。历史CPU异常根因仍UNKNOWN。

验收后正常业务60.51秒短测：GUI0.31473%整机CPU、RSS125.90MiB/
private95.22MiB/1220句柄/10线程；Chrome稳定14进程0.95548%整机、
RSS2473.76MiB/private2223.54MiB/10380句柄，另有1新进程；
CPU仅存活进程口径，非完整峰值/长期稳定。GUI句柄观察高点5841、随后回落1663，11:06:06为1982；
最终RSS143.90MiB/private113.07MiB/9线程、Responding。
11:10:42三轮收口后进一步回落626句柄、9线程，RSS143.27MiB/private112.44MiB。
这是若干快照而非绝对峰值；有释放不等于长期无泄漏。

生产路径仍原浏览器Owner串行Google/INSO + 三模块独立900秒截止时间，
market_actor_factory=None，**没有启用可选双市场Actor/真实网页并行**。
长期稳定、TP实际准时、100%/150%DPI与游戏影响不因本次发布自动通过。

自有268022721字节冻结暂存及兼容副本已在路径/重解析点/活动检查后退休；
保留安装、可用回滚、受保护数据备份及必要小型故障证据，不碰Chrome/Profile、
未知页、原长测或其他工作树。报告只交Owner转CEO。

最终交付状态 **BUSINESS_RUNNING / V16_REVIEW_REQUIRED**。
构建、备份、只替换程序、空闲启动、四页只读实机与业务恢复均有实际证据；
三个自然轮次均有真实开始/完成记录；**周期完成不是发单发信成功**。
无新合格目标就不制造业务；下一次900秒实际准时、真正并行及长期稳定仍未验证。
不以Mock、旧TP收据、独立定时器或配置true代替生产成功。
无需再次点击开始、重跑历史订单或发送测试邮件；程序保持原业务运行。


## 最新隔离整改：四个 Google 子表常驻复用（2026-10-28）

状态：**源码已实现，REVIEW_REQUIRED；未安装、未连接生产浏览器。**
本节是 Owner 最新需求的离线整改，不覆盖下方真实安装版本及健康未通过记录。
应用源码 `c24d686096b1f6b5157ac1e443167be5662f6b54`，
src树 `81ab97bbbff5f220e70ae2ad73f8c5ff4e497f8f`。

- 2026、SHAHAB、RFQ_BRIEF、报价输入按需各保留一个自有页面，跨轮次复用，
  不做半小时刷新。原3页数量拒绝已移除，原认证、页面归属、未完成操作保护保留。
- 嵌套模块复用原页面池；跨连接只保留浏览器原生页面编号和安全状态，
  不共享旧连接的页面对象，不接管人工或上个进程的未知页面。
- 普通空闲页误关后，下次实际需要时补开对应子表；未确认写入/脚本页关闭时
  继续阻断，不补页重发或重写。普通读取一分钟内用内存，不为补页重复下载。
- 四子表沿用原全局安全锁及原业务Owner串行操作。来源三个表的普通缓存仍60秒；
  报价输入、采购/报价/TP前鲜检和写后读回仍实时，不让缓存充当业务授权。
- INSO未改：不存在需要删除的全局1页计数，原会话唯一身份检查保留。
  没有新增浏览器、后台定时器、依赖、调度器或通知发送框架；双Actor上限不变。

### 复用与改动范围

`src/launcher/google_quote_update.py` 扩展已有作用域页面池为可保留原生编号，
沿用原归属/认证/清理；移除数字3拒绝，专用RFQ_BRIEF获得独立槽位。
`src/launcher/google_web.py` 原生产组装启用保留模式，嵌套作用域复用原连接，
离开后不保留Playwright对象。原TTL及写入校验算法未改。
两个原Google测试文件补充常驻/误关/保护/队列回归；
`tests/research/background_targets.py` 合成目标从固定同一编号改为每页唯一编号，
以真正检测目标串认。`docs/modules/SHEETS.md`及原任务同步最新契约。

### 测试与限制

安装源码上的两条新增负例曾明确复现3页保护拒绝；整改后的328项首轮专项通过。
最新常驻设计专项 **371 PASS，17.49秒**，Ruff通过。
最终测试提交 `8b18b47cee22be95517b160a23b51db82504623a`，src树不变。
首轮全量3053通过/1失败/1跳过（125.05秒）；唯一失败是旧测试明确要求禁止第四页，
与Owner最新需求冲突。已改为旧页不接管/新页复用断言，对应13项通过0.62秒；
最终完整离线回归 **3054 PASS / 1 SKIP，123.76秒**，src树复核不变。
唯一跳过是当前Windows无法创建符号链接（原测试第56行）；受改文件Ruff及diff检查通过。
未将离线通过当作生产实测。
涵盖四页跨轮次复用、同页嵌套复用、原锁串行、仅补被关闭空闲页、
60秒边界、Stop禁止补页、未知写入关闭禁止重试、身份/认证/未完成操作保护。
真实四页常驻、重新附着及误关补开仍 **NOT_VERIFIED**，未接触9222。
现有安装仍bb04d92；Owner安全停止后的程序、数据、配置、邮件队列、Chrome均未改。
Google告警策略未调整，不能宣称现有程序已消除告警；历史性能异常未归因，
TP准时、实际网页并行、长期稳定性也不因本次源码整改变为PASS。
本任务10个已结束合成测试目录在绝对路径及重解析点检查后已退休；
保留原必要故障证据、程序回滚、runtime、Profile及旧长测，不扩大清理。
仅交Owner转CEO独立复审，不自行安装或恢复业务，不自行向CEO发消息。


## 最新现场：Owner 授权 Windows 发布 / 2026-10-28（健康验收未通过）

**已安装并真实启动；V16_REVIEW_REQUIRED。生产健康不作 PASS。**
Owner 授权基线 `1507972e722b72341381a782c5fc18411c3ea74d`，
应用 `bb04d92f08a0ceca2075a2c17b153f2921803765`，
src 树 `d5f270aa8c392e9b374bfdef396d229af2d4e1e6`。
本轮不改应用源码、配置或通知策略，原离线3040/1SKIP仅归属该源码。

### 实际构建、替换与启动

- 原唯一 `build_windows_release.ps1 -Version 1.6 -BuildOnly`，
  复用 `.worktrees/v1-4-order-mail-inspection/.venv-release/Scripts/python.exe`，
  Tcl8.6.15 / PyInstaller6.16.0；冻结自检及 RELEASE_SCAN_OK 通过。
- 候选与安装 EXE SHA256：
  `745BEC95F0426673C82ED4AB76EE38DCAB442F2922FAEF124D7B040F947F51CE`。
  2875 个程序资产全部匹配；冻结的缓存、Backend、Reader、TP及可选接续模块
  代码逐一与已审核源码编译对象匹配。没有临时开启 Actor。
- 安装路径：`D:/Program_Leo/INSO_Leo/dist/INSO_V1.6/INSO_V1.6.exe`。
  2026-10-28 09:38:01(+08)完成替换；安装自检和空闲界面自检通过。
- 旧程序实际 PID85528 已在09:29:31(+08)正常退出 code0，现场无旧实例、锁空闲，
  非本轮强杀。新 GUI PID86248，观察器86684，09:38:36开始，标题明确 V1.6，
  原命名互斥锁被持有，窗口 Responding、诊断 gui_ready。Windows截图通道超时，
  自定义按钮无可识别文字，故本次不冒充完整菜单/托盘指针验收。
- Owner 确认点击“开始运行”；09:42:37询价 begin，09:44:43报价 begin，
  09:45:03报价 deferred/900s；09:45:03 TP begin，09:45:24 TP deferred/900s。
  这是真实配置业务恢复，不是 Mock、只读探针或仅 GUI 启动。
- 当前实际路径：`v16_enabled/v13_enabled/tp_enabled=true`、三个900s周期，
  原同步浏览器 Owner + 独立模块截止时间；主构造未注入 market_actor_factory，
  **双市场 Actor 未启用、真实网页并行未上线**，历史454.210s迟到问题仍 OPEN。

### 账本与回滚保护

回滚目录：`D:/Program_Leo/INSO_Leo/dist/release-backups/INSO_V1.6-cache-20261028T013533Z/program`。
原 EXE `696E732B3B697EBDAE6267118959D11C8C87BE4A2B76DAFD7F17C2EA7127189A`，
全部旧资产哈希核对、回滚程序自检通过。新鲜备份只复制指定配置、加密 Vault
及 SQLite 验证备份，不遍历 runtime/Profile。兼容性只在副本验证，原迁移返回无需升级，
副本与原库全部表摘要一致；**生产未执行迁移/还原/清理**。

安装独占原互斥锁，只替换 EXE/_internal；runtime junction 仍指向
`D:/Program_Leo/INSO_Leo/dist/INSO_V1.4/runtime`，配置/Vault哈希不变，
V1.4/V1.5程序资产不变。实际业务库由原配置指向 V1.2 runtime/production；不猜路径。
安装与空闲启动前后全表一致，原四TP/六TP-SENT、113条不可变命令及144条SENT保留。
历史17条 INTERRUPTED_UNSENT、2条STATUS_WRITE_PENDING仍为原持久化人工/状态保护，
没有重置、重购或伪造来源；未发现 UNKNOWN/SENDING/RESEARCHING 在途阻断。

恢复后只读核验：完整性ok，原命令/144条SENT/4TP全行不变；收件结果146 SENT，
新增2条PURCHASE_EXCEPTION类型的运行故障通知，非测试邮件，SMTP接受不等于投递。
采购结果SAVED仍23，无新采购成功凭据；来源变化拦截2次，未把它写成成功业务。
不恢复旧数据库，否则可能丢掉恢复后的新收据。需要回滚时只正常退出后恢复程序，
保留当前账本和所有新旧SENT/UNKNOWN；本次未执行程序回滚，因启动/自检正常，
现场问题属受原保护拦截的Google业务读取，不靠换回同样有该保护的旧程序消除现场。

### 现场阻断与实际性能

本次已直接取得固定脱敏分支 `google-busy-page-budget` 共10次，报价和TP各耗尽
原5次读取后延期。**只能证明操作页预算保护触发**，不能断定哪几个保留页、
为何累计至上限，不能声称全部Google不可访问或缓存已修复告警。
启动前只读连接原9222：1context/2pages，1个Google-owned页，原只读安全判定
无正在脚本/可见对话框/未保存，未新建或关闭页面；恢复后未与业务争用Chrome检查。
未清保护页、绕过页数上限、放宽重试或关通知。Owner已被告知需要安全停止保留现场。

资源实测（16逻辑CPU，主程序与观察器分开）：空闲43.41s主程序3.35449%host CPU、
98.8MiB RSS/71.97MiB Private/531句柄；观察器0%host/20.75MiB/128句柄。
正常Esc后72.98s含Owner恢复的混合区间1.68741%host；随后57.36s业务区间
1.56123%host、121.39MiB RSS/90.89MiB Private/1057句柄/12线程，仍Responding。
原生线程有界采样含用户态/内核态差分，但不足定位旧3.264%问题根因。
**资源异常/波动保持OPEN，不报长期稳定PASS，不用操作焦点/优先级改数字。**

当前最终可核实状态：**INSTALLED_IDLE / GOOGLE_HEALTH_HOLD /
RESOURCE_WARNING / V16_REVIEW_REQUIRED**。
Owner已确认安全停止，原询价轮次09:54:33.381(+08)记录stopped、总耗时716.204s。
停止后只读核验1context/2pages/1空闲Google-owned，原unsafe/read-failed/refresh-pending
均false，未新建或关闭页面。原144SENT/4TP完整；当前146SENT另有1条自然故障通知
PENDING，原队列未清理/未强制发送。停止前的阶段性待确认状态已由此收口凭据替代。
09:50:12主进程仍Responding，RSS123.93MiB、Private93.6MiB、1426句柄、10线程；
单次运行与短测不能证明长期稳定。后续现场状态变更需追加新凭据。

本轮自有BuildOnly stage和兼容性数据副本已在标记、绝对路径和无重解析点检查后退休，
stage回收268020692字节；保留新鲜程序/配置/加密Vault/账本备份，不删除旧回滚或共享数据。
本地小型脱敏诊断因健康HOLD/停止待确认而保留，无原始TSV或兼容数据库副本。
下一步最小范围：在停止确认后独立审查page-budget页面归属/生命周期与资源证据；
不得为“上线成功”删除保护、改源码或发测试通知。本报告由Owner转CEO，执行方不自行发送。

## 历史源码交付：Google 三子表共享 60 秒快照 / 2026-10-28

**GOOGLE_SHEET_TTL_CACHE_REVIEW_REQUIRED / V16_REVIEW_REQUIRED。**
已拉取核对正式审核 `161e5113f5c299739afc4f6443ed656b160a34f0`。
CEO 已接受 E4 周期一致性源码；本轮未重做 E4、认证集合、Stop 或 Actor 架构。
仅隔离源码/合成离线测试；不安装、不接触生产/Chrome/Google/Vault/生产 SQLite/SMTP。
Owner 转交 CEO，本执行者不直接发送。

### 实际变化与复用

复用唯一 GoogleSheetsWebService、原 GRID_LOCK、原下载/校验/清理、原 Reader、
TP 身份与邮件账本。内存 LRU 最多 6 项，按 `(spreadsheetId, exact title)` 隔离，
仅 `2026`、`SHAHAB`、`RFQ_BRIEF`；单个下载原 32MiB/100000 行上限保留。
无持久缓存、原始 TSV 留存、新线程、后台定时器、客户端、浏览器或依赖。
每子表成功完成原生完整获取/结构及 gid 校验后独立起算：年龄 `<60s` 命中，
`>=60s` 下次请求才刷新。现有 UI 锁合并并发获取，不睡眠等待 TTL。
返回复制数据，调用者无法修改存储的快照；不跨服务生命周期/Profile/分支混用。

| 普通缓存读取 | 必须实时核验，计数单列 |
| --- | --- |
| RowReader.read_discovery_rows → get_discovery | 原 get/read_rows，从不拿缓存代替 |
| BriefReader.read_discovery → read_brief_discovery | 原 read_brief/BriefReader.read；TP 动作前 `_revalidate` |
| 询价/报价发现、仪表盘、TP 自动发现 | 原采购/品牌/报价身份状态检查；TP 人工重跑选取 |
| 跨模块及跨轮询共用 60s | 原写前表头、写后真实 TSV 读回都保留 |

已成功的完整实时源读取可更新普通发现快照；这不减少该次实时 I/O。
任何本地写尝试在动作前失效对应子表；原成功读回仍为唯一写入证明，
不把乐观写值塞进缓存。发现来源变化仍由旧门禁拒绝，绝不写错行/重复发信。
已知 Busy/认证/结构/归属/Stop/取消/下载失败清空服务快照，无旧值兜底。
每次命中也检查原共享安全准入和立即停止。缓存命中不触发成功恢复回调，
原 Backend 用真实成功读取代次判断是否恢复 Google，不能靠缓存清除故障。
`报价输入` 不参与；普通读取合同不扩大原 A:G/Brief A:Q 白名单。

### 下载指标与精确测试归属

- 应用提交：`bb04d92f08a0ceca2075a2c17b153f2921803765`。
- `src/` 树：`d5f270aa8c392e9b374bfdef396d229af2d4e1e6`。
- 综合受影响专项：**463 PASS，20.77 秒**（最后追加两项 Brief schema 用例前）。
- 最终缓存专项：**36 PASS，1.19 秒**；Ruff / diff 检查通过。
- 最终冻结源码全量：**3040 PASS / 1 SKIP，123.99 秒**。
  唯一跳过 `tests/workflow/test_v12_evidence_and_safety.py:56`，本机测试环境不支持符号链接。
  全量期间 src 树保持不变；后续仅报告/任务/JSON 变更。10 个本轮自有测试目录在
  结束及绝对边界/重解析点核验后清理，无生产/长测目录清理。。
- 下载指标（合成原生 UI）：24 个查询候选、两个子表跨阶段普通发现合计 2 次下载
  （旧阶段快照需 4 次）；4 并发同子表 1 次；0/59.999 秒共 1 次，到60秒第2次。
- 源写入场景：普通预热1次 + 原写前/读回2次 + 写失效后普通获取1次；总4次。
  采购鲜检：普通发现1次 + 实时核验1次。不是全程序绝对60秒硬限流。

测试经过原 UI 下载/写入动作的合成页面、原 Reader/Backend/TP 接续及隔离账本。
覆盖三子表独立过期、文档隔离、有界淘汰、调用者修改隔离、跨轮次/模块复用、
并发合并、完成后 TTL 起算、写入成功/结果不明失效、原安全读回、保护故障、
过期失败不回退、缺失/超大文件、结构损坏、MPN/状态/品牌/数量/行/TP 变化、
人工 TP 鲜读、原来源事务和 SENT/UNKNOWN 防重复。没有真实业务成功或邮箱投递声明。

开发中初轮兼容专项曾有10项失败（197通过）：必须保留实时核验对发现快照的更新，
并避免以缓存命中清除故障；以原生成功读取代次补齐恢复语义。旧跨阶段次数4改2，
直接改测试表值改为走原单格写以核验失效；没有放宽原重试/邮件条数断言。
新增夹具曾有错误导入、未按原手工允许状态设置以及把同步 TP 状态规则错误套用
到完整来源接续的断言，均修正为原实现语义；未新增业务权限或修改保护集合。

变更清单：应用 `src/launcher/{google_web,backend}.py`、
`src/sheets/{google_reader,tp_brief}.py`、`src/workflow/tp_research.py`；
测试 `tests/launcher/{test_google_snapshot_cache,test_google_web}.py`；
契约 `docs/modules/SHEETS.md`。本次附原报告、统一任务和原 JSON 证据更新。

### 范围、未解决事项和下一步

缓存可能减少读取压力，但 **不能证明已解决当前生产 Google 不可用邮件**。
本轮未安装或取新生产证据，原故障精确保护分支仍 UNKNOWN；通知策略完全未改。
原生产版本仅依据历史发布记录，不作新实机运行状态核验。新功能默认未部署。
历史 TP 迟到454.210秒、真实网页重叠、长期稳定性、系统 DPI/游戏影响仍 OPEN。
源码及证据仅请 Owner 转 CEO 独立复审，不自行宣布整体 PASS 或申请停止生产。

## 历史整改：E4 原业务周期一致性 / 2026-10-28（CEO 已接受源码）

**REVIEW_REQUIRED，仅执行方离线验证；由 Owner 转交 CEO，不自行发送。**
本轮基于远端正式审核 `85b24f09f1a912345d78a640dbc666d0cc0d28d1`。
CEO 已关闭原生登录异常专项 SOURCE_PASS；保留既有 E 架构，只整改
`E4_OWNER_POLL_PARITY_CHANGES_REQUESTED`，不再重做前期认证或 Stop 修复。

### 最小源码变化与证据

仅 `src/launcher/business_continuations.py` 增加 7 行，恢复原 Backend 三个入口：
安全站点恢复检查 → 询价/报价轮次刷新仪表盘 → 询价轮次清空当轮统计。
调用位于原 Owner 的模块上下文及原页面/发现作用域内、认领订单前；
生成器每轮只进入一次，不在每 50 毫秒派发 tick 重读 Google。
没有新增统计器、恢复器、状态账本、线程、依赖或通知策略。

对应测试仅扩充 `tests/launcher/test_business_continuation_loop.py`：
实际 Backend 可选组合 + 原 Runtime + 原三模块端口 + 合成 SQLite/outbox，
保留原 13 种故障/业务用例，新增 3 种集成场景。两轮以上模拟验证：
原仪表盘三项从 `(1,1,1)` 更新到 `(0,0,0)`；旧轮询投影不累积；
统计调用次数等于询价/报价开始轮数，恢复检查次数等于模块开始轮数；
受保护操作关闭、原 Owner 线程执行；第二轮不重复采购、报价写回或 TP 入队。
人工 INSO 验证失败仍阻断；只有原认证探测成功才解除人工等待并恢复 V12，
并不冒充业务读取成功清除原故障计时。真实浏览器及生产业务未执行。

- 独立源码提交：`bfa835b7eda1c71ddf4f4d7f383f2f4d2b7a2234`。
- `src/` 树：`d5024ea81060ef4285d8bf7d7453a2a305f1b71d`。
- 受影响专项：**173 PASS，20.81 秒**；Ruff / diff 检查通过。
- 最终确切源码完整离线回归：**3004 PASS / 1 SKIP，128.29 秒**。
  唯一跳过：`tests/workflow/test_v12_evidence_and_safety.py:56`，测试环境不能创建符号链接。
  完整测试期间 `src/` 未改；后续仅报告/证据变更，源码树一致。
  4 个本轮自有合成测试目录在进程结束及绝对路径/无重解析点校验后清理。。
- 首次新增两轮测试的预期漏计原完成回调真实写入的任务标识，1 项断言失败；
  修正为比较原回调形成的整组投影，再验证下轮完整清空。不是应用故障掩盖，
  未删改旧 13 项安全场景。上轮 3001 的证据仅归属历史源码，不套用于本次。

### Owner 再次收到 Google 通知：尚未解决，不能宣称生产已修复

Owner 本轮报告数小时前再次收到不可用邮件。本轮未读生产日志/账本，
未连接 Chrome/Google，因此该组邮件的精确原因和是否属于误报仍 UNKNOWN。
按归档发布记录，正式版本仍为 `04075bc`；本轮未核对现场 EXE 哈希或进程，
不能把发布记录说成新的实机核验。此前 `0d77be23` 的五种脱敏 Busy 分支诊断
尚未安装；这次 E4 三入口恢复也未安装，不会改变当前程序的通知行为。

既有脱敏日志仅证明历史几组故障在 TSV 下载前被 Busy 保护拦截。
手动可打开表格不能证明自动读取具备安全页面/结算条件。现有通知按轮次去重，
多个失败轮次仍可能各发一次，不应直接称历史 SENT 重发或同一命令重复发送。
本轮不静默禁用通知、不移除保护、不清人工页面、不放宽重试。
后续最小建议（未实施）：在独立获准的生产诊断窗口安装已审查的脱敏诊断，
取得实际分支后修确切原因；再独立评审“读取暂缓/自动重试”措辞及连续同一故障
提醒去重，保留真实安全故障、结果 UNKNOWN 和人工处理通知。不能凭猜测压掉报警。

### 边界与未关闭事项

生产程序、配置、Vault、邮件状态与保护浏览器本轮完全未操作；仅使用独立
合成测试目录，未安装/启动真实并行。一个 Runtime、两 Actor 上限、来源行
全事务租约、原认证集合、120 秒等待、Stop 和 SENT/UNKNOWN 均未修改。
可选新组合仍默认 OFF，这不代表更改既有生产 TP 配置或正常业务授权。
实际页面重叠、TP 历史 454.210 秒迟到、长期稳定性、系统 DPI/游戏影响
仍 NOT_VERIFIED / OPEN，不因本次离线回归宣布整体 V1.6 PASS。

## 历史统一交付：直接登录异常整改 + 阶段 E 隔离接续集成（已由上方新审核修正）

**状态：REVIEW_REQUIRED。以下为执行方离线证据，尚无 CEO 对最终源码的独立 PASS。**

本次只做隔离源码开发和离线回归，未安装、未启用新组合、未停止或重启生产，
未访问生产数据库/config/Vault、9222、Google/六源网站，未采购或真实发信。
既有正常业务授权不变。本轮不重新核对生产实时状态，也不沿用旧 PID 作判断。

### 结果与边界

| 项目 | 结果 | 准确范围 |
| --- | --- | --- |
| `DIRECT_SITE_LOGIN_ERROR_CHANGES_REQUESTED` | PASS（离线，待复审） | 实际 `SiteLoginError.reason_code` 经原精确认证集合进入站点延期；无新增认证 token，无 Worker 登录 |
| E1 三模块业务接续 | PASS（离线，待复审） | 原询价认领/重复检查/采购路由、原报价受保护历史查询/写回、原 TP 调研/邮件队列已接到同一 Backend 可选组合 |
| E2 来源行全事务排他 | PASS（离线，待复审） | 同一来源 FIFO，租约覆盖查询、Owner FX、鲜检、外部动作判断、原持久化终态；读返回不释放整笔业务 |
| E3 认证恢复/大结果 | PASS（离线，待复审） | 原 Owner 登录巡检的精确成功回执恢复对应站点；人工页不清理；合法超限数据交 Owner 完整处理，不截价 |
| E4 调度/停止/GUI | PASS（离线，待复审） | 一个 Runtime，两个市场执行槽，最多三个模块事务；完整周期身份、原 120 秒等待、停止排空、UNKNOWN 保护及独立界面状态 |
| E5 最终全量 | PASS（离线） | **3001 PASS / 1 SKIP，120.81 秒**；跳过因本机无符号链接创建能力，未改变权限强行通过 |
| 实际网页重叠、实际 TP 准时性 | NOT_VERIFIED | 未获本轮真实浏览器测试授权；历史迟到 454.210 秒的验收问题仍 OPEN，合成时钟不能关闭它 |
| 长期资源、真实 DPI/游戏影响 | NOT_VERIFIED | 未运行新监控或长测；旧 9f 长测未操作、未查询，不作为本版本通过依据 |
| 新安装/生产并行 | DEFERRED | 本轮未授权；新 Actor 组合默认 OFF，须显式注入已有 Backend 进行隔离/审核测试 |
| Google 历史不可用通知精确分支 | UNKNOWN | 原诊断仍未安装；本轮未调查会话、未放宽重试或发测试故障邮件 |

**新 Actor 组合默认 OFF，不表示生产 TP 被关闭。** 生产 TP 配置本轮未读未改。
`MAIL_QUEUED` 仅表示原不可变邮件命令入队确认，不等于 SMTP 接受或邮箱投递。
报价跟进继续使用原 Owner 的 INSO 历史/Google 路径，没有另造六源报价规则。
普通 Research 1～6 个月、TP 1～12 个月、采购权限/金额、SENT/UNKNOWN、收件人规则保留。

### 完整 SHA 与测试归属

- 最新远端补充审核基线：`06ed60feb7ce9a56e83e3b251760ef8ba8cad037`。
- 独立直接登录最小修复：`68e1a2d2aa2b289c1fd38da33686851ff90bec7d`。
  对应源码树 `0de681c1f7590779f647a17841230b498ff35aef`；92 项专项通过，
  独立全量 **2961 PASS / 1 SKIP，113.55 秒**。证据提交 `2ea0b9826470f431f1fa8ab5f4269cddc7be98b5`。
- 最终应用源码：**`3547c4162d0b5c0308c84ae8a7feba23a39f6a70`**。
- 最终 `src/` 树：**`5ce508705c7e4099d41ae5c9456eaf19a80e427b`**。
- 最终专项 **87 PASS / 8.23 秒**；完整 **3001 PASS / 1 SKIP / 120.81 秒**，
  均归属上述最终应用源码。全部变更 Python 文件 Ruff、`git diff --check` 通过。
- 初次 E4 全量曾有 2 项失败（原等待回调兼容）；修源码恢复原接口，没有改弱原测试。
  回调后的共享安全复核、Google 写回待确认及入队前故障均已补回归。

| 独立增量 | 完整提交 SHA |
| --- | --- |
| E2 原来源全事务租约 | `c0ae6a4b087eaa1622177bceea61b3042ff6113b` |
| E1 同一 Research 的逐来源接续 | `6d82fcc6b4070d8e572e3f5a9e865daff9bcf2e9` |
| E1 原 TP 业务接续 | `85002563c39cfd60f17220840d58c6953d0c42b1` |
| E1 原询价与报价接续 | `1f32f8564574a1ee6f7e35924c84536995717b78` |
| E3 Owner 恢复与完整结果交接 | `5405275372dab707c73e14d0945d52bfa03d91cc` |
| E4 原 Backend 实际组合 | `b35e6061d4e0ec28f7f44945b7edd6a21d73ff31` |
| E5 兼容与安全复核修正 | `3547c4162d0b5c0308c84ae8a7feba23a39f6a70` |

### 文件与复用

17 个应用文件、8 个测试文件有变更，完整清单与机器可读统计见
[原证据文件](docs/evidence/v16/order-resource-regression.json) 的 `combined_stage_e_final`。

- `launcher`：原 Backend 组合、逐来源交接、原 Actor、原登录巡检、原有界观测；无新定时器/浏览器/发送器。
- `research`：同步入口与接续入口共用同一六源解析和完成逻辑；TP 一次 Owner 汇率快照。
- `workflow`：原 Runtime/订单资源、真实任务身份、原状态机/账本/邮件队列；无第二账本、无伪造 inquiry_id。
- `sheets.pending`：复用原 Schema 的来源快照；TP 复用当前批次映射，已完成 TP 不重复读原订单，动作前仍鲜检目标。
- 原采购、SMTP、状态存储迁移和六源采集器没有复制；没有新增依赖。

实际隔离测试经过原 Backend/Runtime/三个业务状态机、原 SQLite/outbox 和实际线程传输，
使用合成数据、假站点客户端及假发信器。13 种组合覆盖正常、Stop、初始化/终退失败、
在途归属故障、报价重试让出、TP 表头/来源变化、采购 UNKNOWN、120 秒安全间隔、
品牌回调清理故障、入队前共享故障、Google 状态写回待确认。
这些不能当作实际网站、真实采购、真实邮件或正式无人值守成功。

### 交接与剩余工作

已退休本轮 **37** 个结束的测试临时目录，逐个核对绝对边界且无重解析点；
保留小型脱敏 Git 证据，未清理生产、回滚、CDP、未知文件或旧长测。

请 Owner 将本报告和最终提交转交 CEO 独立复审；本执行方不直接向 CEO 发消息。
复审后才另行安排明确的安全浏览器窗口，验证真实解析结果重叠、同订单排队、
TP 实际到期延迟和真实界面状态。真实启用、安装、长期运行仍需对应授权及验收。
**不自行宣布整体 V1.6 PASS、BUILD_READY 或解除任何发布门禁。**

## Historical execution status — Actor remediation (superseded by combined delivery above)

Overall REVIEW_REQUIRED. Production04075bc is unchanged by this task; Owner's
previous开始运行 confirmation and17:01–17:04 module logs supersede old temporary
safe-stop/pending-resume statements below. No current real process state is
inferred from an old PID. No production EXE/config/Vault/SQLite/SMTP/browser
operation or installation was performed by this continuation.

| Stage / issue | Result and exact scope |
| --- | --- |
| A terminal lifecycle | PASS; source4a669daea75ad4ba8227787de1dc1c8e265e9abe; CEO393a892 accepts |
| B Stop + actual module FIFO | PASS scoped;42a881231da1221343aa1766ca732a0c5fe96d5d then583f1c07412671670d9d9522de493d296f51c03a; CEO8fb3f50 accepts |
| C immutable typed ports | PASS scoped;c71ac4f9c22edd9587f710d086f23db95b576efa; CEO8fb3f50 accepts |
| D optional read-actor foundation | PARTIAL;18320d6bfd288369c9bb75211359465310b5bb26, not enabled; scoped foundation accepted |
| D submit/final exit race | Fixed287e23830dfd4aa226b3162464084ae1e969a4c7; final owner terminal still required; REVIEW_REQUIRED |
| D manual/auth classification | Fixedf7d70baa51f942f27064ee9f84684549f1795d7b using canonical exact reason sets; REVIEW_REQUIRED |
| E full business continuation/owner auth/GUI binding | NOT_IMPLEMENTED; ports are prerequisites only |
| F real business-page overlap / TP due-to-start | NOT_VERIFIED; prior454.210s lateness remains FAIL/open |
| Google busy diagnostics | Source-onlyPASS0d77be23fe1bd1c56b9478f9059be453b93c6ef0; live precise branch UNKNOWN |
| Deployment/current production replacement | NOT_AUTHORIZED this round / not performed |
| V1.6 long run,100/150%DPI, Chrome game impact | NOT_VERIFIED; old9f soak cannot substitute |

Final application source **f7d70baa51f942f27064ee9f84684549f1795d7b**;
Git src tree **18bde855d3323b1a3aa1585ff0e983cdc28cea6a**.
Exact final full **2951PASS /1SKIP /114.03s**, scoped Ruff --no-cache and diffPASS.
Auth/retry/site login focused304PASS1.30s; actor Stop/submit32PASS0.29s;
Google transport122PASS1.99s. Tests use synthetic data/HTML and real local Python
threads/queues only, with no network/business/SMTP. This is NOT actual website
concurrency or repaired live TP scheduling proof. Previous failed commands/test
fixture corrections remain historical and are not counted as successful runs.
15existing completed task-owned test directories retired by checked explicit
absolute names, no reparse traversal/ACL change; small stdout/summary evidence
retained. No persistent monitor or worker left by tests.

Changed production-source files grouped by purpose: workflow/service.py owns
lease lifecycle/fairness/read handoff; workflow/market_messages.py and
research/market_contracts.py own immutable ports; launcher/market_actors.py owns
optional bounded thread transport; launcher/backend.py adds explicit fault port
and reuses unchanged old auth-stop set; research/runtime.py creates thread-local
read session; research/service.py and tp.py expose existing source acquisition;
research/cdp_pages.py and five market source finally blocks verify own cleanup;
research/icnet.py shares its existing90s constant; research/site_login.py exports
existing safety semantics; launcher/google_quote_update.py only logs fixed busy
branches. Corresponding workflow/launcher/research tests and existing report/
task/design/evidence updated. No price algorithm/month window/SMTP/production DB
schema/120s wait or procurement permission change, no new dependencies.

Recommended next work: keep current reviewed production installed. Integrate
owner-side business continuations with one lease held across read, FX/projection,
fresh source/durable validation and external effects; bind actor global faults
before consuming success and bridge original owner's auth recovery/GUI events.
Do not enable this single-query optional bridge as if it protects a whole order.
Then request a separate authorized safe real-browser window for parsed-source
and due-TP timelines, without using normal production as an experiment.

## Historical execution records (latest status above takes precedence)

## Current source safety continuation after CEO59f0628 —2026-10-27

**REVIEW_REQUIRED. Installed04075bc unchanged. New source20fda49c4573a0c59917d8ddf009655d220a41a2 NOT_DEPLOYED.**
Reused existing factory/facade/composition, backend source-query and module gates,
WorkflowRuntime.abort_module_resource and canonical teardown. No new dependency,
Chrome/Profile, daemon, scheduler, SMTP framework or business ledger.

New explicit native_page_owner proves original native target after navigation
without document JavaScript. Legacy page_owner unchanged, so Google/INSO marker
loss still quarantines writes. Intermediate full caught an unsafe compatibility
regression; corrected by separate explicit read-only API, not weakening old test.
Unknown createTarget outcomes (including Chrome-created/no-response-ID) latch
uncertainty without guessed close. Injected thread-safe admission spans shared,
fallback and reattached clients. Cannot rebind/reset to bypass fault; both guards
invalidated on conflicting bind. No Playwright objects/exception instances shared
through this guard. Source before/finally and module terminal checks defeat
translated unavailable/success returns; global runtime fault attribution avoids
blaming historic order. Unknown-resource teardown detaches only, never legacy
park/sweep; guards also fence direct park calls. All source changes uninstalled.
Guard scope is one runtime and all bound clients, not a cross-process orphan
reconciliation service or permission to enable unbound future actors.

Final full **2840PASS/1SKIP113.03s**, final targeted309PASS13.04s, Ruff/diffPASS.
Native Owner-authorized safe-stop window: same9222, max2own background tabs,
independent thread-local clients; HQEW/ICnet actual navigationoverlap0.109s/0.219s.
EachHTTP200; exacttarget+owner verified beforeANDafter navigation; own exacttarget
close confirmed, initial1humanpage preserved/final1page, no extraChrome/Profile.
No source price parsing, login/credential retrieval/Google/INSO/write/purchase/
testSMTP. Probe precedes only final rebind/terminal/teardown/attribution hardening;
native proof function unchanged, final-source offline result separate. Evidence
page-admission-native-owner.json retains actual probe sourcehash, no false exact
final-source live proof or installed-code claim.

Owner corrected actual control label to开始运行 and confirmed initial restore;
new true cycles15:59:46inquiry/16:02:35quotation/16:03:20TP; TPfinished16:03:37,
inquiry16:12:24. Later quotation deferredGOOGLEbusy again; current141SENT, historic
139SENT/108commands/4TP intact, noPENDING/SENDING/UNKNOWN. Two postinstall runtime
fault notices; no new TPmail/purchase/write success claimed. Not suppressed.
Owner subsequently authorized/confirmed this NEW safe-stop browser window. All
own tabs closed; Windows screenshot stillFrameArrivedtimeout/unlabelled controls.
Owner confirmed clicking开始运行; subsequent real logs verify inquiry17:01:44,
quotation17:04:01 and TP17:04:34 starts; TP completed17:04:51 (+08).
Quotation deferred after32.594s on Google read busy; no permanent outage claim.
141SENT above is the preceding snapshot, not a claim about all later activity.
No force-kill, restart or guessed click. Current reviewed EXE stays installed.

Unified task checklist updated; native-identity prerequisite now positive-live
PASS and shared guard source regressionPASS, pending independentReview. **Actual
module actors, same-source order leases, siteauth pacing, fair dispatch and TP
454.210s delay remain open.** Do not announce completeV1.6 or deploy newsource.
Long-term memory/game/DPI/business success/readback gaps also remain open.


## Prior installed-state observation —2026-10-27 15:40 +08 (superseded above)

**REVIEW_REQUIRED / REVIEWED_FIX_INSTALLED / PAGE_PARALLELISM_NOT_READY.**
Owner separately authorized stop/backup/reviewed install/restore, then confirmed
normal tray exit. Old99dd main74176/observer84608 exited normally at06:47:18Z,
exitcode0. Reviewed04075bc application (build checkout1b19390298c6151e08d1e513a2a153ddcae2c1cf)
installed06:53:09Z at`D:/Program_Leo/INSO_Leo/dist/INSO_V1.6/INSO_V1.6.exe`.
EXE SHA256 **696E732B3B697EBDAE6267118959D11C8C87BE4A2B76DAFD7F17C2EA7127189A**.
2875 assets match;43 locked packages and Tcl8.6.15 checked; canonical build48.718s,
frozen dependency/self-check/release scan and installed idle-self-check PASS.
Installed frozen code independently confirms nested context/cycle receipts present
and later page-factory changes absent. Not a deployment of67be3f7.

Fresh rollback:`D:/Program_Leo/INSO_Leo/dist/release-backups/INSO_V1.6-reviewed-20261027T065133Z/program`;
verified canonical SQLite backup and protected opaque config/vault/OAuth copies
alongside. Full-table/schema/recipient/immutable-command comparisons PASS before
and after install; canonical migration on COPY unchanged. No production migration
was needed by installer; normal application still uses existing idempotent init.
Runtime junction still V1.4 runtime, config/vault/V1.4/V1.5 assets unchanged.
Rollback restores program only against compatible CURRENT ledger, never old DB.
TP and quotation explicitly true under Owner authority. Original4TP/6TP-SENT
preserved. Private manifests/backups retained locally, not uploaded.

### Actual production receipts (not Mock)

Main85528/observer85924 started06:54:03Z; genuine three-module business began
14:54:06+08. Inquiry2 completed, quotation1 deferred then1 completed, TP2 completed.
Parent inquiry cycle b8c312... kept the same ID after nested quotation3f0797...
and TPe5c289... returned, corroborating installed context restoration. Offline
STOP/pause/shared-fault edge coverage remains distinct from this happy-path proof.

FirstTP completed14:57:05.219, planned next15:12:05.219; actual second begin
15:19:39.429, completed15:19:52.104. Completion-to-start1354.210s, **454.210s late**
while quotation held the single browser actor. Independent begin/end receipts and
900s scheduling policy verified; timely independent execution **FAIL/open**.
No old4TP/6SENT reused as new TP success. Inquiry next start900.010s after finish;
quotation deferred-to-next-start900.020s. Still no genuine concurrent module actors.

Actual result counts are log OCCURRENCES, not unique orders: SOURCE_CHANGED4,
SOURCE_IDENTITY_UNRESOLVED1, NO_RECENT_QUOTE31, PRICE_UNCHANGED1. No new verified
purchase or Google write/readback success; SAVED23 unchanged. No statuses reset,
source protections relaxed, or forced write to obtain a PASS. Correctness of
current conflicting source rows was not independently verified by this experiment.

Coherent read-only ledger check: integrityOK,108 old commands immutable,139 old
SENT full rows and4TP full rows unchanged; current140SENT, no PENDING/SENDING/UNKNOWN.
Only new receipt is1PURCHASE_EXCEPTION:SENT Google runtime fault notification.
Transport SENT means SMTP acceptance, not final delivery. Restart preserved old
SENT; no live UNKNOWN case existed to exercise. Google alert at09:57:23 belonged
to old run;14:56:49 belonged to new reviewed run, distinct commands/attempt1.
New quotation exhausted5GOOGLE_WEB_READ_BUSY checks then deferred; TP subsequently
completed and later quotation recovered. Exact busy DOM condition UNKNOWN.
Notification dedup is perCYCLE, not perrun; repeated persistent faults may notify
again nextcycle. Suggested wording refinement: distinguish busy/read-retry from
entire Spreadsheet unavailable. No policy/notification hotpatch or test SMTP.

### Read-only native Chrome prerequisite window (Owner explicitly authorized)

Owner confirmed all modules safely stopped, GUI retained. No in-flight receipt
at entry. Existing9222 Chrome reused, no launch/profile/context clone; max2 own
background tabs, two independent sync clients each confined to its own thread.
Canonical uninstalled page factory used unchanged. Two same authorized test-MPN
HQEW navigations overlapped0.125s (first) /0.532s (second, waiting for load).
Both returnedHTTP200 at expectedhost; exact blank/native target identity/initial
owner confirmed. Navigation then encountered context transition(first) or load
timeout(second); **post-navigation ownership NOT_VERIFIED**, not a PASS.
First error only class captured, so context-transition cause is inference rather
than a captured authoritative error message. No raw DOM/account/screenshot saved.
Both runs closed only their own2targets; initial1page retained and final1page,
all own targets absent. No Google/INSO operation, credential retrieval/login-form submission, purchase,
write or testmail; existing browser cookies/session were reused. This proves native dual-client creation/navigation overlap only;
not price parsing, per-order exclusion, module actors or full parallel acceptance.
Bounded actor integration, shared fault admission, site auth/pacing and same-order
queue remain NOT_IMPLEMENTED. Do not install this source prerequisite as fullparallel.
GUI capture FrameArrived timeout; accessible Tk controls unlabelled, no guessed
click. Owner asked to use existing Start control to restore original business;
resume confirmation pending at report timestamp (update on actual evidence).
A final bounded IC.net pair also returnedHTTP200 and overlapped0.204s. Its
postnavigationowner evaluation explicitly reported execution-context-destroyed;
actual marker survival remainsUNKNOWN. Native identity/blankowner/cleanup PASS,
original1page retained. No challenge/login bypass or forced navigation retry.
Both sites require further navigation/ownership investigation before enabling
business actors; not proof that window.name was lost, and not parsing acceptance.

### Finite resource result (distinct main/observer; not24h)

31samples/1800.063s, maxgap60.078s, exact mainPID85528 creation verified.
Average hostCPU **0.28961%** on16logical CPUs; RSS114.96→137.50MiB,
Private86.67→107.32MiB, peaks137.70/108.51MiB. Handles1045→peak5646→minimum1004→1138;
GDI136–138, USER258, native threads9–13. Handles released substantially; allocation
objects/semaphore ownership not measured this window. Memory has not demonstrated
a stable upper bound: no no-leak/long-term PASS. Observer128handles, ~20.85MiB,
CPU below counter resolution. Finite sampler84696 ended with collector exitcode0; no resident monitor.
Probe prior sample CPU1.89s over1741s,14.44MiB/1thread170handles; not subtracted.
Other offline checks ran on host, not isolated benchmark. NoChromeGPU/gameFPS or
foreground-vs-tray attribution. Existing old9f soak evidence cannot certify V1.6.

Evidence:`docs/evidence/v16/reviewed-*`; no customer data/raw mail/credentials/DB.
Canonical checklist in task updated. Previously written NOT_DEPLOYED/wait-exit
entries below are historical SUPERSEDED, not current blockers. No new installation
or source policy change from this native experiment. FullV1.6 remains incomplete;
new-source browser prerequisite failure and actor integration require work/review.


## Historical CEO remediation delivery —2026-10-27 (superseded by current section above)

**REVIEW_REQUIRED / SOURCE_FIXES_NOT_DEPLOYED. Not all V1.6 requirements complete.**
Remote review71a68f28d90ef96656cb78291c075361cb8112e2 was fetched and inspected,
not assumed present. Existing clean development checkout reused on independent
`codex/v1-6-audit-fixes`; review target remains`codex/v1-6-independent-scheduling`.
Running frozen99dd22c program was never stopped/restarted/replaced. No production
DB/config/browser session or original24h tree access in this round. Only existing
sanitized logs/prior exports and finite native process counters were read.

| Stage | Independent commit | Result |
| --- | --- | --- |
| A context/timing primary repair |a2bc2f01acbde576caf378d625788cd3e31d0d24|PASS offline, requires review; pushed before later work |
| B future cycle receipts and existing-log audit |b6187b5ffa8b279c0fc82c57e1e478a9472e2148|Source PASS offline; real TP900s and current SMTP receipt state NOT_VERIFIED |
| C page concurrency safety design |74f93dd6156d1c1a2fdb6a5d751c80382f7f089f|Design delivered; implementation DEFERRED, actual overlap NOT_VERIFIED |
| A explicit cancellation/cleanup unwind follow-up |6f8dd048248eae8875fba7a036327242b0e92027|PASS offline |
| A failure-cache isolation including identical wall time |04075bc884c9c2927e677edcbddcb43419833aef|PASS offline; final changed application source |
| D resource evidence/checklist and this report |Evidence-only delivery HEAD, full SHA in final handoff|Finite observations PASS; long-term stability NOT_VERIFIED |

### Changes and tests

Backend restores nested cycle/last-poll/research-failure-cache/pending-pause
metadata on every unwind. It never rolls back business/session changes. Each
execution starts with an empty failure cache rather than relying on distinct
wall-clock timestamps; parent cache is restored when nested work exits. Existing
outer pause wins over subsequent local pause. Observer retains ancestor waiting
stages, restores outer focus, and stores each module's own start/end/elapsed in
additive GUI DTO fields, rendered on existing cards. Unsafe cleanup invalidates
the actor; typed shared fault retains original cause; cancellation propagates
through CombinedCycle. No next purchase after STOP/shared failure and no shortened
120s safety wait. Resource ownership and fresh business permissions stay strict.

Changed application files: launcher/backend.py and workbench_snapshot.py;
workflow/service.py and v13_integration.py; gui/contracts.py, workbench.py, main.py.
Tests: launcher/test_v16_nested_context.py and test_v16_cycle_receipts.py.
No business pricing/window/transaction rule, schema, outbox semantics, dependency,
browser launcher or alternate ledger added. Task packet contains single unified
PASS/FAIL/NOT_VERIFIED/DEFERRED checklist; existing reports are historical below.

Frozen99dd22c method negative control: two new real-closure tests fail on incorrect
outer cycle identity, as expected. Repaired real launcher closure -> CombinedCycle
-> durable V12 flow / V13 engines / TpCycle covers32 cases including raw/typed
timeouts, pause, STOP, cancellation, shared DB fault, cleanup failure and pending
outer pause. Only external ports are synthetic; no real mail/site/DB operations.
115 unwind-targeted PASS14.27s; final frozen-wall cache cases32PASS9.55s and
final application source full2802PASS/1SKIP113.81s; Ruff/diff PASS. Additional
existing isolated Tk card assertions1PASS3.29s (no application-source delta)
verify waiting inquiry120s and borrowed quotation10s display independently.
No repeated broad visual simulation was added. One earlier full attempt at the
same application source had2801PASS/1FAIL/1SKIP due to existing Mock Tk initialization
`invalid command name tcl_findLibrary`; isolated existing module2PASS1.59s and the
one fresh full confirmation passed. The intermittent Tcl/global-test-state cause
is UNKNOWN, not called repaired. Skip is existing unavailable symlink capability;
isolated safety module8PASS/1SKIP0.48s confirms it, no permission rule bypassed.

### Real evidence remains qualified

Existing sanitized logs as of11:23:59 contain purchase5/quotation4 distinct cycle
tags:8SOURCE_CHANGED,104NO_RECENT_QUOTE,3PRICE_UNCHANGED,4unresolved identities.
Because the running code has the reviewed nested-context defect, these are
**log tag counts, not proof of independent correctly attributed module cycles**.
No newly confirmed procurement or quote Sheet-write/readback success was found.
No identity/state was changed to force success. Current production TP900s run
begin/end receipts are absent: NOT_VERIFIED, not inferred from four historical TP.

Future-source logging now records every module begin/terminal phase, cycle,
monotonic elapsed and next-delay on the existing bounded rotating log, including
empty TP. Strict allowlists suppress raw bodies/identifiers/nonfinite values.
Three real empty TpCycle engine invocations900s apart PASS offline; no historical
SENT used as proof. `completed` means cycle ended, not successful external orders.
This instrumentation is not in the running EXE and cannot backfill its history.

Prior exported SMTP evidence as of10:25:26:139SENT, historical138 unchanged then;
one new PURCHASE_EXCEPTION recipient accepted by transport. Current SMTP/UNKNOWN
state was not reread from productionDB, mailbox final delivery not established,
and real restart idempotency DEFERRED because restart is prohibited this round.
Existing offline SENT/UNKNOWN/atomic claims remain covered by full regression.

True webpage parallelism is not implemented. Separate design
`docs/V16_PAGE_CONCURRENCY_DESIGN.md` identifies exact-target page-event correlation,
same-URL reuse, sync-object thread affinity, shared auth/pacing, per-order exclusion
and callback/context gaps. Preferred bounded independent sync-client actors share
one protected Chrome; INSO/Google/writes remain exclusive. Broad async migration
cost is higher. No locks removed, profile duplicated or fake overlap timeline
submitted. Actual browser validation cannot commandeer live session under this
round's explicit prohibition; C remains open.

### Finite resource evidence, not a stability certificate

Read-only GetProcessTimes/memory/handle/process-tree observations only. Main window
11:29:31–11:35:31:360.36s,7samples/60s; application CPU0.20361–0.24420%host,
RSS138.45–141.42MiB,Private108.61–111.36MiB,9native threads. Handles5586→5700→
5708→5736→1111→1133→1121. A type snapshot confirms owning applicationPID74176
5770→1131handles and5196→576semaphores (4620released). This repeats earlier transient
release evidence; exact allocating Python/library/native objects remain UNKNOWN.
No speculative code fix or forced collection was introduced.

Observer:0%observedCPU/~20.75MiB RSS/1thread/128handles. Playwright driver observed
in5samples, then absent; surviving-cohort CPU0–0.06024%host. Missing/exited cohorts
do not mean zero total cost. First inventory matched inherited9222 flags on child
commands, so Chrome root attribution there was ambiguous and not used. A separate
60.375s/3sample ancestry-resolved window proves one canonical browser root and
separate browser/GPU/renderer/utility/crashpad process groups; all reported0CPU in
those two short comparable intervals. This is not active Research/game evidence.
Process-role memory counters are included in JSON; RSS sums can double-count
shared physical pages. No raw process command lines, page/customer data saved.
Offline regression ran on the same host during part of collection; this is not
an isolated idle benchmark. GPU utilization, frame rates, per-site attribution,
strict continuous multi-cycle bounds and unattended V1.6 stability NOT_VERIFIED.

New EXE real menu/tray/normal exit, real stop/restart recovery,100%/150%systemDPI,
and GUI/live-ledger consistency remain DEFERRED/NOT_VERIFIED per checklist.
Original9f/70956 result is deliberately not collected by this task and cannot
certify V1.6. Existing V1.5/V1.4 rollback assets/compatible-ledger strategy retained;
not re-certified against a newly installed program because no program installed.

### Proposed later deployment (not executed; separate Owner permission required)

1. CEO review P1 and observability commits, with C explicitly deferred. They are
   source fixes, not permission to overwrite running production.
2. Obtain a normal stop/install window; drain current effects, verify UNKNOWN,
   take fresh verified current ledger/config/vault backup and exclusive mutex.
3. Build only reviewed source using the single existing Windows flow; frozen
   selfcheck/scan/assets PASS. Preserve working V1.6 and V1.5/V1.4 rollback assets.
4. Asset-only install; no assumed schema migration or order-state reset. Verify
   current ledger/SENT/immutable commands before/after. Start idle first.
5. Resume existing authorized configured business without new per-order approvals.
   Verify real module-cycle receipts, empty TP and actual900s deadlines; confirm
   GUI/ledger and external results only when naturally eligible orders occur.
6. Test live tray/ordered exit/restart in the approved window; run finite multi-cycle
   resource and long-term checks on reviewed source. Never relabel old9f soak.
7. Rollback if necessary uses current compatible ledger, never restores old
   pre-effect DB. Do not resend historical SENT or reset UNKNOWN to manufacture PASS.

Recommendation: a reviewed replacement is needed to deliver P1 fixes/receipts,
but **do not install in this task**. No unconditional V1.6 completion or webpage-
parallel/long-term production PASS is claimed. Evidence `docs/evidence/v16/audit-*`.

---
## Historical initial release snapshot (unchanged facts at original timestamp)

Status: **PRODUCTION_INSTALLED_RUNNING / REVIEW_REQUIRED**.
As of 2026-10-27 10:27 Asia/Shanghai. This is not a claim that all three
external write chains or long-term unattended operation have passed.

## Version and installation

- Owner baseline: `669fe6ada3a450eaef5f74532a371d6fb55ffd01`.
- Built application source: `99dd22c43fd83852dc1d45d13c4cfed46b0ebe0d`.
- Branch: `codex/v1-6-independent-scheduling`.
- Installed: `D:/Program_Leo/INSO_Leo/dist/INSO_V1.6/INSO_V1.6.exe`.
- EXE SHA256: `16E38F30E253041F7ED41E0447DEF744F6912D7B310F6DBDF616556CDBDC8B82`.
- Canonical Windows script/spec reused; dependency selfcheck, release scan,
  installed selfcheck and idle GUI selfcheck PASS. All2875 assets matched.
- Real versioned Windows window enumerated. PID74176, existing exit observer84608;
  started09:54:40 with `--start-inquiry`. No concurrent V1.4/V1.5 business instance.
- Inquiry/quotation/TP enabled; independent configured periods900/900/900s.
  Default values retained independently, not a combined15-minute wait.

## Reuse, implementation and changes

Task packet contains reuse matrix and design. Existing WorkflowRuntime gains
three in-memory monotonic deadlines and fixed browser actor ownership. Same
poller/worker threads, mutex, SQLite business ledgers, adapter composition,
quote/inquiry/TP contracts and notification outbox remain canonical. Shared
browser work queues on one owner thread; existing SMTP worker may overlap it.
Only closed-row120s safety waits lend browser time to other due modules; no
shortened wait or order cap. Local module pauses/backoff are isolated; shared
database, security and ownership errors propagate. Shutdown/manual gates remain.
GUI exposes per-module plans and V1.6 title/sidebar; original five pages retained.

Changed files: workflow/service.py, v12_notifications.py, v13_integration.py;
launcher/backend.py, workbench_snapshot.py; core/app_paths.py; gui/app.py,
workbench.py; existing Windows build script/spec/entry. Corresponding workflow,
launcher and GUI tests plus task record. Paths are relative to `src/` except
tests and packaging/scripts. No Research pricing/window/MPN/FX rule changes,
new dependencies, timer daemon, browser manager or business state system.

## Backup and rollback

Fresh protected backup:
`D:/Program_Leo/INSO_Leo/dist/release-backups/INSO_V1.6-before-20261027T015035Z`.
Canonical verified SQLite backup, full private table fingerprints, config and
opaque encrypted vault verified before install. Canonical migrations executed
on copy: zero schema/row delta; production migration NOT_NEEDED, not executed.
Install before/after full ledger comparison identical. FourTP tasks, sixTP-SENT,
138 historicalSENT and all immutable messages preserved. Ongoing read-only audit
still confirms those exact historical rows/commands unchanged.

V1.5 remains intact at `D:/Program_Leo/INSO_Leo/dist/INSO_V1.5`, EXE
`DA21769649159216BB66604AB601F051C55C192BFA62A3F09991F5EE03BA9A4A`;
2875 assets verified. V1.4 and earlier verified rollback backup remain intact.
V1.6 runtime junction targets the original `dist/INSO_V1.4/runtime`.
Config changes restricted to `v16_enabled=true`, `tp_enabled=true` and independent
periods; quotation already enabled. Research config and vault unchanged.

Rollback: stop V1.6 normally, restore backed-up config (including TPfalse), then
launch unchanged V1.5 against the **current compatible ledger**. Never restore
the pre-live database after new mail/submissions; that would forget receipts.

## Actual production results and limits

| Module | Actual evidence | External result |
| --- | --- | --- |
| Inquiry procurement | Three logged cycle IDs; four SOURCE_CHANGED outcomes across two protected orders | Conflicting source identities stopped; no new SAVED procurement confirmed |
| Quotation follow-up | One logged cycle:31 NO_RECENT_QUOTE,1 PRICE_UNCHANGED,1 SOURCE_IDENTITY_UNRESOLVED | No fabricated prices or guessed identity; no new quotation Sheet write confirmed |
| TP | Enabled in canonical three-module runtime; preflight found4already_processed,0new candidates | Four historical tasks/sixSENT unchanged; no new TP mail. Independent current-cycle completion receipt NOT_VERIFIED |

One new PURCHASE_EXCEPTION notification command, one recipient recordedSENT
(138→139 total). This means existing SMTP transport accepted the notification;
mailbox delivery/read receipt is NOT_VERIFIED. No new UNKNOWN/PENDING recipients
observed. No ad-hoc test mail, historical replay, payment or expanded transaction
authority. Existing ERP gate covers procurement inquiries, not payment/contractual
purchase orders. Existing identity exceptions are per-task stops; healthy checks
continue. Normal future eligible tasks remain authorized under Owner's rules.

Real canonical read-only preflight: six sources SUCCESS, INSO quotation read63
rows, Google source/quotation metadata and payload read PASS. Pending sources3/0;
RFQ85rows, fouralready_processed TP. Existing tabs preserved, no leftover owned
probe tabs; protected Chrome/profile not restarted. These results are connectivity
evidence, not successful real purchase/Sheet-write/TP-mail acceptance.

Runtime diagnostics exist in shared `runtime/logs`, current receipt
`runtime-e3408661f02d4adc965f62ce67f97a01.state.json`; sanitized rotating business
log retains inherited filename `INSO_V1.3.log`. Source includes bounded GUI logs,
bounded views and existing file rotation. Do not infer application version from
that inherited logfile name. No fatal native receipt or DB integrity error seen.

## Tests and short performance

Full offline regression2759PASS/1SKIP,100.86s; Ruff and diff check PASS.
Independent deadlines/thread ownership, SMTP overlap/atomic races, SENT/UNKNOWN,
stop/manual safety, source snapshot invalidation, website isolation and individual
UI deadlines covered. Existing legacy readiness timing test failed intermittently
in earlier runs; cleanup now prevents leaked workers after failures and diagnostic
assertion retains exact stacks. Backend53PASS and subsequent full runs PASS;
historical timing cause remains NOT_REPRODUCED, not called a business fix.

Synthetic UI45layouts/90recovery cycles and100/500/1000orders PASS; zero callback
errors. Synthetic screenshot supplied, no real customer contents. Versioned live
window exists; current Windows control read hit application-approval timeout.
Live menu/tray/exit interactions on this newEXE NOT_VERIFIED, not replaced by
synthetic evidence or prior V1.5 Owner tray confirmation.

Two finite native-counter samples, no permanent monitor:

| Period | Duration | HostCPU | RSS MiB | Private MiB | Threads | Handles | GDI/USER |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Active quote queries |121.313s|0.33085%|131.46–135.02|101.13–105.11|9–11|3982–5118|136/258 |
| Later batch boundary/next check |121.75s|0.28956%|135.23–137.87|105.63–107.93|10–11|933–1041|136/258 |

One finite type snapshot between windows5327handles, chiefly4762semaphores;
later fall below1041 rules out extrapolating the earlier rise as proven unbounded
leak. Root lifetime attribution and multi-cycle/long-run bounds NOT_VERIFIED.
Observer0%CPU,~20.75MiB RSS,1thread/128handles. Excludes Chrome/site process costs;
does not prove game FPS or idle/tray performance. No source fix was invented to
hide the transient peak. Original V1.5 high-CPU root cause also remains UNKNOWN.

Protected original24h PID70956 still running source9f; last heartbeat here
~22h52m, zero guards/callbacks, maxgap60.11s. Not24h PASS. That test cannot certify
V1.6. System100%/150%DPI, Chrome gaming impact and V1.6 long-term operation remain
NOT_VERIFIED. No current fatal integrity/resource blocker established, but full
three-module external-success acceptance is incomplete for lack of eligible
successful actions and independent TP completion telemetry.

## Audit recommendation

CEO review implementation and actual rejection/notification evidence, especially
browser-resource serialization, SMTP worker ownership and known identity holds.
Keep truthful distinction: installed and live checks running; zero newly confirmed
purchase/quotation writes, no new TP candidate. Do not mark all end-to-end live
chains PASS or V1.6 long-term unattended acceptance PASS. Owner need not approve
ordinary configured tasks again. Required correction of held source identities
must use existing fresh verification; never reset their state to force a result.
Evidence: `docs/evidence/v16/`; task record provides detailed scope/test log.

## 2026-10-27 remaining execution — reviewed-source installation preparation

Current instruction is the Owner's remaining-needs order, superseding the prior
round's blanket evidence-only restrictions while preserving the explicit live
replacement boundary. Remote CEO PASS ee49203dbae39e79eca1f1c90164f643ba2fe03c
fetched and fast-forwarded in the existing clean checkout; no new worktree.
`git diff 04075bc..HEAD -- src` empty. P1 is accepted and is NOT reopened.
Reviewed application04075bc remains the **only proposed installation candidate**;
future page-parallel increments must not be included without independent review.

Preinstall check: existing release Python at
D:/Program_Leo/INSO_Leo/.worktrees/v1-4-order-mail-inspection/.venv-release/Scripts/python.exe
imports PyInstaller/customtkinter/playwright and initializes Tcl8.6.15. No dependency
installed. Ordinary global Python first lacked tzdata during test collection;
reused release environment's existing zoneinfo via command-local PYTHONTZPATH,
then targeted reviewed-path43PASS13.91s. Prior reviewed full2802PASS/1SKIP remains
applicable because source unchanged; no repeated full suite without source delta.
Canonical scripts/build_windows_release.ps1 -Version1.6 -BuildOnly with explicit
PythonExecutable is the sole build path; no new launcher/release system.

Read-only installed identity: main74176 / observer84608 still present, actual
D:/Program_Leo/INSO_Leo/dist/INSO_V1.6/INSO_V1.6.exe SHA256
16E38F30E253041F7ED41E0447DEF744F6912D7B310F6DBDF616556CDBDC8B82.
No stop/restart or production config/SQLite/browser access. V1.5/V1.4 EXE paths
and before-20261027T015035Z backup are present; presence is not a fresh full rollback
integrity certification. Fresh backup and full manifest verification wait for stop.

### One-time proposed installation window (NOT AUTHORIZED yet)

1. Stop admissions using existing normal UI stop/drain, let in-flight effects
   settle, then normal exit and confirm both process exit and exclusive mutex.
   If current effects cannot settle/UNKNOWN or ownership uncertain, preserve state
   and stop affected installation step; never force-kill Chrome or replay effects.
2. Fresh canonical SQLite backup after exclusive access; integrity_check, full-table
   and immutable-command/recipient fingerprints; preserve SENT/UNKNOWN/PENDING,
   original4TP/6TP-SENT, all newer naturally produced effects. Opaque credential
   and config backups verified locally without exposing contents. Record junction.
3. Canonical single formal build from exactly reviewed04075bc, frozen dependency
   selfcheck, artifact scan/asset hashes. No page-parallel code in this artifact.
   Do not assume migrations; test existing canonical compatibility on backup copy.
4. Asset-only EXE/_internal replacement after verified rollback backup. Keep runtime
   junction/current compatible ledger, V1.5/V1.4 programs and protected Chrome.
5. Installed selfcheck, safe idle startup, version/assets/GUI/log/ledger comparison,
   single-instance check. Restore already-authorized existing three-module business
   only after these checks; no expanded recipients/permissions/forced old tasks.
6. Observe real per-module receipts, especially emptyTP900s start/end and UI,
   natural eligible outcomes, current SMTP and finite multi-cycle resources.
   External success requires result/readback, SMTP acceptance is not delivery.
7. If startup/integrity/safety fault: stop affected work normally and restore
   prior verified **program assets only against current compatible ledger**;
   never restore stale pre-effect DB or reset historical mail statuses.

Impact: automatic checks pause during drain/build/installation/idle verification;
no duplicate production instance. Window length is measured, not guaranteed.
Unique Owner action: authorize this normal stop/install/resume window. If existing
UI cannot be normally exited by available tools, Owner uses tray Exit once.
No production replacement, migration or backup was performed by preparation.

## 2026-10-27 execution update — installation AUTHORIZED, awaiting normal exit

Owner explicitly authorized the proposed single stop/backup/build/install/idle/
resume-business window. The earlier "NOT AUTHORIZED yet" deployment boundary is
**SUPERSEDED by that authorization**, not by source tests. Actual replacement has
**NOT occurred**: last exact process check still shows74176(main)/84608(observer),
installed EXE16E38F30...DC8B82 unchanged. Windows skill tool found/restored the one
correct V1.6 window, but screenshot failed twice and accessibility exposes only
unlabelled Tk panes. No guessed click, force-kill or alternate UI automation.
Owner asked only to Safe Stop, allow drain, then tray Exit; authorization itself
need not be requested again. Once clean exit is verified, continue the approved
single installation workflow; do not ask approval at each normal check.

Reviewed artifact must use **04075bc application / 1b19390298c6151e08d1e513a2a153ddcae2c1cf
checkout**. No P1 rewrite. All43release-lock packages match in existing release
Python, Tcl8.6.15 ready. Necessary43targetedPASS13.91s; prior reviewed2802PASS/1SKIP
still applies to unchanged candidate. No replacement build has been made while
normal exit is outstanding; no production backup/migration/state change performed.
V1.4/V1.5 and existing backup assets are retained, current-ledger-only rollback
strategy unchanged. Fresh integrity/recipient/immutable-command verification is
still required after drain; old139SENT statistics are not current receipt proof.

### Independent C prerequisite — exact native page identity (NOT installed)

Separate source49677b7e658034f687fa0ed73c5bb5ff6bfadf3d, compatibility follow-up
f49d78526f6c30cc57b710f466883792ff574e0d. Only production-source change is
research/cdp_pages.py: random per-create marker filters foreign page events,
then page-specific CDP Target.getTargetInfo must match the exact createTarget
response before assigning ownership. Failure closes only that exact created
native target. Never selects first same-site page or clears other actor pages.
After proof, remove creation fragment using history.replaceState; preserve
window.name ownership and exactabout:blank used by existing initial-navigation
failure and last-tab guards. No Chrome launch, context/profile clone, adapter
pricing/FX/month-window/outbox/transaction change, source allowlist expansion,
new dependency, timer, daemon or production toggle.

Initial full test exposed real compatibility issues in this **uninstalled** delta:
creation fragment broke exact-blank guards; fixed in follow-up before delivery.
Test fixture event/native-target protocol updated in tests/research/background_targets.py,
test_cdp_pages.py and test_icnet.py. Final full **2806PASS/1SKIP110.02s**;
additional positive ownership/blank tests **12PASS0.57s**; scoped Ruff/diff PASS.
One additional test-only positive case was added after full run; no further
application-source change. Native browser behavior is not yet tested.
Global interpreter initially lacked tzdata/pypdf; reused existing release packages
with command-local PYTHONPATH, without installing anything. First release-Python
full also lacked pytest in a subprocess; corrected inherited environment, not
product source. All earlier failed attempts remain classified in small evidence.

**This closes only an offline ownership prerequisite.** Finite independent sync
actors, cross-module order/resource arbitration, auth/pacing integration, actual
web navigation overlap timeline and real-browser acceptance remain **NOT_IMPLEMENTED /
NOT_VERIFIED**. No claims based on thread/callback/sleep overlap. This independent
increment cannot be mixed into already approved04075bc installation. It requires
its own CEO source review and later safe browser acceptance window.

Existing unified checklist remains authoritative. Stage2 is now
**AUTHORIZED_WAIT_NORMAL_EXIT / NOT_DEPLOYED**, stages3/5 not falsely passed;
TP900s real receipts and currentSMTP/restart/GUI/long-run evidence wait for the
reviewed deployment. Old9f soak remains closed and is not restarted. Small new
summary docs/evidence/v16/remaining-preinstall.json; final/failed test stdout
retained locally,391424417bytes of completed owned test scratch retired under
original test-owner identity, no ACL changes or protected-directory cleanup.

### Delivery hygiene for this continuation

Completed cleanup-test scratch directories retired only by checked absolute
names under D:.tmp, no reparse traversal; protected rollback/runtime unchanged.
Finite resource collector and browser probe processes exited; no new automation.
Native browser helper reused canonical source factory and is temporary, not a
second production browser framework. Full source follow-up **2815PASS/1SKIP109.85s** on67be3f7 application;
prior targeted664PASS6.46s / ownership20PASS0.58s retained accurately.
ScopedRuff/diffPASS. One skip remains environment capability, not a passed case.


## 2026-10-27 continuation — bounded original-source order leases (not deployed)

CEO98ffd2ea0688c37b67811f02593b29ee3ef0a27e accepts the prior20fda49
shared CDP admission/native ownership increment only. Installed04075bc remains
unchanged; Owner restored business and new17:01–17:04 cycles confirm running.

Reuse audit: WorkflowRuntime already owns the module RLock/resource lifecycle;
WorksheetIdentity supplies canonical spreadsheet+worksheet identity. Existing
V12/TP stores remain the durable business/receipt authority. Their separate task
IDs cannot alone exclude simultaneous work on the same original row. Extend
that runtime with bounded ephemeral source-row admission; no second ledger,
scheduler, dependency or business identity. Capacity bounds resource requests,
not business order throughput. Default admission is closed, not wired into
production dispatch. Rejected admissions consume no persistent work.

Same original spreadsheet/sheet/physical row queues FIFO across requirement
tokens; differing snapshot/MPN does not bypass that lock. Exact granted lease
and admitting scheduler thread required for release; forged/copy/foreign/double
release fails closed. Stop cancels undispatched requests only; active leases
remain until known completion/drain. Shared resource abort closes admission;
backend treats typed ownership faults as GLOBAL_STOP, never a historic-order
failure. Existing transaction/identity/amount/SENT/UNKNOWN gates stay mandatory.

Targeted64PASS10.66s; final exact application-source full2861PASS/1SKIP115.96s;
scoped Ruff and git diff checks PASS. Tests cover FIFO, independent sources,
finite admission, cancellation, stop/drain, foreign/forged release, reconfigure
refusal and backend global fault attribution. These are isolated resource tests,
NOT integrated module actor/real browser business concurrency acceptance.

| Unified remaining item | Current status |
| --- | --- |
| Previous P1 / reviewed04075bc installation | PASS; not reworked/reinstalled |
| Native read-only target ownership after navigation | PASS scoped live prerequisite |
| Shared CDP fault admission | PASS scoped CEO98ffd2e source review |
| Original-source FIFO resource lease component | PASS offline; REVIEW_REQUIRED |
| Actor dispatch using these leases + existing durable claims | NOT_VERIFIED / not implemented |
| Site auth/pacing and protected Google/INSO actor integration | NOT_VERIFIED / not implemented |
| Fair module result handoff / TP timely900s actual start | FAIL prior454.210s delay; not fixed |
| Actual business-page overlap and same-order serial timeline | NOT_VERIFIED |
| Naturally eligible new purchase, Google write/readback, TP mail | NOT_VERIFIED; not manufactured |
| Sustained V1.6 memory,100/150% systemDPI, Chrome/game impact | NOT_VERIFIED |
| Deployment of new concurrency source | DEFERRED; current production preserved |

No replacement, browser experiment, production DB/config mutation or test mail
performed by this resource component. Overall REVIEW_REQUIRED persists.


## Stage A — terminal lease lifecycle correction (2026-10-27)

CEO4c40ba4 / architecture3d77a67 followed. Minimum delta in existing
WorkflowRuntime: configure_modules refuses a faulted runtime and never resets
its fatal latch. Order admission close is terminal even before first configure;
configure_order_leases cannot reopen it after Stop/drain. An explicit new
WorkflowRuntime is required for a new safe lifecycle; construction alone does
not verify a browser or grant business authority. Exact active lease release
still works after close/abort; pending entries are canceled. Existing same-row
FIFO, capacity and foreign/forged/double-release protections remain unchanged.
No new scheduler/resource manager/ledger, no deployment or production changes.

Tests:65PASS11.15s targeted; full2864PASS/1SKIP112.70s; Ruff --no-cache and
git diff checks PASS. Added fatal abort/drain/reconfigure refusal, ordinary
Stop/drain implicit rearm refusal, fresh runtime separation and close-before-
configuration. Existing wrong-thread and copied-lease regressions retained.
Initial Ruff cached invocation hit write permission; no-cache succeeded without
ACL changes. Stage A source ready for independent Review. Stages B–F still open;
this does not implement business actors or correct TP454.210s delay.


## Stage B — Stop/dispatch boundary and bounded source fairness

Extends the same WorkflowRuntime, not a worker pool or business execution path.
Exact scheduler-owned lease has an atomic begin_order_dispatch transition under
existing lock. Stop-before-transition returns False: scheduler must cancel its
reserved lease without dispatch; Stop-after-transition drains acknowledged work.
Only scheduler owner can cancel a never-dispatched reservation. Committed work
cannot be canceled through reservation API; duplicate dispatch, copied/wrong-
thread handles are rejected. Future coordinator must acknowledge submit failure,
worker cancellation or completion before releasing; this API alone is not an
integrated queue/worker proof. No in-flight business result is fabricated.

Fairness delta: capacity bounds distinct original-source slots/active leases.
Same-row FIFO waiters no longer consume independent-row slots. Each source
queue is bounded by configured module count (at least1); overflow remains in
existing domain work, not dropped. Total transient requests <= capacity times
module count; active leases <= capacity. This is browser resource budgeting,
not an order-processing limit. Still no fair module deadline dispatch integration
or numeric TP timeliness claim; observed454.210s delay remains open.

Tests69PASS10.47s targeted; final full2868PASS/1SKIP112.36s; Ruff/diff PASS.
Exact Stop-before/after-dispatch, reserved rollback, active drain, duplicate,
foreign/copy dispatch and independent-row progress under busy-row waiters added.
No production DB/config/EXE/browser access by implementation or tests.

### Google fault notices — existing production log only, no browser experiment

Available sanitized logs2026-10-27 show retry exhaustion at09:57:23,14:56:49,
16:03:20,17:04:34 (+08). Each group has5google-open-sheet failures classified
QuotationInputBusy/GOOGLE_WEB_READ_BUSY. This proves failure before TSV download,
not that Google cannot open or that every site operation is down. Existing code
can raise busy for protected pooled entry, unsafe pending/dialog surface, or
>=3owned operation pages. Logs lack branch-specific detail; which condition
actually fired remains UNKNOWN. A manually openable Sheet does not clear these
settlement/ownership guards. Existing notices deduplicate by cycle, so repeated
failed cycles can generate new notices; these log observations are not fresh
SMTP receipt/final delivery proof. No test SMTP, cleanup of protected pages or
production notification change performed. Minimum follow-up is branch-specific
sanitized diagnostics, retaining all existing protection and bounded retries.


## Stage C — immutable Public Contract, isolated and uninstalled

Implements CEO3d77a67 approved boundaries without enabling business actors.
Research owns MarketReadQuery/Result: five market sources only (INSO excluded),
ordinary canonical SourceResult/IcNetResult or TP raw TpOffer tuple; IC.net TP
context retains stock/brand. TP raw handoff deliberately avoids independent FX
snapshots per worker; existing owner-side TpFx/ranking remains canonical.
Workflow owns version1 task identity using existing SheetRecordIdentity and
real domain task ID, module/cycle/request IDs, monotonic due/admission times,
immutable completion/cancel/fault and bounded enum progress. No fabricated
inquiry ID, new business ledger, callback, browser or session in payload.

Exact canonical deeply immutable payload validation rejects mutable evidence,
noncanonical objects, wrong source/mode, invalid identity/version, NaN times,
protected INSO, naive reference date and free-text faults. Resource fault reasons
cannot use non-global scope. Default repr excludes source snapshot/MPN/result.
These are in-memory ports, not external logs/export or authority for effects.
40PASS0.57s (message+lease tests), scoped Ruff/diff PASS. Prior A/B full remains
2868PASS1SKIP112.36s; no new full claim for this separate additive port commit.
Actor lifecycle, actual source handoff and fair module continuations still not
integrated; real browser proof and TP lateness remain open. Production unchanged.


## CEO393a892 follow-up — actual module-aware source FIFO admission

A terminal lifecycle and B local stop boundary accepted by CEO. Correct the B
comment/behavior gap before actor use: request_order_lease now REQUIRES explicit
validated MarketModule from approved immutable contract, verifies it is configured,
stores it with scheduler owner/source key, rejects same-token module substitution,
and admits at most one outstanding request per actual module per source row.
It never infers module from token labels. Repeated inquiry cycles cannot reserve
TP/quotation's positions; those cycles remain in canonical domain work for later
retry. Existing FIFO and distinct-source budget retained. This changes an unused
isolated API; no production caller or feature enabled. Tests updated to provide
real module argument rather than illustrative token labels.

88PASS10.39s targeted across leases/messages/backend fault tests; Ruff/diffPASS.
Initial2failures were test loops still passing inquiry instead of loop module;
corrected fixtures and final88PASS. Prior B full2868/1SKIP belongs to earlier
source only. Added each module's100repeated cycles vs other modules' admission,
eventualFIFOclaim and independent-source progress, module forgery/type refusal.
No actual deadline/worker acknowledgment/business parallelism PASS inferred.


## Stage D — optional bounded read actors and canonical source handoff (PARTIAL)

Not connected to ProductionBackend's running module loop and NOT deployed.
Extends one WorkflowRuntime with bounded request registration, earliest-due
eligible selection, per-source module-aware FIFO leases, dispatch transition and
exact immutable terminal acknowledgment. A coordinator-dispatched lease cannot
be released through the raw lease API before terminal acknowledgment. Stop
cancels waiting/reserved work and retains submitted requests until acknowledged.
Late/different-cycle/source results are rejected. No additional durable queue.

Launcher MarketReadActors explicitly starts at most2fixed non-daemon threads;
blocking inbox wait creates no idle monitoring loop. Each thread constructs,
uses and detaches its own ResearchMarketSession. No Backend/WorkflowRuntime,
Page/Browser/credential/session object is sent into worker arguments. Transport
inboxes1peractor, terminal outbox2peractor, bounded enum observations4peractor;
no unbounded executor. No synchronous whole-batch wait on dispatch_ready.
Known submit refusal gets scheduler-owned canceled terminal; Stop/initialization/
teardown and typed native-lease failures have explicit terminal/fault messages.
Faults close shared admission, latch Runtime; Backend accept_market_fault port
uses original GLOBAL_STOP/notification path without blaming a historic order.
The port must still be consumed by future production composition, not a worker.

Research reuses all canonical parsers/adapters. collect_tp now calls extracted
collect_tp_offers then the SAME selection/FX logic; ordinary service unchanged.
New single-source interface performs no Excel writes, business mutation or
Backend callbacks. TP raw offers retain currency/date and IC.net stock/brand;
existing task owner keeps its one TpFx snapshot. ResearchMarketSession attaches
only same9222, IC.net configured CDP only, navigation to own pages, no login
providers. Four market sources usable in optional port; BOM auth and INSO remain
on existing owner path, not removed from six-source normal/TP research. BOM
actor requests explicitly hand back MARKET_OWNER_REQUIRED, never no-price.

Canonical factory supplies task-scoped native target ownership. Canonical source
finally blocks use close_research_page: legacy behavior outside optional scope;
inside, prove exact request-created native target before retirement, preserve
changed review markers, neutral blank protects last tab, shared uncertainty
stops without sweeping. Missing native lease explicitly invalidates common
admission even if adapter translates fault. No browser/Profile clone/launch.

Same-site actor queries conservatively serialize. Shared IC.net fence reuses
canonical90s rule across clients, checked by Runtime without a sleeping timer;
other source tasks remain dispatchable. Existing owner login/recovery coordination
and module-level protected operation handoff are NOT yet wired (Stage E open).
Normal inquiry/quotation query mode cannot silently use TP offer/month profile.

Tests: final targeted60PASS0.37s; earlier integrated parser/scope/backend58PASS
10.63s and first actor5PASS0.21s. Intermediate full2901PASS/1SKIP115.24s belongs
to pre-final mode/init-latch hardening only; final full to follow. Tests use actual
Python worker/queue paths + Events and existing synthetic HTML parsers, NOT real
Chrome or business success. They verify independent TP read can dispatch/return
while synthetic quotation read is unfinished, source-row serial completion,
Stop, initializer/native fault, terminal lease and existingIC90s pacing. No sleep/
Mock interval is claimed as web overlap or corrected real TP latency.

Remaining integration is material: current lease spans a READ REQUEST, not an
entire pending procurement/quotation/TP transaction. Existing synchronous domain
flows and Excel/FX finalization must resume on original owner with the same
real identity and a lease held across the full business continuation; no writes
can be enabled using this optional query bridge alone. All six source results,
owner auth recovery and GUI cycle/state handoff must remain canonical. Payload
bounds reject oversized data without truncation; owner fallback/chunk handling
needs review before broad use. Real browser Stage F not authorized this round.
Thus actual BUSINESS_ACTORS_NOT_INTEGRATED / TP454.210s_DELAY_OPEN persists.


## Google busy observation follow-up (separate from actor deployment)

Only adds fixed sanitized step labels immediately before the SAME existing
QuotationInputBusy raises: refresh-surface, refresh-uncertain, protected-entry,
pooled-unsafe and page-budget. No text/URL/account/worksheet value or screenshot
logged, no guard bypass, no retry/mail-policy change, no page mutation/cleanup.
122PASS1.99s Google transport/update regressions; new3branches assert unchanged
exception and original page set/human-page preservation. The two refresh paths
retain original recovery tests. This source is NOT installed, so prior current
production notices still have UNKNOWN precise busy branch; do not infer a cause
from new diagnostics that have never run there. Four observed retry-exhaustion
groups each failed before TSV download; manual Sheet access can coexist with
these operation ownership/settlement guards. No new production browser/DB access.

Stage E actor auth/owner recovery integration remains OPEN; this observation
increment is not full Stage E completion. New executable/install/browser test
requires existing independent Review and separately authorized safe windows.


## Stage D terminal race correction — isolated pre-deployment follow-up

Inspection found a real submit/exit race in the optional uninstalled actor bridge:
worker fatal/Stop could finish final empty inbox check before an already reserved
producer enqueued, leaving no terminal. Added one short launcher transport RLock
shared by submission, normal Stop signal and worker final inbox reconciliation.
No Research/browser call is under that lock; page reads still overlap. A producer
cannot enqueue after the worker's final retirement without Stop being visible,
and committed cancellation reaches scheduler terminal acknowledgment. No second
resource manager or business ledger. Same-runtime latch remains irreversible.

Final32actor tests PASS0.29s, including20Stop/submit interleavings and a barrier-
controlled initializer fault in the commit/enqueue gap, assert no real read and
no active lease residue. Combined actor/parser/backend62PASS10.45s before the
last additional tests. Previous full2907PASS/1SKIP113.12s belongs to0d77be2 source;
full final race-corrected source is running and must be recorded separately.
No production access, deployment or browser experiment. Actual module business
continuations, auth-owner recovery and Stage F remain OPEN, TP lateness not fixed.


## CEO8fb3f50 auth/manual classification correction (not deployed)

Prior frozen actor correction is287e23830dfd4aa226b3162464084ae1e969a4c7,
full2929PASS/1SKIP117.29s (src tree efe1f4d096d7c8e32e90f6a50cfd365b7356febf).
This closes the earlier missing final-source full evidence for that increment.

Fix the newly reviewed classification drift without a login recipe or text
matching. Move exact existing Backend INSO reason set to public Research
site_login.AUTH_SESSION_STOP_REASONS; Backend's old private name aliases the
IDENTICAL set, preserving ordinary behavior. Public SITE_AUTH_RECOVERY_REASONS
extends it only with explicit existing market/site_login emitted codes. Actor
returned evidence and direct exceptions both use set membership, not substring.
Manual verification, stale/unverified session, security event, OTP and required
verified lease defer the site to original owner; no source success/no-price or
worker login. Authenticated READ_EMPTY/READ_UNAVAILABLE stays a read failure.

304PASS1.30s targeted actor/site retry/login/sweep suite. Includes18 positive
returned/direct safety-reason cases and4negative non-auth cases. Initial targeted
command referenced a nonexistent filename and ran no tests; corrected to real
canonical test files, no dependency or production change. Final full on this
new classification source follows separately; old2929 is not reused as its PASS.
Still no module continuation/protected recovery/live callback integration or
real-browser/TP timeliness/long-term acceptance. Current04075 production unchanged.


## Direct canonical SiteLoginError supplemental remediation (isolated)

CEO basis06ed60feb7ce9a56e83e3b251760ef8ba8cad037; only newly requested route
changed. Application68e1a2d2aa2b289c1fd38da33686851ff90bec7d, exact src tree
0de681c1f7590779f647a17841230b498ff35aef. _fault recognizes reason_code ONLY
on actual Research SiteLoginError instances; existing .code/.reason and returned
SourceEvidence paths and EXACT SITE_AUTH_RECOVERY_REASONS are unchanged. No
new safety tokens, exception-text parsing, login recipe, worker credential,
Stop/Public Contract or original Owner permission change.

92PASS1.13s actor/site_login focused. Actual SiteLoginError raised by actor test
session covers manual challenge, stale/unverified session, OTP, security event,
market login-not-confirmed. All yield SITE_DEFER/no result, blocked site, exact
terminal lease release, shared runtime remains open. Native/untyped non-auth
negatives and native initialization GLOBAL_STOP tested; existing adapter/evidence
positives, resource/cleanup and Stop races retained. Exact frozen-source full:
2961PASS/1SKIP113.55s. Ruff/diffPASS. Executor Windows offline evidence only,
not CEO independent rerun or real browser/production validation.

Overall REVIEW_REQUIRED; E/F and historical454.210s TP lateness remain open.
Owner asked to complete BOTH supplemental remediation and isolated continuation;
prior E work is preserved in local codex/v1-6-e-continuation-isolated, not mixed
into this scoped fix. Continuation resumes in separate increments. Final combined
report goes to Owner for forwarding; never sent directly to CEO.


## Stage E execution — E-0 verified / E-2 first dependency increment

Remote4b6018b (CEO latest scoped PASS) fast-forwarded; its src tree equals
18bde855d3323b1a3aa1585ff0e983cdc28cea6a and prior2951/1SKIP evidence. No A/B/C
rewrite or production reinstall. Owner now requires ALL reports via Owner only;
Executor must not send reports/messages to CEO tools. Current phase authorizes
isolated source/tests only, not production browser/runtime/config/DB/SMTP.

Reuse: extend existing Runtime OrderResourceLease/RLock/FIFO, not a parallel
lock/ledger. New BusinessContinuationLease retains that SAME original-source
resource across sequential reads, Owner FX/source check and effects. Query
terminal clears query dispatch metadata but DOES NOT release business lease.
Exact scheduler owner + immutable matching BusinessTerminalReceipt required
for release. Active query/effect blocks release; UNKNOWN latches global abort
and holds lease for canonical durable reconciliation, never inferred safe by
Stop/timeout. Source-row lease still grants no write/purchase/mail authority.
New query transport IDs are runtime-nonce+sequence, preserving actual domain IDs
and rejecting old query terminals without an unbounded tombstone history. Pending
FIFO identity is retained; Stop cancels undispatched pending requests. Optional
D single-read compatibility remains; E business continuation uses explicit bound
read port and cannot use raw release to bypass full-business acknowledgment.

89PASS0.94s focused leases/actors/continuation; Ruff/diffPASS. Tests cover three
modules same row, independent row, query→effect gap, Stop/drain, unknown effect,
exact/foreign/copy release and old completion. No new full-regression claim yet;
full after integration. E1 real module bindings, E3 recovery, E4 GUI/scheduler and
E5 comprehensive regression still OPEN. This E2 resource contract alone is not
business success, fresh domain verification or real-browser/TP timing proof.

## Stage E1 increment — canonical Research owner continuation

Depends on c0ae6a4 (E2 retained-source transaction resource). ResearchService
synchronous ordinary/TP entrypoints now drive the SAME one-source continuation;
canonical adapters, collectors, calendar selectors, ranking, Excel and FX are
reused. Owner accepts frozen actor results one source at a time and owns final
aggregation. TP retains one TpFx snapshot. Ordinary foreign-currency sources
remain Owner-side until raw ordinary projection is safely split; initial actor
eligibility ordinary IC/HQ, TP IC/Findchips/HQ/LCSC, never BOM/INSO on workers.
This is a Research public seam, NOT yet three domain modules attached to the
production scheduler or proof of timely TP / actual website overlap.

197PASS8.51s Research/TP/domain regression, including mixed actor/Owner result
equivalence, six-source order, Owner callbacks, one FX, no TP ordinary Excel,
wrong source/thread and incomplete/double finish. First run found3 regressions
in existing collector monkeypatch injection; dynamic canonical collect_tp call
restored and all passed. One earlier command referenced a nonexistent test file
and ran nothing. No tests weakened. Production/browser/config/DB untouched.
Status E1 PARTIAL, E2 resource contract offline PASS, E3/E4/E5 integrated OPEN.
All delivery reports go ONLY to Owner for forwarding, never sent to CEO tools.

## Stage E1 — three original-domain continuation ports (isolated)

Canonical Research/retained-source increments c0ae6a4,6d82fcc,8500256 were
preserved separately while native login correction68e1a2d and exact evidence
2ea0b98 were completed;402ec1f combines histories, keeping CEO supplemental
review and both records intact. Prior isolated E tree (without new login fix)
ran2967PASS/1SKIP118.18s; this number is NOT attribution for later source.

V12 now exposes its SAME prepare/settle and durable WorkflowWorker claim ports.
Owner does duplicate check before asynchronous Research and uses original brand,
notification, amount/permission and purchase routing after fresh source check.
V13 exposes its SAME closed per-candidate protected INSO query and original
settle/update path; no invented six-source quotation policy. TP already binds
canonical Research/outbox continuation. Full source-row resource survives read
return through fresh verification and durable business terminal for all3 ports.
Original single worker exclusion is reused for V12; no new lock/DB/ledger.
Immutable owner completion retains module/cycle/domain/observed-source identity.
Potential write UNKNOWN retains source and global abort; no blind retries.

Offline checks:137PASS11.07s existing V12/V13/RFQ006 after seam extraction;
93PASS5.29s quote/read integration after binding;5PASS0.91s new actual domain
ports. TP/actor/resource141PASS8.77s earlier incremental source. Subsequent final
regression must be separately bound. No production/real browser/SMTP operation.
E1 ports OFFLINE IMPLEMENTED; E3 owner recovery, E4 scheduler/GUI assembly and
E5 final integration remain OPEN. Not evidence of TP punctuality or real overlap.

## Stage E3 — original-owner recovery and bounded-payload handoff

Reuse canonical SiteLoginSweep/GUI frozen verdicts via explicit owner-only
recover_sites_on_owner callback after all market slots acknowledge cleanup.
Only exact successful canonical site verdicts re-admit that auth-blocked source;
manual/failed/mismatched verdicts keep protection. Stop/global resource fault
cannot recover/rearm. No worker credentials/login/new sweep recipe or timer.

Valid payloads above existing transport limit now raise typed
MarketPayloadLimitError, route MARKET_OWNER_REQUIRED, and use original Owner
canonical full source collector/selector instead of slicing or pretending empty.
Owner-required source remains worker-blocked for the run. Pending undispatched
reads retire only on exact Runtime proof; submitted queries still drain. Site
failures do not become successful no-price results. Auth allowlist unchanged.

83PASS2.92s actor/recovery/TP/inquiry/quotation/market-read focused.129-offer
case has actual lowest at last record and confirms it survives Owner full read.
Native direct exception six cases also independently6PASS/58 deselected0.25s;
removed test fixture initialization-order dependency. Earlier new recovery test
failed because its fake inherited unrelated class-state initialization, fixed
explicit per-instance setup (no source weakening). No browser/production I/O.
E4 actual scheduler/GUI assembly and final integrated regression remain OPEN;
these ports alone do not prove real TP deadline/web overlap or long-term safety.

## Stage E4 — canonical Backend continuation assembly, isolated and default OFF

Reuse one ProductionBackend poll thread + ONE WorkflowRuntime module deadlines,
source FIFO, fixed MarketReadActors, original three domain continuation ports,
original fault/three-hour/defer handlers, existing mail worker and GUI DTOs.
Explicit constructor assembly hook market_actor_factory selects this path for
isolated validation. Default None preserves all current production/launcher
behavior; no config, alternate EXE entrypoint, new scheduler/daemon/browser or
persistent state system. Not a permission to enable it in production.

Each active module keeps its own cycle/task/source context and bounded1terminal
receipt. Owner steps submit source work and return, never Future.wait on a batch.
At most3 module transaction reservations coexist, while Runtime itself enforces
at most2market read execution slots and same-site exclusion. Same source row
remains FIFO through research, fresh source validation and original effects.
Reservations waiting on one row cannot consume another row's worker execution
slot. Original TP batched discovery source snapshots reused; completed TP still
skip original source reads; claim and pre-mail target revalidation remain fresh.

Query/initialization/native teardown faults close safety admissions before
result application. Owner effects recheck same shared safety latch. Stop drains
acknowledged reads; timeout never proves termination; UNKNOWN holds source
quarantine and original durable command/state. The ended inquiry call releases
its EXISTING Research worker exclusion while retaining UNKNOWN source/ledger,
so a later explicit safe new lifecycle is not broken by a stale global lock.
No forced thread, Chrome, page/profile cleanup or production process action.

Protected INSO preparation is closed before async yield. Each owner INSO read
and purchase continuation rebinds/verifies its REAL task using original guard;
no previous task's session is restored by copying mutable browser state. Native
quote queries stay owner-only. Existing closed-page retry and120s purchase row
wait pump other eligible modules without reducing their original deadline.
Google write settlement waits NEVER yield. GUI keeps three independent stages,
cycle elapsed/deadlines, validated-current-source progress; stale progress is
ignored. Unchanged resource-wait notifications coalesce, existing bounded GUI
projection stays authoritative; GUI never reads worker/browser/SQL directly.

Offline actual-call-path checks:9-mode canonical Backend/Runtime/V12/V13/TP
assembly (normal, Stop, initialization, teardown, in-flight ownership fault,
quote retry, TP header, TP identity change, unknown purchase; plus inquiry wait
mode in final source) uses synthetic clients and isolated original SQLite/outbox.
123PASS15.83s focused before final batching change;113PASS11.05s TP/read batching
regression after it. Earlier51PASS4.10s safety/UI/sweep scoped and73PASS5.40s
consumer fault/isolation. Final exact-source full regression follows separately.
These are NOT real page overlap, measured production TP lateness, actual SMTP
or live business successes. Real timeliness/website overlap/long-term remain
NOT_VERIFIED; old454.210s failure is NOT declared fixed by synthetic clocks.

Production04075bc, runtime/config/Vault/SENT/UNKNOWN/Chrome and70956 old soak
were NOT accessed, replaced or interrupted. Auth allowlists, ordinary1..6month
and TP1..12month algorithms, purchase permissions and irreversible gates remain
original. No packaging/install/test email. Reports ONLY to Owner for forwarding.

## E5 integration regression corrections — exact final source follows

Initial frozen E4b35e606/fe964266 full run:2996PASS/2FAIL/1SKIP132.11s.
Two unchanged RFQ006 legacy backend tests correctly rejected the changed quote
wait callback identity. Restored EXACT original stop-event wait for default
composition; cooperative closed-page pumping is selected only in explicit
continuation assembly. No test expectation weakened. This failed full is not
called PASS and is not reassigned to later source.

Source inspection also required rechecking the SAME shared safety latch after
legacy brand completion/quotation callbacks and immediately before TP immutable
outbox enqueue. A swallowed/recorded old collaborator failure cannot progress to
unsafe routing. Google STATUS_WRITE_PENDING after original purchase completion
counts as unconfirmed business terminal, retaining source quarantine and original
ledger. Actual original PurchaseCompletionActions/_complete_inquiry are exercised
in synthetic integrated tests, including unknown purchase/status write, brand
cleanup failure and pre-enqueue resource fault.13 assembly modes in final tests;
no real purchase/Google/SMTP action.87PASS8.23s original-backend/completion/domain
focused after corrections (includes preserved RFQ006 assertions).

Safe Stop/global stop now immediately signal the ALREADY EXISTING thread-safe
actor stop port; owner-only lease drain remains on poll thread. Does not alter
accepted actor transport race protocol. No new auth tokens/Owner permissions.
Final full result and source/tree SHA recorded separately after this commit.
