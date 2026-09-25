# INSO_V1.0 Windows GUI

Production mode is the default:

```powershell
python -m src.gui.main
```

For a UI-only demo, explicitly use `python -m src.gui.main --mock`. Production mode composes the existing Sheets, Workflow, and Research public runtime entry points through `src/launcher`; GUI itself imports only `GuiBackend`.

Create Git-ignored `runtime/production.json` with non-secret values:

```json
{"spreadsheet_id":"...","worksheet_titles":["2026","shahab"],"client_secret_file":"runtime/client_secret.json","sqlite_path":"runtime/production/workflow.sqlite3"}
```

Provide the existing non-secret Research settings in `runtime/research.json`. OAuth refresh grants remain in the protected local store. The production SQLite file is stable across launches. Sheet Brand updates are disabled. Missing config, authorization, credentials, CDP, or human-verification challenges fail closed and appear as “需要人工处理”.

`GuiBackend.get_current_run_results()` and run metrics describe only the current run. `get_result_history()` separately exposes the cached Research-owned Excel history for the results table. The table normalizes Research outcomes to `成功` / `部分成功` / `异常`; Research manual-review or all-failed results display as red `异常`. Legacy rows with no saved status display `--` rather than inferring a result. GUI code consumes only `GuiBackend` and does not parse Excel. History cache refresh is owned by the launcher at workbook-change and Research completion boundaries.

V1.2 adds sanitized `V12OrderStateDTO`, alert, and workflow-event DTO contracts in
`contracts.py`. The results table uses the latest active alert as its red status;
the existing single-page layout stays intact. Order details show the business
label and full event history. The production backend reads these DTOs only when
the existing SQLite database is already at the V1.2 schema version; it never
migrates the database or enables V1.2 external actions.
