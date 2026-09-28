# 项目管理基线

本文件只记录项目级长期规则与当前稳定锚点，不记录开发流水账。

## 核心规则

- **简单优先、保持瘦身。** 能删就删，能合并就合并；不为未来假设增加框架、状态、流程或文档。
- 一个事实只保留一个 canonical 来源；已被新结论取代的过程记录应删除或停止作为日常上下文。
- Git + canonical docs 是事实源；聊天上下文不是长期事实源。
- 日常启动优先只读 `AGENTS.md + PROJECT_BASELINE.md + CURRENT_TASK.md`，其他文档按需读取。
- **聊天不是功能载体。** 任何需要跨窗口复用的稳定能力，必须落到代码、测试或 canonical 文档；不能依赖“上一个窗口知道怎么做”。
- **重复故障必须产品化解决。** 同类问题再次出现时，优先修公共 helper / contract / regression test，而不是再写一版操作步骤给下一个窗口。
- **交付以可验收结果计，不以过程计。** 方案、排查、文档、PARTIAL 报告都不能替代 READY/PASS/live/commit/push。阶段目标未满足就继续执行，除非触发明确升级条件。
- **控制 token 和上下文成本。** 阶段指令保持最短充分；不重复背景、不重复已验证事实、不把每次失败重新包装成新计划。能从 Git/canonical docs 读取的事实不在聊天里重讲。

## 协作基线

- 日常执行主链：**Owner ↔ Main Programmer**。
- Main Programmer 默认独立跑完整阶段：诊断 → 实现 → 测试 → 修复 → live 验收 → commit/push，再向 Owner 汇报。
- CEO 兼任架构师与 Safety，只处理阶段目标、业务规则、Safety Gate、重大跨模块架构、release/merge 与真正升级事项。
- CEO 对治理质量负责：应把已验证的跨窗口事实及时固化到 canonical docs，把重复技术问题推动成共享代码/测试，而不是反复靠聊天提醒 Main Programmer。
- 普通 bug、selector/parser、timeout、测试组织、局部重构、普通 commit/push 不升级 CEO。
- Owner 不是调试中继站：普通技术失败不得要求 Owner 在 Main Programmer 与 CEO 之间反复搬运信息或逐步指导实现。
- CEO 维护治理/架构类文档；Main Programmer 维护 `CURRENT_TASK.md` 与实现侧局部文档。

## 当前稳定锚点

- V1.1 Research Stability：**CLOSED**。
- `release/v1.1 = 44cd4a4cdb05fc069189801d24c4710bfd9445f3`。
- V1.2 开发分支：`feature/v1-2`；V1.1 Research stability 已同步。
- 生产浏览器：**Chrome only**；Edge 不再支持。
- 凭据唯一来源：**Core Vault**。
- **INSO runtime readiness 是跨版本基础设施契约。** 所有 INSO 功能默认必须自行做到：approved Chrome/CDP 可用 → Core Vault credential 可读 → 普通认证自动恢复 → 唯一 authenticated shell 可用。普通 Chrome/CDP/session/认证问题不得升级为 Owner blocker；若公共实现缺失或回归，Main Programmer 先修复公共能力再继续业务。唯一例外是 CAPTCHA/OTP/设备验证等明确人工安全挑战。
- **INSO 普通认证恢复必须是可执行共享能力，不是文档步骤。** 禁止每个新窗口自己临时填表/点按钮。共享 helper 必须执行“填账号 → 读回确认非空 → 填密码 → 读回确认非空（不记录值）→ 单次精确提交 → 验证唯一 authenticated shell”；任一前置检查失败都不得提交。
- LCSC Vault SiteId：`szlcsc.com`；认证跳转 host：`passport.jlc.com`。
- V1.2 Production Write Gate：**CLOSED**。

## 架构原则

- 模块化但不过度分层；跨模块只依赖明确 Public Contract。
- 稳定能力优先兼容；新增版本优先 additive / seam-based 改动。
- 没有真实重复或维护痛点，不为抽象而抽象。
