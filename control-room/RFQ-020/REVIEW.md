# RFQ-020 — CEO 独立 Review（2026-11-14）

**结论：`PASS_BUILD_AND_ISOLATED_SELF_CHECK / RELEASE_HOLD / NOT_INSTALLED / BUSINESS_GUI_BLOCKED / OWNER_APPROVAL_REQUIRED`.**

## Review 依据及验收范围

CEO **实际读取并交叉核对**执行者 `6f1b1d250f60c61b630f97f1eb5c55628769f2a4` 和文档补充 `aece41a8cac79ae031fab43e59c273c6bfc317b5` 的 GitHub diff、[执行记录](EXECUTION_LOG.md)、[最终报告](FINAL_REPORT.md)、[JSON](../../docs/evidence/rfq020/rfq020-build-2026-11-14.json)、[完整产物文件清单](../../docs/evidence/rfq020/INSO_V1.6-artifact-manifest.sha256)，以及 `scripts/build_windows_release.ps1`、`scripts/windows_release_entry.py`、`src/core/app_paths.py`、`src/launcher/backend.py`、`scripts/scan_release_artifact.py` 的实际源码。相对 RFQ-019 CEO Review `64dba150`，变化仅是控制室文档、证据和为保证清单哈希不受 Git EOL 影响的 scoped `.gitattributes`；**没有业务源码、测试、构建脚本、Spec、lock 变更**。固定已审源码仍为 `25894eface6ea622153d1573c19d0ca6b9ad72aa`。

### 已接受的构建和 staging 自检证据

- Executor 报告独立 release venv 使用 Python **3.12.10** / Tk **8.6.15** / PyInstaller **6.16.0**，按锁文件安装 42 个包且 `pip check` 无依赖冲突；源锁未改。
- 执行规范 `scripts/build_windows_release.ps1 -BuildOnly -Version 1.6`，只写入 `build/windows-release-stage-1.6/dist/INSO_V1.6/`，产出 EXE **8,436,056 bytes**，声称 SHA256 **`b358f68715f9e1dadeae19d5ad5b0f517664756105ebf1fcea1b843dc482d29c`**；产物 2,872 文件约 261 MB，无 `runtime/`。**此哈希是由 Executor 对本地候选运行后报告的，CEO 没有远程访问 Windows 候选 EXE 本体进行独立重算。**
- CEO **从 GitHub 实际读取全部 2,872 条 manifest 记录**：全部符合 SHA256+相对路径格式，2,872 个路径无重复，EXE 首行 SHA 与执行报告一致，无任何 `runtime/` 路径。CEO **独立在审查环境用 SHA256 实现重算下载内容**，得到清单文件自身哈希 **`c8806aea1b4d9f3df1d39261bc4aa81a213ab3ea9c335b4a40970f12c57d5b65`**，与 Executor 的证据完全一致；算法先以字符串 `abc` 的标准哈希做了正确性检查。`.gitattributes` 为清单文件设置 `-text`，合理地避免 autocrlf 影响哈希追溯。
- Executor 报告 script-internal `--self-check`、手工 `--self-check` 均 exit 0；`--idle-self-check` exit 0、约 3 秒，界面已渲染、状态“已停止”、业务/订单线程均未启动；离线扫描 `RELEASE_SCAN_OK`。CEO 在 `windows_release_entry.py:79-103,155-195,234-256` 验证这两条分支直接返回，不经过 `src/gui/main.py` 的正常入口及 `start_process_services()`；`src/core/app_paths.py:18-25` 证实 frozen 程序根目录为 EXE 父目录。因此**仅在 staging 自检这种有限场景**可合理预期不使用生产目录资源。
- Executor 在 **22:38–22:45 自检窗口**前后只读比对：旧 EXE SHA `E9E3DA33…`、app PID38948/watch34304、SQLite 文件大小和 mtime、WAL/SHM、Chrome9222 的 15 页均未改变。之后旧程序继续运行业务；其**后续** SQLite mtime 和页数发生变化。不能把前述窗口证据说成整晚生产环境绝对不变。CEO 无法独立归因后续变化于旧程序、其他操作或系统事件，仅确认 Executor 声明本 RFQ 未连接受保护 CDP 或写生产 DB。
- 回滚资产仅进行了只读盘点：运行中旧版 EXE `E9E3DA33…` 的**当前完整程序+配置+一致数据库备份**尚不存在，不能将零散 `_internal.prev-*`、EXE-only、旧版本备份冒充当前可用回滚。B3/B4 未关闭。

