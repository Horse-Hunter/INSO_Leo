# Agent 入口

- **简单优先。** 只做满足当前目标的最小改动；不为未来假设增加框架、层级、流程或文档。
- 日常启动默认只读：`AGENTS.md`、`docs/PROJECT_BASELINE.md`、`docs/CURRENT_TASK.md`；其他文档按任务需要再读。
- Git 与 canonical docs 是共享事实源；旧聊天和已被新结论取代的记录不作为当前事实。
- CEO 兼任架构与 Safety，维护项目级治理/架构文档；Main Programmer 维护 `CURRENT_TASK.md`、代码、测试和实现侧局部文档。
- Main Programmer 默认自行完成一个完整阶段：诊断 → 实现 → 测试 → 修复 → live 验收 → commit/push，再直接向 Owner 汇报。
- 普通技术问题不得中途请求 CEO Review。仅业务规则变化、真实外部写入/Safety Gate、CAPTCHA/OTP/设备验证、破坏性 Git、重大跨模块架构变化或 release/merge 节点升级 CEO。
- 不扫描整个 Repo；缺证据写 `UNKNOWN`，不猜。
