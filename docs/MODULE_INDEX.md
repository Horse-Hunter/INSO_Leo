# 模块注册表

本文件只维护模块职责与跨模块依赖边界，由 CEO/架构师维护；模块内部实现写在各自 module doc。

| module | path | responsibility |
| --- | --- | --- |
| `core` | `src/core/` | 公共基础能力、Credential Provider |
| `gui` | `src/gui/` | Dashboard / DTO 展示，不做业务计算 |
| `launcher` | `src/launcher/` | Runtime 组装、Chrome/CDP 生命周期 |
| `sheets` | `src/sheets/` | Google Sheets 读取与明确授权的安全写回 |
| `research` | `src/research/` | 只读市场调研、价格聚合、Research Excel |
| `workflow` | `src/workflow/` | Scheduler、状态、retry、跨模块编排 |
| `inso` | `src/inso/` | V1.2 重复检查与受控采购草稿能力 |
| `quotation` | `src/quotation/` | 后续报价模块，当前非主线 |

依赖原则：

```text
workflow -> core, sheets, research, inso, quotation
launcher -> gui, workflow, sheets, research, inso
gui -> core
sheets | research | inso | quotation -> core
```

规则：

- 跨模块只通过 Public Contract；不导入其他模块私有实现。
- GUI 不直接访问浏览器、Excel、Sheets 或业务模块内部实现。
- Research 不承担主动采购。
- INSO 主动采购不改写 Research 的价格/库存/MPN 规则。
- 模块职责、依赖方向或跨模块 Public Contract 变化必须升级 CEO。
