# RFQ-002 — CEO Review 报告（2026-10-02）

## 结论先行

V1.2 已完成本机 EXE 打包、依赖自检、安全扫描和正常入口窗口启动检查，
Owner 已获得程序路径，计划在下一笔真实新订单验证最终保存并发送。
**这不是 RFQ-002 全部验收 PASS，也不是独立 Review 结论。**

最终保存并发送、五秒等待及上方最新首行确认已经接入源码并随本次打包；
按 Owner 明确要求，执行者没有运行此新增提交步骤的测试或真实提交。
最终提交及其确认行为仍未实测，打包后的完整业务链也未执行。

## 1. 仓库与现场

- 仓库：Horse-Hunter/INSO_Leo。
- 分支：feature/v1-2。
- 实现起始基线：`51d17ba3aac6658bad25e468358aa1e6f51186f9`；提交后的最终
  审查指针以 `feature/v1-2` 远端最新 HEAD 为准，不使用起始基线冒充交付版本。
- 唯一当前实现现场：`D:\Program_Leo\INSO_Leo\.worktrees\v1-2-design`。
- RFQ-002 为 `REVIEW_REQUIRED`，不是 Review PASS。
- Owner 进一步明确授权将 WorkBuddy 与本执行阶段累积实现、测试、脱敏记录
  commit/push 到 feature/v1-2。本报告随该实现检查点发布；EXE、runtime、
  原始探测 JSON 与测试输出不进 Git。远端新增规则提交通过正常 merge 保留。
- CEO chat 从远端 feature/v1-2 读取本报告及实际源码差异，无需访问本机。
  不要将 Git 发布或本地 EXE 交付等同于未执行的回归/业务验收已经通过。
- 部署 EXE：`D:\Program_Leo\INSO_Leo\dist\INSO_V1.2\INSO_V1.2.exe`。
- 启动检查实例已正常关闭；未点击开始询价，未让该实例执行订单。

## 2. 最新 Owner 决策（优先于历史限制）

1. 严格 Reuse-First：继承 V1.1/WorkBuddy 的配置、OAuth、Research、Workflow、
   Vault、Chrome/CDP、GUI、数据库和发布工具，不重建这些能力。
2. 只使用 `127.0.0.1:9222` 与
   `D:\Program_Leo\INSO_CDP\chrome-profile`。保护 Chrome/profile，不新增 CDP。
3. 七天重复检查从**下方采临时询价**读取完整历史、日期、数量及真实制单人，
   不得用上方业务询价列表替代，不因价格资格过滤丢弃零报价历史。
4. Owner 接受真实草稿结果，要求删除自动采购截图。旧证据保留。
5. Owner 授权**客临时询价表单单次保存并发送**；先完成原 AI/parent 校验，
   点击后等待五秒，再查上方业务询价；未知结果不自动重发。
6. Owner 放宽十行代码限制，要求详细报告并亲自 Review。
7. Owner 确认上方列表按时间倒序，最终确认只看**首页最上面一条**，检查
   同型号、本次时间和不同于提交前首行的单据编号。历史超过一页不能阻挡提交。
   下方七天重复检查仍须完整分页，两者不能混同。
8. Owner 明确禁止执行者测试新增最终提交步骤；首次实际验证留给下一笔真订单。
9. Owner 随后明确授权现在打包 EXE，取代先前 Phase B 暂缓要求。

真实 SMTP 属于此前 Owner 授权范围；重要/重复通知沿用原收件人与触发规则，
登录停止告警只发指定 Owner 邮箱。新增提交授权**不开放**单独 INSO 保存、
generic Send、Sheets 写入或任意历史记录修改。

## 3. 已实现与复用范围

- 沿用唯一正常生产入口与 V1.2 装配，不设置 V1.1-only 静默降级路径。
- 延续现有 Sheets 读取、Research、重复判断、类型/采购员选择、AI 识别、
  原生回填和父页面型号/品牌/数量核对。
- Findchips 原生明确无结果页按无结果处理，不将登录/脚本/空白错误泛化成无结果。
- 通知台账保持已创建命令内容不变，SENT 不重发，原 worker 处理允许的通知重试。
- 自动采购截图已从生产链移除；没有删除旧截图或修改生产数据库。
- 最终提交仍通过原选择器/动作边界：只有明确 Owner 例外与唯一精确 form 控件
  才能 dispatch。默认 gate 与单独 Save 仍关闭，generic Send 不绑定。
- 校验通过先持久化 AI_RECOGNIZED；提交前事务落 UNKNOWN 和提交开始事件，
  随后只可能点击一次。没有提交重试或提交后自动重新登录再点击。
- 提交前记住上方首行 ID；提交后复用原查询并核验首页、结算、response/cache/DOM
  的身份及顺序，只读首行型号、时间、新 ID。上海时区解析复用现有代码。
- 确认后沿用 SAVED 状态，GUI 显示“已发采购单”；无法确认显示
  “提交结果待确认（不会自动重发）”。此成功标准不证明供应商端实际收件。
- 任何已有采购状态阻止再次建草稿/提交，旧测试草稿不自动补发。
- 仅归还程序自己创建的操作 tab，不关闭借用的 Owner tab 或 Chrome。
- 未新增数据库迁移。中断重启保留待确认，旧 reconciliation 不得拿旧记录
  确认这次新提交；提交前首行基准只在当前调用内保留，中断需人工核实。

具体代码职责及源码入口见 `FINAL_SUBMISSION_REVIEW.md`。关键 Review 文件：

