# INSO 模块

## RFQ-003 提交事实与查询恢复（2026-10-07）

沿用唯一 fresh-owned-tab / fixed CDP / lower Stock_VenQuote 查询链。
原子提交前 arming 不等于点击证明：必须原生唯一 Save-and-Send 调用成功返回后
记录 SAVE_CLICK_COMPLETED；只有独立 durable click receipt 才允许 SUBMIT_UNCONFIRMED。
该状态与 SAVED 分开，禁止再次 dispatch；尝试写源状态并提示 Owner 人工确认。
点击结果未知且无 receipt，不可写发给采购。单独 Save 和 generic send 仍关闭。
下方历史明确空结果与查询失败分开；查询失败初次加最多三次 fresh-tab 重试，
180 秒可中断等待；耗尽 GLOBAL_STOP。认证/人工验证立即 GLOBAL_STOP，
初次登录及中途失效的 human-needed 页均保留，最终清理只断开客户端、不 park。

## Owner 2026-10-06：提交后确认

上方查询只核对已结算首页第一条：型号匹配、新 ID 与提交前首条不同、记录
时间与本次提交时间前后相差不超过 30 分钟。分页总数可能保留旧值（响应
`total=-1`），不得据此要求首页包含全部记录；仍要求本次请求/响应/cache/DOM
的 ID 和顺序一致、查询完成、当前页为 1。页码取当前表格自己的分页栏数字
`em:last-child`，不是装饰用空 `em`。下方七天历史仍须完整分页。

本文件只保存当前有效的 INSO runtime、重复检查、采购草稿和 Save 边界；历史 discovery 已由 Git 保存，不在这里重复。

## Shared runtime

- Production browser：Chrome only；launcher 使用 approved dedicated profile + CDP `127.0.0.1:9222`。
- Credential：只通过 Core Vault，Site ID = `yingsuo.alperp.cn`。
- `ensure_inso_authenticated()` 是共享的"建立会话"能力。所有 INSO 功能复用它，不自行重写浏览器步骤。
- **每次进入 INSO 都重新导航并重新确证登录**（Owner rule 2026-10-01）。任何"已经打开的"页面都不算证据。
- 已验证 ordinary controls（2026-10-01 对着真实登录页核过）：
  - account：`input#personname:visible`
  - password：`input#password:visible`
  - submit：`button.sign-button.submit:visible`（`onClick="login()"`，由页面自己提交 `_xsrf`）；精确 `get_by_text("登录", exact=True)` 作为回退
  - 手机验证码块 `#YZM`（含 `#YZM_Code` + `#send-code`）服务端默认 `display:none`，由 ERP 自己的 JS 在服务端要求时才亮出
- account/password 都必须 fill 后 read-back 确认非空，才允许单次 submit；不得记录或输出 secret value。
- 成功只以唯一 authenticated shell 为准：INSO HTTPS origin + list frame `/InnerEnquiry/YeWuXJ/List.aspx` + `#DetailFieldValue`、`button#select_btns`、`#_id_dg`。
- CAPTCHA / OTP / device verification → `MANUAL_VERIFICATION_REQUIRED`；不得绕过。`#YZM` 可见同样按人工挑战处理。

### 登录建立：每次进入都重开并重新确证（Owner rule 2026-10-01）

**INSO 登录存活很短**：同一个 cookie 罐里，几分钟前 `List.aspx` 还 200 直出，十几分钟后就落到 `checking.aspx?gourl=…` / `login.aspx?t=islogin`。`erp_token` 等 150 个 cookie 一个不少、时钟上都没过期 ⇒ **cookie 在、页面看着正常，都证明不了会话有效**。运行中途失效正是 `AI_RECOGNITION_READY` 之后采购腿报 `CONTROL_NOT_FOUND`（界面显示「采购录单异常」）的根因：Research 跑几分钟，采购腿接手时登录已经掉了。

**两条已被实测否掉的判据（不要再回退到它们）**：

| 判据 | 为什么会骗人 |
|---|---|
| 已经渲染的页面 | 会话死后文档照旧渲染（"化石页"），曾据此误判"登录态完好" |
| `context.request` 原始 GET | 实测**在 `List.aspx` 自己的 URL 上返回 200**，正文却是那个 2 784 字节的 `.winbox` 过期弹窗桩 —— 状态码、路径、无密码框三项一致地骗人。上一版探针的 `AUTHENTICATED` 误报就出在这里 |

