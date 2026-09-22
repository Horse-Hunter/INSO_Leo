# 产品基线

本文件只维护产品范围和长期跨模块业务规则。模块规则归 `docs/modules/`，安全归 `BOUNDARIES.md`，依赖归 `MODULE_INDEX.md`；实现状态以 Git `main`、当前 Task 和 Final Report 为准。

## 产品目标

- 项目：`<PROJECT_NAME>`。
- 目标：`<PRODUCT_GOAL>`。
- 主要用户：`<PRIMARY_USERS 或 UNKNOWN>`。
- 可衡量结果：`<SUCCESS_METRIC 或 UNKNOWN>`。

## 当前 V1 用户流程

```text
<V1_FLOW_STEP_1>
-> <V1_FLOW_STEP_2>
-> <V1_OUTCOME>
```

## V1 包含

- `<CONFIRMED_SCOPE_ITEM>`
- `<CONFIRMED_CROSS_MODULE_RULE>`

## V1 不包含

- `<EXCLUDED_ITEM>`
- `<FUTURE_VERSION_ITEM>`

## 跨模块全局业务规则

- `<RULE_THAT_TRULY_AFFECTS_MULTIPLE_MODULES>`

## Future Scope / 产品级 UNKNOWN

- `<PRODUCT_LEVEL_UNKNOWN>`

只影响单一模块的事实或 UNKNOWN 留在对应 module doc 或 Task，不写入本文件；不要维护易 stale 的逐模块实现状态。
