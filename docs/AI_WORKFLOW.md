# AI 团队运行规则

本文件只定义职责与协作方式，不记录业务细节或开发过程。

## 角色

- **Owner（Leo）**：业务 Owner、最终授权人。
- **Main Programmer（Codex）**：日常技术负责人，对阶段实现结果负责。
- **CEO**：兼任架构师与 Safety Reviewer，负责阶段目标、业务规则、重大边界与版本 Gate。
- Specialist 只在确有必要时临时加入。

## 默认工作方式

日常主链是 **Owner ↔ Main Programmer**，不是 Owner 在 Main 与 CEO 之间反复搬运。

Main Programmer 收到阶段目标后，默认连续完成：

`诊断 → 实现 → 测试 → 修复 → live 验收 → commit/push → 向 Owner 汇报`

第一次失败应自行继续排根因；不得用 `PARTIAL` 代替普通技术问题的继续处理，也不得每个 commit 都请求 CEO Review。

Main Programmer 可自主处理普通 bug、selector/parser、session 恢复、timeout、测试、局部重构、实现细节及开发分支 commit/push。

## 何时升级 CEO

仅在以下情况暂停：
- 需要改变已冻结业务规则或存在真实业务歧义；
- 需要打开 Safety/Write Gate 或产生新的真实外部写入；
- CAPTCHA、OTP、设备验证等需要 Owner 人工介入；
- reset/clean/force push/删除未知工作等破坏性 Git；
- 高影响跨模块 Public Contract / 总体架构变化；
- release、merge 或稳定基线变更。

其余问题由 Main Programmer 负责到底。

## 文档职责

- CEO：`AGENTS.md`、`PROJECT_BASELINE.md`、`AI_WORKFLOW.md`、`SAFETY.md`、`REPORTING.md` 及项目级架构/跨模块基线。
- Main Programmer：`CURRENT_TASK.md`、代码、测试及实现侧局部文档。

文档只保留当前有效事实；不堆历史流水账。
