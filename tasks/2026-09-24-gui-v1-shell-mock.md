# Task: INSO_V1.0 Windows GUI Shell + Mock Backend

status: in_progress
owner: Independent Programmer
created: 2026-09-24
updated: 2026-09-24

## problem

INSO_Leo V1 currently has no operator-facing Windows desktop interface. Main Programmer is stabilizing the V1 Research / Workflow / Sheets core, so GUI work must proceed on a strictly decoupled shell and a Mock Backend without touching core automation logic. We need a first runnable INSO_V1.0 GUI that demonstrates the Dashboard, state transitions, and resource-safe operation.

## goal

Deliver a self-contained Windows GUI application (`INSO_V1.0`) with:

- a single-page dark Dashboard in the WorkBuddy / ChatGPT visual style;
- a backend abstraction (`GuiBackend`) that hides automation internals;
- a fully functional `MockBackend` so the GUI can demo Start / stop-after-cycle / results / health without real backend dependencies;
- resource management safeguards (worker thread isolation, bounded logging, no duplicate workflow starts, clean shutdown);
- tests and entry-point script.

## current_facts

- Base branch: `inso-v1-gui` cut from `origin/main` at `ce265c5` (`feat(workflow): implement V1 mainline`).
- No `gui` module exists in `src/` or `docs/MODULE_INDEX.md`.
- No `requirements.txt` / `pyproject.toml` exists; project baseline states Python 3.12, pytest, ruff.
- Core modules `research`, `sheets`, `workflow` have V1 implementations on `origin/main`; they must remain untouched.
- The canonical Research Excel output is `调研价格.xlsx` in the project directory; V1 writes it via `src.research.excel_output`.
- UI reference: dark charcoal background, white primary text, green normal, yellow warning, red fault, rounded cards, generous whitespace, no dense button grids.

## scope

- Create `src/gui/` module with public contracts, state models, Mock Backend, resource manager, and customtkinter app.
- Create `tests/gui/` covering contracts, Mock Backend lifecycle, and resource cleanup.
- Add `requirements-gui.txt` for the GUI dependency (`customtkinter`).
- Update `docs/MODULE_INDEX.md` to register `gui` module and its allowed dependency boundary.
- Add `src/gui/README.md` documenting the Backend Contract and run instructions.
- Add `src/gui/main.py` entry point and a Windows launcher stub `scripts/run_inso_gui.py` or equivalent under `src/gui/`.

## non_scope

