# Lean AI Baseline 通用模板

这套模板用于为新项目建立精简、可持续的 Human + Chat + Coding Executor + Git 协作基线。它只提供治理方法和文档结构，不包含任何具体项目事实，也不绑定厂商或模型。

## 目录

```text
lean-ai-baseline/
├─ AGENTS.template.md
├─ docs/
│  ├─ AI_START_HERE.template.md
│  ├─ AI_TEAM.template.md
│  ├─ TASK_PROTOCOL.template.md
│  ├─ BOUNDARIES.template.md
│  ├─ MODULE_INDEX.template.md
│  ├─ PRODUCT_BASELINE.template.md
│  └─ modules/MODULE.template.md
└─ prompts/
   ├─ ROLE_BOOTSTRAP.template.md
   └─ REPORTS_HANDOFF.template.md
```

## 每个文件解决什么问题

| 文件 | 用途 |
| --- | --- |
| `AGENTS.template.md` | Coding Executor 最低硬规则 |
| `AI_START_HERE.template.md` | 按角色路由最小上下文 |
| `AI_TEAM.template.md` | 组织、权限、升级和 Handoff |
| `TASK_PROTOCOL.template.md` | 阶段级 Task、执行、Review 和完成标准 |
| `BOUNDARIES.template.md` | 真实副作用与安全授权 |
| `MODULE_INDEX.template.md` | 正式模块/角色名称、职责与依赖 |
| `PRODUCT_BASELINE.template.md` | 产品范围和跨模块业务事实 |
| `modules/MODULE.template.md` | 单模块 Public Contract 和长期规则 |
| `prompts/*` | 新窗口身份声明、汇报、提问与交接骨架 |

## 新项目如何使用

1. 将本目录复制到新 Repo 外作工作副本。
2. 把 `AGENTS.template.md` 复制为 Repo 根目录 `AGENTS.md`。
3. 把 `docs/*.template.md` 复制到 `docs/` 并移除文件名中的 `.template`。
4. 每个正式模块复制一份 `docs/modules/MODULE.template.md`，以模块名重命名。
5. 替换全部 `<PLACEHOLDER>`，删除不适用的可选角色/规则，不保留示例事实。
6. 建立首个 Task Packet，检查文档之间无重复或冲突后提交 baseline commit。

## 必须替换

- `<PROJECT_NAME>`、`<PRODUCT_GOAL>`、`<V1_FLOW>`、`<OWNER>`。
- `<MODULE_ID>`、`<DISPLAY_NAME>`、角色名、代码/测试路径、Public Contract 路径。
- 模块职责、允许/禁止依赖、V1 范围、真实安全授权和项目级 UNKNOWN。

一个事实只在一个主文档详细描述；其他文件只引用。未知事实写 `UNKNOWN`，不要把模板占位符当成已确认事实。
