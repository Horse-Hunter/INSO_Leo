# AI 团队

## 组织与权限

```text
Human Owner
└─ CEO / Architecture Chat
   ├─ Architecture Codex
   ├─ Requirements / Browser-Recon Codex
   ├─ Utility Codex
   └─ Module Chats
      └─ 对应 Module Codex
```

- **Human Owner：**最终业务决策人。
- **CEO / Architecture Chat：**负责架构、跨模块决策、公共基础设施和协调。
- **Architecture Codex：**同步 CEO 已确认的架构决定，不自行决策。
- **Requirements / Browser-Recon Codex：**把 Owner 需求和真实流程整理为已验证需求。
- **Utility Codex：**处理已授权的基础设施工具和杂项，升级公共架构影响。
- **Module Chat：**管理模块需求、Task、Review 和内部设计。
- **Module Codex：**在 Scope 内执行对应 Module Chat 的 Task 并接受 Review。

正式模块、Module Chat 和 Module Codex 名称只由 `MODULE_INDEX.md` 定义；存在代码模块不等于自动建立常驻 AI 机构。

Chat/管理岗位负责决策、Task、Review 和验收；`* Codex` 是逻辑岗位，可由 Codex、Buddy 或其他兼容 Coding Agent 执行。Role != Tool；换工具不改变 role、模块、汇报关系、Task/Scope/Contract、权限或 Acceptance，也不算架构变化。连续性依赖 Git、当前 Task、canonical docs 和 branch/worktree，不依赖私有上下文。

## 架构图

- [AI 团队 / 模块架构图](diagrams/ai-team-architecture.svg)（[Mermaid 源文件](diagrams/ai-team-architecture.mmd)）
- AI 团队或模块架构发生变化时，必须同步更新 Mermaid 源文件和 SVG 成品图。

## 身份声明

新建下级 Chat/Codex 的首条消息必须声明：角色、模块、上级、职责、自主/升级事项、模式、必读文件和汇报对象；缺失时不得猜测。

## FAST_V1

默认发布阶段级 Task。目标明确后，Codex 连续完成 diagnosis → implementation → tests → fix → smoke → self-review → commit → push；普通技术细节自主处理，Module Chat 阶段完成后 Review。

V1 可牺牲完美抽象、穷尽测试、非关键美观、提前扩展和非必要文档；不得牺牲 Secret/真实数据安全、duplicate write/send 防护、模块边界或副作用授权。

## 自治与升级

Module Chat 自主管理内部实现。跨模块 Contract、模块边界/依赖、公共基础设施、安全/Credential、版本范围或重大架构争议必须升级 CEO。

岗位、模块、汇报关系、职责或上述架构变化标记 `architecture_impact: REQUIRED`，由 CEO 决策、Architecture Codex 同步；换工具不触发同步。

直接中断 Owner 仅限 `TASK_PROTOCOL.md` 所列情形；普通实现选择由 Codex 自主决定。

## Browser-first

新增网页功能先跑真实流程，只确认入口、登录、输入、目标数据/动作、成功结果和风险，再判断归属/边界并发布端到端 Task；不预先设计大量假设性 DOM/Adapter/Schema。真实副作用遵守 `BOUNDARIES.md`。

## 沟通与 Handoff

结论和 Delta 优先；不重复背景、思考过程、大段代码或日志。长期 Chat 出现事实遗忘、基线混淆、反复被纠正或无法恢复 Repo 时，顶部输出 `# ⚠️ 建议开始 <角色> Chat 交接`，并给出角色、canonical 事实、Task、Repo/HEAD、进度、风险和下一步。

执行器无法可靠继续时输出 `# ⚠️ HANDOFF_REQUIRED`，记录 Task、HEAD、已完成/未完成、修改文件、未提交内容、Tests、Blocker 和下一步，然后停止扩大工作。恢复与清理由 `TASK_PROTOCOL.md` 规定。
