# 精简 AI 团队项目模板

复制本目录的 `AGENTS.template.md` 为项目根目录 `AGENTS.md`，将 `docs/*.template.md` 去掉 `.template` 后复制到项目 `docs/`，将 `docs/modules/MODULE.template.md` 按实际模块复制并命名。`prompts/` 供启动新 Agent 或临时交接时复制使用。删除未启用的占位内容；`UNKNOWN` 表示尚无证据，不得当作已批准规则。

## 启动顺序

1. 复制模板，填写 `PRODUCT_BASELINE.md` 中已确认的目标、范围和真实业务事实。
2. Main Programmer 按实际代码初始化 `MODULE_INDEX.md`，只建立确实存在或有明确近期需要的模块。
3. CEO 定义第一阶段的 `CURRENT_TASK.md`：目标、业务结果、边界和可观察的 Acceptance。
4. Main Programmer 按阶段自主开发、验证、修复、review、commit/push；需要时 CEO 临时引入 Specialist。
5. 阶段完成后把仍成立的长期事实更新到产品基线、模块注册表或 module docs，再切换 `CURRENT_TASK.md` 到下一阶段或 `NONE`。
6. 不保存历史 Task 文档；Git 历史保留已完成工作。

项目业务文档主要由 Main Programmer 随真实实现持续生成和维护，Owner/CEO 不必在启动时先写大量设计文件。软件保持模块化，AI 团队保持扁平化；组织复杂度必须低于问题复杂度。不要提前建立无用模块、团队、依赖或审批层。

## Canonical 归属

| 事实 | 文件 |
| --- | --- |
| 团队、权限、工作流、Review、Handoff | `docs/AI_WORKFLOW.md` |
| 安全和外部真实副作用 | `docs/SAFETY.md` |
| 产品范围与跨模块业务规则 | `docs/PRODUCT_BASELINE.md` |
| 模块职责、Public Contract 入口与依赖 | `docs/MODULE_INDEX.md` |
| 当前唯一阶段 | `docs/CURRENT_TASK.md` |
| Owner 汇报格式 | `docs/REPORTING.md` |
| 模块长期业务规则和 Public Contract | `docs/modules/<MODULE>.md` |
| 实现、验证和历史 | Git 当前代码、测试和提交 |

每项事实只在一个主文件详述，其他文件链接过去。Secret、真实数据和 runtime 输出留在源码与 Git 之外。阶段完成前检查完整 diff，清除临时 debug、handoff 和无关生成文件；不要为了文档结构而改产品实现。
