# 模块注册表

本文件只登记软件模块职责、Public Contract 与依赖方向，不定义 AI 岗位，也不记录模块内部算法。Main Programmer 可维护普通新增或实现变化；模块职责或跨模块 Public Contract 边界变化须升级 CEO。

## 注册表

| module_id | display_name | code_path | Public Contract / module doc | status |
| --- | --- | --- | --- | --- |
| `core` | Core | `src/core/` | `docs/modules/CORE.md` | V1 |
| `sheets` | Sheets | `src/sheets/` | `docs/modules/SHEETS.md` | V1 |
| `research` | Research | `src/research/` | `docs/modules/RESEARCH.md` | V1 |
| `workflow` | Workflow | `src/workflow/` | `docs/modules/WORKFLOW.md` | V1 |
| `inso` | INSO | `src/inso/` | Future Version Contract：`UNKNOWN` | Future Version |
| `quotation` | Quotation | `src/quotation/` | Future Version Contract：`UNKNOWN` | Future Version |

测试按 `tests/<module>/` 镜像模块归属。


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

跨模块调用只使用 Public Contract，不导入私有实现。普通注册和实现变化由 Main Programmer 维护；模块职责或有跨模块影响的 Public Contract、依赖边界变化须升级 CEO，详见 `AI_WORKFLOW.md`。
