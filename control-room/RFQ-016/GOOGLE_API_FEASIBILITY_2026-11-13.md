# RFQ-016 — Google API 长期稳定性可行性核查（2026-11-13，只读调查，未改生产代码）

**范围：** 仅调查与验证方案。未修改任何生产源码，未创建真实授权，未改表格共享，未连/关 CDP 9222，未触发报价/邮件/重启/部署。
**分支：** `workbuddy/v16-rfq016-stabilization`（已快进同步到 `a72037a2`；本文件为新增记录，不影响代码）。
**证据级别：** 源码与仓库记录可复核；运行环境仅查看文件存在性/时间戳与日志文本，未读取任何令牌、密钥或凭据内容。Google Cloud 控制台状态、真实表格共享设置、Apps Script 工程**均未访问**。

## 0. 先说结论（一句话）

**当前 V1.6 生产根本不用 OAuth，全部 Google 读写都走 CDP 原生页面。** 因此“每七天重新授权”是 2026-10-06～10-18 那段 OAuth 通道的历史症状，已经被 CDP 替换“绕过”，不是今天的运行故障；今天的故障是 CDP 页面读写的稳定性。若要根治，推荐 **Service Account（服务账号）** 作为长期授权，API 接管读取与单格/单行写入，**保留“更新报价”按钮点击的 CDP 通道**，并分两个增量落地。

## 1. 现状事实（已核实）

| 事实 | 证据 |
| --- | --- |
| 生产组装用 CDP：`write_service = web_service`，`reader = GoogleSheetsRowReader(web_service, …)` | `src/launcher/backend.py:1058`（组装）、`:1100`（写通道=CDP） |
| OAuth API 服务构造函数仍存在但**生产无调用**（仅测试 `tests/sheets/test_google_oauth.py` 与离线 smoke 引用） | `grep -rn build_read_write_google_sheets_service src tests` |
| OAuth 曾接入生产：`a1bed409`（2026-10-06）引入，`23671c7b`（2026-10-18）以 CDP 通道替换 | `git log -S build_read_write_google_sheets_service -- src/launcher/backend.py`；`docs/modules/SHEETS.md` “Owner CDP web transport replacement (2026-10-18)” |
| OAuth 实现=桌面型 installed app，`access_type="offline"`、`prompt="consent"`、`run_local_server` | `src/sheets/google_oauth.py:110-129` |
| 令牌缓存=DPAPI(CurrentUser) 加密文件，路径 `%LOCALAPPDATA%\INSO_Leo\sheets-oauth-<24hex>.bin`，键=`sha256(客户端文件字节)+scope` | `google_oauth.py:53-57`；`src/core/protected_local_store.py:65-69` |
| 磁盘上确有 2 份授权缓存（2026-10-17 21:35 / 21:37），另有一份 `…79545c71….bin.recovery-backup-20261009_134759` | `%LOCALAPPDATA%\INSO_Leo` 目录清单（仅文件名/大小/时间） |
| OAuth 客户端文件自 2026-09-21 22:25 起**未被修改**（400 字节，单文件） | `stat` 元数据，未读内容 |
| 当前 V1.6 日志（11-06～11-13，约 3.3 MB）中 **0 条** oauth / authoriz / invalid_grant / refresh token 文本 | `grep -i` 于 `dist/INSO_V1.6/runtime/logs/*.log` |
| 冻结包**已自带** Google API 运行依赖（在 EXE 内嵌的 PYZ 归档里，不是 `_internal/` 目录里） | 第三阶段归档核查（§18）；第二阶段曾据目录清单误判为“缺失”，已由其自身推翻 |
| 仓库内**没有**任何 service account 代码或文档 | `grep -rni "service_account|服务账号" src docs control-room tasks` 为空 |
| 生产配置键已含 `client_secret_file`（值=`D:\Program_Leo\secrets\google-sheets-oauth-client.json`） | `dist/INSO_V1.6/runtime/production.json`（仅键名与路径） |

## 2. 历史“每七天重新授权”的证据与未确认项

**能证明的：**
- 代码路径是一条标准“桌面 OAuth + offline refresh token + 本地加密缓存”的实现；只要缓存存在且 `credentials.valid` 为假，就 **只做 `refresh()`，不做重新走同意页**（`google_oauth.py:126-128`）。所以“每周弹一次授权”不可能是本代码主动重复弹窗，只能是**刷新令牌本身被 Google 判废**（或缓存不可读）。
- 失效后的行为是 `GoogleSheetsAuthorizationError`（脱敏，无 cause），缓存文件**不会被删除**，也不会自动进入同意页（`allow_interactive=False` 的生产写回更直接抛错）。因此每一次令牌失效都表现为“需要人工处理”，与 Owner 描述的体验一致。
- 时间线：OAuth 生产期 2026-10-06 → 2026-10-18；缓存文件最后更新 2026-10-17 21:35/21:37；2026-10-09 13:47 出现一次人工恢复备份。CDP 替换后（10-18 起）生产日志里再无 OAuth 痕迹。**“周更授权”这一症状与 OAuth 生产期完全重合，并在改用 CDP 后消失。**

**可以排除的：**
- **客户端配置文件变化**：`google-sheets-oauth-client.json` 自 2026-09-21 起 mtime 未变，字节未变（缓存键因此稳定）。此项不成立。
- **缓存键抖动**：两份缓存（1014/1030 字节）最可能是同一客户端的“读/写两个 scope”（缓存键含 scope，属设计内行为）；此点为**推断**，因未解密文件内容故不能逐项确认。可确认的是：客户端文件未变 ⇒ 缓存键未因客户端轮换而漂移。

**未确认（必须 Owner 在 Cloud Console 确认，我不访问）：**
- 该 OAuth 客户端的 **Publishing status（Testing / In production）** 与 **User type（External / Internal）**。
- 若是 **Testing + External**，Google 公开政策规定 refresh token **7 天后失效** —— 这是最符合“每七天一次”的机制解释；本机证据只能证明“令牌被判废”，不能证明“因此判废”。
- 2026-10-09 那次恢复的具体原因（令牌被撤销？缓存损坏？）无保留日志，标记 `NOT_RETAINED`。

