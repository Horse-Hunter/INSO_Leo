# Agent 入口

- 简单实现，目标优先。
- 新窗口先读 `docs/PROJECT_BASELINE.md`、`docs/CURRENT_TASK.md`，再按任务读取对应 module doc；真实外部写入再读 `docs/SAFETY.md`。
- Git、代码、测试和 canonical docs 是事实源；不依赖旧聊天。
- CEO 负责业务目标、验收、治理、架构边界和 Safety Gate；Main Programmer 负责实现、测试、修复、live 验收、commit/push。
- CEO 给 Main Programmer 的任务只包含：业务目标、验收、必读事实源、Safety 边界。禁止重复背景和数百行流程式 prompt。
- 普通技术问题由 Main Programmer 解决到 DONE；重复问题收敛为共享代码/contract/回归测试。
- Owner 不参与普通调试或消息搬运。
