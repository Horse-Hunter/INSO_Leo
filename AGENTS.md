# Agent 入口

- **目标优先，简单实现。** 只做当前业务目标需要的最小改动，不为未来假设增加框架、流程或文档。
- 新窗口先读：`docs/PROJECT_BASELINE.md`、`docs/CURRENT_TASK.md`；再按任务读取对应 module doc。涉及真实外部写入时再读 `docs/SAFETY.md`。
- Git、代码、测试和 canonical docs 是事实源；旧聊天、历史 Task、已被新结论取代的记录不是当前事实。
- **CEO 是治理、业务规则、架构边界和 Safety Gate 主责。** Main Programmer 负责实现、测试、修复、live 验收、commit/push。
- **CEO → Main Programmer 的指令只允许包含四类内容：业务目标、验收标准、必读事实源、Safety/Write 边界。** 不重复项目背景，不写浏览器/登录/Git/调试操作手册，不把治理规则复制进任务；默认保持短指令，禁止数百行流程式 prompt。
- 普通技术问题由 Main Programmer 连续解决到 DONE；Owner 不参与普通调试和消息搬运。只有业务规则歧义、真实写入 Gate、CAPTCHA/OTP/设备验证、破坏性 Git、重大架构或 release/merge 才升级。
- 同类问题第二次出现时，必须收敛为共享代码/contract/回归测试，不再靠聊天或 Owner 教学。
- INSO 任务必须复用 `docs/modules/INSO.md` 的共享 runtime/session 能力；普通 Chrome/CDP/session/认证恢复不是 Owner blocker。
- 汇报只报可验收结果；有问题时在技术事实后加“说人话”，说明问题、影响和下一步责任人。
- 不得把 password、secret、token、cookie 或 Vault value 写入 Git、日志、fixture、evidence 或报告。
