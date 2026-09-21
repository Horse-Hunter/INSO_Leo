# AI Team

## 角色层级

- **Human Owner** → 最终业务决策人。
- **Architecture / CEO Chat** → 项目总指挥和总架构；负责模块划分、跨模块 Contract、架构 Gate、公共基础设施和总体协调。架构发生变化时，负责要求 Architecture Codex 同步 Repo。
- **Architecture Codex** → 按 Architecture Chat 已确认的决定修改架构相关 Repo 文件；不自行决定新的项目架构。
- **Requirements Codex** → 将 Human Owner 的业务描述整理成模块需求文档；不负责最终架构决策或业务实现。
- **Utility Codex** → 处理密码箱、辅助工具及其他项目杂项；涉及公共架构时必须回到 Architecture Chat Review。
- **Module Chats** → Research、Sheets、Workflow、INSO、Quotation。每个 Module Chat 是该模块的长期 Coordinator / Product Analyst / Reviewer，管理本模块需求、Task 和 Review；跨模块变化提交 Architecture Chat 决策。
- **Task Codex** → 由对应 Module Chat 指挥；一次只执行一个明确 Task Packet；不自行扩大 Scope 或修改跨模块架构。

## 决策原则

- Human Owner → 最终业务决策。
- Architecture Chat → 项目架构与跨模块决策。
- Module Chat → 模块内部设计决策。
- Codex → 执行已经确认的 Task，不作为架构决策者。

## Repo / Chat 事实优先级

```text
当前 GitHub main 的正式项目事实
>
已确认但尚待 Repo 固化的 Architecture Decision
>
Chat 历史摘要或推断
```

架构变更确认后，应尽快同步 Repo，避免长期依赖 Chat 上下文。

## Chat 交接

当长期 Architecture Chat 或 Module Chat 因上下文过长不适合继续工作时，应先生成交接提示词，再由新 Chat：

1. 读取 GitHub 当前事实。
2. 读取交接摘要。
3. 继续原职责。

不要仅依赖旧 Chat 的历史上下文。

## Communication Discipline

默认使用精简可复制模式；不重复已确认背景；Draft/Review 优先输出 Delta；接近单次复制不便的长度时主动拆 Part 1/Part 2；给 CEO Review 优先纯文字并突出结论、变化、`UNKNOWN`、需决策事项和下一步。
