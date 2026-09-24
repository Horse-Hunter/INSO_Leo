# Sheets module

Google Sheets one-shot read/query and explicitly commanded safe-update boundary. Scheduling, global state, retry, and duplicate prevention belong to `workflow`.

Sheets V1 includes the pending-record read foundation, Google Sheets API reader, OAuth User Authorization, and safe blank-only Brand writes to column F. Live reading is validated. Live Brand writing remains operationally unvalidated because no safe production candidate was available.

The read-only production runtime is selected explicitly with `INSO_SHEETS_READ_CONFIG_FILE`. The pointed-to local JSON file must provide exactly `oauth_client_secret_file`, `spreadsheet_id`, and a non-empty ordered `worksheets` list. Keep it outside the repository or name it `*.local.json`; both the runtime config and OAuth client file are local inputs and must never be committed. Runtime composition remains one-shot and does not persist OAuth tokens.

See `docs/MODULE_INDEX.md` and `docs/modules/SHEETS.md`.
