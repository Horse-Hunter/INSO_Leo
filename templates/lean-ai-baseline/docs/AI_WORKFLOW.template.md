# AI 开发工作流

## 团队和决策

默认常驻团队：Human Owner → CEO → 一名 Main Programmer。软件保持模块化，AI 团队保持扁平化；组织复杂度必须低于问题复杂度。Role != Tool：Codex、WorkBuddy 或其他 Coding Agent 可执行同一角色，换 Agent 不改变权限、目标、Acceptance 或架构。

Owner 决定业务方向和需要授权的真实操作。CEO 将业务想法转成阶段目标，定义业务边界与 Acceptance，决定是否启用临时 Specialist，处理真正业务/架构/安全决策，阶段末做一次最终 Review，决定是否 merge 主分支并维护产品方向。CEO 不拆大量模块任务、不管理模块百分比、不逐函数指挥实现、不逐次 Review 普通 bug、不为每个软件模块设管理岗位。

Main Programmer 对完整阶段结果负责。可跨模块修 bug、改普通内部 API、增删内部实现、添加测试、局部重构、更新普通依赖与非高风险 runtime、维护开发脚本及 parser/selector/API client、处理测试失败、普通环境问题与页面变化；直接维护 `MODULE_INDEX.md`、`CURRENT_TASK.md` 和相关 module docs；在自己的开发 branch commit/push。不得自行 merge/force push 主分支、降低安全约束、决定新业务规则、为美观大规模重写架构或未经授权增加生产写入/删除/发送/提交。

## 临时角色

- **Security Specialist：**仅在新增高风险能力时由 CEO 临时创建，例如外部真实写入/删除、表单/订单/报价提交、主动消息、支付、Credential 新能力。交付安全边界、Public API 和 tests 后退出。已批准且稳定的安全 API 可由 Main Programmer 正常调用，不逐次重启 Specialist。
- **Architecture Specialist：**仅在大版本重构、模块职责重大改变、Public Contract 大规模变化、Repo 总体结构或 AI 治理重大变化时创建；普通局部重构不需要。
- **Independent Programmer：**默认零个。仅在边界明确、可独立测试、修改文件重叠很少三项同时满足时并行，最多两个；分别使用独立 branch/worktree 与明确写入范围，不为表面并行拆任务。
- **Utility Programmer：**一次性解决环境、Git/worktree、Shell、浏览器/CDP、依赖、脚本和调试工具问题，解决即退出。

## 阶段循环与升级

Owner 提业务目标 → CEO 写 `CURRENT_TASK.md` 的边界和 Acceptance → Main Programmer 自主开发、测试、修 bug → 必要时临时 Specialist → 适用的真实 smoke → self-review → commit/push → CEO 一次最终 Review → CEO 决定是否进入主分支。按完整用户能力设阶段，不按软件模块碎拆。减少过程控制，加强结果验收；真正高风险时才增加 Review。

Main Programmer 必须升级 CEO：业务语义不明、改变长期业务规则、模块职责或有跨模块影响的 Public Contract、新增高风险生产副作用、降低安全约束、可能破坏稳定生产能力、需要 Owner 登录/CAPTCHA/OTP/device verification、需要不可逆真实操作。明确有界授权的重复机械步骤按 `SAFETY.md` 执行。当前等待决定写入 `CURRENT_TASK.md`，向 Owner 提问用 `REPORTING.md`。

新增网页能力采用 Browser-first：在已授权只读范围先确认真实入口、登录、输入、目标数据/动作、成功结果和风险，再定义模块边界与端到端验收；不要先假设 DOM、adapter 或 schema。真实提交另需安全授权。

## 事实、文档和完成标准

`CURRENT_TASK.md` 是唯一当前阶段记录，控制在一两页，由 Main Programmer 维护。已知事实优先从产品基线、模块注册表、当前任务、module docs、runtime 文档、Git 当前代码/配置和已记录 Owner Decision 恢复。Known Facts Must Not Be Re-Asked；只问新业务决定、新授权、材料不存在的信息、人工验证或真正歧义。缺证据写 `UNKNOWN`。

长期文档只记当前仍成立的事实：先以代码和验证建立事实，再沉淀到 canonical docs。Main Programmer 随开发维护业务文档，CEO 最终 Review。不记执行者、Agent 对话、中间 debug、失败尝试、过期计划或长日志。完成阶段需满足 Acceptance、执行适用 tests/smoke、检查完整 diff、清理 secret/生成物、更新长期事实并把 Current Task 切至下一阶段或 `NONE`。Git 历史保留历史，不建立 completed task 档案。

## Git、替换与 Handoff

先查 `git status`、`git diff`、近期提交；保护 dirty checkout。开发用独立 branch/worktree；同一 dirty worktree 只有一名写入执行器。不 reset/clean/stash/discard 未知内容，不覆盖未知用户文件；runtime、secret、真实数据与源码和 Git 分离。正常开发 branch commit/push 由 Main Programmer 自行执行，主分支合并由 CEO 决定。

新 Agent 按 `AGENTS.md` → 本文件 → `SAFETY.md` → `PRODUCT_BASELINE.md` → `MODULE_INDEX.md` → `CURRENT_TASK.md` → `git status` → `git diff` → 近期提交 → 相关 module doc/code 恢复。Git + canonical docs 是共享记忆，不依赖隐藏聊天上下文。仅执行器中途故障、上下文严重退化或 dirty worktree 接管时生成临时 Handoff，字段只含 Role、Goal、Branch/worktree、Last Good Commit、Done、Uncommitted、Tests、Blocker、Next；恢复后删除。事实无法可靠恢复时停止有风险的写入并交接。
