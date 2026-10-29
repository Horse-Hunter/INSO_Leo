# Task: 任务中心默认新订单在前

status: in_progress
owner: Codex Executor
created: 2026-10-29

## problem / goal
Owner要求任务中心按新订单在前显示。当前默认保留本轮/TP/历史拼接顺序，未统一排序；1000条截断发生在排序前。

## scope / requirements
仅离线修改显示排序及必要的只读DTO接线。复用已有workflow_items.created_at，随原all_items查询返回，不新增数据库查询、字段或迁移。默认按首次入库时间倒序；重跑/状态变化不改订单新旧。无入库时刻的旧历史单在已知入库单之后按原处理时间倒序；完全无时间的独立TP/旧单末尾，固定ID稳定排序。不得用TP updated_at或来源行号伪造新旧。
统一合并后先排序再取最新1000；搜索/筛选/分页维持默认顺序，手动表头排序继续可用。

## non_scope
不修改业务处理顺序、权限/幂等、邮件、采购、报价、TP算法；不连接Chrome；初始仅离线修改。Owner随后明确授权：做完确认没问题直接打包覆盖运行。发布必须沿用原构建/安全停止正常退出/新鲜备份/仅程序文件替换/原CLI恢复，禁止Computer Use和强杀，不回滚账本。COMPUTER_USE_NOT_USED。

## acceptance / verification
- 新入库单在前；旧单重跑不前移；同时间稳定；缺失时间末尾。
- 混合模块及1000条截断保留最新单；筛选分页一致；手动排序保留。
- 只读入库时刻来自原持久数据，重启/状态更新不改变，无GUI线程数据库访问。
- 对应离线回归、ruff/diff；仅源码交付REVIEW_REQUIRED，不自动部署。

## reuse / execution
原WorkItem/WorkflowStateStore.all_items、Order、GUI纯state投影、WorkbenchView和Backend快照复用；唯一缺口是入库时间未进入显示DTO。追加可选只读时刻，原schema/业务调用不变。

## completion
pending

## Owner release authorization
2026-10-29 Owner明确要求测试通过后直接打包覆盖运行，无额外源码复审门禁。Owner已确认本次从托盘正常退出；实际退出及锁仍须核验。旧生产59F1983...仅在最终完整回归通过后替换。

## Regression finding
首次最终全量3145PASS/1FAIL/1SKIP128.52秒，原7天规则bad-date测试发现新增WorkItem显示时间解析不能破坏原未知日期处理。复用原inquiry_intake_at的容错解析作为内部纯函数，未知日期仅显示None；新增三项回归，不弱化原7天保守跳过。
