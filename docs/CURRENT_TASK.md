# Current Task

Status: READY_FOR_CEO_REVIEW

Goal: 修复 V1 真实运行中暴露的后台运行、Findchips 币种换算、价格源型号匹配与 LCSC 可用性问题，使 V1 能稳定无感执行并生成可信的 `调研价格.xlsx`。

Business Outcome: Owner 在一次性完成必要授权/登录后，日常运行 V1 不再弹 Google OAuth 授权页或可见浏览器窗口；价格按网站实际币种正确换算为 RMB；常见分隔符差异不会造成误判无结果；LCSC 恢复为可用价格源。

Acceptance:
- Google Sheets OAuth token 安全持久化/刷新：首次授权允许人工完成；后续正常运行不重复弹授权页。Token/Secret 不进 Git、不打印。
- Research 正常运行不要求可见浏览器窗口；保留 CAPTCHA/OTP/device verification fail-closed，首次/失效登录允许 Owner 人工介入。
- Findchips 每个价格 tier 必须保留并识别页面真实币种（USD/HKD），跨币种比较前分别换算 RMB。增加 URAM3T21 回归测试：页面可见 HK$1,855.5900 与 USD $227.5800/$225.7000 时不得混用汇率或把币种识别错；有库存与无库存候选仍按现有 V1 规则分开。
- 价格源 MPN 匹配新 Owner Decision：比较前对 target/observed 去除连字符 `-` 与所有空白并忽略大小写；规范化后接受完全匹配，或 observed = 完整 target + 最多 6 个尾随字符。不得因为 `-`/空格差异判为无结果；不得引入无界 Levenshtein/任意内部字符猜测。
- 将该价格源匹配规则统一应用于 Findchips / HQEW / LCSC / Bom.Ai；IC.net 规则保持原有严格匹配，除非实际证据证明也需要改变并升级 CEO。
- 定位 LCSC 当前 SOURCE_UNAVAILABLE/“暂时不可用”的真实 failure_code 与页面行为，修复 acquisition/parser/session 路径；真实 smoke 中 LCSC 对有效型号能返回业务结果或真实无结果，不得把技术失败伪装成无结果。
- 增加/更新单元测试和针对上述四项的回归测试；完成一次真实 V1 smoke，检查 Excel 中原始来源列、市场最低参考价和预估总价。
- 不改变 V1 其他已确认业务规则；不把 live smoke 变成 production daemon；不增加新的真实写入副作用。

Constraints:
- V1 其余已确认 Contract 保持有效。
- Secret、OAuth refresh token、cookie、浏览器 profile 不得提交 Git。
- 不绕过 CAPTCHA / OTP / device verification。
- 先复现和记录 Findchips 1059.68 的具体计算链（raw price/currency/fx/normalized）再修，禁止凭猜测硬编码。
- LCSC 必须基于当前真实网站行为修复，不用伪 fixture 掩盖 live failure。
- 保护原始 dirty checkout 与历史 research-v1-production-runtime-buddy；开发从最新 main 建独立 clean branch/worktree。

Done:
- CEO 已根据 Owner 真实运行反馈定义本阶段与 Acceptance。
- Owner 已明确批准新的价格源 MPN 规范化/<=6 suffix 规则。
- Sheets OAuth 首次授权后将 refresh grant 以 Windows CurrentUser DPAPI 加密保存到仓库外；第二次真实构建 Sheets service 未调用授权流程。
- Findchips 现按逐档可见币种和价格采集、分别换算 RMB 后比较。复核发现先前 `1059.68` 来自专用 CDP Chrome 旧 Cookie 会话返回的 Avnet USD 157.9875（无库存），并非 Owner 截图所见报价。同一 URL 不带 Cookie 时返回 DigiKey HKD 1855.5900（库存 8）和 Mouser USD 227.5800/225.7000（库存 0）。Findchips CDP 查询已改用临时无 Cookie browser context，关闭后不留会话状态。
- 四个网页价格源统一使用去连字符/空白、忽略大小写、最多 6 个尾随字符的匹配；IC.net 严格规则保持不变。
- LCSC 真实失败码 `AUTHENTICATED_SESSION_REQUIRED`；页面先到已登录 JLC passport，进入搜索页后合作库存卡片无“更新时间”使原 parser 报 `COOPERATION_CARD_UNPARSEABLE`。会话与卡片解析已修复，URAM3T21 真实返回库存 2、CNY 1870.683574。
- 后台 CDP 新标签页不激活浏览器窗口；最终 smoke 后专用 Chrome 仍为 minimized。
- 修正后只读 V1 live smoke 写入新 Git 忽略目录 `runtime/followup_findchips_0924/`：入队 3、二次 poll 0、处理 3、Excel 业务行 2。URAM3T21 的 Findchips 列为 1586.74（HKD 有库存）/1513.86（USD 无库存），立创 1870.68，市场最低参考价 1586.74，预估订单总价 31734.89。换算使用 ECB 2026-09-23 HKD/RMB 0.8551158581547605747100753022、USD/RMB 6.707387608447988782753483481。Google OAuth 全程未再提示授权。
- Full pytest 312 passed / 10 skipped；ruff、secret scan、git diff check 通过。

Current: Owner 指出 Findchips 实际页面与 CDP 旧会话不符；已修正并重新完成真实 smoke，等待 CEO Final Review。

Next: CEO Final Review；由 CEO 决定是否进入 `main`。

Blockers: NONE

Owner Decisions:
- 正常稳态运行目标为后台无感；一次性首次授权/登录或安全挑战可人工完成，但后续不得每次弹窗。
- 价格必须先识别页面真实币种，再按对应汇率转 RMB 后比较。
- 价格源 MPN 比较前去除 `-` 与所有空白、忽略大小写；规范化后 suffix 最多 6 个字符（含）。
- 本阶段必须修复 LCSC，而不是接受“暂时不可用”。

Branch: fix/v1-live-runtime-stability

Last Good Commit: 7f2bcae