- **唯一生产入口（Owner 2026-10-01 订正）**：先打开 `https://yingsuo.alperp.cn/login.aspx?t=islogin`，通过既有 ordinary login 登录，等 ERP 自己跳到首页，再点击首页原生 `a#iframe_YeWuXJ_menu`（业务询价）。**禁止直接导航 List.aspx**。必须核验首页内唯一的 list 子 frame 及既有查询控件。直接列表页能做查询，却缺少父页采购弹窗容器，点击新增不会出现客户控件。
- `InsoSessionGuard.ensure_authenticated(force_login=...)` 三态：
  - 无论 force_login 值，都按上述唯一入口重新建立并确证会话；参数保留兼容既有调用，不得恢复直连列表的捷径。
  - 结果：`AUTHENTICATED` / `RESTORED` / `DEAD`。`DEAD` 按 `SESSION_STALE` 上报（不是 `CONTROL_NOT_FOUND`），并带 reason（如 `MANUAL_VERIFICATION_REQUIRED`）。
- **提交登录后必须等 ERP 自己跳走**再点击首页菜单。生产等待复用当前 Playwright page 的事件循环，不得普通 sleep 导致导航/frame 事件无法更新。
- 重登是 ordinary login：`_existing_or_new_login_page()` 在 INSO origin 的页里选一个（**已在 `List.aspx` 的页优先**，其次登录页，再其次第一个 INSO 页）。列表页优先是为了让租约保持唯一：另选一页去变成列表页会多出第二个 shell，而 `attach_inso_research_session` 要求唯一，整轮会 fail closed。**不能用"context 只有一页"当规则**，真实 context 里合法地躺着 Research 标签（hqew.com / ic.net.cn），那条规则正是让中途恢复无法动作的原因。
- **租约是页身份锁定的**：重登会让 `_reattach_inso_session()` 重新租 shell；旧租约只 invalidate，**不 close**（浏览器是共享的，关掉就把刚恢复的登录一起杀掉）。
- 采购腿接线（`src/launcher/backend.py::_LivePurchaseDraftWriter`）：入口 `ensure_authenticated(force_login=True)`；失败后的复诊用 `force_login=False`，因为只有它能诚实回答"是不是登录掉了"，从而只对确曾失效的会话**有界重试一次**。重试不会重复落行——`ai_appendRow` 是 ERP 自己的客户端行交接，会话确证已死即该交接从未发生。构建不出守卫（无凭据等）时**退回原有行为**，不凭空造新失败。

- reused Owner browser/page 不关闭；app-owned 资源只按既有 ownership lifecycle 清理。重登后的重租同样不关旧页面。
- **我们自己开的 shell 标签要交还**（Owner rule 2026-10-01）：`ensure_inso_authenticated()` 会回报"这一页是不是本次调用开的"；只有本次开的页才会被记进租约（`owns_operation_page`），并在 `close_after_drain()`（整批到期工作排空后）关掉。**Owner 自己开着的 INSO 标签一律不动**——`_existing_or_new_login_page()` 复用了它，就不该由我们关。浏览器本身永不关闭（reused 时）。下一次进入会重新打开并重新登录，不丢任何东西；而把 shell 留在那里，正是制造"看着已登录、其实会话已死"的化石页的来源。

普通 Chrome/CDP/session/ordinary recovery 问题属于共享 runtime 技术问题，不是 Owner blocker。

## Duplicate history

