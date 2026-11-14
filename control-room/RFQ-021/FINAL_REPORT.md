# RFQ-021 — 最终发布候选集中交付（最终报告）

**RFQ 状态：`READY_FOR_CEO_RELEASE_REVIEW`。未部署、未切换、未启用业务。**

```text
正在实现什么：
把最后三个"不能安全上线"的问题一次修完，并交出一个可追溯、可安装、可回滚的最终候选。

理想变化是什么：
以后装新版本，普通双击只是"看一眼"，不会偷偷跑业务；要跑业务必须写明订单、模块和写入范围；
即使程序中途崩掉，没确认的 Google 写入也不会因为重启就被当成没发生。

以前是什么：
双击就会连邮件、迁移数据库、启动业务线程；启动范围只能限制"询价单"，报价/TP/通知照跑；
跨服务写入保护只活在内存里，重启即忘。

现在是什么：
B5/B6/B7 三项阻断在源码和测试层面都已关闭；候选 EXE 从本轮提交重建并通过三种自检；
安装/备份/回滚手册与三个脚本已就绪。仍有一项环境层面的测试噪声需要 CEO 知悉（见"测试结果"）。

做完了什么：
安全预览模式、受控启动范围、持久写入意图账本、负向回归测试、最终候选构建与哈希、切换材料。

测试结果：
新增 35 项负向测试全部通过；所有受影响模块（launcher/research/sheets/inso/gui）2886 项全绿；
完整套件仍有少量与代码无关的失败，已在下方如实列出，未删除、未跳过任何测试。

你接下来需要做什么：
Review RFQ-021
```

## 1. 三项阻断的关闭情况

| 阻断 | 状态 | 证据 |
|---|---|---|
| **B7** 正常 GUI 有副作用 | **关闭** | 普通启动＝安全预览：不调 `start_process_services`、不迁移、不读 IMAP、不发 SMTP、不连 CDP；按钮禁用；`--start-inquiry` 缺范围直接拒绝 |
| **B5** 无受控启动范围 | **关闭（源码/测试层面）** | `RunScope` + `ExternalWritePolicy`；订单、模块、写入目标三重限制；写入需 `OWNER-APPROVED:` 审批串；范围只能收窄不能放宽 |
| **B6** 重启丢 UNKNOWN | **关闭（源码/测试层面）** | `workflow_write_intents` 在外部请求前落盘；UNKNOWN 跨进程保持阻断；账本损坏/不可读一律 fail closed |

**边界：** B5/B6 的"关闭"指实现与负向测试可验证，**不等于**真实业务已跑通。一次真实受控运行仍未执行，属 `NOT_VERIFIED`。

## 2. 关键设计（为什么不会偷偷放宽）

- **默认拒绝**：没有范围就 `SCOPE_MISSING`，按钮不可点；没有审批串就不允许任何写入目标。
- **单一收口**：Google 写入只经过 `begin_document_write` 一个租约；INSO 写入只在既有 `OwnerAuthorizedSaveAndSendGate` 外面套一层"范围先行拒绝"；通知派发只有一个函数。
- **只能收窄**：范围判断是"额外的前置拒绝"，原有的生产写入门（`SAVE_DATA` 永远关闭）原样保留，测试里专门钉住了这一点。
- **可恢复但不可自动放行**：账本里的 UNKNOWN 只能人工结算，代码里没有任何自动清理路径。

## 3. 候选与构建

| 项目 | 值 |
|---|---|
| 源码提交 | `8cded532221571e99697af7668634afab3ea07af` |
| 构建环境 | `.venv-release`（Python 3.12.10 / Tk 8.6.15 / PyInstaller 6.16.0，锁未改） |
| 候选 EXE | 8,455,788 B / `63bcd6cea66003f84ce016cfa8742dc479a9d67ce3f579a92b5b7c398bf4465b` |
| 产物 | 2,872 文件，无 `runtime/`、无配置、无数据库、无密钥、无浏览器资料 |
| 清单 | `docs/evidence/rfq021/INSO_V1.6-artifact-manifest.sha256`（2,872 行，自身 `d5cc3d4c…`） |
| 独立复算 | `verify_release_candidate.ps1`：2,872/2,872 一致，0 缺失 / 0 不一致 / 0 多余 |
| 自检 | `--self-check` 0；`--idle-self-check` 0；`--preview-self-check` 0（两轮）；扫描 `RELEASE_SCAN_OK` |

RFQ-020 的 `b358f687…` 已明确不作为本轮源码的构建证据。

## 4. 安全 GUI 验证（B7 的实证）

`--preview-self-check` 在真实候选 EXE 上连续两轮：

- 标题正常、界面渲染成功、状态"已停止"；
- 开始按钮文本「安全预览（不启动业务）」、`state=disabled`；
- `business_thread_started=false`、`order_thread_started=false`、`mail_service_started=false`、`process_services_consumed=false`；
- 两轮都成功获取/释放单实例锁 → 退出干净、可再次启动。

报告：`docs/evidence/rfq021/v16-preview-self-check.json`。

## 5. 测试结果（如实）

- 新增负向测试 35 项：全通过。覆盖范围校验、写入前后拒绝顺序、崩溃后阻断、hold 不被释放动作结算、账本不可用 fail closed、预览启动不启服务、无范围启动被拒、按钮禁用态。
- 受影响模块合并运行（`tests/launcher research sheets inso gui`）：**2886 passed，0 failed**（161.60 s）。
- 完整套件：**4,223 项、4,220 通过、2 失败、1 跳过**（382.18 s）。
- 这 2 项失败是同一个用例的两个参数：`test_backend_closes_only_owned_browser_after_runtime_thread_exits[False]/[True]`（停止后状态停在"采购模块暂停"）。
- **对照：未修改的父提交基线在同一环境跑出 2 failed + 4 errors + 4,181 passed，两个失败就是同样这两个 nodeid。** 失败集合没有变化，属既有负载敏感问题，不是本轮改动引入。
- 这两项单独运行连续 6 次全部通过，且包含在刚才 2,886 项全绿的那次运行中。
- 过程中另有一次沙箱受限运行出现 4 项 `readonly database` 失败，放行后不复现；**没有删除、跳过或 deselect 任何测试来换取全绿。**

## 6. 切换材料

`control-room/RFQ-021/INSTALL_AND_ROLLBACK.md` 给出可执行步骤：离线校验 → 程序/配置快照 → 有界停机与中止条件 → 停机后一致性 DB 备份 → 受控安装 → 首次仅安全预览 → 业务启用条件 → 回滚（默认不回数据库）。

配套脚本：`verify_release_candidate.ps1`、`backup_running_release.ps1`、`install_release_candidate.ps1`。本轮只准备，全部未在生产执行。

## 7. 仍未验证 / 仍需 Owner 决定

1. 新候选未安装、未作为正式程序运行；只有三种自检模式被执行。
2. 一次真实受控业务运行（哪怕只读）未执行。
3. 停机耗时、GUI 停刷、Chrome 残留页仍为历史观察项。
4. 构建不可位级复现：哈希只标识这一次构建。
5. 旧运行 EXE `E9E3DA33…` 的源码血缘仍未证明。
6. 221 行 / SHAHAB-115 / 3 条 V13 hold 保持原状，未处理。
7. `sqlite3.exe` 与 `.backup` 在本机的可用性未验证。

**下一步只能是 CEO Review；安装、停机与业务启用各自需要 Owner 单独授权。**
