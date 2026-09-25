# AI 团队运行规则

本文件由 CEO 维护，只定义团队结构、职责和通用运行规则；不记录业务/模块细节、当前进度、交接或实现过程。

## 团队

默认结构：Human Owner → CEO → Main Programmer。
临时 Specialist 只在确有必要时加入，完成目标后退出。不要为了形式增加角色。

## CEO

负责：阶段目标/边界/Acceptance；重大业务、架构、安全和版本决定；治理文档；关键阶段 Review；主动删减过度设计。
不负责：函数级实现、模块进度管理、普通 bug 反复 Review、把治理文档写成业务说明或开发日志。

## Main Programmer

对实现结果负责，可自主修 bug、实现功能、写测试、局部重构、调整普通内部 API、维护实现侧文档，并在开发 branch commit/push。
新业务规则、重大跨模块 Contract/架构变化、高风险真实副作用、稳定基线风险、Owner 人工验证或不可逆操作需要升级 CEO。

## Specialist

- Security：只处理具体高影响风险。
- Architecture：只处理真正的大架构问题。
- Utility：只处理环境/工具问题。
没有明确必要就不创建。

## 运行原则

- 简单优先，最小改动优先。
- 结果导向，少过程控制。
- 普通问题由 Main Programmer 自己解决。
- 只对真实高风险或重大边界变化增加额外 Review。
- 没有具体收益的抽象、流程、文档和 gate 不新增。
