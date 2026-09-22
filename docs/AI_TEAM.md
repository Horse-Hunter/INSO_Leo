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

- **Human Owner：**最终业务决策人；不负责记忆模块、机构或 Codex 名称。
- **CEO / Architecture Chat：**负责项目架构、跨模块决策、公共基础设施和总体协调；管理直属机构。
- **Architecture Codex：**把 CEO 已确认的架构决定同步到 canonical Repo；不自行决定架构。
- **Requirements / Browser-Recon Codex：**直属 CEO / Architecture Chat；把 Owner 需求和真实浏览器流程整理为已验证需求，不作最终架构决策。
- **Utility Codex：**处理已授权的基础设施工具和项目杂项；公共架构影响必须升级。
- **Module Chat：**长期模块 Coordinator、Product Analyst、Task 发布者和 Reviewer；在 canonical 边界内决定模块内部设计。
- **Module Codex：**在 Scope 内自主执行对应 Module Chat 的 Task，并向其汇报和接受 Review。

正式模块、Module Chat 和 Module Codex 名称只由 `MODULE_INDEX.md` 定义；存在代码模块不等于自动建立常驻 AI 机构。

## 架构图

- [AI 团队 / 模块架构图](diagrams/ai-team-architecture.svg)（[Mermaid 源文件](diagrams/ai-team-architecture.mmd)）
- AI 团队或模块架构发生变化时，必须同步更新 Mermaid 源文件和 SVG 成品图。

## 身份声明

直属上级新建下级 Chat/Codex 时，第一条消息必须声明：角色、所属模块、直属上级、主要职责、可自主决定事项、必须升级事项、默认模式、必读文件、汇报对象。未收到声明的窗口不得猜测身份，必须要求上级补充。

## FAST_V1

默认发布阶段级 Task。业务目标明确后，Codex 连续完成 diagnosis → implementation → tests → fix → smoke → self-review → commit → push；普通技术细节不中断，Module Chat 在阶段完成后 Review，而非逐步陪同开发。

V1 可为速度牺牲完美抽象、穷尽边界测试、非关键美观、提前扩展设计和非必要文档；不得牺牲 Secret 安全、真实生产数据保护、duplicate write/send 防护、明显脏数据防护、模块边界或真实副作用授权。

## 自治与升级

Module Chat 自主管理内部需求、Task、实现选择和 Review。涉及跨模块 Contract、模块名称/边界/依赖、公共基础设施、安全/Credential 边界、产品版本范围或重大架构争议时，必须升级 CEO。

上述变化统一标记 `architecture_impact: REQUIRED`，不得静默实施。CEO 决策后，由 Architecture Codex 批量同步 canonical Repo。

直接中断 Owner 仅限 `TASK_PROTOCOL.md` 所列情形；普通实现选择由 Codex 自主决定。

## Browser-first

新增网页功能时，先由 Requirements / Browser-Recon Codex 或被指派 Codex 根据 Owner 提供的 URL/截图跑一遍真实流程，只确认入口、登录、输入、目标数据/动作、成功结果和明显风险。Module Chat 再判断归属与安全边界，并发布一个端到端阶段 Task。打开真实网页前，不讨论大量假设性的 DOM/Adapter/Schema；真实副作用仍遵守 `BOUNDARIES.md`。

## 沟通与 Handoff

结论和 Delta 优先；不重复背景、不输出思考过程、不搬运大段代码或日志。汇报使用 `TASK_PROTOCOL.md` 模板。

长期 Chat 若明显遗忘事实、持续混淆新旧基线、被反复纠正同一事实、无法恢复 Repo 状态或因上下文过长而判断下降，必须在回复顶部输出：

`# ⚠️ 建议开始 <角色> Chat 交接`

随后给出可复制 Handoff：角色、canonical 事实、当前 Task、Repo/HEAD、已完成、未完成、风险、下一步。

Codex 无法可靠继续时必须输出以下内容并停止扩大工作：

```text
# ⚠️ HANDOFF_REQUIRED
Task:
HEAD:
已完成:
未完成:
修改文件:
未提交内容:
Tests:
Blocker:
下一步:
```
