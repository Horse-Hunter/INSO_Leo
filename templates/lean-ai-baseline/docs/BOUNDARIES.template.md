# 安全边界

本文件是 canonical 安全规则。一个 Task 的授权覆盖其中明确限定的动作；目标、身份或权限不确定时必须 fail closed。

## GREEN — 可自主执行

- 读取 Repo、文档、代码和 Git 历史。
- 修改 Task Scope 内代码；使用 synthetic/fake 数据测试。
- 对已批准来源进行 read-only 访问并生成安全本地输出。
- 正常执行 `git status`、`diff`、`log`、`commit` 和 Task branch push。

## YELLOW — 需要明确授权

- 修改真实外部系统或生产数据。
- 首次或此前未授权的外部写操作。
- 删除、移动、覆盖真实用户文件/数据，或进行大规模迁移。
- 提交表单、发送客户消息、创建订单或付款。
- 改变 Credential 行为或执行高风险 Git 操作。

Task 已明确授权有边界的 YELLOW 动作后，不必逐步重复确认；目标或风险变化时重新确认。

## RED — 禁止

- 将真实 password、secret、token、cookie、vault value 或 customer data 写入 Git、Task、log、fixture、evidence、截图或示例。
- 绕过 CAPTCHA、OTP、设备验证或其他安全挑战。
- 目标不确定时猜测写入，或安全检查失败后 silent fallback。
- 删除未知 untracked 文件；用 `git reset --hard` 覆盖未知工作；运行 `git clean -fd`；force push 主分支；删除未知 branch/worktree。
- 未经授权修改真实订单、支付、客户记录或其他系统。

## 系统专项规则

- **外部数据/API：**写入前唯一定位并校验目标，只更新必要字段，冲突时不写。
- **网站/浏览器：**允许浏览、授权登录、搜索和读取；提交/发送/购买/删除/修改/付款属于 YELLOW。
- **本地文件：**runtime/data 与源码分离；不删除、移动或覆盖未知文件。
- **Git：**检查、commit、正常 Task branch push 属于 GREEN；merge、rebase、dirty-tree switching 可能影响用户工作时需授权。
- **Credential：**可在已授权流程中调用 Credential Provider；不得打印、复制、持久化或提交返回的凭据。

启用前按项目补充真实系统专项规则，但不得降低以上最低边界。
