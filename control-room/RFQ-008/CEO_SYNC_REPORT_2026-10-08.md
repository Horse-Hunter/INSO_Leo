# CEO Sync Report — V1.3 Owner 增量 / 2026-10-08

状态：**REVIEW_REQUIRED**。Owner 已明确授权验证后生产覆盖；此授权不等于 CEO 独立 PASS。历史 RFQ-003/004/005/006/007/008 REVIEWED_DONE 结论保持不变。

## 1. 审查基线与范围

- 仓库：Horse-Hunter/INSO_Leo。
- 同步分支：`codex/v13-readiness-repair`；不改写 `feature/v1-3-integration` 历史 reviewed branch。
- 远端前一 reviewed 基线：`df64762ae6ad0893879814e847888246f5b5a93f`（GUI 源表统计 PASS）。该基线获批 DB11A02B 候选已按 Owner 授权部署。
- 本报告前源码/审计 HEAD：`0bccecd92b22fd59ee977ae2e6c4a1115614b684`。
- 最终生产代码提交：`20fad4938a8312da00b1bd48e10af4f3c1bdbc8f`。本次报告只新增文档，不重构、不重新构建、不再部署。

## 2. 最终行为与生产修改

### Chrome 后台运行
代码 `2e5387297d428ae836f4c10a04af7651ca491e67`。
`browser_bootstrap.py`、`google_quote_update.py`、`inso_session.py` 复用 `research/cdp_pages.py` 的 background target。空 context 的第一窗口在创建时请求 minimized，不建立第二个 Chrome/profile、不先前台打开再隐藏、不增加抢回焦点 timer。协议失败不回退前台建页；人工验证码/OTP 保护页保留，Owner 主动一键登录的人工提示仍可用。
验证限度：三轮现有最小化 Chrome 空白 target 探针保持前台与窗口 bounds，未通过关闭固定 Chrome 去测试冷启动；不能声称所有 OS/网站场景绝对不抢焦点。

### 采购状态重试误报警
代码 `9a01b64168bb2ea5d4fa751dc167959da4653ff2` + `80f9c3776ec15ee212451008e2c7c80df20f41f6`。
`sheets/purchase_status.py`、`launcher/purchase_completion.py` 在新鲜唯一身份确认后，将已为“发给采购”或“采购已报价”的行视为采购状态写回义务已满足，不倒退状态、不再次写表、不重新创建发送时间、不错误发异常邮件。
旧 STATUS_WRITE_PENDING 的恢复必须有 durable SAVED 和对应原表完成状态，只恢复本机采购投影；不因为 Google 状态单独推断未知提交成功，不再次 Save-and-Send。品牌复用现有 fuzzy policy 和 canonical source-brand expectation；型号、数量、等级和唯一身份保护仍严格。真实冲突邮件不再无条件要求把高级完成状态改回“发给采购”。

### 模糊型号比较与搜索边界
基础比较代码 `9bd601ebd6cb15cfbd511d031af69e4a8448523a`；最终 INSO 搜索修正 `20fad4938a8312da00b1bd48e10af4f3c1bdbc8f`。
共享 `core/mpn.py`：NFKC/大小写规范化，去空白、下划线、横线；源型号清理后去末尾两位，返回型号必须以前缀开头，后面最多十个清理后字符；1–2位仅精确、空值拒绝。Research 六网站、采临时询价防重复和报价识别复用比较规则；采购提交/源表身份不使用此宽松规则。
**Owner 最终规则：INSO 搜索必须使用原表完整型号原文。** Research INSO、lower-history duplicate、quotation 三入口均保留型号大小写/空格/下划线/横杠；HTTP 仅作 transport encoding，解码后的搜索值不变。防重复 bridge 不再发送 canonical comparison key。只在返回结果比较时清理和去末尾两位。
中间 `9365917` 的首段检索已被最终原文搜索规则取代，不能作为最终行为描述。其他五网站现有搜索策略未在这次 INSO 澄清中修改。网站原生结果数量/第一页限制仍是已知边界，不保证远端结果穷尽。

