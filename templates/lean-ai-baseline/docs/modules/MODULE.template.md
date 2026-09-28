# <DISPLAY_NAME> 模块

## Public Contract

- 入口：`<PUBLIC_ENTRY>`
- 输入：`<INPUT_CONTRACT>`
- 输出：`<OUTPUT_CONTRACT>`
- 状态/错误：`<STATUS_OR_ERROR_CONTRACT>`

## 当前长期规则

- `<DURABLE_RULE>`

## 边界

- 负责：`<OWNED_RESPONSIBILITY>`
- 不负责：`<NON_RESPONSIBILITY>`
- 依赖方向见 `../MODULE_INDEX.md`，安全见 `../SAFETY.md`。

只保留当前有效 contract。经 live 验证、需要跨窗口稳定复用且已有回归测试保护的运行 contract（包括必要 selector/protocol）可以保留；临时 discovery、错误尝试、workaround 和历史阶段记录一律交给 Git 历史。
