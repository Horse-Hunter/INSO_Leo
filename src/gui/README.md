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

### 金额、货量与来源详情

- `Order.min_reference_price` 和 `Order.total_price` 使用 `decimal.Decimal`。生产后端必须保留 Research 金额精度，不得转换为 binary `float`。
- `Order.stock_label` 是 IC.net Research 提供的展示语义（`货多`、`货少`、`待验证`）；GUI 不合并其他来源库存。
- 五源详情使用展示型 `SourceDetail(source, display_value, remark, url)`。后端可传入 `1586.74`、`1513.86（无库存）`、`1800（ABC-123-T）`、`无结果` 或 `1050（两个月）`；GUI 不解析或重新解释 Research 规则。

## 模块边界

- `src/gui/contracts.py`：公共数据类与 `GuiBackend` ABC。
- `src/gui/state.py`：纯状态构造与工具函数。
- `src/gui/resources.py`：1000 条日志 ring buffer、资源清理器、内存诊断工具。
- `src/gui/mock_backend.py`：Mock 后端，模拟后台 worker、订单生成、健康状态。
- `src/gui/app.py`：customtkinter 单页面 Dashboard。
- `src/gui/main.py`：入口脚本。

## 设计约束

- UI 线程不执行自动化任务；backend callback 只把不可变事件放入 Queue，Tk 主线程通过固定 `after` drain loop 更新 widget。
- 禁止在 GUI 中创建多个并行的 workflow 会话（backend start 去重）。
- 关闭窗口时先取消已调度的 `after`，注销 callback/listener，再调用 backend `shutdown()` 并等待 worker 正常退出。
- 结果表按 `inquiry_id` 增量同步；结果快照未变化时不操作 Treeview。
- Excel/结果目录操作仅为入口预留；Mock 阶段不写入真实数据。
