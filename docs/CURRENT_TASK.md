# Current Task

Status: READY_FOR_CEO_REVIEW

Goal: 移除 Research 的订单人工复核结果。调研有报价时归为成功或部分成功；五个价格来源均完成但完全无报价时归为异常；仅技术失败且无报价时继续 Workflow retry。

Business Outcome:
- GUI 和持久化 Excel 对每笔调研展示真实结果状态：成功、部分成功、异常。
- 无库存报价可作为部分成功的兜底报价；五个价格来源都完成但无任何报价时记为异常并停止该 inquiry，不等待人工复核。
- 报价来源技术失败且无正常报价时仍由 Workflow 按现有策略重试。
- 登录、CAPTCHA、OTP 等安全挑战继续由 launcher fail closed 并提示人工处理，不作为 Research 结果状态。

Acceptance:
1. Research public status 包含 SUCCESS、PARTIAL_SUCCESS、EXCEPTION、RETRYABLE_FAILURE，不再定义 MANUAL_REVIEW_REQUIRED。
2. 五个价格来源完成且全无报价时，Research 持久化 EXCEPTION 和可理解的型号/无报价备注；Workflow 直接记 FAILED，不进入 retry 或 MANUAL_REVIEW。
3. 只有无库存报价时继续使用原有兜底价格计算，并返回 PARTIAL_SUCCESS。
4. 无正常报价且存在价格源技术失败时仍返回 RETRYABLE_FAILURE，沿用现有 15/30/60 分钟 retry。
5. 成功/部分成功的价格算法、MPN、汇率、货量、来源、retry 与 Excel 幂等规则保持不变。
6. launcher 历史读取将 EXCEPTION 显示为“异常”；已存在 Excel 的 MANUAL_REVIEW_REQUIRED 状态继续兼容为“异常”。
7. Research deterministic tests 覆盖以上聚合、持久化与状态流转；Workflow tests 验证 EXCEPTION 直接 terminal FAILED 且无 retry；全量 ruff、deterministic pytest 与 diff check 通过。

Constraints:
- Research 调研结果不再要求人工复核；运行环境的身份验证和安全挑战仍须 fail closed。
- 保持 Research 价格、MPN、汇率、货量、五源、Brand 写回安全边界不变。
- Workflow dedup 与 retry 策略不变，除明确的 EXCEPTION terminal mapping。
- 保留旧 Excel 状态和已有 SQLite MANUAL_REVIEW 记录的读取兼容性。
- 不开启新的 Google Sheet 写入；不得提交 runtime 配置、OAuth grant、SQLite、browser profile 或 credential。

Architecture Decision:
- `ResearchStatus.EXCEPTION` 是已完成调研、全部报价来源无有效报价的终态；Workflow 映射至 `FAILED`。
- `MANUAL_REVIEW` 留作旧 SQLite 数据兼容状态，不由新的 Research result 产生。
- OAuth/CAPTCHA/OTP 等运行安全状态继续由 launcher 管理，与订单结果 status 分离。

Done:
- Research 无库存报价聚合映射为 PARTIAL_SUCCESS。
- 全部价格源无报价且无技术失败映射为 EXCEPTION；Workflow terminal FAILED 分支已实现。
- Research/Workflow/launcher 历史展示已统一；旧 Excel 与 SQLite MANUAL_REVIEW 数据兼容。
- GUI 每秒按缓存的 Research history snapshot 重算 row style；仅 style tag 改变时只更新对应 Treeview tag。
- deterministic regression 覆盖固定 history snapshot 从 recent 到 legacy 的 24h 边界迁移，并确认 Excel reader 只读取一次。
- `ruff check src tests`、GUI tests（36 passed）、完整 deterministic pytest（361 passed, 10 skipped）、`git diff --check` 通过。
- Self-review 完成；未执行 live Research smoke。

Current:
- CEO 对 commits 5bc988e / 4d75c96 的 Research / Workflow 状态契约复审通过：SUCCESS/PARTIAL_SUCCESS/EXCEPTION/RETRYABLE_FAILURE 映射、无库存兜底、无报价 terminal FAILED、技术失败 retry、旧 MANUAL_REVIEW 兼容均与已确认业务语义一致。
- CEO 指出的 GUI 24h 颜色过期 blocker 已修复并新增 deterministic regression；history getter 仍使用轻量内存缓存。

Next:
CEO Final Review；不要 merge main。

Blockers:
NONE

Owner Decisions:
- 24 小时内普通记录使用浅蓝色强调；24 小时外及无时间 legacy 记录使用白色。
- stop-after-cycle 灰色文案采用“本轮订单处理中，正在安全结束…”。
- 结果区标题改为“询价结果”，图例显示“蓝色：24小时内｜白色：历史”。
- 订单结果表状态只显示“成功 / 部分成功 / 异常”；异常使用红色字体。
- Research 不产生人工复核订单状态；只有全部五个价格源完成且无任何报价才返回异常。只找到无库存报价时返回部分成功；技术失败且无报价继续 retry。
- 下轮轮询使用 mm:ss 倒计时；首次 poll 未建立 deadline 时显示“即将轮询”；停止后归零。
- V1.1 完成后再做 EXE/Windows 发布。

Branch: feature/v1-1-gui-usability

Last Good Commit: 5bc988e
