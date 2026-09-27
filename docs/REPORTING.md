# 汇报规则

默认 **Main Programmer 直接向 Owner 汇报**；普通开发不经过 CEO 中转。

阶段完成时只报：

```text
状态：DONE / BLOCKED
完成：<关键结果>
验证：<测试 + live>
需要 Owner：NONE / 一个明确动作
阻塞：NONE / 唯一真实 blocker
Commit：<SHA + push 状态>
```

只有业务规则、Safety/Write Gate、重大架构或 release/merge 节点才升级 CEO。

规则：
- 不贴长篇过程日志，不重复背景。
- `NOT_LIVE_VERIFIED` 不等于 `FAIL`。
- 普通技术失败先自行诊断和修复，不以汇报代替解决。
- 一个答复尽量只要求 Owner 做一个动作。
