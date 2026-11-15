<#
Verify a SQLite backup as rollback material: structure, provenance, quiescence.

RFQ-021-R5. `integrity_check` alone proves nothing about *which* database this
file is. A year-old ledger with the same schema passes it. This script binds the
copy to the live ledger it must come from:

  1. the copy is byte-identical to `-SourceDatabase` (so it is that database,
     not another valid file);
  2. no `-wal` sits beside the source or the copy (a clean stop checkpointed it;
     a byte copy taken while open would silently drop committed pages);
  3. no process is running from `-InstallDir` when the check runs;
  4. `PRAGMA integrity_check`, the business tables, a non-empty ledger and
     recent activity;
  5. a report binding all of the above to the copy's SHA256.

The installer accepts nothing less than a PASS report whose source and hashes
still match what it is about to protect.

Usage:
  powershell -ExecutionPolicy Bypass -File scripts\verify_database_backup.ps1 `
      -DatabaseBackup D:\...\workflow.sqlite3 `
      -SourceDatabase D:\Program_Leo\INSO_Leo\dist\INSO_V1.4\runtime\production\workflow.sqlite3 `
      -InstallDir     D:\Program_Leo\INSO_Leo\dist\INSO_V1.6

Exit codes: 0 = verified, non-zero = refused (report says why).
#>
param(
    [Parameter(Mandatory = $true)][string]$DatabaseBackup,
    [Parameter(Mandatory = $true)][string]$SourceDatabase,
    [string]$InstallDir = "",   # required in practice; see the explicit refusal below
    [string]$Report = "",
    [string]$PythonExecutable = "",
    [string[]]$RequireTable = @("workflow_v12_purchase_state", "workflow_v13_holds", "workflow_v12_events"),
    [int]$MinPurchaseRows = 1,
    [int]$MaxAgeHours = 72
)
$ErrorActionPreference = "Stop"

function Write-Failure([string]$message) {
    Write-Output "DB_VERIFY_RESULT = FAIL"
    Write-Output "reason = $message"
    exit 2
}

function Get-Sha256([string]$path) {
    return (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
}

# A clean stop is also a fact about handles, not only about process names: any
# process (including an install in another directory that shares this junction)
# holding the ledger open means the copy is not provably a point-in-time state.
# Opened read-only, FileShare.None, and released immediately; nothing is written.
function Assert-NoOpenHandle([string]$path) {
    $handle = $null
    try {
        $handle = [System.IO.File]::Open(
            $path,
            [System.IO.FileMode]::Open,
            [System.IO.FileAccess]::Read,
            [System.IO.FileShare]::None)
        return $true
    }
    catch { return $false }
    finally { if ($handle) { $handle.Dispose() } }
}

if (-not (Test-Path -LiteralPath $DatabaseBackup -PathType Leaf)) {
    Write-Failure "database backup not found: $DatabaseBackup"
}
if (-not (Test-Path -LiteralPath $SourceDatabase -PathType Leaf)) {
    Write-Failure "source database not found: $SourceDatabase"
}
$db = (Resolve-Path -LiteralPath $DatabaseBackup).Path
$source = (Resolve-Path -LiteralPath $SourceDatabase).Path
if ([string]::IsNullOrWhiteSpace($Report)) { $Report = "$db.verify.json" }

# A clean stop is a fact, not a checkbox: it can only be claimed when the
# installation it belongs to was named and nothing is running from it.
if ([string]::IsNullOrWhiteSpace($InstallDir)) {
    Write-Failure "-InstallDir is required: without it the clean-stop state cannot be proven"
}

# --- 1. the copy must be the source, byte for byte -------------------------
$backupHash = Get-Sha256 $db
$sourceHash = Get-Sha256 $source
if ($backupHash -ne $sourceHash) {
    Write-Failure "the copy is not the live ledger: backup=$backupHash source=$sourceHash"
}

$item = Get-Item -LiteralPath $db
if ($item.Length -lt 4096) { Write-Failure "implausibly small ($($item.Length) bytes)" }

$header = New-Object byte[] 16
$stream = [System.IO.File]::OpenRead($db)
try { $null = $stream.Read($header, 0, 16) } finally { $stream.Dispose() }
if (-not ([System.Text.Encoding]::ASCII.GetString($header)).StartsWith("SQLite format 3")) {
    Write-Failure "not a SQLite file"
}

# --- 2. a clean stop checkpointed the WAL; a live copy would not ------------
foreach ($path in @("$source-wal", "$db-wal")) {
    if ((Test-Path -LiteralPath $path -PathType Leaf) -and ((Get-Item -LiteralPath $path).Length -gt 0)) {
        Write-Failure "a non-empty $path exists; the ledger was not quiescent, so this copy is not consistent"
    }
}

# --- 3. nothing may be running from the install being protected -------------
if (-not [string]::IsNullOrWhiteSpace($InstallDir)) {
    if (-not (Test-Path -LiteralPath $InstallDir -PathType Container)) {
        Write-Failure "install directory not found: $InstallDir"
    }
    $root = (Resolve-Path -LiteralPath $InstallDir).Path.TrimEnd('\')
    $running = @(Get-CimInstance Win32_Process -Filter "Name='INSO_V1.6.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.ExecutablePath -and $_.ExecutablePath.StartsWith($root, [StringComparison]::OrdinalIgnoreCase) })
    if ($running.Count -gt 0) {
        Write-Failure ("INSO_V1.6 is still running from {0} (PIDs: {1})" -f $root, ($running.ProcessId -join ', '))
    }
}

# --- 3b. no process may still hold the ledger open --------------------------
if (-not (Assert-NoOpenHandle $source)) {
    Write-Failure "another process still holds the live ledger open: $source. The program is not stopped (or a second install is using it); this copy cannot be proven to be a point-in-time state."
}
if (-not (Assert-NoOpenHandle $db)) {
    Write-Failure "the backup copy is open in another process: $db. Close it (or antivirus/indexer preview) and re-run."
}

# --- 4. structure and business content -------------------------------------
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
    result["table_count"] = len(names)
    for table in tables:
        present = table in names
        count = con.execute("SELECT COUNT(*) FROM " + table).fetchone()[0] if present else None
        result["tables"][table] = {"present": present, "rows": count}
    for extra, sql in (("purchase_rows", "SELECT COUNT(*) FROM workflow_v12_purchase_state"),
                       ("saved_purchase_rows", "SELECT COUNT(*) FROM workflow_v12_purchase_state WHERE outcome='SAVED'"),
                       ("hold_rows", "SELECT COUNT(*) FROM workflow_v13_holds"),
                       ("active_alert_rows", "SELECT COUNT(*) FROM workflow_v12_active_alerts WHERE active=1"),
                       ("open_write_intents", "SELECT COUNT(*) FROM workflow_write_intents WHERE state<>'SETTLED'"),
                       ("event_rows", "SELECT COUNT(*) FROM workflow_v12_events"),
                       ("max_event_at", "SELECT MAX(occurred_at) FROM workflow_v12_events"),
                       ("max_purchase_update", "SELECT MAX(updated_at) FROM workflow_v12_purchase_state")):
        try:
            value = con.execute(sql).fetchone()[0]
            result[extra] = int(value) if isinstance(value, int) else value
        except sqlite3.Error:
            result[extra] = None
    try:
        result["purchase_outcomes"] = {
            str(row[0]): int(row[1])
            for row in con.execute(
                "SELECT outcome, COUNT(*) FROM workflow_v12_purchase_state GROUP BY outcome")
        }
    except sqlite3.Error:
        result["purchase_outcomes"] = None
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
if ($null -eq $check.purchase_rows) { Write-Failure "workflow_v12_purchase_state could not be counted" }

# An unresolved write intent means the previous process may have dispatched an
# external write without confirming it. Switching over that state would make a
# rollback lose or replay a real order, so it is refused rather than recorded.
if ($null -ne $check.open_write_intents -and [int]$check.open_write_intents -gt 0) {
    Write-Failure "$($check.open_write_intents) unresolved write intent(s) exist in the ledger. Resolve or explicitly account for them before taking a rollback snapshot; never clear them automatically."
}

# Recency: an old-but-valid ledger is the wrong rollback target.
$lastEvent = [datetime]::Parse($check.max_event_at, [Globalization.CultureInfo]::InvariantCulture,
    [Globalization.DateTimeStyles]::RoundtripKind)
$ageHours = ([datetime]::UtcNow - $lastEvent.ToUniversalTime()).TotalHours
if ($ageHours -gt $MaxAgeHours) {
    Write-Failure ("the ledger's last event is {0:N1} h old (limit {1} h); this backup is not current" -f $ageHours, $MaxAgeHours)
}

$payload = [ordered]@{
    schema_version = 3
    database_backup = $db
    database_sha256 = $backupHash
    source_database = $source
    source_sha256 = $sourceHash
    source_size_bytes = $item.Length
    install_dir = (Resolve-Path -LiteralPath $InstallDir).Path
    program_stopped = $true
    quiescence = "no process runs from install_dir; the ledger file accepted an exclusive handle; both WAL sides are empty"
    wal_clean = $true
    size_bytes = $item.Length
    integrity_check = $check.integrity_check
    required_tables = @($RequireTable)
    tables = $check.tables
    purchase_rows = $check.purchase_rows
    saved_purchase_rows = $check.saved_purchase_rows
    purchase_outcomes = $check.purchase_outcomes
    hold_rows = $check.hold_rows
    active_alert_rows = $check.active_alert_rows
    open_write_intents = $check.open_write_intents
    event_rows = $check.event_rows
    max_event_at = $check.max_event_at
    max_purchase_update = $check.max_purchase_update
    event_age_hours = [math]::Round($ageHours, 2)
    verified_at = (Get-Date).ToUniversalTime().ToString("o")
    result = "PASS"
}
$payload | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $Report -Encoding UTF8

Write-Output "DB_VERIFY_RESULT = PASS"
Write-Output "database_sha256 = $backupHash"
Write-Output "source_database = $source"
Write-Output "purchase_rows = $($check.purchase_rows)"
Write-Output "max_event_at = $($check.max_event_at)"
Write-Output "event_age_hours = $([math]::Round($ageHours, 2))"
Write-Output "report = $Report"