| 范围 | 文件 |
| --- | --- |
| 写入授权、唯一按钮与单次点击 | `src/inso/write_safety.py`、`src/inso/purchase_writer.py` |
| 正常生产提交装配与结果确认 | `src/launcher/backend.py`、`src/launcher/v12_composition.py` |
| 首页结算、原时间解析复用 | `src/inso/duplicate_history.py` |
| 提交前持久化、防重复路由 | `src/workflow/v12_store.py`、`src/workflow/v12_flow.py` |
| 页面 ownership、待确认文案 | `src/inso/session.py`、`src/gui/app.py` |
| 同一版本化发布流程 | `scripts/build_windows_release.ps1`、`packaging/INSO_V1.1.spec` |

## 4. 验证证据与不能混淆的范围

| 项目 | 证据/结果 | 范围限制 |
| --- | --- | --- |
| 此前源码回归 | 执行记录：926 passed / 11 skipped | 在最终提交及打包修改之前，不证明新代码通过 |
| 此前真实订单续跑 | 原 Research、下方重复判断、未保存草稿、AI/parent 校验及 SMTP 台账记录 | 不是最终保存并发送验收 |
| 当前源码静态检查 | `ruff check src` PASS | 不等于自动测试/真实业务验证 |
| 发布脚本语法 | PowerShell parser errors=0 | 不覆盖业务逻辑 |
| 差异格式 | `git diff --check` PASS | 有既有 CRLF 提示，非失败 |
| 本次打包 | `build_windows_release.ps1 -Version 1.2` 成功 | 沿用旧 spec 和资产，V1.1 未覆盖 |
| 冻结依赖自检 | `--self-check` exit 0 | 不运行业务、不证明完整装配后的订单链 |
| 干净产物扫描 | `RELEASE_SCAN_OK` | 在关联私有运行目录之前扫描，不宣称带生产 runtime 的目录也是干净分发包 |
| 正常 EXE 入口启动 | PID 36596；INSO_V1.2 标题；窗口响应正常，正常关闭 | STOPPED 状态，未点开始、未执行订单或 packaged 完整链 smoke |
| 新增最终提交 | 未测试/未真实执行 | Owner 明确要求留给下一笔真订单 |

扩大检查范围至既有 `scripts/windows_release_entry.py` 时有三个原有 Ruff
风格问题，未为打包扩展业务代码，不宣称全仓库 Ruff 全通过。

最终 EXE SHA256：
`99F131DBDFC69C961121FF896FF8C9573C0BC0CBAB3D73B1BEFF60455E095D7C`

本次打包/启动检查没有执行真实 Save、Save-and-Send、SMTP、Sheets 写入、
订单重跑、凭据探测或 CDP 页面操作；不把更早已授权的 SMTP 验证说成本轮发送。

## 5. 本机部署与保护事项

V1.2 使用独立产物目录；本机 `runtime` junction 指向：
`D:\Program_Leo\INSO_Leo\.worktrees\v1-2-design\dist\INSO_V1.1\runtime`。

这复用现有配置、SQLite、Excel 和历史采购状态，避免换 EXE 后丢状态或重发。
**部署目录不是独立可搬走的通用分发包。** 在安全迁移其 runtime 之前，不得
删除/移动该目标目录或 archive 当前工作区；本机仍依赖原配置中的合法路径。
打包所需 Tcl/Tk 在 Owner 本机身份下可用，沙箱探测失败不等于安装损坏；
复用原 Python 环境成功构建，没有重装或换一套环境。

## 6. CEO 需要给出的独立 Review

- 从最新 Owner 授权审查 narrowly scoped Save-and-Send 例外，不按旧绝对禁止
  误判，也不要把这一例外理解成所有生产写入都已开放。
- 检查 UNKNOWN 先落库、唯一按钮身份、旧单防补发、异常/重启不重试是否成立。
- 检查“下方完整七天历史”与“上方首行提交确认”边界没有串用；新增首页模式
  不改变默认完整集合判据，时间排序事实来自 Owner 确认而非本轮探测。
- 检查时间精度、首行 ID 变化和待确认策略；并明确记录成功不等于发送送达证明。
- 核对发布与 runtime ownership；不要因 worktree 清理破坏 Owner 当前 EXE。
- 必须明确列出未执行最终提交测试、新完整回归与 packaged 完整业务链 smoke。
  Owner 的“不测试提交”授权不能被改写为“提交测试已 PASS”。
- Git 发布使代码和脱敏记录可供远端 Review；最终回归、独立 Review 及首次
  最终提交仍未完成，不因 Owner 收到 EXE 自动标成 REVIEWED_DONE。
- 未跟踪的原始 probe JSON、测试目录及本机运行数据不要 blanket stage/commit；
  Review 既有记录是否脱敏后再由执行者处理版本控制交付。

本报告只请求 CEO 独立审查，不授权 CEO 运行真实提交测试、重跑旧订单或重开发。
如发现问题，应写入 RFQ-002 REVIEW.md 并返还执行者，不开启新的平行任务。

## 7. 阅读入口

按顺序阅读当前工作区：
`AI_START_HERE.md` → `control-room/COORDINATION.md` →
`control-room/RFQ-002/TASK_SPEC.md`（最新授权取代历史限制）→
本报告 → `FINAL_SUBMISSION_REVIEW.md` → `EXECUTION_LOG.md` → 实际源码 diff。

Owner 下一步已告知：来真订单时打开 V1.2 并点击开始询价；遇待确认不重跑补发。
执行者没有向 CEO chat 自动发消息，本报告由 Owner 转交。