- No modification to `src/research/*`, `src/sheets/*`, `src/workflow/*`, `src/quotation/*`, or `src/inso/*` business logic.
- No real production launcher / automation wiring (deferred to Main Programmer's Production Launcher Contract).
- No real browser, Excel automation, or credential access from the GUI layer in this task.
- No persistent GUI runtime database or complex historical statistics in this task.
- No multi-page navigation, settings panel, or user authentication flow in this task.

## requirements

### Functional

- Dashboard title: `INSO_V1.0`.
- Top-right status display: 已停止 / 运行中 / 本轮结束后停止 / 需要人工处理.
- Central action button mutates by state:
  - `STOPPED` → `启动自动调研`.
  - `RUNNING` → `本轮结束后停止`.
  - `STOPPING_AFTER_CYCLE` / `MANUAL_REVIEW` / transient states → disabled or context label.
- Stop semantics are cooperative: current cycle finishes, data/state is persisted (mocked), and no next cycle starts.
- Run info panel shows: 当前运行状态, 本轮发现订单, 已完成, 正在处理, 待处理, 下次轮询时间.
- Results table shows columns: 型号 | 品牌 | 数量 | 货量 | 最低参考价 | 总价 | 状态.
- Clicking a row expands details for sources: INSO, Findchips, 华强, 立创, 正能量, plus 备注.
- Provide stubs: `打开 Excel`, `打开结果目录`.
- Health bar at bottom: Google Sheets, Browser/CDP, Credential, Research → 正常 / 正在运行 / 需要登录 / 异常.
- Errors are hidden behind `查看详情`; dashboard shows only status pills.

### Technical / Architecture

- `GuiBackend` ABC exposing: `start()`, `request_stop_after_cycle()`, `get_status()`, `get_current_run_results()`, `get_health()`, `open_excel()`, `open_results_dir()`.
- Backend returns immutable data classes; UI consumes only the contract.
- Mock backend runs on a dedicated worker thread; UI communicates via thread-safe callbacks / queues.
- Each `start()` generates a unique `run_id`; results are tagged by `run_id` / `inquiry_id`.
- Mock cycle simulates: poll → research → finalize → emit order; cycle length ~10–15 s for demo; one order per cycle.
- Start is idempotent / mutually exclusive: cannot create overlapping workflows.
- Logs kept in fixed 1000-entry ring buffer; log listener releases on close.
- GUI close triggers worker join / timer cancellation; no orphaned Python processes.
- Excel reads (if any) must release file handle immediately; mock backend does not touch real Excel in this task.
- Diagnostic hooks expose: elapsed runtime, GUI process memory, worker state, current run_id, last poll time (not all need UI display in V1).

### Visual

- Dark charcoal (`#121212`–`#1E1E1E`) background.
- White (`#FFFFFF`) primary text; secondary text `#9CA3AF`.
- Green `#10B981` for normal / success; yellow `#F59E0B` for warning; red `#EF4444` for fault.
- Rounded cards (`corner_radius=12`), minimal 1-pixel borders or no borders.
- Generous internal padding; single page, no left sidebar.

### Safety / Boundaries

- GUI module must only import `core` for shared primitives; it may not import `research`/`sheets`/`workflow`/`inso`/`quotation` internals.
- Do not embed secrets; mock backend uses fake credentials only.
- Do not perform real network calls, browser launches, or production data writes.

## acceptance

- [x] Independent `inso-v1-gui` branch/worktree exists from latest `origin/main`.
- [x] `src/gui/` contains `__init__.py`, `contracts.py`, `state.py`, `mock_backend.py`, `resources.py`, `app.py`, `main.py`, `README.md`, `smoke.py`.
- [x] `tests/gui/` contains tests for state, contract, and mock backend lifecycle.
- [x] `docs/MODULE_INDEX.md` registers `gui` with correct dependency boundary.
- [x] GUI window launches and renders dark Dashboard (verified by `python -m src.gui.smoke`).
- [x] Clicking `启动自动调研` transitions status to 运行中; mock orders appear in results table after one cycle.
- [x] Clicking `本轮结束后停止` transitions to 本轮结束后停止 and status returns to 已停止 after current cycle.
- [x] Clicking a result row expands five-source detail panel.
- [x] Health bar shows 正常 / 正在运行 for mock components.
- [x] Closing the GUI terminates worker thread and timers; no leftover Python process observed in Task Manager.
- [x] `ruff check src/gui tests/gui` passes.
- [x] `pytest tests/gui` passes (16 tests).

## verification

- Ran `python -m src.gui.smoke` and confirmed the dark Dashboard window renders and closes cleanly.
- Ran `ruff check src/gui tests/gui` → all checks passed.
- Ran `pytest tests/gui -v` → 16 passed.
- Inspected `git status --short` → only `docs/MODULE_INDEX.md`, `requirements-gui.txt`, `src/gui/`, `tasks/2026-09-24-gui-v1-shell-mock.md`, `tests/gui/` changed; no core module files touched.

## completion

- status: complete
- changed:
  - Added `src/gui/` module (contracts, state, resources, mock backend, customtkinter app, main entry, smoke script, README).
  - Added `tests/gui/` (state, resources, mock backend lifecycle tests).
  - Added `requirements-gui.txt` with `customtkinter`.
  - Updated `docs/MODULE_INDEX.md` to register `gui` module and dependency boundary.
  - Added Task Packet `tasks/2026-09-24-gui-v1-shell-mock.md`.
- verified:
  - `ruff check src/gui tests/gui` passed.
  - `pytest tests/gui -v` passed (16 tests).
  - GUI smoke run opened and closed successfully.
- limitations:
  - UI visual styling is customtkinter-based; minor pixel-level polish may be needed after CEO review.
  - Automated app construction test was moved to `src/gui/smoke.py` because instantiating Tk in pytest caused process exit quirks (tests still verified via standalone script).
  - No real production launcher wiring; deferred to Main Programmer's contract.

