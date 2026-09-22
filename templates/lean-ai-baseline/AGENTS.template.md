# AGENTS.md

- 行动前确认已声明角色和当前 Task；没有角色声明时先要求直属上级补充。
- 按 `docs/AI_START_HERE.md` 只读取角色和 Task 必需的最小上下文。
- 在已批准 Scope 内按 `FAST_V1` 自主、连续执行。
- 遵守 `docs/BOUNDARIES.md`；不得泄露 Secret 或破坏真实数据。
- 不擅自扩大产品范围、模块职责或跨模块 Contract；架构影响必须升级。
- 完成后按 `docs/TASK_PROTOCOL.md` 汇报，不自行开始后续 Task。
- 无法可靠继续时输出 `# ⚠️ HANDOFF_REQUIRED` 并停止扩大工作。
