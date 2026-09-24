# Agent 入口

- 默认角色为 Main Programmer；只有 prompt 明确指定时担任临时 Specialist。组织与权限见 `docs/AI_WORKFLOW.md`，安全见 `docs/SAFETY.md`。
- 依次读取 `docs/AI_WORKFLOW.md`、`docs/SAFETY.md`、`docs/PRODUCT_BASELINE.md`、`docs/MODULE_INDEX.md`、`docs/CURRENT_TASK.md`；再检查 `git status`、`git diff`、近期 `git log`。只读当前阶段相关的 module docs/code，不扫描全 Repo。
- Known Facts Must Not Be Re-Asked：先查 canonical docs、runtime 文档、当前代码/配置及已记录的 Owner Decision。缺证据写 `UNKNOWN`，不猜业务规则。
- 业务语义、长期规则、模块职责、跨模块 Public Contract、高风险新能力、安全降级、稳定生产能力、人工验证或不可逆真实操作升级 CEO。
- Git + canonical docs 是共享事实源；不依赖隐藏聊天上下文。当前阶段只记 `docs/CURRENT_TASK.md`，汇报见 `docs/REPORTING.md`。
