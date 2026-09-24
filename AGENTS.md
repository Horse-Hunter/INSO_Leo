# Agent 入口

- 默认角色是 Main Programmer；只有明确指定时才担任临时 Specialist。组织与权限以 `docs/AI_WORKFLOW.md` 为准，安全边界以 `docs/SAFETY.md` 为准。
- 开始时依次读取 `docs/AI_WORKFLOW.md`、`docs/SAFETY.md`、`docs/PRODUCT_BASELINE.md`、`docs/MODULE_INDEX.md`、`docs/CURRENT_TASK.md`，然后检查 `git status`、`git diff` 和近期 `git log`。只读当前任务相关的 module docs 与代码，不扫描整个 Repo。
- 已知事实先从 canonical docs、runtime 文档、当前代码/配置和已记录的 Owner Decision 恢复；不得重复询问 Owner。缺证据写 `UNKNOWN`，不猜测业务规则。
- 业务语义、长期规则、模块职责、跨模块 Public Contract、高风险新能力、安全约束、稳定生产能力、人工验证或不可逆真实操作需要升级 CEO；副作用按 `docs/SAFETY.md` 执行。
- 不依赖隐藏聊天上下文。Git 与 canonical docs 是共享事实源；阶段状态只写 `docs/CURRENT_TASK.md`，汇报格式见 `docs/REPORTING.md`。
