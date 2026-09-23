# Task: CANONICAL-INTEGRATION-001

status: in_progress
actor_role: Architecture Codex
module: architecture
reports_to: CEO / Architecture Chat
execution_mode: FAST_V1
architecture_impact: REQUIRED

## Problem

Research V1、Sheets V1 与 Credential Vault 分散在 canonical main、备份分支和原 dirty checkout，尚未形成唯一代码基线。

## Goal

在独立 clean worktree 中把已完成成果安全统一到最新 `origin/main`，保留 Baseline V2 与安全备份。

## Current Facts

- 集成起点为 `origin/main` 的最新 Baseline V2。
- Sheets 实现位于 `backup/sheets-v1-before-baseline-v2`，其 HEAD 为 `c3a597d963ed418e45f6c7c75249bdef1b8147b4`。
- Vault 仅从明确列出的本地源码、测试和历史 Task 导入；不得导入 runtime Vault 或 Secret。
- 原 dirty checkout 只读，不执行 reset、clean、rebase 或 branch switching。

## Required Context

- `AGENTS.md`
- `docs/AI_TEAM.md`
- `docs/TASK_PROTOCOL.md`
- `docs/BOUNDARIES.md`
- `docs/MODULE_INDEX.md`
- `docs/PRODUCT_BASELINE.md`
- `docs/modules/CORE.md`
- `docs/modules/SHEETS.md`

## Write Scope

- `src/sheets/`、`tests/sheets/`
- 明确列出的 `src/core/` Vault 源码和 `tests/core/CredentialVault.Tests.ps1`
- 本 Task 指定的历史 `tasks/` 文件及本 Task Packet
- `docs/modules/SHEETS.md`、`docs/modules/CORE.md`

## Scope

- 移植四个已确认 Sheets 实现提交，选择性恢复 live-read 历史证据。
- 导入已确认 Vault 源码、测试和无敏感信息的历史 Task。
- 依据实际实现最小同步 Sheets/Core canonical 文档。
- 执行适用测试、静态检查、Secret 与 Git 一致性检查，并正常推送 main。

## Non-scope

- Workflow、Research 新功能、Sheets 新功能或真实外部 smoke。
- Vault Python bridge、GUI 新功能或 Secret 迁移。
- 合并/清理原 dirty checkout、删除任何备份或 force push。

## Requirements

- 最新 Baseline V2 与 Research canonical 实现不得被旧文档覆盖。
- 不导入任何真实 credential、cookie、token、runtime data 或用户本地参考文件。
- 保持 `research -> core`、`sheets -> core`，不得引入 Research/Sheets 互相依赖。

## Acceptance

- [ ] canonical 分支同时包含 Research V1、Sheets V1 和 Vault 源码/测试。
- [ ] Sheets/Core module docs 与真实实现一致且保持简短。
- [ ] Research、Sheets、全量 Python 测试与静态检查通过。
- [ ] Vault 测试仅使用临时 synthetic 数据并通过。
- [ ] `git diff --check`、Secret scan 与 tracked runtime 检查通过。
- [ ] 正常推送最新 main，原 dirty checkout 和两份备份保持不变。

## Execution

仅在 `codex/canonical-integration-001` clean worktree 执行；完成后 commit、fetch 复核并正常 push `HEAD:main`。禁止真实 Google Sheet 写、网页 live smoke 或真实 Vault 访问。

## Final Report

使用 CEO 指定的本 Task 精简报告格式，列出整合内容、验证、canonical HEAD、push 和备份状态。