### 报价输入 B/L 与差异提醒
代码 `726fc30`；`workflow/v13_quote_update.py`、`launcher/google_quote_update.py`、`launcher/v13_integration.py`、`launcher/backend.py`。
新鲜 canonical 原表验证同时返回 status 和原型号。报价输入 B 严格等于源表原型号；INSO 选中 raw14 证据不可变，派生输入仅改 B，以及型号原文不同时在 L 追加“报价实际型号：XXX”，已有备注后换行保留。提交前再验证原型号，写入/重试间原型号变化则 fail closed。
型号差异通过现有 durable outbox 提醒 `linan229@qq.com` 和 `shawn@inso-hk.com`。同 inquiry/源型号/选中报价内容去重，进程重启/写回重试不重复创建；收件人分别重试，邮件只说明检测结果，不冒称脚本已完成。
保留 rolling72h、最低人民币等值供方未税价、正价优先/仅零价时选零、tie 最新、RAW readback、弹窗证据/30秒状态检查、脚本清除输入行、durable hold 及 quotation 正常行间零冷却。

## 3. 只读生产诊断及未解决项

- Owner 指定横杠型号案例：旧拼接搜索为空；原完整型号搜索存在三天内零价“无货”记录。最终 canonical 原文搜索已只读验证检出并选中；未为验证实际执行更新报价。
- **WGI210IT 未闭环**：日志首次在 18:54:43 记录 UPDATE_RESULT_UNCONFIRMED，本机 active durable hold 保留。20:22:31 仍是旧 hold 投影；原表仍为“发给采购”。目前阻塞原因是持久挂起，不是可以据此认定的新搜索失败。日志不足以细分当时是按钮操作、结果弹窗等待或解析失败。
- 没有擅自解除 hold、改 DB、重跑采购或报价。需要 Owner 明确的人工报价重跑/后续处理才能验证真实闭环；本阶段不能标记该订单完成，也不能声称全部真实订单已通过。
- 部署 idle 检查当时未启动业务；Owner 后来自行运行程序。报告任务不启停生产程序。

## 4. 币种核查与 UNKNOWN

| 路径 | 已核实行为 |
| --- | --- |
| Research INSO 历史参考价 | 支持 RMB/USD，USD 经现有 FX 换人民币；其他币种解析时跳过 |
| V1.3 最低供方未税价比较 | RMB/CNY 为人民币，USD/HKD 经共享 FX 换算后比较；不支持的正价币种 fail closed，FX 不可用按既有全局保护处理 |
| 零价无货 | 0 不需要取 FX；符合窗口/型号且无正价时可选 0 |
| Google 报价输入 | 保留报价原币种/原价格，不把兑换后的比较值冒充原报价 |
| 采临时询价防重复 | 基于型号/时间/数量，不按价格判重；价格信息保留原币种 |

不是“所有币种都换人民币”。Apps Script 内部币种转换尚未核实，保持 UNKNOWN。本阶段不新增未获规则批准的汇率或币种映射。

## 5. 验证结果

| 增量最终验证 | Focused | Full safe/offline |
| --- | ---: | ---: |
| Chrome background | 201 passed | 1576 passed / 1 skipped |
| 采购状态/品牌误报警 | 291 passed | 1599 passed / 1 skipped |
| 模糊型号基础 | 核心/六网站/历史/报价/提交保护包含在 full | 1636 passed / 1 skipped |
| B/L + 横杠漏读修复阶段 | 378 passed | 1664 passed / 1 skipped |
| **最终原完整型号搜索** | **406 passed** | **1669 passed / 1 skipped** |

- 唯一 full skip：Windows symlink capability unavailable。
- 最终 Ruff / git diff --check：PASS；保留 RFQ-003/004/005/006、GUI、scheduler、hold、未知故障、采购提交保护、通知去重回归。
- 最终 BuildOnly、candidate release scan、frozen self-check、isolated idle GUI：PASS。
- 部署后 self-check / idle GUI / fixed CDP / release scan：PASS；验证 GUI 正常渲染、无业务线程启动，CDP 现有唯一 context/一页。
- 测试不证明 WGI210IT 历史 hold 自动关闭，也不等于全部真实业务已通。

## 6. 最终正式资产与保护结果

