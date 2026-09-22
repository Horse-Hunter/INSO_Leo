# AGENTS.md

- 行动前确认已声明的角色和当前 Task；未声明角色时，要求直属上级先声明。
- 按 `docs/AI_START_HERE.md` 路由，只读取该角色与 Task 必需的最小上下文。
- 在已批准 Scope 内按 `FAST_V1` 自主、连续执行。
- 遵守 `docs/BOUNDARIES.md`；不得泄露 Secret 或破坏真实数据。
- 不擅自扩大产品范围、模块职责或跨模块 Contract；架构影响必须升级。
- 完成后按 `docs/TASK_PROTOCOL.md` 汇报；不得自行开始后续 Task。
- 上下文退化到无法可靠工作时，输出 `# ⚠️ HANDOFF_REQUIRED` 并停止扩大工作。
