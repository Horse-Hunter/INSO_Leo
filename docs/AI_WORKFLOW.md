# AI 开发工作流

## 原则与团队

软件保持模块化，AI 团队保持扁平化；组织复杂度必须低于问题复杂度。默认常驻团队只有 Human Owner（Leo）→ CEO → 一名 Main Programmer。角色不等于工具：Codex、WorkBuddy 或未来 Coding Agent 都可执行 Main Programmer；换工具不改变职位、权限、边界或架构。

CEO 将 Owner 想法转为阶段目标，定义业务边界与 Acceptance，判断是否需要临时 Specialist，处理真正的业务、架构和安全决定，在阶段结束做一次最终 Review，决定是否进入 `main`，并维护产品方向。CEO 不按模块拆大量任务，不维护模块百分比，不指挥函数实现，不逐次 Review 普通 bug，不为软件模块设置管理岗位。

Main Programmer 对阶段结果负责，拥有跨模块开发自主权：可修 bug、调整普通内部 API、增删内部实现与测试、局部重构、更新普通依赖和非高风险 runtime、创建开发脚本、维护 selector/parser/API client、处理页面变化、测试及普通环境问题；可直接维护 `MODULE_INDEX.md`、`CURRENT_TASK.md` 和相关 module docs，在自己的开发 branch commit/push。不得自行 merge 或 force push `main`，不得自行降低安全约束、决定新业务规则、无必要地大规模重写架构，或未经授权增加生产写入、删除、发送、提交。

## 临时角色与并行

- **Security Specialist：**仅在新增高风险能力时由 CEO 临时创建，例如真实外部写入/删除/覆盖、ERP 写入、表单或订单提交、主动发消息、支付、Credential 新能力。负责安全边界、Public API 和 tests，完成即退出。已批准且稳定的安全 Public API 可由 Main Programmer 正常调用，无需每次重启 Specialist。
- **Architecture Specialist：**仅在大版本架构重构、模块职责重大改变、Public Contract 大规模变化、Repo 总体结构重构或 AI 治理重大变化时临时创建。普通局部重构不需要。
- **Independent Programmer：**默认零个；仅在功能边界明确、可独立测试、与主程序员修改文件重叠很少三项同时满足时并行，最多两个。各自使用独立 branch/worktree 与明确的写入范围；不为表面并行拆任务。
- **Utility Programmer：**一次性处理环境、Git/worktree、PowerShell、浏览器/CDP、依赖、脚本或调试工具问题，解决后退出，不占用主程序员长期上下文。

## 阶段执行与升级

按完整用户能力设阶段目标，允许 Main Programmer 跨 `core`、`sheets`、`research`、`workflow` 等模块交付。默认循环：Owner 提业务目标 → CEO 定义边界和 Acceptance → Main Programmer 自主开发、测试、修 bug → 必要时临时 Specialist → 适用的真实 smoke → self-review → commit/push → CEO 一次最终 Review → CEO 决定进入 `main`。只对真实高风险问题增加 Review；减少过程控制，加强结果验收。

Main Programmer 必须向 CEO 升级：业务语义不明确；改变长期业务规则；改变模块职责；改变有跨模块影响的 Public Contract；新增高风险生产副作用；降低安全约束；可能破坏稳定生产能力；需要 Owner 人工登录、CAPTCHA、OTP 或设备验证；需要不可逆真实操作。明确授权后的有界重复操作按 `SAFETY.md` 执行。遇到需要 Owner 决策时在 `CURRENT_TASK.md` 记录待决项，使用 `REPORTING.md` 的 Owner 模板一次问清。

新增网页能力采用 Browser-first：先在已授权、只读范围内确认真实入口、登录、输入、目标数据或动作、成功结果与风险，再确定模块归属和端到端验收；不能凭假设提前设计大量 DOM、adapter 或 schema。真实写入或提交另按 `SAFETY.md` 授权，人工验证不得绕过。

## 当前任务、事实和文档

`CURRENT_TASK.md` 是唯一当前阶段记录，控制在一两页，由 Main Programmer 维护 Goal、Business Outcome、Acceptance、Constraints、Done、Current、Next、Blockers、Owner Decisions、Branch 与 Last Good Commit。完成后把仍成立的事实提升到 `PRODUCT_BASELINE.md`、`MODULE_INDEX.md` 或 module docs，再把 Current Task 切至下一阶段或 `NONE`。Git 历史保存历史；不保存 completed task 文档、过程考古或长篇开发日志。

Known Facts Must Not Be Re-Asked：优先读取 `PRODUCT_BASELINE.md`、`MODULE_INDEX.md`、`CURRENT_TASK.md`、相关 module docs、runtime 文档、Git 当前代码/配置及已明确的 Owner Decision。只有新业务决定、新授权、现有材料没有的信息、人工登录/验证或真正业务歧义才问 Owner。缺证据写 `UNKNOWN`。

长期文档只记录当前仍成立的事实。代码与真实验证产生事实，再沉淀到 canonical docs；不记录做事者、中间 debug、Agent 对话、失败尝试、过期计划或过程日志。Main Programmer 在实际开发中维护业务文档，CEO 最终 Review。`MODULE_INDEX.md` 管模块职责和依赖，module docs 管 Public Contract，`PRODUCT_BASELINE.md` 管跨模块业务事实，`SAFETY.md` 管安全，`REPORTING.md` 管汇报；每项事实只选一个主文件。

## Git、Review 与 Handoff

开始前检查 `git status`、`git diff` 和近期提交；保护原始 dirty checkout。开发使用独立 branch/worktree；同一个 dirty worktree 只允许一名写入执行器。不 reset/clean/stash/discard 未知内容，不覆盖未知文件，不混入 secret、真实数据或非必要生成文件。阶段完成要满足 Acceptance、运行适用检查和 smoke、检查完整 diff、更新长期事实及 Current Task，并在授权范围内 commit/push。CEO 对阶段结果做一次最终 Review；普通 bug 由 Main Programmer 自行修复。

Agent 替换时按 `AGENTS.md` → `AI_WORKFLOW.md` → `SAFETY.md` → `PRODUCT_BASELINE.md` → `MODULE_INDEX.md` → `CURRENT_TASK.md` → `git status` → `git diff` → 近期提交 → 相关 module doc/code 恢复，不假定继承隐藏聊天上下文。Git + canonical docs 是共享记忆。仅当执行器中途故障、上下文严重退化或 dirty worktree 需要接管时生成临时 Handoff，字段仅 Role、Goal、Branch/worktree、Last Good Commit、Done、Uncommitted、Tests、Blocker、Next。恢复后删除临时 Handoff。若上下文退化到无法辨认事实、分支或未提交内容，先停止有风险的写入，按该格式交接。
