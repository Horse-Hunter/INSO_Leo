# INSO LEO — 三条长期分支与 Owner 验收晋升制

**生效：2026-11-14。唯一版本晋升决定人：Owner。** 每个新 CEO/Executor 必须读此文件。三条长期线指 Git 源码；Windows EXE、数据库、配置和 Chrome 是另外的运行资产，**Git 分支移动绝不等于实际部署或回滚**。

| 长期分支 | 职责 | 允许变动 |
| --- | --- | --- |
| `develop` | 前瞻版集成：DeepSeek/多个 Agent 的新代码及正式安装试运行候选 | 仅经过 Review 的功能/修复合入；允许开发提交 |
| `main` | **Owner 已验收的现版**；生产基准而非最近部署候选 | **只在 Owner 明确说“前瞻版切换为现版本”后晋升** |
| `release/previous` | 上一次 Owner 已验收的现版；用于回退对照 | 随正式晋升一次更新，平时只读 |

## 新窗口必须先定位正确分支

GitHub 默认分支为 `main`；自 2026-11-21 起 `main` 是 **Owner 验收的 V1.6 现版**（`d954e0a5`），不再是历史 V1.1。**CEO/Executor 新窗口仍须先显式打开 `develop` 的 `AI_START_HERE.md`、本制度和当前 RFQ 文件**：`main` 是生产基准，不是开发或管理入口，也不是最近一次部署候选。若当前分支/现场/Owner 验收证据无法确认，停止版本指针变动，先做只读核实。对于本项目，工作会话可断、Windows 业务进程可能仍在运行；续接时先检查旧进程与真实业务状态，禁止重复启动。

## 严格区分 4 种状态

`开发完成` → `已打包/部署` → `试运行中` → `Owner 确认稳定并批准晋升`。

前三项**全部仍属于前瞻版**：正式 EXE 覆盖、启动成功、自然轮询、测试通过、连续稳定多天，都**不能**自动推进 `main`，也不应自动改写 `release/previous`。试运行持续多久由 Owner 决定，没有默认天数/自动晋升计时器。CEO/Executor 只能提出附证据的晋升建议。

## 首次对齐已完成（2026-11-21，Owner 授权）

首次对齐已按“首次对齐与日常晋升不同”一节完成，此前的过渡状态一并作废：

- `main`：`be9d0a51`（历史 V1.1）→ **`d954e0a5`（V1.6 现版）**，纯快进，未强推。EXE `9a0cb3d3…`，清单 `5bd7d7a7…`（2,872 文件）；审核依据 `control-room/RFQ-024/REVIEW.md`。
- 晋升前指针全部以 annotated tag 冻结，可永久追溯：`release/v1.1-main-superseded-20261121`（`be9d0a51`）、`preserve/sheets-v1-local-main-c3a597d9`（本地 `main` 曾停留的 SHEETS 线 `c3a597d9`，含 5 个不在 `origin/main` 的提交）、`release/previous-superseded-20261121`（`d244241e`）、`release/v1.6-official-20261121`（`d954e0a5`）。
- `release/previous` **仍停在 `d244241e`，状态仍为 `NOT_VERIFIED`**。按 Owner 2026-11-21 指令与本节“不得冒充”原则，**没有把它改指历史 V1.1**：本项目尚不存在“经 Owner 在三分支制度下验收过的上一正式版本”，用 V1.1 顶替即为伪造旧版关系。真正的运行级回退证据另记于 `control-room/RFQ-025/`（上一装机版 EXE `fa7a8544…`／源码 `64d3ec2c`，实物保留在 `dist/INSO_V1.6/INSO_V1.6.exe.prev-20261120T065005Z`），但它同样不是 Owner 验收过的正式版。
- `develop`：自 `9ad9ccb8` 起长期只承载政策/文档，已与 V1.6 源码线分叉；2026-11-21 以合并（非强推、非重置）把已验收 V1.6 源码带入 `develop`，此后 `develop` 才真正成为 V1.7 开发与集成分支。`workbuddy/v16-rfq016-stabilization` 保留不动。
- 历史事实（保留追溯）：`develop` 建于 `9ad9ccb8dce6102b2a68c6be47be6aa436381a4d`；`release/previous` 曾以 `d244241e…` 保存“上一次报告部署的 EXE `00ac7d68…`”的可追溯源码；`b357889d…` 由 `24b73be7…` 构建，安装≠现版验收。

下次晋升起，`main` 的“被取代者”就是本次的 `d954e0a5`，按常规“现版→旧版、前瞻→现版”程序执行。

## 首次对齐与日常晋升不同

首次对齐前，`main` 只是旧 V1.1 Git 指针，**不能将它当作已经核实的“上一个现版”**。先取得 Owner 已明确认可的真实现版本及其源码/EXE 对应关系，再建立受控现版基线；`release/previous` 也必须核实后方可标记为有效的正式回退版。若尚无可证实的现版历史，保留 `NOT_VERIFIED`，绝不为完成三分支形式而伪造旧版关系。只有首次对齐完成，此后新晋升才使用如下常规“现版→旧版、前瞻→现版”程序。

## Owner 批准晋升时的唯一执行程序

1. **CEO + 唯一 Executor** 先记录明确 Owner 授权、待晋升的**固定 commit SHA**、匹配的实际 EXE SHA、真实业务试运行证据/遗留 UNKNOWN 和安全状态；检查全部本地 worktree、未提交改动、PR 和远程三线最新 HEAD。没有证据/安全确认就保留 `develop`，不晋升。
2. **保存两份不可变发布标签/证据**：本次将被取代的 `main` 和旧 `release/previous`，记录源码、构建、配置适用范围、回退包与原有 SQLite/Chrome 风险。先做备份/验证，不删除旧源码和历史提交。
3. **先将 `release/previous` 更新到晋升前的原 `main`**，再将 `main` 以受审 PR/受保护快进更新到**固定的**已验收候选（绝不误用后来移动的 `develop` HEAD）。非快进、冲突、分支保护或 SHA 租约不匹配必须停止、复核，**不强推 main**。
4. 记录 `main` / `release/previous` 新旧 commit、对应 EXE SHA 和 Owner 认可时间；保留部署和数据回退证据。**若新 EXE 已在试运行，Git 晋升本身不需要再次覆盖 Windows 程序**。
5. **回退** 不是无条件将旧数据库覆盖现有业务；须先确认停机/在途交易、EXE/API/配置兼容、SQLite/WAL/SHM 与持久 SENT/UNKNOWN、Chrome 9222。版本源码/程序回退和真实数据处置分别核准。

## 多 Agent 与中断恢复

- 每个功能用 `feat/<module>-<task>` 或现有 Executor 分支；工作树隔离，短期分支经 CI/CEO Review 后 PR 进 `develop`。模块合入不触发正式晋升。
- 新窗口先读 [AI_START_HERE](../AI_START_HERE.md)、本政策与当前 RFQ 记录；检查本地 Git 及原运行现场，不覆盖前任窗口未提交内容。
- 旧的 37 条历史分支清理另行执行：先审计独有提交/活动工作树和 PR、保留标签，再在 Owner 确认清单后删除。**创建三条线不授权立即删除其他分支。**
- **CEO 审核：** 无 Owner 明确验收晋升、误将试运行版标为 main、丢失回退锚点、强推/误删或不安全恢复生产数据，一律 `CHANGES_REQUESTED`。
