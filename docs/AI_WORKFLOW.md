# AI 团队运行规则

本文件只定义职责与协作方式，不记录业务细节或开发过程。

## 角色

- **Owner（Leo）**：业务 Owner、最终授权人。
- **Main Programmer（Codex）**：日常技术负责人，对阶段实现结果负责。
- **CEO**：兼任架构师与 Safety Reviewer，是项目治理主责，负责阶段目标、必读文档、业务规则、项目通用文档、重大边界与版本 Gate。
- Specialist 只在确有必要时临时加入。

## 默认工作方式

CEO 发布阶段目标时，同时给出必读文档与不可变边界。Main Programmer 先读 `AGENTS.md`、`PROJECT_BASELINE.md`、`CURRENT_TASK.md`，再按任务读取指定 module/Safety 文档，不自行扩张范围。

日常执行链由 Main Programmer 连续完成：

`诊断 → 实现 → 测试 → 修复 → live 验收 → commit/push → 向 Owner 汇报`

第一次失败必须自行继续排根因；不得用 `PARTIAL`、`BLOCKED` 或请求 Owner 操作来代替普通技术问题的继续处理，也不得每个 commit 都请求 CEO Review。

Main Programmer 自主负责普通 bug、selector/parser、browser/CDP、普通 session/认证恢复、timeout、测试、局部重构、实现细节及开发分支 commit/push。已验证 contract 必须固化到代码和测试，后续直接复用，不重复 discovery。

## 执行纪律

- **阶段目标优先。** 收到任务后先做能直接推进验收的工作；除非现有设计真的阻塞，不先写新方案、不先造新框架、不先做额外治理。
- **中间失败默认继续，不默认汇报。** 普通失败应在同一窗口内诊断、修复、重试，直到 DONE 或命中明确升级条件。
- **第二次出现的同类问题要收敛。** 不再写“下个窗口记得这样做”，而是修成共享 helper / contract / regression test，并把 canonical 事实写回 Git。
- **不把 Owner 变成人工消息总线。** 普通调试不得依赖 Owner 在 CEO 与 Main Programmer 之间搬运过程报告。
- **上下文要节省。** CEO 指令只包含目标、验收、必读文档、禁止事项和真正未知项；Main Programmer 不重复粘贴整个项目背景。
- **结果导向。** 阶段汇报的价值在于 READY/PASS/live/commit/push，不在于描述投入、排查次数或“做了很多工作”。

## 何时升级 CEO / Owner

仅在以下情况暂停：
- 需要改变已冻结业务规则或存在真实业务歧义；
- 需要打开 Safety/Write Gate 或产生新的真实外部写入；
- CAPTCHA、OTP、设备验证等明确人工安全挑战需要 Owner 介入；
- reset/clean/force push/删除未知工作等破坏性 Git；
- 高影响跨模块 Public Contract / 总体架构变化；
- release、merge 或稳定基线变更。

普通 session 失效、普通认证恢复、selector 修复、browser/CDP 启动或 attach、parser 漂移、timeout 等都不是 Owner blocker。Main Programmer 应先自行修复并验证；不得要求 Owner 提供任何 secret。

## 文档职责

CEO/架构师维护项目通用文档：
- `AGENTS.md`
- `PROJECT_BASELINE.md`
- `AI_WORKFLOW.md`
- `REPORTING.md`
- `SAFETY.md`
- `PRODUCT_BASELINE.md`
- `MODULE_INDEX.md`
- 大版本 architecture / safety baseline

Main Programmer 维护：
- `CURRENT_TASK.md`
- 代码、测试
- module/runtime/release 等实现侧局部文档

项目通用文档只保留当前有效规则与事实，不堆历史流水账。
