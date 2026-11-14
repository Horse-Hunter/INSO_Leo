# INSO LEO — RFQ-020 CEO Review（2026-11-14）

**当前状态：`RFQ020_PASS_BUILD_AND_ISOLATED_SELF_CHECK / RELEASE_HOLD / NOT_INSTALLED / RFQ019_PREP_PASS / RFQ018_SOURCE_PASS`。** 最新审核：[RFQ-020 CEO Review](RFQ-020/REVIEW.md)，执行证据：[EXECUTION_LOG](RFQ-020/EXECUTION_LOG.md)、[JSON](../docs/evidence/rfq020/rfq020-build-2026-11-14.json)、[完整 SHA256 清单](../docs/evidence/rfq020/INSO_V1.6-artifact-manifest.sha256)。

- **候选存在且 staging 自检 PASS（仅按 Executor 实测）**：固定代码 `25894efa`，离线 Python3.12.10/Tk8.6.15/PyInstaller6.16.0，`-BuildOnly` 生成候选 `build/windows-release-stage-1.6/dist/INSO_V1.6`，EXE 8,436,056 B / `b358f687…`、2,872 文件、无 `runtime/`；`--self-check=0`、`--idle-self-check=0`（3秒/停止/无业务线程），扫描通过。CEO 从 GitHub 校验清单 2872 无重复文件路径，并独立重算 manifest SHA256 `c8806aea…` 匹配。**CEO 未验证 Windows EXE 实物字节，也未实机执行自检。**
- **现场不变要限时表达**：Executor 比对 22:38–22:45 自检窗口生产 EXE/PID/SQLite size+mtime/Chrome15页不变；稍后自报生产 DB mtime 和 Chrome 页数变化，属于继续运行环境的动态观察，**不能称整个 RFQ 全程无变化或独立证明变动原因**。记录中的 23:00 观测时间早于其 22:50 Git 提交不合时序，正式发布前澄清。
- **B1/B2 阶段性关闭，B3/B4/B5/B6/B7 仍发布阻断**。无完整当前旧版程序+配置+一致 DB 回滚备份、无授权干净 Stop；正常 GUI 启动带 DB/IMAP/SMTP 副作用，full Start 不限单笔，重启丢 process-local document hold，禁止安装/正常 GUI/真实业务 Start。当前旧 EXE `E9E3DA33…` 仍为旧生产候选；其源码血缘不可证。
- **保护**：221 SAVED `rec_440fafd372440ecf9dacabf660dd155d` 不重下；SHAHAB/115 `MANUAL_REVIEW/RECONCILIATION_UNREADABLE` 未证真实采购；3 条 V13 报价 hold 保留。不能操作 Chrome9222、生产 SQLite/WAL/SHM、外部 Google/INSO/SMTP 或晋升分支。
- **接管纠正**：RFQ019 REVIEW 在 Executor 分支和 develop 均存在；`docs/BRANCH_POLICY.md` 只在 develop 存在。下一个窗口明确逐分支读取，不据旧工作树缓存判断仓库全局文件缺失。候选 manifest 可检不代替真实 staging 文件 re-hash。
- **下一步建议**：一次性有界推进 B5/B6/B7 的离线受控启动保护设计与测试，**需 Owner 新授权才能改源码**；届时因源码新 SHA 需重新 build 候选。B3 回滚备份和 B4 停机另按 Owner 维护窗口批准，不自动连锁。
