# INSO_V1.0 GUI Shell

独立 Windows 桌面 GUI 壳层，负责给操作员展示当前运行状态、本次运行结果和健康状态。本模块不直接调用 `research` / `sheets` / `workflow` 内部 adapter；它通过 `GuiBackend` 契约与后端交互。

## 运行方式

```powershell
# 在项目根目录
python -m src.gui.main
```

当前默认注入 `MockBackend`，因此 GUI 无需真实浏览器或 Excel 即可完整演示 Start / 本轮结束后停止 / 结果生成 / 健康状态。

## 后端契约

```python
class GuiBackend(ABC):
    @property
    def run_id(self) -> str | None: ...
    def start(self) -> None: ...
    def request_stop_after_cycle(self) -> None: ...
    def get_status(self) -> RunSession: ...
    def get_current_run_results(self) -> tuple[Order, ...]: ...
    def get_health(self) -> HealthReport: ...
    def get_logs(self) -> tuple[LogEntry, ...]: ...
    def get_diagnostics(self) -> DiagnosticSnapshot: ...
    def open_excel(self) -> None: ...
    def open_results_dir(self) -> None: ...
    def on_status_change(self, callback) -> None: ...
    def on_log(self, callback) -> None: ...
    def shutdown(self) -> None: ...
```

后续 Main Programmer 提供 Production Backend 后，只需在 `src.gui.main` 中替换注入的 backend 实例，GUI 代码无需修改。

## 模块边界

- `src/gui/contracts.py`：公共数据类与 `GuiBackend` ABC。
- `src/gui/state.py`：纯状态构造与工具函数。
- `src/gui/resources.py`：1000 条日志 ring buffer、资源清理器、内存诊断工具。
- `src/gui/mock_backend.py`：Mock 后端，模拟后台 worker、订单生成、健康状态。
- `src/gui/app.py`：customtkinter 单页面 Dashboard。
- `src/gui/main.py`：入口脚本。

## 设计约束

- UI 线程不执行自动化任务；所有耗时工作由 backend worker 线程完成。
- 禁止在 GUI 中创建多个并行的 workflow 会话（backend start 去重）。
- 关闭窗口时触发 backend `shutdown()`，join worker 并释放 timer/listener。
- Excel/结果目录操作仅为入口预留；Mock 阶段不写入真实数据。