- **Owner 2026-10-02 订正：7 天重复检查只查业务询价页面下方「采临时询价」区域，不查上方业务询价单。** Executor 负责落实；生产装配设置 `InsoDuplicateHistoryReader(procurement_history=True)`，复用下方原生查询、解析器及既有 Workflow 168h 判断。禁止新增浏览器、HTTP 查询协议或另一套重复业务规则。
- 原生步骤：填写 `#DetailFieldValue_layout` → 点击 `#tab_b_li2 > a`（必须验证 `tab_b_id == 4`）→ 点击 `#select_btns_layout` → 核验 `Stock_VenQuote` 的同型号请求、下方渲染和分页 → 逐页读取全部历史。分页范围 `#tabs_b_panel_2`；返回 `total=-1` 时必须按下方已渲染总数核验，不得把第一页当完整集合。不能证明完整、重复分页或数量异常则 fail closed。
- 已核证字段：历史行稳定标识 `id`，型号 `PartNo`，数量 `Qty`，日期 `CreateTime`，**制单人 `UserName`**（已对照下方 `th[data-field="UserName"]` 的「制单人」），未税价 `InPrice`，币种 `CurrencyID`。不得使用上方采购员替代制单人；零报价历史不能被 Research 的价格过滤丢弃。
- Workflow 提供 168h 窗口下界；适配器完整核验分页后仅解析所需窗口，旧窗口外缺失数量不影响本窗口。窗口内缺失/非整数/非正数量仍不可伪造核对通过。精确型号、latest-only、数量 equality 和 timestamp 并列规则保持原有 Workflow 判断。
- 历史验收纠正：旧文档的 `CREATOR_NOT_EXPOSED_BY_INSO` 只反映上方旧适配器，不是下方区域事实。旧 RFQ-001 通过的是其记录的保存前安全范围，不证明下方重复检查/制单人端到端完成。验证必须包含生产装配只读查询、全部分页与制单人字段，并区分该验证和真实 GUI 整链验收。
- **上方 `PlaywrightDuplicateHistoryPage` 保留给既有保存结果 reconciliation，不再作为生产重复检查数据源。** 下列 settlement 细节属于该上方查询能力：复用 authenticated shell 的 native search/serializer，不另造第二套请求协议。
- settlement 分两步，**顺序不能颠倒**：① `wait_for_function` 等「请求已结算」（`_select_pending === false` 且 seq 前进）；② `wait_for_function` 等「grid 已渲染」（`_GRID_RENDERED_PREDICATE`：cache/DOM 行数与 response 一致、且 `.layui-laypage-count` 与 page-size select 都已出现；空结果集则要求 cache/DOM 同时为空）。②之后才做那次 authoritative snapshot。
  - 原因：response 只证明**数据**到了，grid 才证明**画出来了**。layui 是异步重建表体与分页器的，旧实现紧跟 ① 只取一次快照，渲染稍慢就读到 `PAGINATION_TOTAL_COUNT=None` ⇒ `RESULT_SET_COMPLETE=False` ⇒ 整单被折成 `DUPLICATE_LOOKUP_UNAVAILABLE` 并路由到人工确认。**踩坑记录：一次快照读 DOM 就是竞态。**
  - ② 只是**闸门**，不是判据：snapshot 之后的 required stages 仍是唯一权威，永远 fail closed；②超时不会直接判负，只是把 `GRID_RENDERED=False` 记进 evidence。等待一律用条件等待，**禁止固定 sleep**（`tests/inso/test_v12_duplicate_history.py::test_no_settle_path_relies_on_a_fixed_sleep` 是守护测试）。
  - `last_settlement_evidence` 现有 `GRID_RENDERED` 键；排障时先看它和 `FAILED_STAGE`。
- 业务窗口：rolling 168h，Asia/Shanghai，下界 inclusive。
- MPN：`dup-mpn-v1` = NFKC + outer trim + ASCII uppercase；内部标点、分隔符、空格保留；禁止 fuzzy。
- 只比较同型号最新记录；数量只比较/展示，不参与 MPN 匹配。
- 同 timestamp 无已证明稳定排序时 → `AMBIGUOUS`。
- BillID 是稳定 list→detail identity。
- creator：下方采购历史使用已核证 `UserName`；采购员/业务员不能替代 creator。上方查询原有字段缺失不得用于本功能验收。
- quote/currency contract 已确认；具体选价业务仍归 Research。

## Purchase draft

Owner update (2026-10-02): automatic purchase-draft screenshots are removed
from the normal production path. Existing local images remain preserved and
ignored; no screenshot is now required for draft completion. The parent
MPN/brand/quantity read-back and existing operation-page cleanup remain intact.

业务动作使用明确 frame/control：

