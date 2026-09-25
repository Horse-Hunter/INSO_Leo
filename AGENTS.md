# Agent 入口

- **全局默认：简单优先。** 先用能满足当前目标的最简单方案；没有已发生的需求、故障或明确风险，不提前增加抽象、层级、状态、框架、流程、文档或安全机制。
- 项目治理基线先读 `docs/PROJECT_BASELINE.md`。团队规则见 `docs/AI_WORKFLOW.md`，安全规则见 `docs/SAFETY.md`，答复模板见 `docs/REPORTING.md`。
- 上述治理文档由 CEO 维护；Main Programmer 除非 CEO 明确要求，不修改这些文件。
- Main Programmer 维护实现相关事实：`docs/PRODUCT_BASELINE.md`、`docs/MODULE_INDEX.md`、`docs/CURRENT_TASK.md`、相关 module/runtime 文档与代码。
- 开始任务时只读取当前任务真正需要的文档和代码，不扫描整个 Repo。已知事实从 Git 与 canonical docs 恢复；缺证据写 `UNKNOWN`，不猜。
- 不依赖隐藏聊天上下文。Git 与 canonical docs 是共享事实源。
