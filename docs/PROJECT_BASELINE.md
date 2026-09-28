# 项目管理基线

本文件只记录项目级长期规则与当前稳定锚点，不记录开发流水账。

## 核心规则

- **简单优先、保持瘦身。** 能删就删，能合并就合并；不为未来假设增加框架、状态、流程或文档。
- 一个事实只保留一个 canonical 来源；已被新结论取代的过程记录应删除或停止作为日常上下文。
- Git + canonical docs 是事实源；聊天上下文不是长期事实源。
- 日常启动优先只读 `AGENTS.md + PROJECT_BASELINE.md + CURRENT_TASK.md`，其他文档按需读取。

## 协作基线

- 日常执行主链：**Owner ↔ Main Programmer**。
- Main Programmer 默认独立跑完整阶段：诊断 → 实现 → 测试 → 修复 → live 验收 → commit/push，再向 Owner 汇报。
- CEO 兼任架构师与 Safety，只处理阶段目标、业务规则、Safety Gate、重大跨模块架构、release/merge 与真正升级事项。
- 普通 bug、selector/parser、timeout、测试组织、局部重构、普通 commit/push 不升级 CEO。
- CEO 维护治理/架构类文档；Main Programmer 维护 `CURRENT_TASK.md` 与实现侧局部文档。

## 当前稳定锚点

- V1.1 Research Stability：**CLOSED**。
- `release/v1.1 = 44cd4a4cdb05fc069189801d24c4710bfd9445f3`。
- V1.2 开发分支：`feature/v1-2`；V1.1 Research stability 已同步。
- 生产浏览器：**Chrome only**；Edge 不再支持。
- 凭据唯一来源：**Core Vault**。
- **INSO runtime readiness 是跨版本基础设施契约。** 所有 INSO 功能默认必须自行做到：approved Chrome/CDP 可用 → Core Vault credential 可读 → 普通认证自动恢复 → 唯一 authenticated shell 可用。普通 Chrome/CDP/session/认证问题不得升级为 Owner blocker；若公共实现缺失或回归，Main Programmer 先修复公共能力再继续业务。唯一例外是 CAPTCHA/OTP/设备验证等明确人工安全挑战。
- LCSC Vault SiteId：`szlcsc.com`；认证跳转 host：`passport.jlc.com`。
- V1.2 Production Write Gate：**CLOSED**。

## 架构原则

- 模块化但不过度分层；跨模块只依赖明确 Public Contract。
- 稳定能力优先兼容；新增版本优先 additive / seam-based 改动。
- 没有真实重复或维护痛点，不为抽象而抽象。
