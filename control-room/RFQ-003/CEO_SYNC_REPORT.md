# CEO 同步 V1.3：V1.2 资料警报与冷却显示修复

状态：修复版已覆盖并待命，本次增量 REVIEW_REQUIRED；真实订单3/4发送，
第四笔五站无报价按规则未发，等待 Owner 核对型号/业务处置。不得称四笔全部完成。
范围：Owner 2026-10-07 要求跟踪当前四条订单、修复确认的问题、覆盖 V1.2，
由 CEO 再把适用改动同步给 V1.3 Codex。本文不授权开发/运行 V1.3。

## 已确认原因与最小修复

1. 原始评级 S 不在原有 A/B/C 合法集合，按既有单行数据异常跳过。
   Owner 改为 A 后原队列正确恢复；采购正常完成，问题不是发送被阻止。
   旧 invalid-input 活跃警报没有解除，GUI 把成功订单仍显示红色“资料待核对”。
2. `src/workflow/v12_store.py`：原有修正资料 -> QUEUED / HUMAN_RESOLUTION_RECORDED
   转换中，复用 `_recover_alerts`，同事务解除 DATA_QUALITY、scope=invalid-quantity。
   这个历史 scope 同时用于数量和新增关键资料校验；其他 scope 不解除。
   保留原事件/警报历史，记录 ALERT_RECOVERED，不删库、不改身份、不放开 gate。
3. `src/launcher/v12_gui.py`：兼容已修正但旧版未解除警报的历史成功订单。
   只在 PURCHASE_RECORDED + 旧 DATA_QUALITY 无效输入/数量码 + 后续明确
   HUMAN_RESOLUTION_RECORDED 事件时，不再把该过期警报当作当前 GUI 警报。
   投影严格只读，不修改历史生产DB；客户资料、提交、安全、通知警报仍显示。
4. `src/gui/contracts.py`：RunSession 末尾新增可选 row_cooldown_until，默认 None，
   既有构造兼容。`src/launcher/backend.py` 用薄 wrapper 暴露原 stop.wait(180)
   的期限，finally 清理，不改等待、停止、行顺序、末行/空轮询规则。
   `src/gui/app.py` 明示“冷却 MM:SS”/“订单处理中”，不再让运行中等待误显即将轮询。

## V1.3 同步边界

- 优先复用共享资料警报生命周期和 DTO；只同步本分支的适用 diff，不复制一套 store/GUI。
- 如果 V1.3 从 B1 之前分叉，必须同时核对 RFQ-003 B1 修复：预入队不算真实开始；
  启动只隔离实际执行后未闭环的订单。不要恢复“所有 queued 都中断”的旧逻辑。
- V1.2 180秒行间冷却只属于采购，禁止给 V1.3 报价腿加同样节流。
  V1.3 row_cooldown_until 默认 None，不应受 V1.2 专属等待影响。
- 不把 PURCHASE_RECORDED 当作“报价完成”，不合并两个模块的业务终态。
- inquiry_id、record_identity、订单唯一定位、Save-and-Send 一次性 durable proof、
  SUBMIT_UNCONFIRMED、STATUS_WRITE_PENDING、固定 CDP/profile、人工验证页保留不变。
- 不映射 S -> A，不扩大评级规则；是 Owner 在源表修正后恢复，不由程序猜评级。
- 不批量重放历史订单、不重新发采购、不清 workflow DB/授权/profile/cookies。
- CEO 将 reviewed commit/diff 和此报告交 V1.3 Codex；执行者补同等离线回归，
  Review 独立进行。这里不自动向另一个 chat 发消息或实施 V1.3。

## 验证及发布

准确的离线验证：相关六模块 focused 999 passed / 1 skipped（36.75s）；
完整 safe/offline 1046 passed / 11 skipped（37.51s）；Ruff src tests / diff check PASS。
现有 BuildOnly、frozen self-check、clean staged release scan 已通过。
待部署候选 SHA256：340D7F7E7E818FA74DE36B138B205F5905F320406FD8D391EF860BD052529E5F。
当前四笔：3笔 PURCHASE_RECORDED、各唯一 SAVE_CLICK_COMPLETED、重要通知各2次
投递成功，Sheets均“发给采购”；1笔 NO_MATCHING_PRODUCT / RESEARCH_FAILED、
五个价格来源均无结果、零提交、异常邮件成功、Sheets仍“未发”。
不放宽无报价不采购规则，不猜型号，不直接修生产DB，不重复发送。
旧空品牌测试行不属于这四笔，不补发。Owner 的当前履约授权独立记录于 TASK_SPEC。
实际覆盖目标：D:\Program_Leo\INSO_Leo\dist\INSO_V1.2\INSO_V1.2.exe。
部署 SHA256 与上述候选一致；deployed self-check exit0，runtime junction未变。
备份：D:\Program_Leo\INSO_Leo\dist\release-backups\INSO_V1.2-20261007-before-input-alert-cooldown-fix。
正常关闭空闲GUI，computer-use启动新版待命，不点击开始，不自动重跑第四笔。
截图接口超时，窗口启动可确认；新版真实订单端到端尚未验证，保留 UNKNOWN。
远端已 fast-forward 到 CEO B1 批准基线 c8d514e；本次 diff 独立 Review，不覆盖
旧 REVIEW.md PASS，不冒充它已经批准本次改动。提交后验证 local/remote 相同。
真实履约观察与离线测试必须分开；禁止拿离线 passing 代替订单发送/表格写回证据。
客户订单原始输出、价格、客户资料、授权内容不进入 Git；只记录匿名结果数量。
