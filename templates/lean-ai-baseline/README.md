# 精简 AI 团队项目模板

目标：用最少的长期规则和最少的角色启动一个可持续维护的 AI 开发项目。默认原则是**简单优先**：没有当前需求、已发生问题或明确高影响风险，不提前增加框架、层级、流程、文档或安全机制。

## 启动

1. 复制 `AGENTS.template.md` 为根目录 `AGENTS.md`。
2. 将 `docs/*.template.md` 去掉 `.template` 后复制到项目 `docs/`。
3. CEO 只填写治理类文档：`PROJECT_BASELINE.md`、`AI_WORKFLOW.md`、`SAFETY.md`、`REPORTING.md`。
4. Main Programmer 按真实项目填写 `PRODUCT_BASELINE.md`、`MODULE_INDEX.md`、`CURRENT_TASK.md` 和必要 module docs。
5. 不为模板完整性保留无用占位；没有证据的事实写 `UNKNOWN`。

## 文档归属

| 类型 | Owner | 文件 |
| --- | --- | --- |
| 项目规则、总体架构原则、大版本概述 | CEO | `PROJECT_BASELINE.md` |
| 团队运行和职责 | CEO | `AI_WORKFLOW.md` |
| 通用安全边界 | CEO | `SAFETY.md` |
| 通用答复格式 | CEO | `REPORTING.md` |
| Agent 入口 | CEO | `AGENTS.md` |
| 产品/业务长期事实 | Main Programmer | `PRODUCT_BASELINE.md` |
| 模块职责和 Public Contract | Main Programmer | `MODULE_INDEX.md`、`modules/` |
| 当前阶段 | Main Programmer | `CURRENT_TASK.md` |
| 实现、验证、历史 | 代码/Git | 代码、测试、提交 |

治理文档不记录业务细节、模块流程、当前进度、任务分工、交接或开发日志。实现侧文档不复制治理规则。每项事实只选一个主文件。
