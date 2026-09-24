# 汇报格式

第一屏给出状态和 Owner 动作，不先贴技术日志。`需要决定` 与 `你要做什么` 必须相邻；`需要决定: NONE` 不代表 `你要做什么: NONE`。

## Main Programmer → 上级

```text
状态：
DONE / BLOCKED

需要决定：
NONE / 一个明确决定

你要做什么：
NONE / 一个明确动作

完成：
- 核心结果

验证：
- 关键 tests / smoke

真实效果：
- 业务上现在能做什么

剩余：
NONE / 真实 gap

Commit：
<hash>

Push：
SUCCESS / NOT PUSHED
```

## Agent 直接询问 Owner

```text
以前：
<原状态>

现在：
<当前问题>

真实效果：
<业务影响>

需要决定：
<一个明确决定 / NONE>

你要做什么：
<一个明确动作 / A 或 B>

还有什么没解决：
<NONE / gap>

建议：
<A / B>

原因：
<一句话>
```

## CEO → Owner

```text
状态：
DONE / CONTINUE / BLOCKED / ESCALATE

需要决定：
NONE / 一个明确决定

你要做什么：
NONE / 一个明确动作

进展：
<真正重要变化>

问题：
NONE / 真问题

下一步：
<谁做什么>
```