- list frame：`iframe#iframe_YeWuXJ_frame`
- 新增：`button#product_add_`
- parent form：`iframe#winIframealert_enquiry`
- customer：`input#CompanyName`
- quotation type：`input#ImpValueF`
- purchaser：`input#UserName_text`（选中后隐藏 `input#UserName` 持有**逗号连接的 id 列表**；控件是**多选 checkbox**，`data-options` 自带 `"checkbox":"true"`）
- AI 录单入口：parent form 内 `#ai_import_`（文案 `AI录单`）→ 同页 `details-dialog` 层 + `iframe[src*='/product/Import_ai.aspx']`；**不是新标签页**
- AI input：`textarea#paste-area`（在 AI 录单 iframe 内）
- AI recognition：`button#ai-recognize`（在 AI 录单 iframe 内）
- AI 预览只校验 `#preview-body > tr input[data-f]` 中的 `PartNo` / `Brand` / `Qty`。Owner 2026-10-06 明确：产品编码在 AI 面板「保存数据」后由 ERP 自动生成，不读取、不校验，不作为继续回填或提交的前置条件。旧四字段假设被此规则取代。
- parent ProductID：唯一 `#_id_dg td[data-field="ProductID"]` cell（首列「编码/型号」）——**只读**
- parent PartNo：唯一 `#_id_dg td[data-field="PartNo"]` cell——**只读**
- parent Brand：唯一 `#_id_dg td[data-field="Brand"]` cell——**只读**
- parent Qty：唯一 `#_id_dg td[data-field="Qty"]` cell——**只读**
- AI 面板提交：`details-dialog._dialog1` 内唯一 `button:has-text("保存数据")`（id `win_btn__dialog11`）→ 纯客户端回填，见下

> **AI 录单的结果由 ERP 自己灌进单据，我们不填这些格（Owner 订正，2026-10-01；2026-10-06 补充）**：只校验型号、品牌、数量；产品编码由 ERP 在保存 AI 数据后生成，不关注、不校验。不得为了满足旧假设制造编码。
>
> **回填走面板自己的「保存数据」**（`details-dialog._dialog1` 页脚，id `win_btn__dialog11`）。逐字核验过的完整链路：
> `保存数据` → `pasteImport()` → `AiImport.doImport()` → `returnSet(buildResult())` + `windowsClose()`；
> `windowsClose(a)` = 隐藏 `._dialogN` + 隐藏 shade + 调用 `alertboxs[a].closeMtd`，而 **`alertboxs[1].closeMtd = function(){ ai_appendRow() }`**；
> `ai_appendRow()` 读回 `returnGet()`，把**识别到的整行**（`a.rows`）`layui table.reload('dg', {data: b, select:true})` 灌进采购临时询价明细表。
> 面板内的 `button#import-btn`（文案 `导入到单据`）是**同一个动作**——`pasteImport` 只是 `AiImport.doImport` 的别名。
>
> **全链纯客户端**：`doImport`、`windowsClose`、`ai_appendRow` 三个函数体已逐字核验，**无任何请求调用**；真正的服务端保存是表单的 `button#btnSave` → `bill_save_auto`，仍由 Production Write Gate 关闭。ERP 自己还留了一句佐证：`ai_appendRow` 里有 `alert_warning('...产品编码为空导入失败(禁止生成产品编码)')` —— 编码必须来自 ERP 解析，不许本地造。
>
> **采购临时询价页的 `编码/型号/品牌/数量` 不由我们填写**（Owner 规则）。这四个 cell 在 DOM 上**确实可编辑**（`td[data-edit="text"]`，transient editor 非 readonly 非 disabled，实测双击可写入、`bill_save` 甚至会主动收割未提交的 editor 值）——所以"**能不能写**"不能当作"**该不该写**"的依据。**不许写**：`ParentProductFields` / `PlaywrightParentProductFields` 只提供读与等待，**连 setter 都不存在**。

选择框（customer / quotation type / purchaser）必须点击站点自己渲染的 option 行选中，fill 文本不算选中。**customer 选完菜单自行关闭；purchaser 选完菜单不会自行关闭**，其自身表格单元会持续遮挡 `#ai_import_`，导致 AI 录单无法点击。因此每次选中后都要补一次站点自身的 document click 关闭残留菜单，并校验菜单已消失，否则 fail closed（Escape 不生效，已验证）。

