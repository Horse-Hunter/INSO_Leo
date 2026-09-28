# 汇报规则

Main Programmer 只在阶段完成或命中真实升级条件时汇报。

```text
状态：DONE / BLOCKED
完成：<可验收结果>
验证：<tests + live>
需要 Owner：NONE / 一个真正必须由 Owner 完成的动作
阻塞：NONE / 唯一真实 blocker
说人话：<仅有 blocker 时解释问题、影响、下一步责任人>
Commit：<SHA + push 状态>
```

普通技术失败继续修，不用 PARTIAL/NEEDS_ONE_CLICK 代替工作。没有 READY/PASS/live/commit/push 的过程说明不算交付。
