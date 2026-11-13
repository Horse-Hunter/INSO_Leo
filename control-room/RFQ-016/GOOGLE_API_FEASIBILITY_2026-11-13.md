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
| 冻结包已自带 `googleapiclient` / `google_auth_oauthlib` / `google` | `dist/INSO_V1.6/_internal/` 目录 |
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

1. `write_payload` 走 API：`values.update` 写 `'报价输入'!<col><row>:<col+13><row>`，`RAW`；以响应 `updatedRange/updatedRows/updatedCells` 作为**写入已提交**证据（服务端确认，强于页面保存指示）。写后 `read_payload` 读回仍是既有逻辑，不是“点前 14 格回读”。
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
