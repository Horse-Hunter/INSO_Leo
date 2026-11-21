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
    [int]$MaxAgeHours = 72,
    # An Owner-authorised, named exemption for specific historical orders the
    # Owner has ruled out of scope. Both switches are required together: an
    # exemption without an authority string is indistinguishable from silently
    # clearing a hold, and is refused. Every exemption is printed and recorded
    # in the report; nothing is exempted implicitly and nothing is cleared.
    [string[]]$OwnerExemptInquiry = @(),
    [string]$OwnerExemptAuthority = "",
    # Offline-gate-test fault simulation. Honoured only when
    # RFQ021_OFFLINE_GATE_TESTS=1, and it can only ever cause a refusal.
    [string]$InjectProcessQueryFault = ""
)
$ErrorActionPreference = "Stop"
$processFault = if ($env:RFQ021_OFFLINE_GATE_TESTS -eq "1") { $InjectProcessQueryFault } else { "" }

function Write-Failure([string]$message) {
    Write-Output "DB_VERIFY_RESULT = FAIL"
    Write-Output "reason = $message"
    exit 2
}

function Get-Sha256([string]$path) {
    return (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
}

# An exemption is only meaningful as an explicit, attributed Owner decision.
# Without the authority string it would be indistinguishable from the automatic
# clearing this gate exists to prevent, so half an exemption is a refusal.
$OwnerExemptInquiry = @($OwnerExemptInquiry | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | ForEach-Object { $_.Trim() })
if ($OwnerExemptInquiry.Count -gt 0 -and [string]::IsNullOrWhiteSpace($OwnerExemptAuthority)) {
    Write-Failure "owner exemptions were requested without an authority reference; an unattributed exemption is indistinguishable from clearing a hold"
}
foreach ($exempt in $OwnerExemptInquiry) {
    if ($exempt -notmatch '^inq_[0-9a-f]{24}$') {
        Write-Failure "the owner exemption '$exempt' is not an inquiry id; refusing to exempt anything that cannot be named exactly"
    }
}

# Fail-closed process enumeration (RFQ-021-R5 P0).
#
# A query that fails, a permission denial and a process whose executable path
# cannot be read all look exactly like "no rows" if the caller only inspects the
# result. None of them proves the program stopped, and the exclusive SQLite
# handle probe does *not* cover a paused program that closed its database
# handles. So the status is three-valued: $null = unknown (must refuse),
# $false = running from this install, $true = provably not running from it.
function Get-StopState([string]$InstallRoot, [string]$FaultMode) {
    if ($FaultMode -eq "query_failed") {
        return @{ Stopped = $null; Detail = "the process query failed (offline fault simulation)" }
    }
    if ($FaultMode -eq "unidentified") {
        return @{ Stopped = $null; Detail = "a process executable path could not be read (offline fault simulation)" }
    }
    try {
        $processes = @(Get-CimInstance Win32_Process -Filter "Name='INSO_V1.6.exe'" -ErrorAction Stop)
    }
    catch {
        return @{ Stopped = $null; Detail = "process enumeration failed: $($_.Exception.Message)" }
    }
    $unidentified = @($processes | Where-Object { [string]::IsNullOrWhiteSpace([string]$_.ExecutablePath) })
    if ($unidentified.Count -gt 0) {
        return @{ Stopped = $null; Detail = "cannot read the executable path of $($unidentified.Count) INSO_V1.6.exe process(es) (PIDs: $($unidentified.ProcessId -join ', '))" }
    }
    $running = @($processes | Where-Object {
        ([string]$_.ExecutablePath).StartsWith($InstallRoot, [StringComparison]::OrdinalIgnoreCase)
    })
    if ($running.Count -gt 0) {
        return @{ Stopped = $false; Detail = "PIDs $($running.ProcessId -join ', ')" }
    }
    return @{ Stopped = $true; Detail = "$($processes.Count) other INSO_V1.6 process(es), none under this install" }
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
    $stop = Get-StopState $root $processFault
    if ($null -eq $stop.Stopped) {
        Write-Failure "cannot prove INSO_V1.6 is stopped for ${root}: $($stop.Detail). An unproven process state is not a clean stop."
    }
    if (-not $stop.Stopped) {
        Write-Failure ("INSO_V1.6 is still running from {0} ({1})" -f $root, $stop.Detail)
    }
    Write-Output "process_state = stopped (proven; $($stop.Detail))"
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
from datetime import datetime, timezone
path, tables = sys.argv[1], [t for t in sys.argv[2].split(",") if t]
exempt_orders = {o.strip() for o in (sys.argv[3].split(",") if len(sys.argv) > 3 else []) if o.strip()}
exempt_authority = sys.argv[4] if len(sys.argv) > 4 else ""


def _instant(text):
    """Parse a stored timestamp, or return None so the caller stays conservative."""
    if not text:
        return None
    try:
        stamp = datetime.fromisoformat(str(text).replace("Z", "+00:00"))
    except ValueError:
        return None
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    return stamp

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

    # --- write-intent admission -------------------------------------------
    # A count that could not be read is NOT zero. Either the journal answers
    # with a real number, or the ledger provably predates the journal and the
    # old state is verified in its own terms: every recorded unknown write must
    # still be protected by an alert or a V13 hold. Nothing is cleared here.
    unknown_outcomes = ("SUBMIT_UNCONFIRMED", "UNKNOWN_WRITE_OUTCOME",
                        "READ_ONLY_RECONCILIATION_REQUIRED", "MANUAL_REVIEW")
    unknown_reasons = ("SAVE_OUTCOME_UNKNOWN", "UPDATE_RESULT_UNCONFIRMED", "UNKNOWN_WRITE_OUTCOME")
    result["write_intent_table_present"] = "workflow_write_intents" in names
    result["write_intent_state"] = "DETERMINATION_FAILED"
    result["open_write_intents"] = None
    result["legacy_unknown_write"] = None
    try:
        if result["write_intent_table_present"]:
            open_intents = con.execute(
                "SELECT COUNT(*) FROM workflow_write_intents WHERE state<>'SETTLED'").fetchone()[0]
            if not isinstance(open_intents, int):
                raise ValueError("the write-intent count is not an integer")
            result["open_write_intents"] = open_intents
            result["write_intent_state"] = (
                "NONE_PROVEN" if open_intents == 0 else "OPEN_WRITE_INTENTS")
        else:
            outcome_marks = ",".join("?" for _ in unknown_outcomes)
            reason_marks = ",".join("?" for _ in unknown_reasons)
            purchase_unknown = [row[0] for row in con.execute(
                "SELECT inquiry_id FROM workflow_v12_purchase_state WHERE outcome IN ("
                + outcome_marks + ")", unknown_outcomes) if row[0]]
            save_unknown = [row[0] for row in con.execute(
                "SELECT inquiry_id FROM workflow_v12_events WHERE event_type='SAVE_OUTCOME_UNKNOWN'")
                if row[0]]
            unknown_orders = {str(order) for order in purchase_unknown + save_unknown}
            alert_orders = {str(row[0]) for row in con.execute(
                "SELECT inquiry_id FROM workflow_v12_active_alerts WHERE active=1 AND reason_code IN ("
                + reason_marks + ")", unknown_reasons) if row[0]}
            holds_present = "workflow_v13_holds" in names
            hold_orders, active_holds, unattributed_holds = set(), 0, 0
            if holds_present:
                for (payload,) in con.execute(
                        "SELECT result_json FROM workflow_v13_holds "
                        "WHERE active=1 AND reason='UPDATE_RESULT_UNCONFIRMED'"):
                    active_holds += 1
                    try:
                        data = json.loads(payload or "{}")
                    except ValueError:
                        unattributed_holds += 1
                        continue
                    held = data.get("inquiry_id") if isinstance(data, dict) else None
                    if not held:
                        unattributed_holds += 1
                        continue
                    hold_orders.add(str(held))
            protected = alert_orders | hold_orders

            # An order that once hit SAVE_OUTCOME_UNKNOWN but was afterwards
            # confirmed SAVED -- with a real receipt reference, recorded no
            # earlier than that last uncertainty -- is not an open write. Its
            # outcome is known and SAVED is terminal for the duplicate guard,
            # so a version switch can neither lose nor replay it. The receipt
            # and the ordering are both required: a SAVED row without a
            # reference, or one stamped before the uncertainty, stays unknown.
            resolved_orders = set()
            for order in unknown_orders:
                row = con.execute(
                    "SELECT outcome, saved_record_ref, updated_at "
                    "FROM workflow_v12_purchase_state WHERE inquiry_id=?", (order,)).fetchone()
                if not row:
                    continue
                outcome, reference, updated_at = row[0], row[1], row[2]
                if str(outcome) != "SAVED" or not str(reference or "").strip():
                    continue
                last_unknown = con.execute(
                    "SELECT MAX(occurred_at) FROM workflow_v12_events "
                    "WHERE inquiry_id=? AND event_type='SAVE_OUTCOME_UNKNOWN'", (order,)).fetchone()[0]
                confirmed = _instant(updated_at)
                uncertain = _instant(last_unknown)
                if last_unknown and confirmed is None:
                    continue        # cannot order the two -> not proven
                if uncertain is not None and confirmed < uncertain:
                    continue        # the uncertainty came after the save
                resolved_orders.add(order)

            exempt_applied = unknown_orders & exempt_orders
            exempt_unmatched = sorted(exempt_orders - unknown_orders)
            unprotected = sorted(unknown_orders - protected - resolved_orders - exempt_applied)
            result["legacy_unknown_write"] = {
                "checked": True,
                "unknown_purchase_rows": len(purchase_unknown),
                "unknown_save_events": len(save_unknown),
                "unknown_orders": len(unknown_orders),
                "protected_unknown_orders": len(unknown_orders & protected),
                "resolved_by_confirmed_save": len(resolved_orders),
                "resolved_by_confirmed_save_orders": sorted(resolved_orders),
                "owner_exempted_orders": sorted(exempt_applied),
                "owner_exempt_authority": exempt_authority,
                "owner_exempt_unmatched": exempt_unmatched,
                "unprotected_unknown_rows": len(unprotected),
                "unprotected_examples": unprotected[:5],
                "active_unknown_alerts": len(alert_orders),
                "active_unknown_holds": active_holds,
                "unattributed_holds": unattributed_holds,
                "holds_table_present": holds_present,
                "outcomes_considered": list(unknown_outcomes),
            }
            result["open_write_intents"] = 0
            result["write_intent_state"] = (
                "LEGACY_NO_JOURNAL_PROVEN"
                if not unprotected and unattributed_holds == 0
                else "LEGACY_NO_JOURNAL_UNPROVEN")
    except Exception as exc:  # noqa: BLE001 - an unreadable journal is a refusal
        result["write_intent_state"] = "DETERMINATION_FAILED"
        result["write_intent_error"] = type(exc).__name__ + ": " + str(exc)
        result["open_write_intents"] = None
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
    $raw = & $PythonExecutable $checker $db ($RequireTable -join ",") ($OwnerExemptInquiry -join ",") $OwnerExemptAuthority 2>&1
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

# --- write-intent admission: a confirmed zero, or a proven legacy state -----
# An unresolved write intent means the previous process may have dispatched an
# external write without confirming it. An unreadable or absent journal is not
# evidence of zero: it is a refusal, unless the ledger provably predates the
# journal and its recorded unknown writes are still protected (never cleared).
$intentCount = $check.open_write_intents
if ($null -eq $intentCount -or -not (($intentCount -is [int]) -or ($intentCount -is [long]))) {
    Write-Failure "the write-intent count is '$intentCount', not a number. An unproven count is not zero."
}
if ([int64]$intentCount -ne 0) {
    Write-Failure "$([int64]$intentCount) unresolved write intent(s) exist in the ledger. Resolve or explicitly account for them before taking a rollback snapshot; never clear them automatically."
}
switch ([string]$check.write_intent_state) {
    "NONE_PROVEN" { }
    "OPEN_WRITE_INTENTS" {
        Write-Failure "unresolved write intent(s) exist in the ledger. Resolve or explicitly account for them before taking a rollback snapshot; never clear them automatically."
    }
    "LEGACY_NO_JOURNAL_PROVEN" {
        $legacy = $check.legacy_unknown_write
        if (-not $legacy -or -not $legacy.checked) {
            Write-Failure "the ledger has no write-intent journal and its legacy state was not verified; absence is not zero."
        }
        foreach ($field in @("unprotected_unknown_rows", "unattributed_holds")) {
            $value = $legacy.$field
            if ($null -eq $value -or -not (($value -is [int]) -or ($value -is [long]))) {
                Write-Failure "the legacy unknown-write check could not determine '$field'; that is not zero."
            }
            if ([int64]$value -ne 0) {
                Write-Failure ("the ledger predates the write-intent journal and holds {0} {1}. Refusing: an unprotected or unattributable unknown write could be lost or replayed by a switch. Preserve it and reconcile by hand." -f $value, $field)
            }
        }
    }
    "LEGACY_NO_JOURNAL_UNPROVEN" {
        $legacy = $check.legacy_unknown_write
        $unprotected = if ($legacy) { $legacy.unprotected_unknown_rows } else { "unknown" }
        $unattributed = if ($legacy) { $legacy.unattributed_holds } else { "unknown" }
        Write-Failure ("the ledger predates the write-intent journal and its unknown-write state is not proven: {0} unprotected unknown order(s), {1} unattributable hold(s). An unprotected UNKNOWN/SENT write could be lost or replayed by a switch; reconcile it by hand and never clear a hold." -f $unprotected, $unattributed)
    }
    default {
        Write-Failure "the write-intent state is '$($check.write_intent_state)'; it is not a proven state. $(if ($check.write_intent_error) { "($($check.write_intent_error))" })"
    }
}
Write-Output "write_intent_state = $($check.write_intent_state)"
$legacyAudit = $check.legacy_unknown_write
if ($legacyAudit) {
    Write-Output "unknown_orders_considered = $($legacyAudit.unknown_orders)"
    Write-Output "resolved_by_confirmed_save = $($legacyAudit.resolved_by_confirmed_save)"
    Write-Output "owner_exempted_orders = $($legacyAudit.owner_exempted_orders -join ',')"
    if ($legacyAudit.owner_exempt_authority) {
        Write-Output "owner_exempt_authority = $($legacyAudit.owner_exempt_authority)"
    }
    if ($legacyAudit.owner_exempt_unmatched) {
        Write-Output "owner_exempt_unmatched = $($legacyAudit.owner_exempt_unmatched -join ',')"
    }
}

# Recency: an old-but-valid ledger is the wrong rollback target.
$lastEvent = [datetime]::Parse($check.max_event_at, [Globalization.CultureInfo]::InvariantCulture,
    [Globalization.DateTimeStyles]::RoundtripKind)
$ageHours = ([datetime]::UtcNow - $lastEvent.ToUniversalTime()).TotalHours
if ($ageHours -gt $MaxAgeHours) {
    Write-Failure ("the ledger's last event is {0:N1} h old (limit {1} h); this backup is not current" -f $ageHours, $MaxAgeHours)
}

$payload = [ordered]@{
    schema_version = 4
    database_backup = $db
    database_sha256 = $backupHash
    source_database = $source
    source_sha256 = $sourceHash
    source_size_bytes = $item.Length
    install_dir = (Resolve-Path -LiteralPath $InstallDir).Path
    program_stopped = $true
    process_state = "stopped (proven: process enumeration succeeded, every INSO_V1.6 process had a readable executable path, none ran from install_dir)"
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
    write_intent_state = $check.write_intent_state
    write_intent_table_present = $check.write_intent_table_present
    open_write_intents = $check.open_write_intents
    legacy_unknown_write = $check.legacy_unknown_write
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
