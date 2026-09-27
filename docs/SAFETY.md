# 通用安全边界

CEO 兼任日常 Safety Reviewer。原则：**最低充分安全、明确边界、fail closed。**

## GREEN — Main 可自主

- Repo/代码/文档读取与普通开发。
- synthetic/fake 测试、已授权 read-only live 验证。
- 未产生真实业务副作用的临时页面/预览。
- 开发分支普通 commit/push。

## YELLOW — 需 Owner/CEO 明确授权

- 真实外部写入、删除、覆盖、发送、下单、付款或迁移。
- 打开 Production Write Gate。
- 新增/改变真实 Credential 行为。
- reset/clean/覆盖未知工作等高风险 Git 操作。

一次边界明确的授权可覆盖同一阶段的重复机械动作；范围或风险变化再升级。

## RED — 禁止

- 将 password、secret、token、cookie、Vault value 写入 Git、文档、日志、fixture 或证据文件。
- 绕过 CAPTCHA、OTP、设备验证。
- 目标不确定时猜测写入，或安全校验失败后静默降级。
- 未授权修改真实订单、客户、支付等外部记录。
- 删除未知用户工作或 force push `main`。

当前 V1.2 Production Write Gate：**CLOSED**。普通技术问题本身不是 Safety escalation。
