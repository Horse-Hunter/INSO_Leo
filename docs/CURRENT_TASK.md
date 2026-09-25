# Current Task

Status: ACTIVE

Goal: 交付 INSO_V1.1 GUI usability 修正：补齐重要程度、展示 Excel 历史询价结果、按 24 小时区分新旧记录、改进 stop-after-cycle 按钮语义，并把下一轮询价改为 15 分钟倒计时。

Business Outcome:
- 操作员打开 GUI 即可看到调研结果 Excel 中的历史订单，而不只看到当前 run。
- 表格补充“重要程度”，与 Research Excel 的“重要等级”原样一致。
- 最近 24 小时处理/更新的结果以浅蓝色强调；24 小时以外或没有处理时间的旧历史记录使用白色。人工处理/异常的警示语义优先于新旧颜色。
- 点击“本轮结束后停止”后，在本轮 due work 安全闭环期间按钮保持灰色禁用并显示“本轮订单处理中，正在安全结束…”，只有 backend 真正 STOPPED 后才恢复“开始询价”。
- “下次轮询时间”改为“下轮询价倒计时”，运行时按 15 分钟周期实时显示 mm:ss；停止请求后立即归零，STOPPED 保持 00:00。

Acceptance:
1. GUI 订单表列顺序固定为：型号 / 品牌 / 数量 / 重要程度 / 货量 / 市场最低参考价 / 总价 / 状态。
2. Order 展示 Contract 增加至少 importance 与 processed_at（或语义等价字段）；金额仍为 Decimal，GUI 不自行重算业务价格。
3. Research Excel canonical schema 增加可可靠判断 24 小时窗口的“处理时间”字段：
   - 新写入/更新的 inquiry 记录明确的处理/更新时间；
   - 使用无歧义、可稳定解析的时间格式（优先 ISO-8601，含时区/UTC 语义）；
   - 旧 workbook 自动兼容/迁移，不删除或重写已有业务值；
   - 旧历史行没有处理时间时保持空值，并在 GUI 中按历史记录白色显示，禁止使用文件 mtime、row number 或其他猜测方式推断时间。
4. 历史结果来源必须是 Research-owned canonical Excel，不从 Workflow SQLite 猜历史业务结果。GUI 不直接解析 Research Excel；由 launcher / Research-owned read-only seam 负责适配。
5. 保留“当前 run 结果”与“历史展示”两个概念：
   - 本轮发现/完成/处理中/待处理 metrics 仍只表达当前运行会话；
   - 订单表改为“询价结果”，展示 Excel 中全部可识别历史结果；
   - 建议新增 GuiBackend.get_result_history()（或语义等价的明确 contract），不要偷偷改变 get_current_run_results() 的既有语义。
6. 历史列表默认按 processed_at 新到旧排序；无处理时间的 legacy rows 放在有时间记录之后，并保持稳定顺序。
7. 颜色语义：
   - 最近 24h 且无警示状态：浅蓝色，推荐 #93C5FD 或与当前 dark theme 等价的高可读浅蓝；
   - >24h 或 processed_at 缺失：白色；
   - MANUAL_REVIEW / error / warning 继续使用既有黄色/红色警示语义，并优先于 24h 浅蓝色；
   - 选中行仍必须清晰可读；
   - 在“询价结果”标题附近增加简洁图例：蓝色：24小时内｜白色：历史。
8. stop-after-cycle UI：
   - RUNNING：按钮为“本轮结束后停止”；
   - 点击后进入 STOPPING_AFTER_CYCLE：按钮立即灰色、disabled，文本为“本轮订单处理中，正在安全结束…”；
   - 当前 cycle 的 due/claimed work 按既有 ProductionBackend 语义 drain；future RETRY_WAIT 不阻止结束；
   - backend 真正 STOPPED 后按钮才恢复“开始询价”；
   - 窗口 X graceful close 现有语义必须保留。
