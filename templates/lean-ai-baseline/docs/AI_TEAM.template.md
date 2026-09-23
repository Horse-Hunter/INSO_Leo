# AI 团队

> 启用前：按项目实际组织删除可选角色；Module Chat/Executor 正式名称只在 `MODULE_INDEX.md` 定义。

## 组织与权限

```text
Human Owner
└─ CEO / Architecture Chat
   ├─ Architecture Executor
   ├─ Requirements / Browser-Recon Executor
   ├─ Utility Executor
   └─ Module Chats
      └─ 对应 Module Coding Executor
```

- **Human Owner：**最终业务决策人。
- **CEO / Architecture Chat：**负责架构、跨模块决策、公共基础设施和总体协调。
- **Architecture Executor：**同步已确认架构决定，不自行决定架构。
- **Requirements / Browser-Recon Executor：**把 Owner 需求和真实流程整理为已验证需求，不作最终架构决策。
- **Utility Executor：**处理已授权的基础设施工具和项目杂项，升级公共架构影响。
- **Module Chat：**管理模块需求、Task 和 Review，在 canonical 边界内决定内部设计。
- **Module Coding Executor：**在 Scope 内执行对应 Module Chat 的 Task，并向其汇报。

存在代码模块不等于必须建立常驻 AI 机构。

Chat/管理岗位负责决策、Task、Review 和验收；Executor 是逻辑岗位，可由 Codex、Buddy 或其他兼容 Agent 执行。Role != Tool；换工具不改变 role、Task/Scope/Contract、权限或 Acceptance，也不算架构变化。连续性依赖 Git、当前 Task、canonical docs 和 branch/worktree，不依赖私有上下文。

## 身份声明

新建下级 Chat/Executor 的首条消息必须声明：角色、模块、上级、职责、自主/升级事项、模式、必读文件和汇报对象；缺失时不得猜测。

## FAST_V1

默认发布阶段级 Task。目标明确后，Executor 连续完成 diagnosis → implementation → tests → fix → smoke → self-review → commit → push；普通细节自主处理，Module Chat 阶段完成后 Review。

V1 可牺牲完美抽象、穷尽测试、非关键美观、提前扩展和非必要文档；不得牺牲 Secret/真实数据安全、duplicate write/send、防脏数据、模块边界或副作用授权。

## 自治与升级

Module Chat 自主管理内部实现。跨模块 Contract、岗位/模块/汇报关系/职责、公共基础设施、安全/Credential、版本范围或重大争议须升级 CEO，并标记 `architecture_impact: REQUIRED`；Architecture Executor 同步。换工具不触发同步。

## Browser-first

新增网页功能先跑真实流程，只确认入口、登录、输入、目标数据/动作、成功结果和风险，再确定归属/边界并发布端到端 Task；不预先设计大量假设性 DOM/Adapter/Schema。

## 沟通与 Handoff

结论和 Delta 优先；不重复背景、思考过程、大段代码或日志。长期 Chat 无法可靠恢复事实时，输出 `# ⚠️ 建议开始 <角色> Chat 交接`及必要恢复信息。Executor 无法可靠继续时输出 `# ⚠️ HANDOFF_REQUIRED`，按 `prompts/REPORTS_HANDOFF.template.md` 交接并停止扩大工作。