> **purchaser 是多选，必须"先清后选"（2026-09-30 线上缺陷）**：每个 option 行是 `tr > td > input[type=checkbox]`，一次点击是 **toggle 而非替换**，控件会把**所有已勾选**的名字写进可见文本。草稿打开时 ERP 会**自动重勾上次用过的采购员**，而 `fill("")` **清不掉 checkbox 状态**。实测两次运行叠加后现场为 `陈熙,颜浩坚`（id `7432,16665`），随后 `SET_PURCHASER` 的精确回读守卫（要求 `input_value()` 恰好等于目标）必然失败并抛 `SecurityViolation`。所以选目标前必须先点掉站点自己渲染为 checked 的行；点完仍 checked 只记 warning **不抛**——目标项恰好已是唯一选中是正确结果，不是失败。

AI 录单为同页异步面板：点击 `#ai_import_` 后才能取到 AI iframe；识别是异步的，按钮先从 `AI 智能识别` 变为进度文案（`🔗 正在连接 AI 服务... 0%` → `✅ 正在校验品牌与物料库... 66%` → `✨ 即将完成，请稍候... 95%`）再到 `重新识别`，约 1s。回读必须在时限内轮询到唯一 ready row，超时仍 fail closed。AI iframe 身份以 scheme+host+path 为界（query 由 ERP 自行携带 `BillPage`/`VendorID`/`h`，`VendorID` 为真实值，不固定）。

**回填与回读的顺序**：`read_ai_result()` 读到唯一 ready row 并通过 `validate_ai_recognition` 之后，由 `InsoPurchaseWriter.commit_ai_entry()` 点面板的 `保存数据`。它作为动作枚举 `WriteAction.AI_ENTRY_COMMIT` 绑定在**"包含该 AI frame 的那个 dialog"内**（scope `ai-dialog`，选择器 `button:has-text("保存数据")`，身份按 id `win_btn__dialog11`——裸 `<button>` 的 `type` 默认是 `submit`，而 `submit` 是 denied semantic，故与 `SAVE_DATA` 一样**只按 id 绑**，见 `_ID_ONLY_ACTIONS`）。该动作**不受 Production Write Gate 约束**（纯客户端），`SAVE_DATA` 照旧受约束。

`ai_appendRow` 经 `layui` **异步** reload 表体，所以点击后按型号等待唯一父页面行（`PlaywrightParentProductFields.wait_for_model`），再回读型号、品牌、数量，沿用原业务匹配策略。等待只是闸门，**回读与比对才是判据**；超时仍 fail closed（`CONTROL_NOT_FOUND`，step `parent-row-missing`）。不再读取或比对产品编码。

parent 四列是**只读 seam**：取唯一、可见、enabled 的 `#_id_dg td[data-field="ProductID"|"PartNo"|"Brand"|"Qty"]`，先读 transient `input` 的 `input_value()`，无 editor 时回退读 `.layui-table-cell` 的 `inner_text()`；缺失、多重、不可见、错误 frame/origin 一律返回 `None`（fail closed）。**没有 setter**——见上。

AI preview 只接受唯一 row；MPN 按 `ai-mpn-v1` exact、Qty positive integer exact；**品牌按 `ai-brand-v1` 只做部分匹配**（Owner 2026-09-29 决定：ERP 的 AI 会把品牌归一成自己的规范码，实测 `HRS(hirose)`→`HRS`、`hirose`→`Hirose`，故 Research 标签与 ERP 码本就会不同；空值仍 fail closed）。缺失、多重、不可见、不可用、错误 frame/origin 或 mismatch 一律 fail closed。

> 复用要求：AI 录单入口的形态以上述已核证结论为准（Phase A 只读验证记录于 `src/launcher/v12_phase_a_readonly.py`）。任何实现都必须复用该结论，不得另造第二套入口（例如新开标签页 goto `Import_ai.aspx`）。

### 每单边界：必须清空所有残留界面（Owner 2026-09-30 指令）

**订单窗口**（承载 `iframe#winIframealert_enquiry` 的 `details-dialog.alert_enquiry`）与 **AI 录单面板**（同页 sibling `details-dialog._dialog1`）都挂在 **INSO 首页**上，不是独立页面。关闭只是 `display:none`——DOM 里的 **checked 状态与 iframe 内容会保留**，ERP 还会在草稿重开时自动恢复上次状态。所以"关弹窗"清不掉状态，必须**关闭 + 校验**。

