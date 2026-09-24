# 安全边界

目标、身份或权限不确定时 fail closed。新增高风险能力由 CEO 临时创建 Security Specialist，完成安全边界、Public API 和 tests 后退出；已批准且稳定的安全 API 可由 Main Programmer 正常调用。

## GREEN — 自主执行

- 读取 Repo 和当前阶段相关资料，在 Scope 内开发、测试、用 synthetic/fake 数据验证。
- 对已批准来源 read-only 浏览与读取，生成安全本地输出。
- 正常 `git status`、`diff`、`log`、开发 branch commit/push。

## YELLOW — 需要明确 Owner 授权

- 真实外部写入、删除、覆盖、迁移、用户数据修改。
- 表单提交、主动消息、订单/报价提交、采购、付款。
- 新增或改变 Credential 行为；可能影响用户工作的高风险 Git 操作。

一次 bounded Owner authorization 可覆盖当前阶段明确限定的重复机械操作，不需逐条再问；目标、范围、身份或风险变化时重新授权。调用已批准的稳定安全 API 仍要遵守其目标校验和授权边界。

## RED — 禁止

- 泄露或提交 secret、token、cookie、vault value、客户数据到 Git、文档、log、fixture、evidence 或截图。
- 绕过 CAPTCHA、OTP、设备验证或其他安全挑战。
- 目标不确定时猜测真实写入，或安全检查失败后 silent fallback。
- 删除未知 untracked 内容、覆盖未知用户工作、`reset --hard`/`clean -fd` 清除未知内容、force push 主分支、删除未知 branch/worktree。
- 未经授权执行真实订单、支付、发送或其他生产副作用。

## 项目规则

- 外部写入前唯一定位目标、重读关键状态、只改必要字段；冲突则不写。
- 浏览器可已授权登录、搜索、只读访问；真实提交属于 YELLOW，安全挑战由 Owner 完成。
- runtime/data 与源码、Git 分离；不移动或覆盖未知文件。
- 凭据仅通过项目已批准的 Provider 使用，不打印、复制、持久化或提交返回值。
- 正常开发 branch commit/push 属于 GREEN；可能影响他人工作的 merge/rebase/dirty switching 需谨慎并取得相应授权。

启用模板时仅添加经证据确认的项目专项规则，不削弱以上最低边界。
