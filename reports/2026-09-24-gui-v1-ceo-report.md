# CEO Report — INSO_V1.0 Windows GUI 第一版

**From:** Independent Programmer  
**Date:** 2026-09-24  
**Branch:** `inso-v1-gui` (pushed to origin)  
**Base:** `origin/main` @ `ce265c5` (`feat(workflow): implement V1 mainline`)

## 交付概览

已按需求完成 INSO_V1.0 Windows GUI 第一版：

- 单页面 Dashboard（customtkinter），深色炭黑风格。
- 后端抽象 `GuiBackend` + 完整可运行的 `MockBackend`。
- 后台 worker 线程、运行会话 `run_id`、资源清理框架、1000 条 ring buffer 日志。
- 16 项 pytest 测试全部通过，ruff 全部通过。
- 仅新增 `src/gui/`、`tests/gui/`、`requirements-gui.txt`，更新 `docs/MODULE_INDEX.md`；未改动 Research / Sheets / Workflow / Quotation / INSO 核心。

## 已实现功能

| 需求 | 状态 |
| --- | --- |
| 顶部标题 + 右侧运行状态（已停止 / 运行中 / 本轮结束后停止 / 需要人工处理） | ✅ |
| 中央动态操作按钮：启动自动调研 / 本轮结束后停止 | ✅ |
| 运行信息卡（发现订单、已完成、正在处理、待处理、下次轮询） | ✅ |
| 本次运行结果主表：型号 / 品牌 / 数量 / 货量 / 最低参考价 / 总价 / 状态 | ✅ |
| 点击订单展开五源详情：INSO / Findchips / 华强 / 立创 / 正能量 + 备注 | ✅ |
| 打开 Excel / 打开结果目录入口 | ✅ |
| 底部健康状态：Google Sheets / Browser/CDP / Credential / Research | ✅ |
| 后端契约 `start / request_stop_after_cycle / get_status / get_current_run_results / get_health / open_excel` | ✅ |
| 每次启动生成新 `run_id`，结果按 `run_id/inquiry_id` 归属 | ✅ |
| UI 线程不执行自动化，后台独立 worker；禁止重复 Start | ✅ |
| 关闭 GUI 时释放 worker / timer / listener，无幽灵进程 | ✅ |
| 诊断数据接口：运行时长、GUI 内存、worker 状态、当前 run_id、最近轮询 | ✅ |

## 验证结果

- `ruff check src/gui tests/gui` — 全部通过。
- `pytest tests/gui -v` — **16 passed**。
- `python -m src.gui.smoke` — Dashboard 窗口正常弹出并关闭。
- `git status` — 仅 `docs/MODULE_INDEX.md` 被修改，无核心模块变更。

## 运行方式

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements-gui.txt
python -m src.gui.main
```

## 已知限制与下一步

- 当前为 `MockBackend`，真实生产 launcher 待 Main Programmer 提供 `ProductionBackend` 后替换注入。
- Excel / 结果目录目前仅做入口预留；Mock 阶段不执行真实文件操作。
- GUI 视觉细节可在 CEO Review 后进一步精调。
- 自动化 app 构造测试被调整为 `src/gui/smoke.py` 手动脚本，避免 pytest 进程中 Tk 退出异常。

## 风险

- **无**：未触碰 V1 自动化核心，branch 独立，未 merge main。