因此**每条订单的开始与结束**都要收敛到"INSO 首页 + 无任何窗口残留"，下一单再从**业务询价**入口重新进入：

- `InsoPurchaseWriter.dismiss_order_surface() -> bool`：先 `dismiss_select_menu()`，再关 AI 录单面板，再经 `details-dialog` → `button[title="关闭窗口"]` 关订单窗口，最后**校验是否还看得见任何一单的界面**才算成功。
- **判据必须是可见性，不能是 DOM 存在性**（2026-09-30 只读实测）：ERP 关闭窗口只设 `display:none`，`details-dialog`、`button[title="关闭窗口"]` 与 `iframe#winIframealert_enquiry` **都留在 DOM 里**（实测 iframe 计数恒为 1，而承载它的 dialog 为 `display:none`、关闭控件 `closeVisible=False`）。用 `count() == 0` 判"已清场"会**永远判失败**，从而在触达表单前就拒绝每一单。正确口径：`_order_window_is_open()` 看承载表单 iframe 的那个 dialog 是否可见，`_ai_panel_is_open()` 看 `details-dialog._dialog1` 是否可见；**本来就不可见 = 已清场**（不是失败）。
- 装配层（`src/launcher/backend.py` 的 `_LivePurchaseDraftWriter.prepare`）在**每单前后各清一次**；开始就清不掉 → 直接 `VALIDATION_FAILED`/`CONTROL_NOT_FOUND`，**不触达表单**（脏界面绝不产生错误写入）；结束清不掉 → 记 warning。
- 关不确定（找不到唯一窗口 / 窗口不只一个候选 / 该关的窗口可见但关闭控件不可见不可用 / 点击异常）一律返回 `False` 且**不改动现场**，绝不假设已关。

### 失败落点：只回填我们自己的词汇（2026-10-01）

`CONTROL_NOT_FOUND` 是**一个 code、四个以上落点**：AI 面板（`prepare`）、面板自己的 commit（`commit-ai-entry`）、表体重载没等到行（`parent-row-missing`）、重载了但不是我们那一行（`parent-id-mismatch`）、以及装配层清场失败（`dismiss-surface`）/ 收尾没关掉（`surface-left-open`）。界面上的「采购录单异常」把这些压成一行，**看不出断在哪**——这正是 2026-10-01 那一整轮取证失败的原因。

- 唯一出口是 `src/launcher/diagnostics.py::log_step(step, cause=...)`：logger 名 `inso.diagnostics`，只带两个字段——我们自己的 step 常量，与 `type(cause).__name__`（**类名，不是 message**）。异常 message 是客户名/字段值藏身处，永不读。
- 持久化落点是 `runtime/logs/INSO_V1.2.log`，由 `src/gui/main.py::_SafeRuntimeLogFilter` 处理。**过滤器是重建而不是放行**：`inso.diagnostics` / `src.launcher.backend` 的行由 `inso_step` / `inso_cause` 两个 extra 重新拼成 `workflow step failed at <step> (<Cause>)`，`record.msg`/`args`/`exc_info` 全部丢弃；step 与 cause 都按正则**校验**（`[a-z][a-z0-9-]{0,31}` / 类名），夹带路径或句子的 extra 会降级成通用行 `launcher event (WARNING)` 而不是被写出去。其余 logger 一律丢弃。
- **踩过的坑**：修好之前 `_failed` 的 `log.warning` 挂在自己的 logger `inso.v12_composition` 上，被过滤器**整条丢掉**，日志文件里只剩两行 `launcher event (WARNING)`——step 证据写了、落了、看不见，等于没写。新增任何"要落盘"的诊断，必须同时改过滤器的白名单，否则静默丢失。
- 判据依旧在回读：记录 step 不改变任何结论，只为下一次少一轮取证。

## Save / reconciliation

