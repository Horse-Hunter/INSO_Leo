<#
Independently verify a SQLite backup before it is accepted as rollback material.

RFQ-021-R4: the installer used to accept a >4 KB file with a SQLite header plus
an operator acknowledgement. That is not verification: a truncated, empty or
half-copied database has the same header. This script opens the backup
read-only, runs `PRAGMA integrity_check`, confirms the required business tables
exist, counts the rows that prove it is the real ledger, and writes a report
bound to the file's SHA256.

The installer refuses to switch unless a report exists whose recorded hash
matches the backup bytes it is about to rely on.

Usage:
  powershell -ExecutionPolicy Bypass -File scripts\verify_database_backup.ps1 `
      -DatabaseBackup D:\...\RFQ-021-pre-switch-<UTC>\workflow.sqlite3

Exit codes: 0 = verified, non-zero = refused (report says why).
#>
param(
    [Parameter(Mandatory = $true)][string]$DatabaseBackup,
    [string]$Report = "",
    [string]$PythonExecutable = "",
    [string[]]$RequireTable = @("workflow_v12_purchase_state", "workflow_v13_holds", "workflow_v12_events"),
    [int]$MinPurchaseRows = 1
)
$ErrorActionPreference = "Stop"

function Write-Failure([string]$message) {
    Write-Output "DB_VERIFY_RESULT = FAIL"
    Write-Output "reason = $message"
    exit 2
}

if (-not (Test-Path -LiteralPath $DatabaseBackup -PathType Leaf)) {
    Write-Failure "database backup not found: $DatabaseBackup"
}
$db = (Resolve-Path -LiteralPath $DatabaseBackup).Path
if ([string]::IsNullOrWhiteSpace($Report)) { $Report = "$db.verify.json" }

$item = Get-Item -LiteralPath $db
if ($item.Length -lt 4096) { Write-Failure "implausibly small ($($item.Length) bytes)" }
$header = New-Object byte[] 16
$stream = [System.IO.File]::OpenRead($db)
try { $null = $stream.Read($header, 0, 16) } finally { $stream.Dispose() }
if (-not ([System.Text.Encoding]::ASCII.GetString($header)).StartsWith("SQLite format 3")) {
    Write-Failure "not a SQLite file"
}

# A -wal beside the copy means unmerged pages: the copy is not consistent.
$wal = "$db-wal"
if ((Test-Path -LiteralPath $wal -PathType Leaf) -and ((Get-Item -LiteralPath $wal).Length -gt 0)) {
    Write-Failure "a non-empty -wal sits beside the backup; the copy was taken while open"
}

if ([string]::IsNullOrWhiteSpace($PythonExecutable)) {
    $candidates = @()
    $onPath = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($onPath) { $candidates += $onPath.Source }
    $candidates += "C:\Users\Leo\AppData\Local\Programs\Python\Python312\python.exe"
    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path -LiteralPath $candidate -PathType Leaf)) {
            $PythonExecutable = $candidate
            break
        }
    }
}
if ([string]::IsNullOrWhiteSpace($PythonExecutable) -or -not (Test-Path -LiteralPath $PythonExecutable -PathType Leaf)) {
    Write-Failure "no Python interpreter available to verify the database"
}

$checks = @'
import json, sqlite3, sys
path, tables = sys.argv[1], [t for t in sys.argv[2].split(",") if t]
result = {"integrity_check": None, "tables": {}, "error": None}
try:
    con = sqlite3.connect("file:" + path.replace("\\", "/") + "?mode=ro", uri=True, timeout=10)
    rows = con.execute("PRAGMA integrity_check").fetchall()
    result["integrity_check"] = ", ".join(str(r[0]) for r in rows)
    names = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    for table in tables:
        present = table in names
        count = con.execute("SELECT COUNT(*) FROM " + table).fetchone()[0] if present else None
        result["tables"][table] = {"present": present, "rows": count}
    for extra, sql in (("purchase_rows", "SELECT COUNT(*) FROM workflow_v12_purchase_state"),
                       ("hold_rows", "SELECT COUNT(*) FROM workflow_v13_holds"),
                       ("event_rows", "SELECT COUNT(*) FROM workflow_v12_events"),
                       ("max_event_at", "SELECT MAX(occurred_at) FROM workflow_v12_events")):
        try:
            value = con.execute(sql).fetchone()[0]
            result[extra] = int(value) if isinstance(value, int) else value
        except sqlite3.Error:
            result[extra] = None
    con.close()
except Exception as exc:
    result["error"] = type(exc).__name__ + ": " + str(exc)
print(json.dumps(result))
'@

# A native argument carrying quotes is mangled by Windows quoting, so the
# checker lives in a real file instead of `python -c`.
$checker = Join-Path ([System.IO.Path]::GetTempPath()) ("rfq021-dbverify-" + [Guid]::NewGuid().ToString("N") + ".py")
$utf8 = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($checker, $checks, $utf8)
try {
    $raw = & $PythonExecutable $checker $db ($RequireTable -join ",") 2>&1
    $code = $LASTEXITCODE
} finally {
    Remove-Item -LiteralPath $checker -Force -ErrorAction SilentlyContinue
}
if ($code -ne 0) { Write-Failure "verification interpreter failed: $raw" }
try { $check = $raw | ConvertFrom-Json } catch { Write-Failure "unreadable verification output: $raw" }
if ($check.error) { Write-Failure "database unreadable: $($check.error)" }
if ($check.integrity_check -ne "ok") { Write-Failure "integrity_check returned: $($check.integrity_check)" }
foreach ($table in $RequireTable) {
    $entry = $check.tables.$table
    if (-not $entry -or -not $entry.present) { Write-Failure "required table missing: $table" }
}
if ([int]$check.purchase_rows -lt $MinPurchaseRows) {
    Write-Failure "workflow_v12_purchase_state has $($check.purchase_rows) row(s); expected >= $MinPurchaseRows"
}
if (-not $check.max_event_at) { Write-Failure "workflow_v12_events is empty; this is not the business ledger" }

$sha = (Get-FileHash -LiteralPath $db -Algorithm SHA256).Hash.ToLowerInvariant()
$payload = [ordered]@{
    schema_version = 1
    database_backup = $db
    database_sha256 = $sha
    size_bytes = $item.Length
    integrity_check = $check.integrity_check
    required_tables = @($RequireTable)
    tables = $check.tables
    purchase_rows = $check.purchase_rows
    hold_rows = $check.hold_rows
    event_rows = $check.event_rows
    max_event_at = $check.max_event_at
    verified_at = (Get-Date).ToUniversalTime().ToString("o")
    result = "PASS"
}
$payload | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $Report -Encoding UTF8

Write-Output "DB_VERIFY_RESULT = PASS"
Write-Output "database_sha256 = $sha"
Write-Output "purchase_rows = $($check.purchase_rows)"
Write-Output "max_event_at = $($check.max_event_at)"
Write-Output "report = $Report"
