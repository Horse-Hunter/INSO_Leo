# Agent 入口

- **简单优先。** 只做满足当前目标的最小改动；不为未来假设增加框架、层级、流程或文档。
- 每个新窗口/新阶段先只读：`AGENTS.md`、`docs/PROJECT_BASELINE.md`、`docs/CURRENT_TASK.md`。任务涉及浏览器、session、外部系统或 Safety 时，再读 `docs/AI_WORKFLOW.md`、`docs/SAFETY.md` 和对应 module 文档。
- Git 与 canonical docs 是共享事实源；旧聊天和已被新结论取代的记录不作为当前事实。
- **CEO/架构/Safety 是项目治理主责。** CEO 维护 `AGENTS.md`、项目级治理/架构/Safety 文档，并发布阶段目标、必读文档与边界；Main Programmer 不自行改项目治理规则，除非 CEO 明确要求。
- Main Programmer 维护 `docs/CURRENT_TASK.md`、代码、测试和实现侧局部文档，并默认自行完成一个完整阶段：诊断 → 实现 → 测试 → 修复 → live 验收 → commit/push → 向 Owner 汇报。
- 普通技术问题不得中途请求 CEO/Owner 接管。selector/parser、browser/CDP、普通 session/认证恢复、timeout、测试和局部实现错误都由 Main Programmer 负责到底；第一次失败必须继续排根因。
- 已验证的页面/selector/session contract 要固化到代码与回归测试，后续直接复用；不得因同一普通技术问题反复 discovery、重复开诊断页面或反复要求 Owner 操作。
- 仅业务规则变化、真实外部写入/Safety Gate、CAPTCHA/OTP/设备验证等明确人工安全挑战、破坏性 Git、重大跨模块架构变化或 release/merge 节点升级 CEO/Owner。
- 不得要求 Owner 提供账号、密码、cookie、token 或其他 secret；凭据只走 canonical Core Provider/Vault。
- 不扫描整个 Repo；缺证据写 `UNKNOWN`，不猜。