- 正式目录：`D:\Program_Leo\INSO_Leo\dist\INSO_V1.3`。
- 最终 EXE SHA256：`BFFEFA407375211E758EC793AF5388D4FBCEF6A7BB01E456251DFE8213EDD98C`。
- 最后完整备份：`D:\Program_Leo\INSO_Leo\dist\release-backups\INSO_V1.3_20261008_201354_8f602a52`；此前 timestamped backups 保留。
- 最后部署 2179 release assets 匹配候选，3953 protected files 哈希无变化；DB/DB backups、OAuth、credentials、production/Research/SMTP config、fixed Chrome profile/CDP 保留。
- V1.2 部署前后 SHA256 均为 `340D7F7E7E818FA74DE36B138B205F5905F320406FD8D391EF860BD052529E5F`。
- 审计区别：早前采购状态修复那次部署仅 running Chrome Local State 一项 hash 变化，未直接写/清 profile，变化 key 未取证为 UNKNOWN；最终两次部署 protected_changes 均为空。不能概括成整个阶段所有 Chrome 文件始终未变化。
- 只替换 V1.3 EXE/_internal，未覆盖 runtime。正常 GUI graceful close 等本轮结束，没有强杀运行订单。
- 原始生产输出/客户资料/凭据和包均留在 ignored 本地 evidence，未入 Git；最近 evidence `.tmp/v13-deploy-20261008_201354_8f602a52`。

## 7. CEO 需独立核查

1. 原文搜索和模糊比较边界；B 列原文、L 追加、发送邮件时机/去重；严格 source identity 与采购第二次发送保护未放宽。
2. 接受既有币种/网站结果限制；WGI210IT durable hold 的处置及按钮/弹窗更细诊断是否作为下一项工作。
3. Owner 已授权部署与独立 CEO Review 状态分开记录。本次增量请求 REVIEW_REQUIRED，不自行改成 REVIEWED_DONE。

本 report 与实现同步到现有分支，未另建架构/浏览器/通知系统，未发送跨任务消息。实现/测试/部署验证未执行真实采购、Save-and-Send、Google 报价输入写入/更新报价、Apps Script、SMTP 测试或历史订单重放；Owner 自行运行的业务不计为部署验证。

---

# CEO Independent Review — V1.3 post-review Owner increment

Date: 2026-10-08  
Status: COMPLETE  
Verdict: **PASS / REVIEWED_DONE**  
Reviewed sync HEAD: `e62f3265c359d394f4b276add0a07cb03ee9ca65`  
Reviewed production-code HEAD: `20fad4938a8312da00b1bd48e10af4f3c1bdbc8f`  
Reviewed baseline: `df64762ae6ad0893879814e847888246f5b5a93f`

## Decision

PASS. No new production blocker was found in the increment from the previously reviewed dashboard baseline through the final original-full-model INSO search correction.

The reviewed implementation preserves the existing irreversible-purchase and quotation replay barriers, source identity rules, durable quotation holds, notification outbox and fixed-CDP architecture.

## Chrome background operation

PASS.

Automatic operation/cleanup surfaces that previously used foreground `context.new_page()` now use the existing CDP background-target primitive for:

- Google quotation input;
- quote last-tab keepalive;
- INSO login/recovery pages;
- shared-CDP parking blank pages.

There is no second Chrome/profile, focus-restoring timer, persistent hiding loop or fallback to foreground page creation after protocol failure.

When the context is empty, the first target requests a new minimized window at creation. Explicit Owner-triggered login sweep failures still retain/present the human-verification page; automatic maintenance remains non-presenting.

The reported live probe is correctly limited to the existing minimized fixed Chrome and does not overclaim cold-start or universal OS focus behavior.

## Purchase-status completion / false-alarm repair

PASS.

A uniquely relocated source row in either `发给采购` or the later `采购已报价` state now satisfies the already-sent purchase-status obligation without writing the source backward.

The completion proof remains strict on:

- canonical source identity;
- exact model;
- exact quantity;
- exact importance/tier source snapshot;
- unique relocation;
- canonical expected source brand, with only the already-approved AI_BRAND_V1 fuzzy brand policy.

A durable `SAVED + STATUS_WRITE_PENDING` row may recover its local V1.2 projection to `PURCHASE_RECORDED` only after a fresh read-only proof that the same source row is already `发给采购` or `采购已报价`. The repair does not infer purchase success from Google status alone, does not call Save/Save-and-Send again, and does not create a new purchase-follow-up sending episode for an already-satisfied row.

The revised operator message also no longer instructs a downgrade from `采购已报价`.

## Shared fuzzy MPN comparison

PASS.

The shared `src/core/mpn.py` policy implements the Owner-defined comparison rule:

- NFKC and case normalization;
- remove whitespace, underscore, Unicode dash punctuation/minus and specified invisible separators;
- for cleaned targets longer than two characters, remove the last two characters to form the comparison prefix;
- the returned model must start with that prefix and may contain at most ten cleaned characters after it;
- cleaned 1–2 character targets remain exact;
- empty values never match.

