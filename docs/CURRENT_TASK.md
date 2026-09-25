# Current Task

Status: NONE

Goal: 等待 Owner / CEO 启动下一阶段。

Business Outcome: INSO_V1.1 GUI usability 与 Research / Workflow 结果状态契约已完成并通过 CEO Final Review。当前生产基线在 V1.0 launcher 之上补齐历史询价展示、重要程度、24 小时新旧结果视觉区分、stop-after-cycle 正确状态反馈、15 分钟倒计时，并将 Research 订单结果统一为成功 / 部分成功 / 异常三类展示。

Acceptance: NONE

Constraints:
- 保持已验收 Research 价格、MPN、汇率、货量、五源与 Excel 幂等规则不变。
- Research public status 为 SUCCESS / PARTIAL_SUCCESS / EXCEPTION / RETRYABLE_FAILURE；不再产生 MANUAL_REVIEW_REQUIRED。
- 五源均完成且无任何报价 -> EXCEPTION -> Workflow FAILED，无 retry；仅无库存报价 -> PARTIAL_SUCCESS；无正常报价且存在技术失败 -> RETRYABLE_FAILURE。
- SUCCESS / PARTIAL_SUCCESS / terminal EXCEPTION 均保留既有 safe Brand updater；EXCEPTION 的 Brand conflict/failure 不改变 FAILED 终态；RETRYABLE_FAILURE 即使耗尽 retry 也不写 Brand。
- 旧 Excel MANUAL_REVIEW_REQUIRED 与旧 SQLite MANUAL_REVIEW 保持兼容读取。
- Production GUI 当前 brand_updater 仍为 disabled / None，不新增 Google Sheet 写副作用。
- runtime 配置、OAuth grant、SQLite、browser profile、secret/token/cookie 继续 Git-ignored。
- CAPTCHA / OTP / 登录 / 设备验证继续由 launcher fail closed 并提示人工处理。
- 不 reset/clean/delete 历史 Research runtime worktree。

Done:
- GUI 订单表增加“重要程度”，结果区改为“询价结果”，展示 Research Excel 全部可识别历史记录。
- Research Excel canonical schema 增加 UTC ISO-8601 “处理时间”与隐藏 _research_status；旧 schema 无损兼容，legacy 时间不猜测。
- 24 小时内普通结果浅蓝显示，24 小时外或无时间 legacy 结果白色；部分成功/异常警示颜色优先。
- GUI 每秒只基于缓存 snapshot 重算轻量 row style；跨 24h 只更新 Treeview tag，不重读 Excel、不重绘整行。
- current-run metrics 与历史展示分离；history 由 Research-owned read_history contract + launcher cache 提供。
- stop-after-cycle 后按钮灰色禁用并显示“本轮订单处理中，正在安全结束…”，backend 真正 STOPPED 后才恢复“开始询价”。
- “下轮询价倒计时”使用 backend 真实 next-poll deadline；首次 poll 前显示“即将轮询”，停止/人工处理时 00:00。
- Research 无库存兜底改为 PARTIAL_SUCCESS；五源正常完成但无报价改为 EXCEPTION；技术失败且无报价继续 RETRYABLE_FAILURE。
- Workflow 将 EXCEPTION 映射为 terminal FAILED 且不 retry，同时保持 resolved_brand 的既有 safe Brand updater 行为。
- Brand updater 的 conflict/failure 不改变 EXCEPTION 的 FAILED 终态；RETRYABLE_FAILURE 第四次耗尽 FAILED 不触发 Brand write。
- GUI aging regression、Research/Workflow status regression 与 Brand updater regression 均有 deterministic tests。
- 最终验证：workflow/research/gui 相关 tests 277 passed；完整 deterministic pytest 365 passed、10 skipped；ruff 通过；git diff --check 通过。
- Windows mock GUI usability smoke 已完成；本轮 Research/Workflow 状态契约变更未执行额外 live Research smoke，deterministic evidence 已覆盖新路径。

Current: NONE

Next:
- Windows 发布阶段：PyInstaller/EXE、应用图标、双击启动、runtime 配置发现、单实例、发布目录结构与发布包 smoke。
- 发布后做长时间 soak / 资源稳定性验收，再决定是否增加开机自启。

Blockers: NONE

Owner Decisions:
- 24 小时内普通记录浅蓝；历史/legacy 白色；异常红色、部分成功警示色。
- Research 订单结果不再进入人工复核状态；运行环境安全验证仍由 launcher 人工处理。
- V1.1 验收后进入 Windows 发布阶段。

Branch: NONE

Last Good Commit: b56768f3f7a4cef4a52a7055a121235e64cbe2f6