- 唯一可能授权的最终动作：`button#btnSave`（表单的「保存」→ `bill_save_auto`，**服务端写入**）。
  - **命名易混，务必分清**：AI 录单面板页脚那个「保存数据」（`#win_btn__dialog11`）**不是**它。前者是纯客户端回填（`WriteAction.AI_ENTRY_COMMIT`，不写服务端），后者是唯一的服务端保存（`WriteAction.SAVE_DATA`）。2026-09-29 的笔记把两者混为一谈并据此**禁止点击面板的「保存数据」**，直接导致采购腿绕开 ERP 原生回填、改成手工敲四格（Owner 于 2026-10-01 订正）。
- Owner 2026-10-02 明确授权例外：`#btnSave2`（保存并发送）只在正常生产装配明确注入 `OwnerAuthorizedSaveAndSendGate` 时绑定；必须是客临时询价 parent form 内唯一可见可用 `button#btnSave2`，id、role 和完整文案完全相等。默认 gate 和 FakeWriteGate 不开放此动作；`#bcSend`（发送）仍禁止，单独「保存」仍关闭。Executor 本轮不做此步骤测试、不重启上线。
- Production Write Gate 默认 CLOSED。
- Save 前必须先持久化 `UNKNOWN_WRITE_OUTCOME`；Save 结果未知时绝不自动再次点击。
- `PlaywrightReadOnlySaveReconciler` 复用 exact history + BillID/PENO/detail read-back；在确认结果前必须证明 candidate set 完整：native response、cache、DOM 一致，分页总数等于 response row count，且为首页单页结果。不能证明完整性时为 `UNKNOWN`：
  - 唯一候选 + stable id + MPN/Brand/Qty exact → `CONFIRMED_SAVED`
  - authoritative settled query + 0 candidate → `CONFIRMED_NOT_SAVED`
  - 多候选 → `AMBIGUOUS`
  - 其余 → `UNKNOWN`
- 当前阶段与 Gate 状态只看 `control-room/COORDINATION.md` 与对应 RFQ Task Spec。

### 最终提交接线（Owner 2026-10-02）

- 删除正常采购路径的自动截图；不删除历史本地证据。
- Owner 后续确认上方按时间倒序：复用 `PlaywrightDuplicateHistoryPage(first_page_only=True)` 原生查询与 settlement，开草稿前记住首页第一行 BillID。只要求首页、查询结算及 response/cache/DOM 顺序一致，不要求全部历史在一页；默认完整集合模式不变。
- 下方采临时询价仍只供 Research/七天重复检查，不用于最终提交确认。
- AI 与 parent 校验通过后，复用已有存储转换持久化 `AI_RECOGNIZED`，再由 `begin_save_dispatch(save_and_send=True)` 在同一事务中保存 UNKNOWN 和 `SAVE_DISPATCH_ARMED`，随后才可能发生单次点击。
- 单次 `save_and_send` 后 `page.wait_for_timeout(5000)`；关闭原有订单弹窗遮挡，再复用上方查询。只看第一行：BillID 不同于提交前第一行、精确型号、PEDate 位于本次点击所在分钟至查询完成时间，才能确认 `SAVED`。时间解析复用已有 Asia/Shanghai 规则；分钟精度下靠新 BillID 排除旧记录，不扫描其他行。
- 无首行、仍是旧首行、时间不符、字段缺失、查询失败均为待确认，不标成未保存、不自动重发。确认仅证明上方出现了业务记录，不证明各供应商收到发送内容。
- 操作退出后仅归还 app-created INSO tab；借用的 Owner tab 保留。绝不关闭 Chrome/context 或创建第二 CDP。
- baseline 仅属于当前调用，不新增持久表/迁移。中断重启不会自动提交，legacy reconciliation 不得拿旧记录确认此次 Save-and-Send；结果需人工核实，不能靠重跑补发。

## RFQ-004 V1.3 read-only quotation capability

`quotation_read.InsoQuotationReader` reuses the existing complete lower native query via per-page display capture. `V13QuotationRow` retains fourteen raw text cells 日期→制单人 separately from its parsed aware time; `select_recent_latest` applies exact MPN and inclusive Shanghai rolling72h, latest timestamp only. No quantity/price/brand business validation. Structure/time failure is not an empty quote. Current live fourteen-column layout remains UNKNOWN; see RFQ-004 Execution Log. Existing V1.2 default query behavior remains unchanged.
