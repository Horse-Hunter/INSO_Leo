# AI 从这里开始

本文件只负责把角色路由到最小上下文。禁止为了“稳妥”而全量读取 Markdown。正式角色名和模块名分别以 `AI_TEAM.md`、`MODULE_INDEX.md` 为准。

## 阅读矩阵

| 角色 | 默认读取 | 仅在需要时读取 |
| --- | --- | --- |
| Human Owner | 无强制要求 | 所请求决策的证据 |
| CEO / Architecture Chat | `AI_TEAM.md`、`BOUNDARIES.md`、`PRODUCT_BASELINE.md`、`MODULE_INDEX.md` | 相关 module doc、Git 当前事实 |
| Architecture Codex | `AGENTS.md`、当前 Task、`AI_TEAM.md`、本 Task 直接影响的架构文档 | `BOUNDARIES.md`、`MODULE_INDEX.md` |
| Requirements / Browser-Recon Codex | `AI_TEAM.md`、`BOUNDARIES.md`、`PRODUCT_BASELINE.md`、Owner 当前需求 | 相关 module doc、真实流程或 Repo 证据 |
| Utility Codex | `AGENTS.md`、当前 Task、直接相关文件 | `BOUNDARIES.md`、受影响 module doc |
| Module Chat | `AI_TEAM.md`、`TASK_PROTOCOL.md`、本模块 module doc | `BOUNDARIES.md`、`MODULE_INDEX.md`、相关 Public Contract |
| Module Codex | `AGENTS.md`、当前 Task、本模块 module doc、Task 相关代码 | 产品基线、模块注册表、其他 module docs、历史 Tasks |

## Canonical 归属

| 事实 | 唯一主要文档 |
| --- | --- |
| AI 组织、权限、升级、Handoff | `AI_TEAM.md` |
| Task 格式、执行、Review、汇报 | `TASK_PROTOCOL.md` |
| 安全与真实副作用授权 | `BOUNDARIES.md` |
| 模块名称、职责、依赖 | `MODULE_INDEX.md` |
| 产品范围、跨模块业务事实 | `PRODUCT_BASELINE.md` |
| 单一模块 Public Contract 与长期规则 | `modules/<MODULE>.md` |
| 当前实现 | Git `main`、当前 Task、代码、测试、Module Final Report |

`tasks/` 是审计历史，不是默认上下文。本地 AI1/AI2/AI3 和旧 Word 文件只作参考，不是 canonical 事实。
