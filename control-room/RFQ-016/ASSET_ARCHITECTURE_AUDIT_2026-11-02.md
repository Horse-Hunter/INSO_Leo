# RFQ-016 — ASSET ARCHITECTURE AUDIT 2026 11 02 — 历史参考索引

**2026-11-14 文档瘦身：** 完整原文保存在下方固定 Git 版本中，现行分支只保留定位信息。没有删除 Git 历史、业务源码或持久化证据。

旧版现场审计发现：V1.6 runtime 可能链接到 V1.4，SQLite 可能通过 V1.2 工作树持久化，Chrome 唯一 Profile 可能实际位于旧 Research 工作树。除非再次核实这些真实路径，否则**不得清理旧目录**。

- **完整原文：** [打开固定版本](https://github.com/Horse-Hunter/INSO_Leo/blob/0db292fe0cb79d5177f436c3f8cc9b87c75288ee/control-room/RFQ-016/ASSET_ARCHITECTURE_AUDIT_2026-11-02.md)
- **当前事实入口：** [CEO 交接](https://github.com/Horse-Hunter/INSO_Leo/blob/workbuddy/v16-rfq016-stabilization/control-room/CEO_HANDOVER.md) · [RFQ-016 执行检查点](https://github.com/Horse-Hunter/INSO_Leo/blob/workbuddy/v16-rfq016-stabilization/control-room/RFQ-016/EXECUTION_LOG.md) · [历史总索引](https://github.com/Horse-Hunter/INSO_Leo/blob/workbuddy/v16-rfq016-stabilization/docs/HISTORY.md)

任何新 CEO/Executor 会话中断后，均须从当前仓库检查点**加上真实进程、SQLite、Google、INSO 和邮件记录**恢复，不能把本文件的历史状态视作实时结果。
