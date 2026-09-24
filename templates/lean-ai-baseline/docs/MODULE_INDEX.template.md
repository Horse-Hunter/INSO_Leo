# 模块注册表

软件模块化与 AI 团队结构无关。本文件只登记当前实际模块的职责、Public Contract 入口和依赖方向；普通实现变化由 Main Programmer 维护，模块职责或跨模块 Public Contract 边界变化升级 CEO。不提前建立无用模块。

| module_id | display_name | code_path | responsibility | Public Contract / module doc | allowed dependencies | forbidden dependencies | status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `<MODULE_ID>` | `<DISPLAY_NAME>` | `src/<MODULE_ID>/` | `<ONE_SENTENCE>` | `docs/modules/<MODULE_DOC>.md` | `<ALLOWED>` | `<FORBIDDEN>` | `<CURRENT_OR_FUTURE>` |

测试建议放在 `tests/<MODULE_ID>/`。跨模块调用只用 Public Contract，不导入私有实现。若项目无需某列，可简化表格；职责和依赖事实须保持可查。