9. 倒计时：
   - UI label 改为“下轮询价倒计时”；
   - RUNNING 且等待下一 poll：显示 mm:ss，按 backend 的真实 next poll deadline 计算，不在 GUI 另造 scheduler；
   - 首次 Start 后、第一次 poll 尚未建立下一轮 deadline 时显示“即将轮询”；
   - 每次 poll 完成/进入下一 interval 后重新显示接近 15:00 的倒计时；
   - STOPPING_AFTER_CYCLE / STOPPED / MANUAL_REVIEW 显示 00:00；
   - stop request 后倒计时立即归零；
   - 不要求精确到毫秒，Tk 1 秒刷新即可，不能导致额外 backend poll。
10. ProductionBackend 应显式维护真实 next-poll deadline（或等价可信状态），不得把“最后 poll 开始时间 + 15 分钟”在 stop/manual-review 后继续暴露为下一轮。
11. 历史 Excel 读取需要缓存/增量策略：不得由 GUI 每秒完整 reload workbook。允许 launcher 在启动、workbook mtime/版本变化、Research 完成事件等边界刷新缓存；get_result_history() 应为轻量内存读取。
12. 现有 Production Launcher、15 分钟 scheduler、SQLite dedup/retry、Research 价格/MPN/汇率/来源/货量规则、OAuth/CDP、Brand write disabled、安全边界全部保持不变。
13. MockBackend 同步支持新 Contract，用于 GUI 演示和 deterministic tests；不要为 Mock 复制生产业务规则。
14. deterministic tests 至少覆盖：
   - importance 进入 GUI table；
   - 新 canonical Excel schema 的处理时间写入、旧 schema 无损迁移、legacy processed_at=None；
   - 历史全部展示、排序、新旧 24h 边界；
   - 24h 浅蓝 / legacy 白色 / warning override；
   - history getter 不导致 GUI tick 每秒 reload Excel；
   - STOPPING button 灰色禁用且不提前恢复；
   - stop 后 countdown=00:00；
   - RUNNING countdown 随时间下降并在 poll interval reset；
   - first poll“即将轮询”；
   - existing graceful close / production launcher regressions。
15. 运行 ruff check src tests、GUI/launcher/research relevant tests、完整 deterministic pytest、git diff --check。
16. 在 Windows 上做一次 GUI smoke：至少目视确认新增列、历史列表、24h/legacy 颜色、stop 文案、倒计时。无需重新跑完整外部 Research live smoke，除非实现触及 production runtime 行为或 deterministic evidence 不足。

Constraints:
- 不删除或覆盖现有 调研价格.xlsx；schema migration 必须向后兼容。
- 不用 Excel 文件修改时间推断订单时间。
- 不修改已验收的 Research 业务算法、Sheets pending 语义、Workflow dedup/retry。
- 不开启 Google Sheet Brand 写回。
- runtime 配置、OAuth grant、SQLite、browser profile、secret/token/cookie 保持 Git-ignored。
- 不 reset/clean/delete 历史 Research runtime worktree。
- 当前阶段不做 EXE/PyInstaller；V1.1 GUI 验收后再进入 Windows 发布阶段。

Architecture Decision:
- gui 仍只消费 GuiBackend/display contract。
- Research 继续拥有 Excel schema；若增加 read-only history reader，优先放在 Research 模块 Public 边界或 launcher 的窄适配层，不把 Excel 解析塞进 GUI。
- Current-run metrics 与历史结果展示分离，避免因为“显示历史”污染 run_id/session 统计。

Done: NONE

Current: 等待 Main Programmer 开发。

Next: Main Programmer 实现 -> deterministic tests -> Windows GUI smoke -> self-review -> commit/push -> CEO Final Review。

Blockers: NONE

Owner Decisions:
- 24 小时内普通记录使用浅蓝色强调；24 小时外及无时间 legacy 记录使用白色。
- stop-after-cycle 灰色文案采用“本轮订单处理中，正在安全结束…”。
- 结果区标题改为“询价结果”，图例显示“蓝色：24小时内｜白色：历史”。
- 下轮轮询使用 mm:ss 倒计时；首次 poll 未建立 deadline 时显示“即将轮询”；停止后归零。
- V1.1 完成后再做 EXE/Windows 发布。

Branch: feature/v1-1-gui-usability

Last Good Commit: 3788a6b795a26c8e1945dedfc08f14e01be18d04
