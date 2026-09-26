# 通用安全边界

本文件由 CEO 维护，只定义项目级通用安全规则。原则：**最低充分安全**。只为具体高影响事故增加必要保护；没有明确风险场景的额外 hardening 默认不是 blocker。

日常安全 Review 由 CEO 兼任；只有首次真实高风险写入、不可逆操作或 CEO 对边界不确定时，才临时启用独立 Security Specialist。

## GREEN

- Repo / 文档 / 代码读取。
- synthetic / fake 测试。
- 已授权的只读操作。
- 普通开发 branch commit/push。

## YELLOW

需要明确 Owner 授权：真实外部写入/删除/覆盖/迁移；提交/发送/下单/付款等真实副作用；新增或改变 Credential 行为；可能影响用户工作的高风险 Git 操作。
一次明确且有边界的授权可覆盖同一阶段内的重复机械操作；目标、范围或风险变化时再升级。

## RED

- 将 password、secret、token、cookie、vault value 等写入 Git、文档、日志、fixture 或证据文件。
- 绕过 CAPTCHA、OTP、设备验证或其他安全挑战。
- 目标不确定时猜测写入，或安全检查失败后静默降级。
- 未经授权修改真实订单、客户记录、支付或其他外部系统。
- 删除未知用户工作、强制清理未知文件、force push 主分支。

安全机制本身也保持简单；能用一个明确校验解决的，不增加一套框架。
