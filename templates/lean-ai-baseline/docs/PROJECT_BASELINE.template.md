# 项目管理基线

本文件由 CEO 维护，只记录项目级长期规则、总体架构原则和大版本概述。不记录业务/模块细节、当前进度、任务分工、交接或实现过程。

## 核心规则

- **简单优先。** 能简单解决就不复杂解决。
- 只为当前已确认需求、已发生问题或明确高影响风险增加复杂度。
- 不为“以后可能需要”、理论完整或架构漂亮提前增加层级、框架、状态、依赖、流程或文档。
- 两个方案都满足目标时，选概念更少、改动更小、路径更直接的方案。
- 发现方案持续衍生新机制时，先删减、合并或推迟。

## 总体架构原则

- 软件保持模块化，但不追求过度分层。
- 跨边界使用明确 Public Contract；内部实现保持自由。
- 稳定能力优先兼容；新增版本优先 additive / seam-based 改动。
- 没有真实重复或维护痛点，不为抽象而抽象。
- 治理文档与业务/模块/任务文档分离。

## 文档边界

CEO 维护：`PROJECT_BASELINE.md`、`AI_WORKFLOW.md`、`SAFETY.md`、`REPORTING.md`、`AGENTS.md`。
Main Programmer 维护：`PRODUCT_BASELINE.md`、`MODULE_INDEX.md`、module docs、`CURRENT_TASK.md` 和 runtime/release/implementation docs。

## 大版本概述

- `main`：当前稳定基线。
- feature branch：开发中，不视为稳定基线。
- 稳定 release：形成后只补“一行版本 + 一句话用途”。

不在这里记录开发进度。
