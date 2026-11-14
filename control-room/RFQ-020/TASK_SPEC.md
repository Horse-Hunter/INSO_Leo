# RFQ-020 — 隔离候选构建与发布自检（2026-11-14）

**状态：`PASS_BUILD_AND_SELF_CHECK / INSTALL_NOT_AUTHORIZED / NOT_DEPLOYED / NOT_MERGED / B5-B7_BLOCKED`。**

## Owner 目标

在 RFQ-018 源码 `PASS_SOURCE_SAFETY_SCOPE`、RFQ-019 发布准备 `BLOCKED`（正常 GUI / 业务试运行）的前提下，只做**可验证的候选构建与自检**，把「源码 SHA → 构建输入 → 候选 EXE → 产物清单 → 自检结果 → 回滚资产」这条链补上；不部署、不停机、不触碰生产。

本轮 Owner 授权范围（唯一）：

1. 在与生产隔离的目录创建 release Python 环境、按锁定依赖安装；
2. 用规范脚本 `-BuildOnly` 构建候选，不覆盖 `dist/INSO_V1.6`；
3. 运行可证明无业务副作用的 `--self-check` / `--idle-self-check` 与离线产物扫描；
4. 只读盘点旧 EXE、`_internal`、配置、SQLite/WAL/SHM、运行状态与回滚路径。

**不授权**生产部署、停机、覆盖安装、正常 GUI 启动、业务 Start、真实外部写入。

## 固定对象

- 工作树：`D:\Program_Leo\INSO_Leo\.worktrees\v16-rfq016-stabilization`（复用，不新建第二个）。
- 分支：`workbuddy/v16-rfq016-stabilization`。
- 固定已通过源码：`25894eface6ea622153d1573c19d0ca6b9ad72aa`（RFQ-018 最终 PASS）。
- 本轮工作树 HEAD：`505d9590a2726c0ec27f2c090d28616e528a6470`（`25894efa` 的后代，仅 control-room 文档 + evidence 差异；`git diff 25894efa..HEAD -- src tests scripts packaging requirements-windows-release.lock` 为空）。
- 生产 EXE：`dist/INSO_V1.6/INSO_V1.6.exe`（本次未替换）。
- 生产数据库：`dist/INSO_V1.2/runtime/production/workflow.sqlite3`（`runtime` junction → `dist/INSO_V1.4/runtime`）。
- Chrome/CDP：`127.0.0.1:9222`（未触碰）。

## 允许 / 禁止

**允许：** 读 Git/文档/证据；只读进程/文件聚合查询；在 `.venv-release` 隔离环境安装锁定依赖；`-BuildOnly` 构建到 `build/windows-release-stage-1.6`；候选 `--self-check`/`--idle-self-check`/离线扫描；写 RFQ-020 文档与证据；本地提交/推送原分支。

**禁止：** 停止/重启/覆盖 V1.6；操作受保护 CDP9222；正常 GUI 启动或业务 Start；真实采购/报价/Google 写入/SMTP；修改生产 SQLite/WAL/SHM；清除 UNKNOWN/hold；重下第 221 行；处理 SHAHAB/115；合并 `develop`；晋升 `main`/`release/previous`；修改 RFQ-018 已 PASS 的业务源码；重跑未变化的 4188 项全量测试。

## 必须交付

1. 构建环境与锁定依赖的实测证据（解释器、Tk、PyInstaller 版本、`pip check`）。
2. 候选构建：固定源码、构建脚本/依赖锁/Spec/图标哈希、候选 EXE SHA256、完整产物清单与聚合哈希。
3. 自检证据：`--self-check`、`--idle-self-check` 退出码/耗时/报告内容、离线扫描结果，以及**自检前后生产资源不变的证明**。
4. 只读回滚资产盘点：旧 EXE、`_internal`、配置、SQLite/WAL/SHM、备份集、junction、`_internal.prev-*`。
5. RFQ-020 `TASK_SPEC`/`EXECUTION_LOG`/`FINAL_REPORT` + 机器可读证据 + 交接记录。
6. 未完成项明确标记 `NOT_VERIFIED`，不扩大任务范围。

## 完成标准

- 候选构建、自检与文件溯源可验证 → `PASS`；否则报告具体阻断原因。
- 生产进程、生产 EXE、生产 SQLite、Chrome 9222、历史 UNKNOWN/hold 均保持原状。
- 候选构建成功**不**触发安装或业务启动；B5/B6/B7 仍为业务试运行阻断项。

## 证据与下一步

- 执行记录：[EXECUTION_LOG.md](EXECUTION_LOG.md)
- 最终报告：[FINAL_REPORT.md](FINAL_REPORT.md)
- 机器可读证据：`docs/evidence/rfq020/rfq020-build-2026-11-14.json`
- 完整产物清单：`docs/evidence/rfq020/INSO_V1.6-artifact-manifest.sha256`（2872 行）
- 下一步：CEO 独立复核 RFQ-020。安装、停机与业务 Start 均需 Owner 单独授权。
