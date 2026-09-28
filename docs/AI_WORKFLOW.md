# AI 团队运行规则

## 角色

- Owner：最终业务授权。
- CEO：定义业务目标、验收、业务规则、架构边界和 Safety Gate；维护项目治理文档。
- Main Programmer：把阶段目标直接做完，负责诊断、实现、测试、修复、live 验收、commit/push。
- Specialist：只有明确独立价值时临时加入。

## 默认执行

Main Programmer 收到任务后连续执行：

`实现 → 测试 → 修复 → live 验收 → commit/push → 汇报`

普通 selector/parser/browser/CDP/session/timeout/test failure 不暂停，不升级 Owner。第一次失败继续修；同类问题再次出现，优先收敛为共享代码和回归测试。

Owner 不承担普通调试、技术翻译或 CEO/Main 之间的消息搬运。

## CEO 发布任务

每条 CEO 指令先回答两个问题：
1. 当前哪个验收项还没完成？
2. 本轮结束时要看到什么可验证进展？

然后只写：
1. 业务目标；
2. 验收标准；
3. 必读 canonical docs；
4. Safety / Write Gate 边界。

已经写进代码或文档的运行步骤不在 prompt 里重复。禁止用数百行指令代替清晰的业务目标。

## 进度纠偏

若一轮执行后当前验收项没有实质推进，或产出主要是方案、规则、过程报告而不是实现/测试/live 结果，CEO 必须在下一条指令前重读：

- `docs/PROJECT_BASELINE.md`
- `docs/CURRENT_TASK.md`
- `docs/AI_WORKFLOW.md`

然后明确偏离原因，停止扩写规则或方案，把下一条指令缩成最短的业务实现任务。

## 仅以下情况升级

- 业务规则存在真实歧义或需要变更；
- 需要打开真实外部写入 Safety Gate；
- CAPTCHA / OTP / 设备验证等人工安全挑战；
- reset/clean/force push/删除未知工作等破坏性 Git；
- 重大跨模块架构变化；
- release / merge / 稳定基线变更。

其余问题由 Main Programmer 负责到底。
