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

The backend observes Research execution by `inquiry_id` and reads only canonical Research workbook display cells for this session. It does not derive inquiry membership from row counts or implement business rules.
