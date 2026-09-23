# 模块注册表

本文件是正式模块、Module Chat 和 Module Codex 名称的唯一来源，只定义职责与依赖方向，不记录模块内部算法。

## 注册表

| module_id | display_name | module_chat_role | module_codex_role | code_path | Public Contract / module doc |
| --- | --- | --- | --- | --- | --- |
| `core` | Core | 当前不设常驻角色 | 按具体 Task 由 CEO 分配 Architecture Codex 或 Utility Codex | `src/core/` | `docs/modules/CORE.md` |
| `sheets` | Sheets | Sheets Module Chat | Sheets Module Codex | `src/sheets/` | `docs/modules/SHEETS.md` |
| `research` | Research | Research Module Chat | Research Module Codex | `src/research/` | `docs/modules/RESEARCH.md` |
| `workflow` | Workflow | Workflow Module Chat | Workflow Module Codex | `src/workflow/` | `docs/modules/WORKFLOW.md` |
| `inso` | INSO | INSO Module Chat | INSO Module Codex | `src/inso/` | Future Version Contract：`UNKNOWN` |
| `quotation` | Quotation | Quotation Module Chat | Quotation Module Codex | `src/quotation/` | Future Version Contract：`UNKNOWN` |

测试按 `tests/<module>/` 镜像模块归属。

表中的 `* Codex` 是逻辑执行岗位，不限定实际 Coding Agent；工具可按 `AI_TEAM.md` 替换，且不改变本注册表。

## 边界地图

| module_id | responsibility | allowed dependencies | forbidden dependencies |
| --- | --- | --- | --- |
| `core` | 公共基础类型与基础设施能力，包括 Credential Provider 边界 | 标准库；已批准的通用库 | 所有业务模块；业务规则 |
| `sheets` | 单次 Google Sheets 读取、待处理查询、Record identity 和明确命令下的安全字段更新 | `core`；已批准 Google adapter | `research`、`workflow`、`inso`、`quotation`；polling、全局状态、业务规则 |
| `research` | read-only 市场调研、evidence、价格聚合和 Research 自有本地 Excel 输出；可直接使用已批准的 INSO read-only Research adapter | `core`；已批准网页/Excel/INSO read-only Research adapter | `sheets`、`workflow`、`inso`、`quotation`；Google Sheet 访问；主动采购行为 |
| `workflow` | Scheduler、全局流程状态、retry、duplicate prevention 和模块衔接 | `core`、`sheets`、`research`、`inso`、`quotation` Public Contract | 模块内部业务逻辑；直接外部 adapter |
| `inso` | Future Version 的主动采购：发布采购需求、发起采购询价和获取采购报价；不承载 Research read-only 历史价格 | `core`；未来批准的主动采购 adapter | `sheets`、`research`、`workflow`、`quotation` |
| `quotation` | Future Version 的报价规则、生成和结果输出 | `core`；显式输入 Contract | `sheets`、`research`、`workflow`、`inso`；直接外部访问 |

```text
workflow -> core, sheets, research, inso, quotation
sheets | research | inso | quotation -> core
```

跨模块调用只使用 Public Contract，不导入私有实现。注册、职责、Contract 或依赖变化均按 `AI_TEAM.md` 标记 `architecture_impact: REQUIRED`。
