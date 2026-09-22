# 模块注册表

本文件是正式模块、Module Chat 和 Module Codex 名称的唯一来源，只定义职责与依赖方向，不记录内部算法。

## 注册表

复制下方行，为每个正式模块填写一次：

| module_id | display_name | module_chat_role | module_codex_role | code_path | Public Contract / module doc |
| --- | --- | --- | --- | --- | --- |
| `<MODULE_ID>` | `<DISPLAY_NAME>` | `<MODULE_CHAT_ROLE 或 当前不设常驻角色>` | `<MODULE_CODEX_ROLE 或按 Task 分配>` | `src/<MODULE_ID>/` | `docs/modules/<MODULE_DOC>.md` |

测试路径建议按 `tests/<MODULE_ID>/` 镜像模块归属。存在代码模块不等于必须创建常驻 AI 机构。

## 边界地图

| module_id | responsibility | allowed dependencies | forbidden dependencies |
| --- | --- | --- | --- |
| `<MODULE_ID>` | `<ONE_SENTENCE_RESPONSIBILITY>` | `<ALLOWED>` | `<FORBIDDEN>` |

## 依赖方向

```text
<CALLER_MODULE> -> <CALLEE_PUBLIC_CONTRACT>
```

跨模块调用只使用 Public Contract，不导入私有实现。注册、职责、Contract 或依赖变化标记 `architecture_impact: REQUIRED`。
