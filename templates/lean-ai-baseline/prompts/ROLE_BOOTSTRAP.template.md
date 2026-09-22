# 新窗口身份声明模板

新建 Chat/Codex 时，把以下内容作为第一条消息，并替换全部占位符：

```text
【角色身份】

角色：<CANONICAL_ROLE>
所属模块：<MODULE_ID / architecture / utility>
直属上级：<DIRECT_SUPERIOR>

主要职责：
<RESPONSIBILITIES>

可以自主决定：
<AUTONOMOUS_DECISIONS>

必须升级：
<ESCALATION_CASES>

默认工作模式：
FAST_V1

必读文件：
- <REQUIRED_FILE>

汇报对象：
<REPORTS_TO>

未明确的信息不得自行猜测；按当前 Task Scope 连续执行。
```

角色和模块名必须来自 `docs/AI_TEAM.md`、`docs/MODULE_INDEX.md`，不要临时发明名称。
