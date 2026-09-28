# 汇报规则

Main Programmer 只在阶段完成或命中真实升级条件时汇报；普通技术失败不得用报告代替继续工作。

```text
状态：DONE / BLOCKED
完成：<可验收结果>
验证：<关键 tests + live>
需要 Owner：NONE / 一个真正必须由 Owner 完成的动作
阻塞：NONE / 唯一真实 blocker
说人话：<仅有 blocker 时，用 1-3 句话解释问题、影响、下一步责任人>
Commit：<SHA + push 状态>
```

规则：

- 没有 READY/PASS/live/commit/push 的过程描述不算阶段成果。
- 普通 selector/parser/browser/CDP/session/timeout/test failure 先自行修复，不列为“需要 Owner”。
- 如果下一步仍由 Main Programmer 自己处理，`需要 Owner` 必须是 `NONE`。
- 不贴长日志，不重复背景，不写责任检讨代替交付。
- 不向 Owner 索要或展示 secret。
