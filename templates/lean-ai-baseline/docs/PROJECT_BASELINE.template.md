# 项目管理基线

只记录长期有效的项目规则与稳定锚点。

## 核心规则

- 业务结果优先；过程说明不能替代交付。
- 每条 CEO 指令必须对应当前未完成验收项，并指向本轮可验证进展。
- 一轮执行没有实质推进时，CEO 在下一条指令前必须重读 `PROJECT_BASELINE.md`、`CURRENT_TASK.md`、`AI_WORKFLOW.md`，纠正偏离后再继续。
- 简单优先；不为未来假设增加框架、流程、角色或文档。
- Git + canonical docs 是长期事实源；聊天不是功能载体。
- 同类问题再次出现时，优先修共享代码/contract/回归测试。
- Owner 不参与普通调试或消息搬运。
- CEO 给 Main Programmer 的任务只写业务目标、验收、必读文档和 Safety 边界；不写数百行操作手册。

## 职责

- CEO：治理、产品/业务基线、总体架构边界、Safety Gate。
- Main Programmer：`CURRENT_TASK.md`、代码、测试、实现侧 module/runtime 文档。

## 稳定锚点

- `<CURRENT_STABLE_BASELINE>`