Research result comparison, lower procurement-history duplicate filtering and quotation candidate filtering reuse this single policy. Exact Google source identity and purchase submission validation do not use the fuzzy policy.

The broader native-query behavior on the five non-INSO Research sources remains the approved fuzzy-search behavior from this increment; live-site recall/pagination limits remain an acknowledged external limitation rather than being presented as exhaustive.

## Final INSO search boundary

PASS.

The final Owner clarification is correctly reflected in all three lower INSO consumers:

- Research INSO;
- procurement-history duplicate check;
- V1.3 quotation read.

They now send the original complete source-model string through the INSO search boundary. Case, whitespace, underscore and dash characters are not normalized before search; HTTP paths/forms encode the original string only as transport data. The duplicate bridge no longer substitutes its canonical comparison key.

Normalization and two-tail-character removal are applied only when returned models are compared.

This final behavior supersedes the intermediate cleaned-prefix / first-literal-token retrieval commits; those intermediate behaviors are not treated as current production semantics.

## Quotation input B/L and model-difference notification

PASS.

The selected INSO raw14 remains immutable evidence. A separate derived fourteen-field payload is created only after a fresh canonical source rebind:

- B is replaced with the current exact source-model text;
- if the selected quote model is literally different, L retains its original remark and appends `报价实际型号：<actual>` on a new line;
- all other fields remain derived from the selected raw14 unchanged.

The updater rechecks the exact source model before writing/submitting; a source-model change between preparation and action fails closed as `SOURCE_CHANGED`.

Model differences enqueue one durable command to both:

- `linan229@qq.com`;
- `shawn@inso-hk.com`.

Deduplication includes inquiry id, exact source model and selected immutable quote payload. The existing outbox owns per-recipient independent retry. The message explicitly reports a detected model difference and does not claim that Apps Script or source-status settlement completed.

No new SMTP implementation/schema was introduced.

## Existing quotation safety / WGI210IT

PASS with an explicit unresolved operational item.

The existing `UPDATE_RESULT_UNCONFIRMED` durable hold for WGI210IT has not been cleared, replayed or reclassified by this increment. That is the safe behavior.

The available historical log cannot prove whether the original uncertainty occurred at the button action, popup appearance or popup/result interpretation. Therefore this review does **not** mark WGI210IT complete and does **not** authorize an automatic replay.

A future manual quotation rerun for that selected row remains a separate Owner action under the already-reviewed one-shot manual hold-bypass rules.

## Currency boundary

PASS.

The reviewed implementation/documentation does not overclaim currency support:

- Research INSO: RMB/USD;
- V1.3 quotation comparison: RMB/CNY aliases, USD and HKD;
- unsupported positive quotation currency: fail closed;
- valid zero quotation: no FX required;
- quote input retains original source currency/price.

Apps Script internal currency transformation remains UNKNOWN and was not silently inferred or expanded.

## Regression / release evidence reviewed

Final reported verification for the current production-code HEAD:

- focused: **406 passed**;
- full safe/offline: **1669 passed / 1 skipped**;
- Ruff: **PASS**;
- `git diff --check`: **PASS**;
- BuildOnly: **PASS**;
- release scan: **PASS**;
- frozen self-check: **PASS**;
- isolated idle GUI: **PASS**;
- deployed frozen / idle GUI / fixed-CDP / scan: **PASS**.

Formal deployed EXE SHA256:

`BFFEFA407375211E758EC793AF5388D4FBCEF6A7BB01E456251DFE8213EDD98C`

The report states V1.2 remained:

`340D7F7E7E818FA74DE36B138B205F5905F320406FD8D391EF860BD052529E5F`

and the final deployment preserved the production workflow DB/backups, OAuth, credentials, production/Research/SMTP configuration and fixed Chrome profile/CDP assets.

## Live-evidence boundary

This review does not convert offline/unit evidence into claims that were not observed live.

Still not proven by this review:

- a fresh real first-insert quotation ending in automatic source transition to `采购已报价`;
- Apps Script internal FX behavior;
- automatic closure of the historical WGI210IT hold.

No additional real procurement, Save-and-Send, quotation update, Apps Script or SMTP execution is required merely for this review.

## Final state

`REVIEW_REQUIRED -> REVIEWED_DONE`
