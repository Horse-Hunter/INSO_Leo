# INSO_V1.1 Windows release soak checklist

The long soak belongs to the next release stage. Use a dedicated, approved CDP
Chrome profile and a test or otherwise explicitly approved Sheets worksheet.
Never put OAuth material, profile contents, runtime configuration, customer
rows, SQLite, or Excel results in the release artifact or diagnostics bundle.

## Start and observation

1. Launch `dist/INSO_V1.1/INSO_V1.1.exe` from Explorer and confirm the window,
   production health, result history, and local `runtime/logs/INSO_V1.1.log`.
2. Keep the application running for 8 hours first; extend to 24 hours only after
   the 8-hour review. Let normal 15-minute polling continue.
3. At startup and hourly, record timestamp, process private bytes, handle count,
   thread count, poll count, worker state, SQLite file size, Excel file size,
   CDP page/context counts, and the configured next-poll deadline.
4. Confirm memory reaches a stable plateau. Investigate monotonic increases in
   threads, handles, CDP pages/contexts, SQLite journals, or Excel temporary files.
5. Confirm each poll cycle occurs at the configured cadence, completed inquiry
   IDs remain deduplicated after restart, and no future retry delays shutdown.
6. Request stop-after-cycle and separately close the window during active work;
   confirm the due queue drains, threads exit, and owned Chrome closes. Reused
   Chrome must remain open.

Keep diagnostics local and redact inquiry IDs and all user/path/credential data
before sharing. Do not use live smoke as a daemon or leave it unattended on
unapproved production work.