> 结论口径：**机制已定位到“refresh token 失效”，根因（Testing 七天）高度可疑但未验证。** 不接受“每七天人工授权”的生产方案，这一点与 Owner 的判断一致。

## 3. 长期授权方案比较

### 方案 A（推荐）Service Account 服务账号
- 原理：SA 是一个带邮箱的机器人身份（`name@project.iam.gserviceaccount.com`），把目标表格**共享给这个邮箱**（编辑者）即可，凭据是本地 JSON 私钥；**没有同意页、没有 refresh token、没有七天规则**，长期静默。
- 对现有表格的影响：只需在表格“共享”里加一个编辑者，**不需要改表格所有者**，不需要迁移文件。
- 组织限制（关键未知）：若表格属于某个 Workspace 域且域策略禁止对外共享，SA 邮箱（外部身份）加不进去；个人 Gmail 表格通常可直接共享。**必须 Owner 实测一次共享能否成功。**
- 凭据存储：私钥 JSON 放在仓库外的 `D:\Program_Leo\secrets\`，按现有规范再加一层 CurrentUser DPAPI（复用 `protected_local_store.protect_bytes`），或直接进现有 `CredentialVault`；**不得进 Git、不得进日志**。
- 作用边界：SA 只能替代 **API** 读写；**点击“更新报价”按钮仍需浏览器里以 Owner 的 Google 账号登录的页面**（脚本按钮不是 API）。
- 另一个实打实的收益：API 读写不再需要 Google 网页登录会话；CDP 里只剩“按钮”这一个用途。

### 方案 B OAuth 正式发布（备选）
- 把同意屏从 Testing 发布到 **In production**（External）后，refresh token 不再受七天限制。但 `spreadsheets` 属 **sensitive scope**，对外发布通常要走 Google **OAuth 验证**（隐私政策、主页、演示视频、可能数周），且以后每次改 scope 都要重审。
- 若 Owner 的 Google 账号在某个 Workspace 组织内，可把应用设为 **Internal**（组织内）而免验证——但这要求表格与账号同属该组织，且需管理员配合。
- 结论：可行但**周期与不确定性都高于 A**，且仍需维护“令牌失效→人工”的兜底。仅当 A 因共享/组织策略不可行时采用。

### 明确不采用
- Testing 状态 + 每周人工授权（Owner 已否）。
- 把 OAuth 客户端文件写进仓库或用长期 access token 硬编码。
- 用 API 重写报价计算（业务逻辑在表格脚本里，禁止改）。

## 4. API 与 CDP 的功能划分

| 业务功能 | 现有实现 | API 可否替代 | 说明 |
| --- | --- | --- | --- |
| 源表 `2026`/`SHAHAB` A1:G 读取 | CDP 下载 TSV | **可以** | 需 +W 列（`quote_date`）以保留 `source_order_dates` 证据；`google_reader` 现固定 `valueRenderOption="UNFORMATTED_VALUE"`（`google_reader.py:167`），迁移需确认取渲染口径 |
| `RFQ_BRIEF` 发现/日期提示 | CDP | **可以** | `BriefReader` 复用同一 reader |
| `报价输入` 表头/元数据校验 | CDP | **可以** | 单次 `values.get` |
| 单格状态写回（A/B 列状态、F/E 列 Brand、意向状态） | CDP 原生键入 | **可以** | `GoogleSheetsBrandWriter`/`…StatusWriter`/`…IntentStatusWriter` 已是 `values.update RAW`，换 transport 即可 |
| 报价输入 14 格写入 | CDP 原生键入 | **可以（写入部分）** | 一次性 `values.update` RAW 写整行；但**写入≠生效**，生效仍靠按钮 |
| “更新报价”按钮与结果弹窗 | CDP 点击 + 脚本结算闩 + 60 秒弹窗 | **不可以** | 容器绑定 Apps Script，只能由页面触发；API 无法代劳。理论上若表格脚本另发布为 Web App 才可由服务端调用，但那要改客户的脚本工程与部署，不在本方案内 |
| 报价结果读回/差异判定 | CDP 下载读回 | **可以** | 读回改 API 后更快，判定逻辑不变 |
| 云端保存证明 | CDP 保存指示 + TSV 读回 | **可以（证明形式改变）** | API 200 + `updatedRange/updatedRows` 即服务端确认；仍需保留写后读回 |
| 仪表盘计数 | 复用 reader | **可以** | 跟随 reader 切换 |
| INSO / IC.net / 其它站点 | CDP | **不可以** | 与本议题无关，永久 CDP |

> 一句话：**API 能把“搬数据”全部接管，把“点表格脚本”留给 CDP。**

## 5. API 写入报价输入 与原“更新报价”按钮的时序（重点）

现状（CDP）：`v13_quote_update._update_one` → `write_payload`（CDP 原生键入 14 格 + 写后读回）→ 布防脚本结算闩（`_SCRIPT_SETTLEMENT_LATCH`）→ `click_update_quote()` → 60 s 弹窗 → 判定。**顺序本来就已经是“先写后点”**（`v13_quote_update.py:249-290`），而且业务层只依赖“service 形状的 `values.update/get`”——`GoogleQuotationInput.write_payload/read_payload`（`quotation_input.py:125-155`）本来就是一次 `values.update` / 一次 `values.get`。**换成 API transport，业务层零改动。**

改为 API 后建议的次序（**不恢复已取消的 14 格回读**）：

1. `write_payload` 走 API：`values.update` 写 `'报价输入'!<col><row>:<col+13><row>`，`RAW`；以响应 `updatedRange/updatedRows/updatedCells` 作为**写入已提交**证据（服务端确认，强于页面保存指示）。**更正（CEO P0-1）**：`GoogleQuotationInput.read_payload` 在生产报价链路中**从未被调用**（`v13_quote_update.py:249-290` 只调 `write_payload`；`tests/launcher/test_google_web.py:1650` 还断言它不应被调用），因此 `v13_quote_update.py:268` 的 `QUOTE_INPUT_READBACK_MISMATCH` 分支在报价流程中当前不可达。现有“写后确认”只存在于 CDP transport 内部（键入后 TSV 读回所写单元格），**不得**据此恢复点前 14 格回读。
2. **新增且仅新增一步**：写完后把该 target 页面重新导航到同一 gid，使页面 client model 与服务器一致（旧闩随刷新销毁）。
3. 重新布防结算闩 → 点“更新报价” → 60 秒弹窗 → 结果判定。
4. 结果/后续读回继续用 API；UNKNOWN 语义、durable hold、不重复点击全部不变。

必须守住的四条时序不变量：
- **写入失败绝不点击**（API 非 2xx → 本次尝试直接失败，不产生点击，不产生外部效果）。
- **写入成功但点击失败/超时 → 视为“已写入未生效”**，按现有 UNKNOWN 处理：不重试点击、不重复写入下一轮前必须重新确认同一订单 identity。
- **脚本进行中不得写该行**（沿用 `_script_pending` / `_active_quote_target` 互斥）；页面刷新前后都由同一 target 与同一 owner marker 证明（`native_page_owner`）。
- **不做客户端并发**：Owner 手动编辑该行时，API 与 UI 之间无冲突检测，最后写者胜；程序只能在“本轮操作自有该行”的窗口内写，窗口由现有 active-quote 标记约束。

残留风险（必须验证）：页面刷新后脚本读的是**服务器值**，理论上无竞态；但若表格脚本使用 onEdit/handler 缓存或客户端变量，行为可能不同——**未验证**，需隔离测试表覆盖。

## 6. 失效与异常恢复策略（设计，不含实现）

| 情况 | 判定 | 处理 | 不允许 |
| --- | --- | --- | --- |
| 401 / `invalid_grant` / `RefreshError` | 授权失效（长期，需人工） | 仅暂停 Google 依赖模块（inquiry/quotation/tp），进程与 INSO 会话保留；**一次性**准确通知（人工重新授权），之后只做廉价探测判定恢复（`GoogleQuotationInput.validate_location_binding` 已有的 `spreadsheets().get(fields="sheets.properties(sheetId,title)")`，不读业务数据） | 全局崩溃、每轮重试刷屏、反复弹授权、清空 UNKNOWN |
| 403 权限/共享 | 权限被改 | 同上，但消息明确“共享/权限”而非“登录失效”；不自动重复 | 猜测重试 |
| 429 | 配额/限流 | 读 `Retry-After`，指数退避并封顶，保持模块节奏；首批失败不发邮件 | 无界重试、加长固定等待 |
| 5xx / 网络超时 | 瞬时 | 复用现有 5 次 2/4/6/8 秒预算；耗尽后按 batch-1 语义下一轮 | GLOBAL_STOP、技术故障邮件 |
| 进程重启 | 状态恢复 | 令牌/密钥缓存持久（DPAPI）；未确认写入留在 SQLite hold；**不自动恢复、不重放** | 重启后自动补写/补发 |
| 写入结果未知 | 外部写入不确定 | 现有 durable UNKNOWN + 禁止重复提交 | 依据表格状态“推断成功”后放行 |

**关于“授权失效不能让 INSO 全局崩溃”**：现状 `SHEETS_AUTH_UNAVAILABLE` 在报价 updater 边界直接 `GLOBAL_STOP`（`backend.py:1254`）。建议改为“Google 依赖模块局部暂停 + 一次通知 + 保留浏览器与在途业务”，这正是 batch-2/3 的改动点，不属于本轮。

## 7. 最小改造方案（复用优先，不建第二套架构）

全部落在既有文件，**不新增 adapter/ledger/scheduler/browser/mail**：

1. `src/sheets/google_oauth.py`：新增 `build_service_account_sheets_service(key_file)`（`service_account.Credentials.from_service_account_file` + `spreadsheets` scope），复用现有 `build("sheets","v4",…)` 返回形状 → `GoogleSheetsRowReader`/三个 writer/`GoogleQuotationInput` **零改动**即可用。
2. `src/launcher/backend.py`：`production.json` 增加 `google_transport`（`"cdp"` 默认 / `"api"`）与 `google_auth`（`mode: service_account|oauth`、`key_file|client_secret_file`）；默认 `cdp` → **未启用前行为完全不变**。
3. `src/sheets/google_reader.py`：API 模式下读取范围扩到含 W 列并构造 `source_order_dates`；确认渲染口径（`FORMATTED_VALUE` vs `UNFORMATTED_VALUE`，见风险 R1）。
4. 报价链路（独立增量，需单独评审）：`GoogleQuotationInput.write_payload/read_payload` 已是一次 `values.update/get`，**无需改动业务层**；只在 `GoogleQuotationUpdateActions` 增加“API 写入后刷新到该 gid 再布防点击”一步，即第 5 节的四步。仍是单次尝试、60 秒、不重复点击。
5. 记录与开关：`docs/modules/SHEETS.md` 增加“transport=api”契约与回退开关；`production.json` 支持一键回退 `cdp`。

## 8. 迁移风险（按严重度）

| # | 风险 | 说明 | 缓解 |
| --- | --- | --- | --- |
| R1 | **文本身份被数值化** | API `UNFORMATTED_VALUE` 会把 `000123` 变 `123`、日期变序列号；CDP TSV 保持显示文本 | 逐列对齐（FORMATTED 文本 + 数量单独解析），14 天只读对比零差异才允许写入 |
| R2 | **按钮仍依赖浏览器登录** | 刷新页面/点按钮需要 Owner 的 Google 会话仍在 CDP profile 内；该会话失效与 OAuth 无关，仍会阻断报价 | 把它当独立健康项：探测失败→局部暂停+一次通知，不混同为“授权失效” |
| R3 | **API 写入可能不触发表格脚本 onEdit** | 若客户表格有 onEdit 自动化，API 写入可能绕过 → 行为改变 | 隔离测试表验证；未证实前不切生产 |
| R4 | 共享/组织策略阻断 SA | Workspace 域禁外链 | Owner 实测；失败则退回方案 B |
| R5 | 私钥保管 | SA JSON 是长期凭据 | 仓库外 + DPAPI/Vault，轮换流程文档化 |
| R6 | 双通道并存造成双写 | 迁移期若 cdp 与 api 同时写同一行 | 单开关互斥；运行时断言 transport 唯一 |
| R7 | 云保存证明语义变化 | 由 UI 证据改为 HTTP 证据 | 保留写后读回，UNKNOWN 语义不变 |

## 9. 需要 Owner 做的操作（我不执行）

1. Cloud Console → OAuth 同意屏：确认 **Publishing status / User type**（用于结案七天问题）。
2. 选择长期方案：**A = Service Account（推荐）** 或 **B = OAuth 正式发布（需验证）**。
3. 若选 A：在现有 Cloud 项目创建服务账号 → 下载 JSON 私钥（保存到仓库外）→ 把 `2026`、`SHAHAB`、`报价输入`/`RFQ_BRIEF` 所在表格**共享给该 SA 邮箱为编辑者**（**这是唯一需要改动表格共享的动作**，由 Owner 决定与执行）。
4. 若选 B：准备隐私政策/主页并提交 OAuth 验证。
5. 提供**一份独立测试表格副本**（真实结构的脱敏副本）用于隔离验证，并授权“共享给 SA + 只读/写入测试范围”。
6. 批准第 7 节的两个增量与一个受控验证窗口（真实表格只读对比，不写生产）。

## 10. 验收条件（未来增量）

- **读取一致性**：同一 120 秒窗口内，API 与 CDP 对 `2026`/`SHAHAB`/`RFQ_BRIEF` 连续 14 次读取，行位置、状态、型号/品牌文本（含前导零）、数量、`source_order_dates` **零差异**。
- **写入一致性**：单格（状态/Brand/意向）写后 API 读回一致；重复执行不产生二次写入。
- **报价语义**：API 写 14 格 + 按钮，20 次连续尝试全部“写后点击”，无一次使用陈旧值；60 秒无弹窗仍进入 UNKNOWN 且不重复点击。
- **故障注入**：401/403/429/超时/重启各 1 次 → 无全局崩溃、最多 1 条准确通知、无重复提交、恢复后自动继续。
- **长期**：连续 ≥ 8 天无人工授权动作（直接证伪七天规则）。
- **回退**：`google_transport=cdp` 一键回退，行为与本批之前完全一致。

`COMPUTER_USE_NOT_USED`

---

# 第二阶段：Service Account 长期授权验证（2026-11-13，离线 + 阻塞项）

**状态标签：** `VERIFIED`（本机实际验证）／`OFFLINE_VERIFIED`（合成凭据、模拟 HTTP、测试替身）／`NOT_VERIFIED`（未验证）／`BLOCKED_OWNER_SETUP`（等待 Owner 准备测试环境）。
**边界：** 未修改任何生产业务源码（本轮只新增一个测试文件与本文档）；未创建/下载真实服务账号私钥；未改表格共享；未连 CDP 9222；未读写生产表格；未部署/打包/重启；未在任何聊天或文件里放置私钥。
**代码：** 新增 `tests/sheets/test_service_account_auth.py`（20 项，全部通过）。

## 11. 结论摘要

| 问题 | 结论 | 标签 |
| --- | --- | --- |
| 宿主环境是否具备 SA 认证能力 | google-auth 2.58.0 / google-api-python-client 2.200.0 / httplib2 0.32.0 / cryptography 50.0.1 均可用，`google.oauth2.service_account` 可导入 | `VERIFIED` |
| **当前冻结包能否跑 SA/API** | **依赖已存在**：`google.oauth2.service_account`、`google.api_core`、`requests`、`urllib3`、`googleapiclient.discovery`、`httplib2`、`cryptography` 均在 EXE 内嵌 PYZ 中，其导入闭包可解析。第二阶段的“缺失”结论已作废 | `OFFLINE_VERIFIED`（归档清单，§18）；**冻结运行期导入仍 `NOT_VERIFIED`** |
| SA 是否绕开七天规则 | 机制上绕开：SA 用本地私钥签 JWT 换 1 小时 access token，**全程没有 refresh token**，Testing/External 的七天到期对象不存在 | `OFFLINE_VERIFIED` |
| 进程重启后是否无交互 | 是：只需私钥文件；子进程实测无需任何缓存/提示即可换到新 token | `OFFLINE_VERIFIED`（真实子进程） |
| 私钥能否安全落盘 | 可用现有 `protected_local_store`（CurrentUser DPAPI）加密，密文不含明文 PEM，同用户可还原 | `VERIFIED`（真实 DPAPI 调用） |
| 401/403/429/5xx/超时分类是否已适配 SA/API | **部分不适配**：429/5xx 在共享分类器里还没被认成“可延迟的读取”，会落到模块级 `_runtime_error` | `OFFLINE_VERIFIED`（见 §14） |
| 真实测试表格读取 | **未做**：仓库与 `D:\Program_Leo\secrets\` 中都没有 Owner 批准的测试表格或测试服务账号 | `BLOCKED_OWNER_SETUP` |
| 连续 8 天无人工授权 | **未做**，需按 §15 第 5 条安排 | `NOT_VERIFIED` |

## 12. 运行条件核查（A）

**宿主 Python（本机）** `VERIFIED`：`google.oauth2.service_account`、`google.auth.transport.requests`、`googleapiclient.discovery`、`httplib2`、`cryptography` 均可导入；`google-auth 2.58.0`、`google-api-python-client 2.200.0`、`cryptography 50.0.1`。

**已安装的 V1.6 冻结包** —— 第二阶段曾判为“缺依赖”，**该结论已作废**；第三阶段按 CEO 要求用 PyInstaller 归档工具核查后确认**依赖已存在**（`OFFLINE_VERIFIED`，证据见 §18）：
- 第二阶段的两条证据都不成立：`_internal/google/` 只有 `auth/`，是因为 `collect_all("google.auth")` 把该包的**源码作为数据文件**摊在磁盘上，而其余纯 Python 包在 **EXE 内嵌的 `PYZ.pyz`** 里；用一个普通解释器把 `_internal` 放到 `sys.path` 上导入失败，根本不构成对冻结运行期的检验（PyInstaller 的冻结导入器从 PYZ 装载，不读 site-packages）。
- 归档实测：`INSO_V1.6.exe`（sha256 `00ac7d68…f30bd`）CArchive 13 项，其中 `PYZ.pyz` 未压缩 8 056 112 字节、**1198 个模块**；`google.oauth2.service_account`、`google.oauth2.credentials`、`google.auth.transport.requests`、`google.auth.jwt`、`googleapiclient.discovery`、`googleapiclient.http`、`googleapiclient.errors`、`requests`、`urllib3`、`httplib2`、`cryptography`、`google.api_core.client_options`、`google_auth_httplib2`、`uritemplate` 全部在其中，且这些模块自身 `IMPORT_NAME` 的目标逐个可解析。
- 只有三个**可选/冗余**依赖不在归档里，且均不影响 SA 读取路径：`oauth2client`（`googleapiclient._auth` 里有 `HAS_OAUTH2CLIENT` 的 try/except 保护）、`rsa`（仅在缺 `cryptography` 时才走的备用签名实现，而 `cryptography` 有 54 个模块在包里）、`cachetools`（该包内没有任何 google 模块导入它）。
- 结论：**依赖缺口不成立，不需要为此改 spec**。剩下的只是“冻结运行期真正 import 一次”尚未验证（不能启动正式 EXE），标 `NOT_VERIFIED`。

**Cloud 项目条件** `NOT_VERIFIED`（无法离线核实，需 Owner 在控制台确认）：Sheets API 是否启用；项目/组织是否允许创建服务账号密钥（`iam.disableServiceAccountKeyCreation` 等策略可能直接禁止）；SA 能否拿到测试表格的共享；是否存在 Workspace 外部共享限制。

**CredentialVault 适配性** `VERIFIED`（代码事实）：现有 Vault 是“站点 → 用户名/密码”的 PowerShell + DPAPI 存储（`src/core/credential_provider.py`、`CredentialVault.psm1`），不是通用二进制容器。把 SA 私钥塞进 Vault 需要改它的结构，没有必要；现有 `src/core/protected_local_store.py` 的 DPAPI 边界与 OAuth 令牌缓存同一套，更适合放单文件私钥（见 §15 第 4 问）。

## 13. 离线验证结果（B）

`tests/sheets/test_service_account_auth.py`，20 项全部通过（`pytest tests/sheets/test_service_account_auth.py -q` → `20 passed`；`tests/sheets` 全目录 `179 passed`；`ruff check src tests` 通过）。合成密钥在运行时用 `cryptography` 现场生成、随测试丢弃，测试里没有任何真实密钥材料。

| 要求 | 覆盖它的测试 | 验证了什么 |
| --- | --- | --- |
| B1 认证对象创建与失败分类 | `test_service_account_credentials_carry_no_user_grant_and_no_consent_step`、`test_authorization_object_failure_is_labelled_and_never_claims_google_is_down` | 对象可从私钥材料构建；无 token 时 `valid=False`；`GoogleSheetsAuthorizationError` 被现有分类器判为“共享/基础设施失败”，且**不被**当成 Google 全站故障 |
| B2 Access Token 到期自动重取 | `test_expired_access_token_is_re_exchanged_automatically` | 过期后自动重新换 token，两次都是 JWT-bearer，**没有 refresh_token** |
| B2' 换取方式本身 | `test_access_token_comes_from_a_signed_jwt_not_a_refresh_token` | 请求体为 `grant_type=…jwt-bearer` + `assertion`；JWT 的 `iss/aud/scope/exp-iat=3600` 正确 |
| B3 退出、重启后无交互 | `test_new_process_authenticates_from_the_key_file_without_any_stored_token` | **真实子进程**只用私钥文件即可换到 token；子进程目录里除私钥外没有产生任何缓存文件 |
| B4 401/403/429/5xx/超时分类 | `test_bounded_read_retry_accepts_only_quota_and_server_faults`、`test_missing_or_insufficient_credentials_are_shared_failures_not_retries`、`test_transport_interruptions_stay_retryable`、`test_api_transport_transients_are_not_yet_shared_site_failures` | 内层 5 次重试只接受 429/5xx/超时，401/403 不重试；**但共享分类器尚不认识 `HttpError`**（见 §14） |
| B5 身份失效不导致全局崩溃 | `test_authorization_object_failure_is_labelled_and_never_claims_google_is_down` | 读取路径上授权失败不会变成“Google 全站不可用”；模块边界才决定暂停（现状差距见 §14） |
| B6 不输出/不缓存明文私钥 | `test_dpapi_protection_hides_the_private_key_without_losing_it`、`test_no_private_key_material_is_committed_anywhere` | 真实 DPAPI 加密后密文不含 `PRIVATE KEY`/`private_key`，同用户可还原；仓库 `src/docs/control-room/tests` 内不存在私钥标记（防未来误贴） |
| 密钥被拒（非“用户授权”） | `test_rejected_signing_key_surfaces_as_refresh_error_without_a_consent_screen` | token 端点 400 `invalid_grant` → `RefreshError`；该路径**没有任何弹浏览器/要人工同意的可能** |

**不能据此声称：** 真实 Google 授权成功、真实表格可读、真实配额可用、真实 8 天稳定。以上全部是合成凭据与假端点。

## 14. 现有错误分类的实测差距（`OFFLINE_VERIFIED`，需后续批次修）

用 `httplib2.Response` 构造真实 `googleapiclient.errors.HttpError` 喂给现有分类器（详见测试中的 pinned 断言）：

| HTTP 结果 | 内层 5 次重试 | `is_isolated_source_read_error` | `_website_failure` | 现状后果 |
| --- | --- | --- | --- | --- |
| 429 / 500 / 503 | **会重试**（读 `resp.status`） | `False` | `None` | 重试耗尽后不被认作“可延迟的读取”，落到 `_runtime_error`：**模块暂停 + 技术通知**，而不是 batch-1 的“下一轮再试、不发邮件” |
| 401 / 403 | 不重试 | `False` | `None` | 同上，且通知文案是内部故障而非“凭据/共享” |
| 超时 / 连接失败 | 会重试 | — | — | 与 CDP 路径一致（可延迟） |
| 授权对象构造失败 | 不重试 | `False` | `None` | 读取侧不会全局停止（好），但通知不准确；**报价写入侧** `get_write_service()` 失败仍走 `GLOBAL_STOP`（`backend.py:1254`） |

原因：`_website_failure` / `is_isolated_source_read_error` 的“瞬时读取”词汇表是围绕 CDP 异常写的，`HttpError` 不在其中。API 迁移必须与“把 429/5xx 的 `HttpError` 纳入瞬时读取、把 401/403 变成准确的凭据/共享通知”同批完成，否则会重演 Owner 最反感的“假故障邮件 / 假暂停”。

## 15. 长期稳定性判断（D）

1. **是否彻底避开个人 OAuth 七天规则？** 机制上是。七天规则作用于 Testing/External 的用户 refresh token；SA 没有 refresh token（§13 B2 实测请求体里根本没有这个字段），access token 1 小时一换、由私钥签名自动获取。但这只解决“授权到期”，不解决“密钥被停用 / 共享被撤 / 配额 / 网络”。
2. **还有哪些情形会让 SA 失效？**（按可能性排序）密钥被删除/停用/轮换；服务账号被禁用或删除；项目被禁用或 Sheets API 被关闭；组织策略禁止创建密钥或禁止对外共享；表格被取消共享、移入回收站或更换所有者；配额 429；本机时钟偏差 > 5 分钟（JWT 被拒）；网络/DNS/代理；以及**与 SA 无关的**“更新报价”按钮仍依赖 CDP 里 Owner 的 Google 网页登录。
3. **能否不重启 INSO、不重复授权自动恢复？** access token 过期、429、5xx、超时**可以**（进程内自动重取/重试，无需重启、无需人工）。私钥被替换或权限被改**不能**自动恢复：需要重新读取凭据，当前没有热加载路径，最省事的是 Owner 替换文件后重启一次。授权失效**不得**让进程崩溃——读取侧今天已经不会全局停，但报价写入侧仍会，这条要在后续批次改。
4. **私钥与 DPAPI/Vault 怎么结合最省？** 用现有 `protected_local_store.protect_bytes/unprotect_bytes` 把 SA JSON 存成 `%LOCALAPPDATA%\INSO_Leo\sheets-sa-<hash>.key`（与 OAuth 缓存同一机制、同一目录、同样“仓库外 + 当前用户”边界），进程启动时解密到内存、用完即弃明文；**不进 Vault**（Vault 是站点账号密码结构，改它属于无谓结构变更），不进 Git，不进日志，不进报告。
5. **8 天无人工授权怎么安排？** 独立、不碰生产：Owner 建/指一份合成测试表 → 以只读共享给测试 SA → 交付一个**独立只读探针脚本**（不是正式程序，不连 CDP、不写表），每天跑一次，把“日期 / 是否成功换到 token / HTTP 状态 / 错误类别 / 是否出现任何人工步骤”追加到本地记录；连续 8 个自然日 8/8 成功且 0 次人工介入才算通过。**一次成功不等于八天正常**，本报告不作此声明。

## 16. 需要 Owner 完成的最小步骤（`BLOCKED_OWNER_SETUP`）

已核查：仓库记录、`D:\Program_Leo\secrets\` 与现有配置中**都没有** Owner 批准的测试表格或测试服务账号，因此本节全部为阻塞项；本轮未创建任何真实授权、未改任何共享。

1. 在现有 Cloud 项目确认 **Sheets API 已启用**、组织策略**允许创建服务账号密钥**。
2. 创建一个只用于验证的服务账号；生成 JSON 私钥后**自行保存到仓库外**（例如 `D:\Program_Leo\secrets\`），**不要把 JSON 内容贴到聊天、Git 或报告里**；只需告知 Executor 文件**路径**与 SA 邮箱。
3. 建一份**合成测试表格**（可复制真实表结构但用假数据），把该表格**只读共享**给 SA 邮箱（验证读取；写入验证留到后续批次另行授权）。
4. 告知 Executor：测试表格 ID、工作表标题、期望读取范围。
5. 顺带确认 OAuth 同意屏的 Publishing status / User type（用于结案历史七天问题）。
6. 若要推进落地，**不需要**为依赖改 spec（§18 已证依赖在包内）；只需批准后续“API 只读候选 + 默认关闭开关”的独立批次，以及一次**隔离验证**：在正式 EXE 之外的隔离副本/独立小脚本里真正 import 一次冻结运行期，把 §18 剩余的 `NOT_VERIFIED` 补成实测。

## 17. 本轮不做什么

不实现 API/CDP 混合版；不改 `src/`；不改 `production.json`；不建服务账号；不下载私钥；不改表格共享；不动 CDP 9222 / Profile / 生产 SQLite / OAuth 缓存；不打包、不部署、不重启；不把模拟通过写成真实授权成功。`COMPUTER_USE_NOT_USED`

---

## 18. 第三阶段：冻结包依赖归档核查（2026-11-13，CEO 要求，只读）

**目的：** 核实第二阶段“已安装 EXE 缺 API 依赖、必须改打包”的结论。CEO 指出该结论证据不足：PyInstaller 的模块可能在 EXE 内嵌的 PYZ 归档里，`_internal/` 目录清单与普通解释器的 `sys.path` 导入都不能代表冻结运行期。**结论：第二阶段的判断是错的，依赖确实在包内。**

### 18.1 方法与隔离

- 隔离副本：把 `dist/INSO_V1.6/INSO_V1.6.exe` **只读复制**到 `%TEMP%\rfq016_pkg_check\`，两份 sha256 均为 `00ac7d68d88e1a27eb52e3b7457b4192b699211df1b1f5e3efe0be406eef30bd`（与已知已安装哈希一致），此后只对副本操作。正式目录未被写入、未被运行。
- 工具：PyInstaller **6.16.0**（来自 `.worktrees/v1-2-design/.venv-release`）的 `pyi-archive_viewer` 与 `PyInstaller.archive.readers.CArchiveReader` / `ZlibArchiveReader`；只解出模块字节码做导入名分析，不执行 EXE、不加载业务、不连 CDP、不访问网络。
- 边界：未改 spec、未构建、未覆盖正式版、未改业务源码、未使用任何真实凭据。

### 18.2 归档实物清单

| 项目 | 实测值 |
| --- | --- |
| CArchive 顶层条目 | 13（`struct`、`pyimod01..04`、4 个 `pyi_rth_*`、`windows_release_entry`、`PYZ.pyz`） |
| `PYZ.pyz` | 未压缩 8 056 112 字节，**1198 个模块条目**，130 个顶层包 |
| `_internal/base_library.zip` | 存在（1 331 373 字节，155 项） |
| `_internal` 磁盘形态 | 运行时 DLL/PYD + 被 `collect_all` 摊成数据文件的包（`google/auth/*.py` 因此可见），**不能据此判断 PYZ 内容** |

### 18.3 关键依赖逐项核对（PYZ 内）

| 依赖 | 条目数 | 结论 |
| --- | --- | --- |
| `google.oauth2.service_account` | 1（`google.oauth2` 子包共 16 项，含 `credentials`、`reauth`、`sts`） | **已存在** |
| `google.auth.*`（`transport.requests`、`jwt`、`crypt.rsa`、`_service_account_info`） | 存在 | **已存在** |
| `google.api_core` | 8 项（`client_options`、`general_helpers`、`universe`、`version*` 等） | **已存在**（`googleapiclient.discovery` 只用到 `client_options`，已解析） |
| `googleapiclient` | 16 项（含 `discovery`、`http`、`errors`、`model`、`_auth`） | **已存在** |
| `requests` / `urllib3` / `httplib2` | 18 / 36 / 6 项 | **已存在** |
| `google_auth_httplib2` / `uritemplate` / `certifi` | 1 / 5 / 2 项 | **已存在** |
| `cryptography` | 54 项（含 `hazmat.primitives.asymmetric.rsa`） | **已存在** |
| `idna` / `charset_normalizer` / `pyasn1` / `pyasn1_modules` | 6 / 7 / 26 / 5 项 | **已存在** |

### 18.4 导入闭包与“缺失”的真实含义

逐个解析归档模块自身的 `IMPORT_NAME` 目标（含嵌套代码对象）：

- `google.oauth2.service_account` → 无未解析项。
- `google.auth.transport.requests` → 未解析项仅 `functools`、`time`，属解释器自带的标准库/冻结模块（`json`、`logging`、`ssl`、`socket`、`datetime` 等在 PYZ 内），不是缺口。
- `googleapiclient.discovery` → 未解析项仅 `collections`、`io`、`os`、`re`、`keyword`（同上，标准库）；`google.api_core`、`google.api_core.client_options`、`google_auth_httplib2`、`httplib2`、`uritemplate` 全部在 PYZ 内。
- 三个**真实不在归档里**的包，均不影响 SA 读取路径：
  - `oauth2client`：被 `googleapiclient._auth` 引用，但字节码里带 `HAS_OAUTH2CLIENT` 的 try/except 保护（旧版兼容分支）；
  - `rsa`：只被 `google.auth.crypt._python_rsa` 使用，是“没有 `cryptography` 时”的备用签名实现，而 `cryptography` 在包内；
  - `cachetools`：**包内没有任何 google 模块导入它**（被 `_oauth2client`/`impersonated_credentials` 等未打包模块使用）。

### 18.5 证据等级

- `OFFLINE_VERIFIED`：上述依赖**确实在**已安装产物的内嵌 PYZ 中，且这些模块的导入目标在包内可解析；第二阶段的“缺失、必须改打包”结论**撤销**。
- `NOT_VERIFIED`：冻结运行期**真正 import 一次**。本轮不能启动正式 EXE（会启动业务），因此不宣称“已实测可运行”；补证方式见 §16 第 6 条。
- 仍然成立、与本议题无关的既有结论：`HttpError` 分类差距（§14）、真实测试表读取 `BLOCKED_OWNER_SETUP`、8 天稳定性 `NOT_VERIFIED`。

### 18.6 最小打包方案（仅在日后确需时）

当前**无需**为 API/SA 依赖修改 `packaging/INSO_V1.1.spec`。若将来确有模块在冻结运行期报 `ModuleNotFoundError`（例如用到 `cachetools` 的 Google 认证扩展路径），最小改法是在 `release_packages` 追加缺失包名（`collect_all` 会连带其数据与子模块），并**在独立目录构建新候选包**验证后再谈覆盖安装；本轮不执行。

`COMPUTER_USE_NOT_USED`

---

## 19. Cloud Console 现场核实（2026-11-13，Owner 授权 CDP；**被 2SV 拦截**）

**授权与边界：** Owner 本轮明确授权为本次配置检查使用现有唯一 CDP（127.0.0.1:9222）。实际执行：只**新建一个**后台标签页访问 `console.cloud.google.com`，结束后把它关掉；13 个报价表格页、2 个 INSO 登录页、1 个 findchips 页**未被导航、未被关闭、未被切走**（收尾复核：17 页，13 Sheets + 2 INSO + 1 findchips + 1 blank，与开工时同量）。未新建 Profile、未重启 Chrome、未输入/读取任何密码、验证码、Cookie 或令牌。

**结果：Cloud Console 当前无法读取任何项目配置。**

- 访问 `console.cloud.google.com` 的任何路径（`/welcome`、`/apis/dashboard`、`/apis/library/sheets.googleapis.com`）都被重定向到 `enable-mfa`，页面原文：**“自 2026年10月6日起，Google Cloud 开始强制执行两步验证 (2SV)…请前往安全设置，开启两步验证”**与“无法访问 Google Cloud”。
- 唯一可读到的项目线索来自该重定向参数与控制台标题：项目**存在**，名称为 `INSO`，**Project ID = `inso-509314`**（`?project=inso-509314`）。这是控制台自己给出的当前项目，但**没有**在完整加载的项目页面上二次确认。
- 按 Owner 指示，随后把设置页交回人工（`myaccount.google.com/signinoptions/twosv`），该页又要求**密码重新验证**，且页面标题显示“尝试的失败次数过多”。因此**立即停止**自动化、未做任何输入，并把该标签页关掉。
- 因此以下各项本轮**全部为 `NOT_VERIFIED`**，不是“未启用”也不是“不存在”：Sheets API 是否仍启用；OAuth 应用的 User type / Publishing status；项目内既有 Service Account 清单；是否允许创建密钥；`iam.serviceAccountKeyExpiryHours` 与 `iam.disableServiceAccountKeyCreation` 等策略。

**为什么这条对项目重要：** 2026-10-06 起 Cloud 强制 2SV。这不影响已登录的 Google 表格读写会话（表格页仍正常），但**任何**后续“去控制台改配置/建服务账号/查发布状态”的动作都会先撞到这道门。服务账号方案本身不需要个人 OAuth 授权，但**创建服务账号和下载密钥必须在控制台完成**，所以 2SV 是这条路的硬前置。

**Owner 最小动作（按顺序）：**

1. **由本人**在自己的浏览器里打开 Google 账号 → 安全性 → 两步验证并完成开启（需要密码与手机/验证器；Executor 不得代做）。若提示“尝试的失败次数过多”，先等待冷却，不要在自动化页面里反复尝试。
2. 完成后告我一声；我再开一个新标签页复核（只读）这六项：项目存活与名称/ID、Sheets API 状态、OAuth 同意屏 User type + Publishing status、既有服务账号、密钥创建策略与 `serviceAccountKeyExpiryHours`、是否可在原项目内建长期 SA。
3. 复核通过后，才讨论“在原项目内建一个专用 SA、只读共享一份合成测试表”的具体动作；**建 SA、下载密钥、改共享仍需 Owner 明确逐步授权**，本轮与下一轮都不自动做。

`COMPUTER_USE_USED`（仅限本轮 Owner 授权的控制台只读检查：一个新标签页、无输入、无凭据读取、无业务操作；已关闭该标签页）

---

## 20. 2SV 开启后复检（2026-11-13 18:13–18:26，仍被拦截）

**授权与边界：** 沿用 Owner 本轮授权，只新建**一个**后台标签页访问控制台；未点击任何按钮、未输入任何内容、未读取/保存/输出密码、验证码、Cookie 或令牌；未新建 Profile、未重启 Chrome、未触碰报价表格/INSO/其它标签页。收尾只关闭本自建标签页（页数 4→3：Owner 的 2SV 设置页、1 个报价表格、1 个 blank）。

**复检结果：拦截仍在。** 等待并复查共三次（首次 18:13、等待约 2 分钟后 18:16、再等待约 5 分钟后 18:22）：

| 时间 | 目标 URL | 实际落点 | 页面提示 |
| --- | --- | --- | --- |
| 18:13 | `/home/dashboard?project=inso-509314` | `enable-mfa?redirectTo=…` | 无法访问 Google Cloud（强制 2SV） |
| 18:16 | 同上 | 同上 | 同上（“启用后可能需要几分钟…刷新查看”） |
| 18:22 | 同上 | 同上 | 同上 |

**新增一条可报告事实（不输出地址）：** 该控制台会话登录的 Google 账号域名是 **`qq.com`**（即个人 Google 账号，非 Workspace 域）。页面同时出现 `gcp-sa-datamigration.iam.gserviceaccount.com`、`system.gserviceaccount.com` 等字符串，属控制台静态文案，**不能**当作“项目里已有服务账号”的证据。

**因此六项仍全部 `NOT_VERIFIED`：** 项目存活与访问权（仅 `INSO` / `inso-509314` 这条线索）、Sheets API 状态、OAuth User type + Publishing status、既有服务账号、密钥创建策略与 `serviceAccountKeyExpiryHours`、能否在原项目建长期 SA。

**两种可能原因（均未验证）：**
1. 2SV 可能开在了**另一个** Google 账号上，而本 Chrome 配置里登录（也就是表格与项目在用）的是 `qq.com` 那个账号 —— 强制策略是按“当前登录账号”判断的。
2. 2SV 确实已开在这个账号上，但控制台声明尚未生效／需要一次新的人工登录才会被认可。

**Owner 最小动作：**
1. 在**已登录本浏览器配置的那个 `qq.com` Google 账号**上确认“两步验证”显示为**已开启**（不要开在别的账号上）；若只是刚开完，等待 10–15 分钟再试。
2. 最省事的解法：**由你本人**在这个 Chrome 里手动打开一次 `console.cloud.google.com`（人工会话会立即刷新声明）。**不要在报价用浏览器里退出 Google 登录**，那会连带丢掉报价表格会话。
3. 完成后告我，我再开一个新标签页复检；仍被拦截就到此为止，不再反复尝试。

**顺带一条判断（推断，未验证）：** 该账号是个人 Google 账号、项目很可能**不属于任何组织**，因此 `iam.serviceAccountKeyExpiryHours`、`iam.disableServiceAccountKeyCreation` 这类组织策略**大概率不适用**（无组织即无组织策略）；但要看控制台“组织策略”页面才能确认，本轮没看到。

`COMPUTER_USE_USED`（仅限本次授权的控制台只读复检：三次页面加载、零点击、零输入、无凭据读取；自建标签页已关闭）
