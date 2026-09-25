# Agent 入口

- **全局默认：简单优先。** 先用满足当前目标的最简单方案；没有当前需求、已发生问题或明确高影响风险，不提前增加复杂度。
- 项目治理基线先读 `docs/PROJECT_BASELINE.md`；团队规则见 `docs/AI_WORKFLOW.md`，安全见 `docs/SAFETY.md`，答复模板见 `docs/REPORTING.md`。
- 上述治理文档由 CEO 维护；Main Programmer 除非 CEO 明确要求，不修改。
- Main Programmer 维护实现侧事实：`PRODUCT_BASELINE.md`、`MODULE_INDEX.md`、`CURRENT_TASK.md`、module/runtime 文档和代码。
- 只读取当前任务真正需要的文档和代码；已知事实从 Git 与 canonical docs 恢复，缺证据写 `UNKNOWN`，不猜。
- Git + canonical docs 是共享事实源，不依赖隐藏聊天上下文。
