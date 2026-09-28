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
