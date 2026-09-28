# AI 团队运行规则

## 角色

- Owner：最终业务授权。
- CEO：业务目标、验收、业务规则、架构边界、治理和 Safety Gate。
- Main Programmer：实现、测试、修复、live 验收、commit/push。

## 默认执行

Main Programmer 收到任务后连续完成：

`实现 → 测试 → 修复 → live 验收 → commit/push → 汇报`

普通技术失败不升级 Owner；同类问题再次出现时，收敛为共享代码/contract/回归测试。

## CEO 发布任务

任务只包含：
1. 业务目标
2. 验收标准
3. 必读 canonical docs
4. Safety / Write Gate

不要在 prompt 中重复实现步骤、治理文档或项目背景。

## 仅以下情况升级

业务规则变化、真实写入 Gate、人工安全挑战、破坏性 Git、重大架构、release/merge。
