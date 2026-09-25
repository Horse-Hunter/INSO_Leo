# 安全边界

本文件是安全规则的 canonical owner。安全同样遵循“简单优先、最低充分”：只为能够具体说明的高影响事故增加必要保护，优先精确校验、窄权限和 fail closed；没有明确故障场景的额外 hardening 默认是 recommendation，不得不断叠加 gate、抽象或流程。目标、身份或权限不确定时 fail closed。新增高风险能力由 CEO 按需临时创建 Security Specialist，完成最小必要边界和 tests 后退出；Main Programmer 可正常调用已批准且稳定的安全 Public API。

## GREEN — 可自主执行

- 在当前阶段范围内读取 Repo、文档、代码和 Git；开发普通实现并用 synthetic/fake 数据测试。
- 对已批准来源做 read-only 浏览和读取，生成安全的本地输出。
- 正常 `git status`、`diff`、`log`、开发 branch commit/push。

## YELLOW — 需要明确的 Owner 授权

- 真实外部写入、删除、覆盖或迁移，尤其真实 Sheet、ERP、用户文件或生产数据。
- 提交表单、发送消息、下单、报价提交、支付以及其他外部高风险副作用。
- 新增或改变 Credential 行为；可能影响用户工作的高风险 Git 操作。

一次有边界的 Owner 授权可覆盖当前阶段明确限定的重复机械操作，不必逐条询问；目标、范围、身份或风险变化才重新授权。新增此类能力只建立与实际风险直接对应的最低必要保护，不为理论完备性增加额外层。调用已批准、稳定的安全 API 不等于重新新增能力；调用时仍遵守该 API 的授权与目标校验。

## RED — 禁止

- 将真实 password、secret、token、cookie、vault value 或客户数据写入 Git、文档、日志、fixture、evidence、截图或示例。
- 绕过 CAPTCHA、OTP、设备验证或其他安全挑战。
- 目标不确定时猜测写入；安全检查失败后静默降级。
- 删除未知 untracked 文件、覆盖未知用户工作、以 `reset --hard` 或 `clean -fd` 清掉未知内容、force push `main`、删除未知 branch/worktree。
- 未经授权修改真实订单、支付、客户记录或其他外部系统。

## 系统规则

- **Google Sheets：**读取可积极进行；真实写入前必须唯一重定位并校验 Record，只更新目标字段，冲突时不写入。具体 V1 Contract 见 `modules/SHEETS.md`。
- **网站/浏览器：**允许已授权登录、搜索和只读浏览；提交、发送、购买、删除、修改、付款属于 YELLOW；安全挑战交给 Owner 完成。
- **本地文件：**runtime/data 与源码分离；不删除、移动或覆盖未知文件。
- **Git：**常规开发 branch commit/push 属于 GREEN；merge、rebase 或 dirty-tree switching 可能影响他人工作时须审慎并获得相应授权。
- **Credential：**仅在已授权流程调用 Credential Provider；不打印、复制、持久化或提交返回的凭据。具体 Provider Contract 见 `modules/CORE.md`。
