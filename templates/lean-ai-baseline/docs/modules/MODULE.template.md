# <DISPLAY_NAME> 模块

## Public Contract

- 入口：`<PUBLIC_ENTRY>`
- 输入：`<INPUT_CONTRACT>`
- 输出：`<OUTPUT_CONTRACT>`
- 状态/错误：`<STATUS_OR_ERROR_CONTRACT>`

## 长期业务规则

- `<DURABLE_MODULE_RULE>`
- `<FAIL_CLOSED_RULE_IF_APPLICABLE>`

## 边界

- 负责：`<OWNED_RESPONSIBILITY>`
- 不负责：`<NON_RESPONSIBILITY>`
- 依赖方向以 `MODULE_INDEX.md` 为准；安全规则以 `BOUNDARIES.md` 为准。

## 外部读写

- 读取：`<AUTHORIZED_READS 或 NONE>`
- 写入：`<AUTHORIZED_WRITES 或 NONE>`
- 真实副作用：`<AUTHORIZATION_REQUIRED 或 NONE>`

## UNKNOWN

- `<MODULE_LEVEL_UNKNOWN>`

不要在本文件保存 selector、XPath、临时 workaround、函数实现细节、测试过程、Task 历史或其他文档已拥有的规则。
