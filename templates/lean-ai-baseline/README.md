# 精简 AI 团队项目模板

目标：让 AI 团队用最少规则持续交付业务结果。

## 启动

1. 复制 `AGENTS.template.md` 为根目录 `AGENTS.md`。
2. 将需要的 `docs/*.template.md` 复制到项目 `docs/`，不要为了模板完整性创建无用文档。
3. CEO 填写项目治理、产品/业务基线、架构边界和 Safety。
4. Main Programmer 维护 `CURRENT_TASK.md`、代码、测试和实现侧 module/runtime 文档。
5. Git 保存历史；canonical docs 只保留当前有效事实。

## 核心原则

- CEO 任务指令只写业务目标、验收、必读文档和 Safety 边界。
- Main Programmer 连续执行到 DONE，普通技术问题不中途转交 Owner。
- 同类问题再次出现时，优先收敛为共享代码和回归测试。
- 交付看 READY/PASS/live/commit/push，不看过程描述。
