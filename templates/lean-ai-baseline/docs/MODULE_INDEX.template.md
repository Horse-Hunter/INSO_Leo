# 模块注册表

本文件由 CEO/架构角色维护，只登记当前模块职责、Public Contract 边界和依赖方向；普通内部实现变化不写入。

| module | code_path | responsibility | public contract | allowed dependencies |
| --- | --- | --- | --- | --- |
| `<MODULE>` | `src/<MODULE>/` | `<ONE_SENTENCE>` | `docs/modules/<MODULE>.md` | `<ALLOWED>` |

模块职责、依赖方向或跨模块 Public Contract 改变时由 CEO 更新。测试默认放在 `tests/<MODULE>/`。
