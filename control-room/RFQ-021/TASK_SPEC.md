# RFQ-021 — 最终发布候选集中交付（2026-11-15）

**状态：`READY_FOR_CEO_RELEASE_REVIEW`（源码/测试/候选/切换材料全部就绪，未部署、未切换、未启用业务）。**

## Owner 目标

一次性解决 B5、B6、B7 三项剩余阻断，完成测试、重建最终候选，并交付 Owner 可照着做的安装与回滚方案。不拆成多个 RFQ，不为普通优化扩大范围。

## 固定对象

- 工作树：`D:\Program_Leo\INSO_Leo\.worktrees\v16-rfq016-stabilization`（复用）。
- 分支：`workbuddy/v16-rfq016-stabilization`。
- 上一轮已审源码基线：`25894eface6ea622153d1573c19d0ca6b9ad72aa`（RFQ-018 PASS；本轮在其上增量修改，未重写既有成果）。
- 本轮源码提交：见 `EXECUTION_LOG.md`（构建前提交，构建只从该提交产出）。
- 构建环境：RFQ-020 建立的 `.venv-release`（Python 3.12.10 / Tk 8.6.15 / PyInstaller 6.16.0，锁文件未改）。

## 本轮必须解决的三项阻断

| 编号 | 问题 | 本轮要求 |
|---|---|---|
| **B7** | 正常 GUI 启动会执行 DB 迁移/恢复并启动 IMAP/SMTP，无法当作"只看界面" | 提供不启业务、不迁移、不读 IMAP、不发 SMTP、不连 CDP 的安全预览；普通启动不得意外触发真实副作用 |
| **B5** | full Start 不限订单/模块/写入范围，`inquiry_ids` 只限 inquiry | 受控试运行入口：限制目标订单、允许模块、外部写入范围；默认禁止真实效果；不允许隐式退回 full Start |
| **B6** | 跨服务 document hold 只在进程内，重启后 UNKNOWN 失去保护 | 写入意图在外部请求前可靠登记；未知结果阻断后续冲突写入；关键记录损坏/缺失 fail closed；不清历史 hold、不把旧 UNKNOWN 当已结算 |

## 允许 / 禁止

**允许：** 读 Git/文档/证据；修改 `src/`、`tests/`、`scripts/` 实现上述三项；写 RFQ-021 文档与证据；在隔离环境离线构建与自检；只读盘点生产现状；本地提交/推送原分支。

**禁止：** 停止/重启/覆盖运行中的 V1.6；操作受保护 Chrome CDP9222；正常 GUI 启动代替自检；业务 Start；真实 Google/INSO/SMTP 写入；修改或备份生产 SQLite；重下第 221 行；处理 SHAHAB/115；清除任何 UNKNOWN/hold；合并 `develop` 或晋升 `main`/`release/previous`；删除或跳过测试制造全绿。

## 必须交付

1. B7/B5/B6 的源码实现与负向回归测试。
2. 完整离线测试结果（含失败如实记录）。
3. 从本轮最终提交重新构建的独立 staging 候选：源码 SHA、构建输入哈希、EXE SHA256、完整清单、自检与扫描结果。
4. 安全 GUI 验证证据（显示、退出、再次启动，无后台业务线程/外部效果）。
5. 安装、备份、首次启动、业务启用条件、回滚的操作说明 + 校验/备份/安装脚本（本轮只准备，不执行生产切换）。
6. 阻断关闭情况与 `NOT_VERIFIED` 清单。

## 完成标准

- 三项阻断在源码与测试层面可验证；候选从本轮提交重建，且不携带任何生产数据库/配置/密钥/浏览器资料。
- 生产运行环境零改动：旧 EXE、进程、SQLite、Chrome 9222 均未触碰。
- 结论只能是 `READY_FOR_CEO_RELEASE_REVIEW` 或 `BLOCKED`；仍有阻断就集中列出，不降低安全要求。

## 证据

- 执行记录：[EXECUTION_LOG.md](EXECUTION_LOG.md)
- 安装与回滚：[INSTALL_AND_ROLLBACK.md](INSTALL_AND_ROLLBACK.md)
- 最终报告：[FINAL_REPORT.md](FINAL_REPORT.md)
- 机器可读：`docs/evidence/rfq021/rfq021-final-candidate.json`
- 候选清单：`docs/evidence/rfq021/INSO_V1.6-artifact-manifest.sha256`