### 记录瑕疵（不阻止本次 staging PASS；**安装前必须修正/核实**）

1. 执行者文档/JSON 标识了 `2026-11-14 23:00+08:00` 的后续观察与生成时间，但其 GitHub 补充提交 `aece41a8` 的提交时间约为当日 22:50+08:00；时间顺序**自相矛盾**。请由 Executor 新窗口核对主机时间/时区/记录生成来源，在发布清单中用可验证的实际观测时间补正，不据此推导出发生了未授权行为。
2. `EXECUTION_LOG.md` 称 `control-room/RFQ-019/REVIEW.md` 在分支不存在，但 CEO **实际已从当前 Executor 分支及 develop 成功读取该文件**；`docs/BRANCH_POLICY.md` 在 Executor 分支确实未找到，但在 `develop` 存在。下一窗口需要**显式读取最新 develop、按分支记录文件可见性**，修正交接文档陈述，避免将旧 workspace 的“未找到”当作整个仓库不存在。
3. 本轮候选 EXE 没有被上传到 GitHub；manifest 可验证只证明**文档自身一致和其所声明的文件名与 SHA**，**不等价于 CEO 重新计算现场全部 2,872 个真实候选文件的 SHA**。任何安装前由 Executor 重新针对 staging 实物跑全量 manifest 校验并记录执行结果，锁定候选目录，期间不重新构建/增删文件。

### 生产发布仍然 HOLD

- **B1/B2 已在本轮 staging 证据范围内关闭**：release 构建环境可用，固定 SHA 对应的候选包已在 Executor 本地生成、自检。尚未完成安装链、实机正常 GUI 验收。
- **B3/B4 未关闭**：没有完整、哈希可核对的现行旧版回滚资产，也没有有界正常停机和无在途证明。用户仍未批准停机、生产数据库备份、覆盖安装。
- **B5/B6/B7 未关闭**：正常 GUI 即调用 `start_process_services()`，可能迁移/恢复生产 DB，启动 IMAP/SMTP；full Start 不保证只一单；跨服务 document hold 为进程内，重启不能证明 UNKNOWN 已结算。因此**严禁用正常 GUI 启动代替 staging idle 自检**，也不能因为候选 BUILD PASS 自动启用业务。
- 旧版业务保护不变：221 行已 SAVED `rec_440fafd372440ecf9dacabf660dd155d` 禁止重放；SHAHAB/115 `MANUAL_REVIEW/RECONCILIATION_UNREADABLE` 原生收据 `NOT_VERIFIED` 禁止自动补单；3 个 V13 报价 hold 不清。Chrome CDP9222 与生产 SQLite/WAL/SHM 不触碰；`main`、`release/previous` 不晋升，`develop` 不合入业务源码。

**下一最快安全路径**：不重复 RFQ-016～020 的已 PASS 步骤。先**一次性**设计并离线验证 B5/B6/B7 的**无真实外部效果的 GUI/业务受控试运行入口**，保证不会自动接入 IMAP/SMTP/生产 DB、不会复用旧 UNKNOWN、不会因为 full Start 对其他订单/模块产生写入。与此同时准备 B3 完整回滚和 B4 授权维护窗口（只有 Owner 单独批准才可执行生产备份/停机/安装）。不应先覆盖旧 EXE 再补安全开关；此类新业务源码改动会产生**新 SHA 和新候选**，必须重建/重测受影响范围并重新审核，不能继续把 `b358f687…` 当新代码的产物。

**最终：`PASS_BUILD_AND_ISOLATED_SELF_CHECK / RELEASE_HOLD / NO_AUTOMATIC_INSTALLATION`.**
