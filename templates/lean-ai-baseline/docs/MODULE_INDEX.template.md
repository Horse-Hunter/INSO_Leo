# 模块注册表

本文件由 CEO/架构角色维护，只登记当前模块职责、Public Contract 边界和依赖方向；普通内部实现变化不写入。

| module | code_path | responsibility | public contract | allowed dependencies |
| --- | --- | --- | --- | --- |
| `<MODULE>` | `src/<MODULE>/` | `<ONE_SENTENCE>` | `docs/modules/<MODULE>.md` | `<ALLOWED>` |

规则：

- 一个稳定职责只有一个 canonical owner / production path。
- 新需求优先扩展现有模块和 Public Contract；不得为同一职责新增平行模块/adapter/runtime。
- 临时 discovery / verification helper 必须在交付前收敛回 canonical path。
- 如果现有模块边界确实无法承载需求，先记录不可复用证据，再由 CEO 决定是否调整职责。
- 模块职责、依赖方向或跨模块 Public Contract 改变时由 CEO 更新。
- 测试默认放在 `tests/<MODULE>/`。
