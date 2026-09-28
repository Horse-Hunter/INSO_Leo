# 项目管理基线

只记录长期有效的项目规则与稳定锚点；当前阶段见 `CURRENT_TASK.md`，实现细节见 module docs。

## 工作原则

- **业务结果优先。** 交付以 READY / PASS / live / commit / push 为准，方案、排查和过程报告不能替代完成。
- **每条指令都服务当前需求进度。** CEO 下给 Main Programmer 的任务必须对应一个当前未完成验收项，并明确本轮要推进到的可验证结果。
- **进度慢立即复盘规则。** 一轮执行若没有明显推进当前验收项，CEO 在下一条指令前必须重读 `PROJECT_BASELINE.md`、`CURRENT_TASK.md`、`AI_WORKFLOW.md`，检查是否又陷入过度规划、重复 discovery、无关治理或过程汇报，并把任务重新收缩到最短业务路径。
- **简单优先。** 能用现有能力解决就不新增框架、层级、状态、角色或文档。
- **Git 是长期记忆。** 跨窗口要复用的事实必须落到代码、测试或 canonical doc；聊天不是功能载体。
- **重复故障产品化解决。** 同类问题再次出现时，修共享 helper / contract / regression test，不再给新窗口重讲操作步骤。
- **Owner 不是调试中继。** 普通技术失败由 Main Programmer 自己处理；CEO 不通过 Owner 反复转发过程信息。
- **节省上下文。** CEO 给 Codex 的任务只写业务目标、验收、必读文档和 Safety 边界；不写数百行程序员操作手册。

## 职责

- Owner：业务最终授权。
- CEO：业务规则、治理文档、总体架构边界、Safety/Write Gate、阶段目标与验收。
- Main Programmer：代码、测试、实现侧文档、live 验证、开发分支 commit/push。

## 稳定锚点

- V1.1 Research Stability：CLOSED，`release/v1.1 = 44cd4a4cdb05fc069189801d24c4710bfd9445f3`。
- V1.2 开发分支：`feature/v1-2`。
- Production browser：Chrome only。
- Credential 唯一来源：Core Vault。
- INSO runtime readiness 是共享基础能力：Chrome/CDP → Core Vault → ordinary recovery → unique authenticated shell。普通 readiness 问题内部解决；只有 CAPTCHA/OTP/设备验证等人工安全挑战可升级 Owner。
- V1.2 Production Write Gate：CLOSED。
