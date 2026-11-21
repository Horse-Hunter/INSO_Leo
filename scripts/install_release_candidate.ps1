<#
Install a verified candidate over a stopped release -- or refuse and say why.

RFQ-021-R5. Nothing is touched until every one of these is proven:

  1. authorisation switches and a full 64-hex `-ExpectedPreviousExeSha256`;
  2. the rollback snapshot re-verifies file by file;
  3. the snapshot *is* the installed build (EXE + every `_internal` file, no
     extra program file on either side);
  4. `runtime` is a **junction** whose target equals `-RuntimeTarget`;
  5. the snapshot's configuration is byte-identical to the live configuration
     behind that junction, and its `sqlite_path` still resolves to the database
     the database report covers;
  6. the database report proves provenance: the copy is byte-identical to the
     live ledger, no non-empty `-wal`, the program was **proven** stopped
     (process enumeration succeeded and every INSO_V1.6 executable path was
     readable), integrity ok, business tables present, recent activity -- all
     bound to the copy's hash;
  7. the write-intent journal answers with a real 0, or the ledger provably
     predates it and its recorded unknown writes are still protected. An
     absent, unreadable or null count is never treated as zero;
  8. the candidate re-verifies against its own manifest;
  9. no process is running from the target directory -- and an unprovable
     process state refuses here and again immediately before the first move.

After the copy, **every installed program file is re-hashed against the
candidate manifest**. A count check is not integrity. If anything mismatches --
or the copy throws halfway -- the previous build is restored and verified file
by file against the rollback snapshot, and the script reports `FAIL_RESTORED`.
If the restore itself cannot be completed or proven (including an error while
restoring), it reports `ROLLBACK_REQUIRED` with the exact paths to restore by
hand. It never starts anything and never claims PASS on a partial switch.

Usage:
  powershell -ExecutionPolicy Bypass -File scripts\install_release_candidate.ps1 `
      -CandidateDir   build\windows-release-stage-1.6\dist\INSO_V1.6 `
      -Manifest       docs\evidence\rfq021\INSO_V1.6-artifact-manifest.sha256 `
      -TargetDir      D:\Program_Leo\INSO_Leo\dist\INSO_V1.6 `
      -RuntimeTarget  D:\Program_Leo\INSO_Leo\dist\INSO_V1.4\runtime `
      -RollbackDir    D:\Program_Leo\INSO_Leo\dist\release-backups\RFQ-021-pre-switch-<UTC> `
      -DatabaseBackup D:\...\workflow.sqlite3 `
      -DatabaseReport D:\...\workflow.sqlite3.verify.json `
      -ExpectedPreviousExeSha256 <sha256 of the installed EXE> `
      -ConfirmDatabaseBackupVerified -ConfirmSwitch

Re-check an installed release later (read-only):
  ... -TargetDir <dir> -Manifest <manifest> -VerifyInstalledOnly
#>
param(
    [string]$CandidateDir = "",
    [Parameter(Mandatory = $true)][string]$Manifest,
    [Parameter(Mandatory = $true)][string]$TargetDir,
    [string]$RuntimeTarget = "",
    [string]$RollbackDir = "",
    [string]$DatabaseBackup = "",
    [string]$DatabaseReport = "",
    [string]$ExpectedPreviousExeSha256 = "",
    # The executable this release replaces, and the one it installs. They differ
    # whenever a version bump changes the EXE name (V1.6 -> V1.7), so both sides
    # of the switch are named explicitly instead of assuming the same file.
    [string]$PreviousExeName = "INSO_V1.6.exe",
    # Empty means "whatever the candidate manifest lists" -- exactly one root EXE.
    [string]$CandidateExeName = "",
    # Install this release into a directory of its own instead of switching one
    # in place. Used when the previous release must stay runnable, byte for byte.
    [switch]$FreshInstall,
    [switch]$ConfirmDatabaseBackupVerified,
    [switch]$ConfirmSwitch,
    [switch]$VerifyInstalledOnly,
    [int]$MaxAgeHours = 72,
    # Offline-gate-test fault injection. Honoured only when the environment
    # variable RFQ021_OFFLINE_GATE_TESTS=1 is set, and every one of them can only
    # ever cause a failure -- none can turn a bad install into PASS.
    [switch]$InjectSwitchFault,
    [switch]$InjectPostCopyCorruption,
    [switch]$InjectRestoreFault,
    # "always" / "unidentified" / "before_switch": see Get-StopState.
    [string]$InjectProcessQueryFault = ""
)
$ErrorActionPreference = "Stop"
if ($env:RFQ021_OFFLINE_GATE_TESTS -ne "1") {
    $InjectSwitchFault = $false
    $InjectPostCopyCorruption = $false
    $InjectRestoreFault = $false
    $InjectProcessQueryFault = ""
}

function Get-Sha256([string]$path) {
    return (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
}

# Fail-closed process enumeration (RFQ-021-R5 P0).
#
# "No rows" is not "not running" when the query itself failed, when access was
# denied, or when a process's executable path cannot be read: each of those could
# be the program this install is about to overwrite. The status is three-valued;
# $null means unproven and must refuse. Used both before the first verification
# and again immediately before the first move.
function Get-StopState([string]$InstallRoot, [string]$FaultMode, [string[]]$ExeNames, [string]$Label) {
    if ($FaultMode -eq "query_failed") {
        return @{ Stopped = $null; Detail = "the process query failed (offline fault simulation)" }
    }
    if ($FaultMode -eq "unidentified") {
        return @{ Stopped = $null; Detail = "a process executable path could not be read (offline fault simulation)" }
    }
    # Both sides of a cross-version switch are queried: a stale process of either
    # name under this install is a live scheduler on the same ledger.
    $filter = (@($ExeNames | Select-Object -Unique) | ForEach-Object {
        "Name='" + ($_ -replace "'", "''") + "'"
    }) -join " OR "
    try {
        $processes = @(Get-CimInstance Win32_Process -Filter $filter -ErrorAction Stop)
    }
    catch {
        return @{ Stopped = $null; Detail = "process enumeration failed: $($_.Exception.Message)" }
    }
    $unidentified = @($processes | Where-Object { [string]::IsNullOrWhiteSpace([string]$_.ExecutablePath) })
    if ($unidentified.Count -gt 0) {
        return @{ Stopped = $null; Detail = "cannot read the executable path of $($unidentified.Count) $Label process(es) (PIDs: $($unidentified.ProcessId -join ', '))" }
    }
    $running = @($processes | Where-Object {
        ([string]$_.ExecutablePath).StartsWith($InstallRoot, [StringComparison]::OrdinalIgnoreCase)
    })
    if ($running.Count -gt 0) {
        return @{ Stopped = $false; Detail = "PIDs $($running.ProcessId -join ', ')" }
    }
    return @{ Stopped = $true; Detail = "$($processes.Count) other $Label process(es), none under this install" }
}

function Stop-Switch([string]$message) {
    Write-Output "INSTALL_RESULT = FAIL"
    throw "Refusing to switch: $message"
}

function Get-Sha256([string]$path) {
    return (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
}

# A path written through the `runtime` junction and the same path written at the
# junction's real target name the same file. Normalise both to the real form
# before comparing, or a valid report would be refused for naming the file the
# way the operator can actually see it.
function Get-ComparedPath([string]$path, [string]$targetDir, [string]$junctionTarget) {
    $full = [System.IO.Path]::GetFullPath($path).TrimEnd('\')
    $prefix = ([System.IO.Path]::GetFullPath($targetDir).TrimEnd('\')) + '\runtime'
    if ($full.StartsWith($prefix + '\', [StringComparison]::OrdinalIgnoreCase)) {
        $full = $junctionTarget.TrimEnd('\') + $full.Substring($prefix.Length)
    }
    return $full.TrimEnd('\')
}

function Assert-DatabaseReport {
    # One gate, two callers: the in-place switch and the fresh install. A switch
    # also proves the report names *this* install; a fresh install proves the
    # ledger instead, because it inherits the live configuration through the
    # junction it points at rather than owning it.
    param(
        [string]$DatabaseBackup,
        [string]$DatabaseReport,
        [string]$JunctionTarget,
        [string]$ConfigRoot,
        [string]$InstallDirForReport,
        [int]$MaxAgeHours
    )
if (-not (Test-Path -LiteralPath $DatabaseBackup -PathType Leaf)) {
    Stop-Switch "database backup not found: $DatabaseBackup. A switch without a database rollback is refused."
}
$db = (Resolve-Path -LiteralPath $DatabaseBackup).Path
if ([string]::IsNullOrWhiteSpace($DatabaseReport)) { $DatabaseReport = "$db.verify.json" }
if (-not (Test-Path -LiteralPath $DatabaseReport -PathType Leaf)) {
    Stop-Switch "no verification report at $DatabaseReport. Run scripts\verify_database_backup.ps1 first."
}
$report = Get-Content -LiteralPath $DatabaseReport -Raw -Encoding UTF8 | ConvertFrom-Json
if ($report.result -ne "PASS") { Stop-Switch "database verification report is not PASS" }
if ($report.schema_version -lt 4) {
    Stop-Switch "the database report is schema $($report.schema_version); it does not carry the quiescence and write-intent proofs this installer requires. Re-run verify_database_backup.ps1."
}
if (-not $report.quiescence) { Stop-Switch "the database report carries no quiescence proof" }
if (-not $report.process_state) { Stop-Switch "the database report carries no proven process state" }
if ($report.program_stopped -isnot [bool] -or -not $report.program_stopped) {
    Stop-Switch "the database report does not prove the program was stopped"
}
if (-not $report.wal_clean) { Stop-Switch "the database report does not prove a checkpointed WAL" }
if ($report.integrity_check -ne "ok") { Stop-Switch "database integrity_check was $($report.integrity_check)" }
if ([double]$report.event_age_hours -gt $MaxAgeHours) {
    Stop-Switch ("the ledger's last event is {0} h old; this backup is not current" -f $report.event_age_hours)
}
if ([int]$report.purchase_rows -lt 1) {
    Stop-Switch "database backup has no purchase rows; it is not the business ledger"
}
foreach ($table in @("workflow_v12_purchase_state", "workflow_v13_holds", "workflow_v12_events")) {
    $entry = $report.tables.$table
    if (-not $entry -or -not $entry.present) { Stop-Switch "database backup is missing table $table" }
}
$dbHash = Get-Sha256 $db
if ($report.database_sha256 -ne $dbHash) {
    Stop-Switch "the verification report describes different bytes ($($report.database_sha256)) than $dbHash"
}
if ($report.source_sha256 -ne $report.database_sha256) {
    Stop-Switch "the report does not bind the copy to its source database"
}
# A report is only about *this* machine's *this* install. Without this, a
# perfectly valid report from another installation would authorise a switch.
# A fresh install into a new directory deliberately skips this: the ledger is
# shared through the runtime junction, so the report was produced against the
# install that owns that junction -- and the ledger itself is still bound below.
$reportInstall = if ($report.install_dir) { ([string]$report.install_dir).TrimEnd('\') } else { "" }
if ($InstallDirForReport) {
    if (-not $reportInstall -or -not [string]::Equals($reportInstall, $InstallDirForReport, [StringComparison]::OrdinalIgnoreCase)) {
        Stop-Switch "the database report belongs to '$reportInstall', not to this installation '$InstallDirForReport'"
    }
}
# A write-intent count that is absent, null or not a number is not zero. Only a
# confirmed 0, or a proven legacy ledger whose unknown writes are still
# protected, may authorise the switch.
$intentCount = $report.open_write_intents
if ($null -eq $intentCount -or -not (($intentCount -is [int]) -or ($intentCount -is [long]))) {
    Stop-Switch "the report's write-intent count is '$intentCount', not a proven number. An unproven count is not zero."
}
if ([int64]$intentCount -ne 0) {
    Stop-Switch "$([int64]$intentCount) unresolved write intent(s) were in the ledger; switching over an unconfirmed external write can lose or replay an order"
}
switch ([string]$report.write_intent_state) {
    "NONE_PROVEN" { }
    "LEGACY_NO_JOURNAL_PROVEN" {
        $legacy = $report.legacy_unknown_write
        if (-not $legacy -or -not $legacy.checked) {
            Stop-Switch "the report claims a legacy ledger without verifying its unknown-write state; absence of the journal is not zero"
        }
        foreach ($field in @("unprotected_unknown_rows", "unattributed_holds")) {
            $value = $legacy.$field
            if ($null -eq $value -or -not (($value -is [int]) -or ($value -is [long]))) {
                Stop-Switch "the report's legacy unknown-write check could not determine '$field'; that is not zero"
            }
            if ([int64]$value -ne 0) {
                Stop-Switch ("the ledger holds {0} {1}; switching over it could lose or replay an unknown write" -f $value, $field)
            }
        }
    }
    "LEGACY_NO_JOURNAL_UNPROVEN" {
        Stop-Switch "the report's legacy unknown-write state is not proven; an unprotected UNKNOWN/SENT write could be lost or replayed by a switch. Reconcile it by hand and never clear a hold."
    }
    default {
        Stop-Switch "the report's write-intent state is '$($report.write_intent_state)'; it is not a proven state"
    }
}

# The configuration must still point at the ledger the report covers.
$liveProduction = Get-Content -LiteralPath (Join-Path $JunctionTarget "production.json") -Raw -Encoding UTF8 | ConvertFrom-Json
$sqlitePath = [string]$liveProduction.sqlite_path
if ([string]::IsNullOrWhiteSpace($sqlitePath)) { Stop-Switch "production.json has no sqlite_path" }
$configDb = if ([System.IO.Path]::IsPathRooted($sqlitePath)) { $sqlitePath } else { Join-Path $ConfigRoot $sqlitePath }
if (-not (Test-Path -LiteralPath $configDb -PathType Leaf)) {
    Stop-Switch "the configured ledger does not exist: $configDb"
}
if ((Get-Sha256 $configDb) -ne $report.source_sha256) {
    Stop-Switch "the configured ledger ($configDb) is not the database this report covers"
}
$reportedSource = if ($report.source_database) { ([string]$report.source_database) } else { "" }
if (-not $reportedSource) {
    Stop-Switch "the report names no source database; its provenance cannot be checked"
}
$comparedConfig = Get-ComparedPath $configDb $ConfigRoot $JunctionTarget
$comparedReport = Get-ComparedPath $reportedSource $ConfigRoot $JunctionTarget
if (-not [string]::Equals($comparedReport, $comparedConfig, [StringComparison]::OrdinalIgnoreCase)) {
    Stop-Switch "the report's source path '$reportedSource' is not the ledger the live configuration names ('$configDb')"
}
foreach ($path in @("$db-wal", "$configDb-wal")) {
    if ((Test-Path -LiteralPath $path -PathType Leaf) -and ((Get-Item -LiteralPath $path).Length -gt 0)) {
        Stop-Switch "a non-empty $path exists; the ledger is not quiescent"
    }
}

    return @{
        Database = $db
        Report = $DatabaseReport
        Source = $report.source_sha256
        ReportInstall = $reportInstall
    }

}

function Read-Manifest([string]$path) {
    $entries = @{}
    foreach ($line in (Get-Content -LiteralPath $path -Encoding UTF8)) {
        if (-not $line.Trim()) { continue }
        $split = $line.IndexOf("  ")
        if ($split -lt 1) { Stop-Switch "malformed manifest line in $path" }
        $hash = $line.Substring(0, $split).Trim().ToLowerInvariant()
        if ($hash.Length -ne 64) { Stop-Switch "malformed manifest hash in $path" }
        $entries[$line.Substring($split + 2).Trim().Replace('\', '/')] = $hash
    }
    return $entries
}

function Get-ManifestExe([hashtable]$manifest, [string]$Name) {
    # A release's root EXE is whatever its manifest lists -- the name changes
    # when the version changes, so it is read from the manifest rather than
    # assumed, and a manifest naming two (or none) is refused outright.
    $exes = @($manifest.Keys | Where-Object { $_ -match '^[^/]+\.exe$' })
    if ($exes.Count -ne 1) {
        Stop-Switch "the manifest must list exactly one root EXE; it lists $($exes.Count)"
    }
    if ($Name -and $exes[0] -ne $Name) {
        Stop-Switch "the manifest's EXE is $($exes[0]), not the expected $Name"
    }
    return $exes[0]
}

function Assert-InstalledMatches([string]$target, [hashtable]$expected, [string]$ExeName) {
    # Program files only: a rollback snapshot's manifest also lists the
    # configuration it captured, and those live in the snapshot, not in the
    # install directory. Every program entry is still checked byte for byte.
    $program = @($expected.Keys | Where-Object { $_ -eq $ExeName -or $_ -like "_internal/*" })
    $problems = New-Object System.Collections.ArrayList
    foreach ($rel in $program) {
        $dest = Join-Path $target $rel
        if (-not (Test-Path -LiteralPath $dest -PathType Leaf)) {
            [void]$problems.Add("missing $rel")
            continue
        }
        if ((Get-Sha256 $dest) -ne $expected[$rel]) { [void]$problems.Add("mismatch $rel") }
    }
    $expectedInternal = @($program | Where-Object { $_ -like "_internal/*" }).Count
    $internal = Join-Path $target "_internal"
    $onDisk = if (Test-Path -LiteralPath $internal -PathType Container) {
        @(Get-ChildItem -LiteralPath $internal -Recurse -File).Count
    } else { 0 }
    if ($onDisk -ne $expectedInternal) {
        [void]$problems.Add("_internal holds $onDisk file(s); the manifest expects $expectedInternal")
    }
    return $problems
}

# --- verify-only mode: read-only re-check of an installed release ----------
if ($VerifyInstalledOnly) {
    $expected = Read-Manifest $Manifest
    $installedExe = Get-ManifestExe $expected $CandidateExeName
    $programEntries = @($expected.Keys | Where-Object { $_ -eq $installedExe -or $_ -like "_internal/*" })
    if ($programEntries -notcontains $installedExe -or -not ($programEntries -like "_internal/*")) {
        Write-Output "INSTALLED_VERIFY = FAIL"
        Write-Output "  the manifest lists no complete program (EXE plus at least one _internal file)"
        exit 1
    }
    $problems = Assert-InstalledMatches ((Resolve-Path -LiteralPath $TargetDir).Path) $expected $installedExe
    if ($problems.Count) {
        Write-Output "INSTALLED_VERIFY = FAIL"
        foreach ($problem in $problems) { Write-Output "  $problem" }
        exit 1
    }
    Write-Output "installed_exe = $installedExe"
    Write-Output "installed_files = $($programEntries.Count)"
    Write-Output "INSTALLED_VERIFY = PASS"
    exit 0
}

# --- fresh install: a release directory of its own -------------------------
# Owner decision (RFQ-025): V1.7 goes into its own directory so the accepted
# V1.6 build stays runnable and byte-identical. Nothing here touches another
# install; the business ledger and configuration are inherited through the
# runtime junction, exactly as the in-place layout does it.
if ($FreshInstall) {
    if ([string]::IsNullOrWhiteSpace($CandidateDir)) { Stop-Switch "-CandidateDir is required" }
    if ([string]::IsNullOrWhiteSpace($RuntimeTarget)) { Stop-Switch "-RuntimeTarget is required" }
    if ([string]::IsNullOrWhiteSpace($DatabaseBackup)) { Stop-Switch "-DatabaseBackup is required" }
    if (-not $ConfirmSwitch) {
        Stop-Switch "without -ConfirmSwitch (an Owner-approved maintenance window is required)"
    }
    if (-not $ConfirmDatabaseBackupVerified) {
        Stop-Switch "without -ConfirmDatabaseBackupVerified. A verified ledger backup is not optional."
    }

    $target = [System.IO.Path]::GetFullPath($TargetDir).TrimEnd('\')
    $createdRoot = $false
    if (Test-Path -LiteralPath $target) {
        $occupied = @(Get-ChildItem -LiteralPath $target -Force -ErrorAction SilentlyContinue)
        if ($occupied.Count -gt 0) {
            Stop-Switch "$target is not empty; -FreshInstall never overwrites an existing install"
        }
    }

    & (Join-Path $PSScriptRoot "verify_release_candidate.ps1") -CandidateDir $CandidateDir -Manifest $Manifest
    if ($LASTEXITCODE -ne 0) { throw "Candidate verification failed; nothing was changed." }
    $candidate = (Resolve-Path -LiteralPath $CandidateDir).Path
    $approved = Read-Manifest $Manifest
    $CandidateExeName = Get-ManifestExe $approved $CandidateExeName
    if (Test-Path -LiteralPath (Join-Path $candidate "runtime")) {
        Stop-Switch "the candidate directory carries its own runtime; the install must inherit the live one through a junction"
    }
    if (-not (Test-Path -LiteralPath $RuntimeTarget -PathType Container)) {
        Stop-Switch "runtime target not found: $RuntimeTarget"
    }
    $normalizedExpected = (Resolve-Path -LiteralPath $RuntimeTarget).Path.TrimEnd('\')

    # The ledger gate. The report was produced against the install that owns the
    # shared runtime, so it is not required to name the new directory -- but the
    # ledger it describes must still be the one this configuration points at.
    $dbState = Assert-DatabaseReport -DatabaseBackup $DatabaseBackup -DatabaseReport $DatabaseReport `
        -JunctionTarget $normalizedExpected -ConfigRoot $normalizedExpected -InstallDirForReport "" `
        -MaxAgeHours $MaxAgeHours
    $DatabaseReport = $dbState.Report

    # Two schedulers must never share one ledger. Neither the new target nor the
    # install that owns the runtime may have a live process.
    $gateNames = @($PreviousExeName, $CandidateExeName) | Select-Object -Unique
    foreach ($root in @($target, $dbState.ReportInstall)) {
        if ([string]::IsNullOrWhiteSpace($root)) { continue }
        $state = Get-StopState $root "" $gateNames $PreviousLabel
        if ($null -eq $state.Stopped) {
            Stop-Switch "cannot prove no scheduler is running under ${root}: $($state.Detail). Nothing was created."
        }
        if (-not $state.Stopped) {
            Stop-Switch "a scheduler is still running from $root ($($state.Detail)). Stop it normally first; never force-kill."
        }
    }
    if ([string]::IsNullOrWhiteSpace($dbState.ReportInstall)) {
        Stop-Switch "the database report names no install directory; the previous scheduler's location cannot be checked"
    }

    # --- create, copy, verify ------------------------------------------------
    if (-not (Test-Path -LiteralPath $target)) {
        New-Item -ItemType Directory -Path $target | Out-Null
        $createdRoot = $true
    }
    try {
        $runtimePath = Join-Path $target "runtime"
        if (Test-Path -LiteralPath $runtimePath) { Stop-Switch "unexpected existing runtime at $runtimePath" }
        New-Item -ItemType Junction -Path $runtimePath -Target $normalizedExpected | Out-Null
        $junctionItem = Get-Item -LiteralPath $runtimePath -Force
        if ($junctionItem.LinkType -ne "Junction" -or
            (([string]@($junctionItem.Target)[0]).TrimEnd('\') -ne $normalizedExpected)) {
            throw "the runtime junction does not point at $normalizedExpected"
        }
        Copy-Item -LiteralPath (Join-Path $candidate $CandidateExeName) -Destination $target
        Copy-Item -LiteralPath (Join-Path $candidate "_internal") -Destination (Join-Path $target "_internal") -Recurse
        $problems = Assert-InstalledMatches $target $approved $CandidateExeName
        if ($problems.Count -gt 0) {
            $detail = ($problems | Select-Object -First 5) -join "; "
            throw "post-copy verification failed ($($problems.Count) problem(s)): $detail"
        }
    }
    catch {
        $reason = $_.Exception.Message
        Write-Output "INSTALL_ERROR = $reason"
        # Remove only what this run created: never a pre-existing file, never
        # another install, and never the runtime itself (the junction target
        # lives outside this directory).
        foreach ($name in @($CandidateExeName, "_internal", "runtime")) {
            $path = Join-Path $target $name
            if (Test-Path -LiteralPath $path) {
                Remove-Item -LiteralPath $path -Recurse -Force -ErrorAction SilentlyContinue
            }
        }
        if ($createdRoot -and (Test-Path -LiteralPath $target) -and
            -not (Get-ChildItem -LiteralPath $target -Force)) {
            Remove-Item -LiteralPath $target -Force
        }
        Write-Output "INSTALL_RESULT = FAIL_CLEANED"
        Write-Output "NOTE: nothing outside $target was touched; any existing install is unchanged and was not started."
        exit 2
    }

    Write-Output "install_dir = $target"
    Write-Output "installed_exe = $(Join-Path $target $CandidateExeName)"
    Write-Output "installed_exe_sha256 = $(Get-Sha256 (Join-Path $target $CandidateExeName))"
    Write-Output "installed_files_verified = $($approved.Count)"
    Write-Output "runtime_junction = $normalizedExpected"
    Write-Output "rollback_kind = PREVIOUS_INSTALL_UNTOUCHED"
    Write-Output "rollback_previous_install = $($dbState.ReportInstall)"
    Write-Output "rollback_database = $($dbState.Database)"
    Write-Output "rollback_database_report = $DatabaseReport"
    Write-Output "INSTALL_RESULT = PASS"
    Write-Output "NOTE: nothing was started. The previous install on disk is unchanged."
    exit 0
}

if ([string]::IsNullOrWhiteSpace($CandidateDir)) { Stop-Switch "-CandidateDir is required" }
if ([string]::IsNullOrWhiteSpace($RuntimeTarget)) { Stop-Switch "-RuntimeTarget is required" }
if ([string]::IsNullOrWhiteSpace($RollbackDir)) { Stop-Switch "-RollbackDir is required" }
if ([string]::IsNullOrWhiteSpace($DatabaseBackup)) { Stop-Switch "-DatabaseBackup is required" }

# --- 0. explicit authorisation ----------------------------------------------
if (-not $ConfirmSwitch) {
    Stop-Switch "without -ConfirmSwitch (an Owner-approved maintenance window is required)"
}
if (-not $ConfirmDatabaseBackupVerified) {
    Stop-Switch "without -ConfirmDatabaseBackupVerified. A program snapshot alone is not a rollback."
}
if ($ExpectedPreviousExeSha256 -notmatch '^[0-9a-fA-F]{64}$') {
    Stop-Switch "-ExpectedPreviousExeSha256 must be the full 64-hex SHA256 of the installed EXE"
}
$expectedPrevious = $ExpectedPreviousExeSha256.ToLowerInvariant()
# Message label only: the gate tests and every run log speak of "INSO_V1.6",
# while the file itself is "INSO_V1.6.exe".
$PreviousLabel = $PreviousExeName -replace '\.exe$', ''

# --- 1. the snapshot itself --------------------------------------------------
if (-not (Test-Path -LiteralPath $RollbackDir -PathType Container)) {
    Stop-Switch "rollback snapshot not found: $RollbackDir. Run backup_running_release.ps1 first."
}
$snapshotManifest = Join-Path $RollbackDir "PROGRAM-MANIFEST.sha256"
if (-not (Test-Path -LiteralPath $snapshotManifest -PathType Leaf)) {
    Stop-Switch "rollback snapshot has no PROGRAM-MANIFEST.sha256; it cannot be verified."
}
$snapshotRoot = (Resolve-Path -LiteralPath $RollbackDir).Path
$snapshot = Read-Manifest $snapshotManifest
if ($snapshot.Count -lt 2) {
    Stop-Switch "rollback manifest is empty or truncated; refusing to treat it as a snapshot."
}
$snapshotBad = 0
foreach ($rel in $snapshot.Keys) {
    $full = Join-Path $snapshotRoot $rel
    if (-not (Test-Path -LiteralPath $full -PathType Leaf)) { $snapshotBad++; continue }
    if ((Get-Sha256 $full) -ne $snapshot[$rel]) { $snapshotBad++ }
}
if ($snapshotBad -gt 0) {
    Stop-Switch "rollback snapshot failed verification ($snapshotBad file(s)); do not switch."
}

# --- 2. the snapshot must be the installed build ----------------------------
$target = (Resolve-Path -LiteralPath $TargetDir).Path
$targetExe = Join-Path $target $PreviousExeName
$targetInternal = Join-Path $target "_internal"
if (-not (Test-Path -LiteralPath $targetExe -PathType Leaf)) { Stop-Switch "no installed EXE at $targetExe" }
if (-not (Test-Path -LiteralPath $targetInternal -PathType Container)) {
    Stop-Switch "no installed _internal at $targetInternal"
}
if (-not $snapshot.ContainsKey($PreviousExeName)) {
    Stop-Switch "rollback snapshot does not contain the old EXE ($PreviousExeName); it cannot roll the program back."
}
if ($snapshot[$PreviousExeName] -ne $expectedPrevious) {
    Stop-Switch "snapshot EXE ($($snapshot[$PreviousExeName])) is not the build named by -ExpectedPreviousExeSha256"
}
$liveHash = Get-Sha256 $targetExe
if ($liveHash -ne $expectedPrevious) {
    Stop-Switch "installed EXE is $liveHash, not the expected $expectedPrevious; the snapshot is of a different build"
}

$targetFiles = @(Get-ChildItem -LiteralPath $targetInternal -Recurse -File)
if ($targetFiles.Count -lt 1) { Stop-Switch "_internal is empty; refusing to snapshot-match an empty install" }
$listedInternal = @($snapshot.Keys | Where-Object { $_ -like "_internal/*" })
if ($listedInternal.Count -ne $targetFiles.Count) {
    Stop-Switch "snapshot lists $($listedInternal.Count) _internal file(s) but the install has $($targetFiles.Count); the snapshot is incomplete or stale"
}
$broken = 0
foreach ($file in $targetFiles) {
    $rel = $file.FullName.Substring($target.Length + 1).Replace('\', '/')
    if (-not $snapshot.ContainsKey($rel) -or (Get-Sha256 $file.FullName) -ne $snapshot[$rel]) { $broken++ }
}
if ($broken -gt 0) {
    Stop-Switch "the snapshot does not reproduce the installed program ($broken file(s) missing or different)"
}
$unknown = 0
foreach ($rel in $snapshot.Keys) {
    if ($rel -eq $PreviousExeName -or $rel -like "_internal/*") {
        if (-not (Test-Path -LiteralPath (Join-Path $target $rel) -PathType Leaf)) { $unknown++ }
    }
}
if ($unknown -gt 0) {
    Stop-Switch "the snapshot holds $unknown program file(s) the install does not have; it is not this build"
}
# The same set, kept for the restore check: a rollback is only proven when the
# restored tree matches *this* list, not merely this EXE.
$snapshotProgram = @{}
foreach ($rel in $snapshot.Keys) {
    if ($rel -eq $PreviousExeName -or $rel -like "_internal/*") { $snapshotProgram[$rel] = $snapshot[$rel] }
}

# --- 3. the runtime junction must be a junction, pointing where we expect ----
$runtime = Join-Path $target "runtime"
if (-not (Test-Path -LiteralPath $runtime)) {
    Stop-Switch "no usable runtime junction at $runtime (missing, or its target is gone); the layout this installer protects is not in place"
}
$runtimeItem = Get-Item -LiteralPath $runtime -Force
if (($runtimeItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -eq 0) {
    Stop-Switch "expected a runtime junction at $runtime; refusing to touch an unexpected layout."
}
# A symlink is a reparse point too; the release layout is a junction.
if ($runtimeItem.LinkType -ne "Junction") {
    Stop-Switch "runtime is a reparse point of type '$($runtimeItem.LinkType)', not a Junction"
}
$junctionTarget = @($runtimeItem.Target)[0]
if (-not $junctionTarget) { Stop-Switch "runtime exists but exposes no junction target" }
$normalizedJunction = ([string]$junctionTarget).TrimEnd('\')
$normalizedExpected = (Resolve-Path -LiteralPath $RuntimeTarget).Path.TrimEnd('\')
if ($normalizedJunction -ne $normalizedExpected) {
    Stop-Switch "runtime points at $normalizedJunction, not $normalizedExpected"
}

# --- 4. the snapshot's configuration must be the live configuration ----------
foreach ($name in @("production.json", "research.json")) {
    $snapshotConfig = Join-Path $snapshotRoot "config\$name"
    $liveConfig = Join-Path $normalizedJunction $name
    if (-not $snapshot.ContainsKey("config/$name")) {
        Stop-Switch "rollback snapshot is missing the mandatory config\$name"
    }
    if (-not (Test-Path -LiteralPath $liveConfig -PathType Leaf)) {
        Stop-Switch "the live configuration behind runtime is missing: $liveConfig"
    }
    if ((Get-Sha256 $snapshotConfig) -ne (Get-Sha256 $liveConfig)) {
        Stop-Switch "the snapshot's config\$name is not the live configuration behind runtime; the backup is stale or was taken from another install"
    }
}

# --- 5. the database report must describe *this* ledger ---------------------
$dbState = Assert-DatabaseReport -DatabaseBackup $DatabaseBackup -DatabaseReport $DatabaseReport `
    -JunctionTarget $normalizedJunction -ConfigRoot $target -InstallDirForReport $target `
    -MaxAgeHours $MaxAgeHours
$db = $dbState.Database
$DatabaseReport = $dbState.Report

# --- 6. the candidate, verified before anything moves ----------------------
& (Join-Path $PSScriptRoot "verify_release_candidate.ps1") -CandidateDir $CandidateDir -Manifest $Manifest
if ($LASTEXITCODE -ne 0) { throw "Candidate verification failed; nothing was changed." }
$candidate = (Resolve-Path -LiteralPath $CandidateDir).Path
if ($candidate -eq $target) { Stop-Switch "candidate and target are the same directory" }
$candidateInternal = Join-Path $candidate "_internal"
$approved = Read-Manifest $Manifest
# The candidate's own EXE name, read from its manifest: a version bump renames
# it, so the switch must not assume the name it is replacing.
$CandidateExeName = Get-ManifestExe $approved $CandidateExeName

# --- 7. the target must not be running (by path, not just by name) ---------
# An unqueryable or unidentifiable process is NOT "not running".
$gateFault = if ($InjectProcessQueryFault -eq "always") { "query_failed" } else { $InjectProcessQueryFault }
$stop = Get-StopState $target $gateFault @($PreviousExeName, $CandidateExeName) $PreviousLabel
if ($null -eq $stop.Stopped) {
    Stop-Switch "cannot prove $PreviousLabel is stopped for ${target}: $($stop.Detail). Refusing to switch on an unproven stop."
}
if (-not $stop.Stopped) {
    Stop-Switch "$PreviousLabel is still running from $target ($($stop.Detail)). Stop it normally first; never force-kill."
}

# --- 8. switch ------------------------------------------------------------
$stamp = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")
$previousExe = Join-Path $target ($PreviousExeName + ".prev-" + $stamp)
$previousInternal = Join-Path $target ("_internal.prev-" + $stamp)
$switched = $false

function Restore-Previous {
    param([string]$Target, [string]$PreviousInternal, [string]$PreviousExe,
          [string]$PreviousExeName, [string]$CandidateExeName)
    # Restore only what was actually moved aside, and never throw out of the
    # recovery path: a fault inside recovery must still end in an explicit,
    # honest result instead of an uncaught script error.
    $problems = New-Object System.Collections.ArrayList
    if (Test-Path -LiteralPath $PreviousInternal) {
        try {
            if (Test-Path -LiteralPath (Join-Path $Target "_internal")) {
                Remove-Item -LiteralPath (Join-Path $Target "_internal") -Recurse -Force
            }
            Move-Item -LiteralPath $PreviousInternal -Destination (Join-Path $Target "_internal")
        }
        catch { [void]$problems.Add("_internal restore failed: $($_.Exception.Message)") }
    }
    else { [void]$problems.Add("no saved payload at $PreviousInternal") }
    if (Test-Path -LiteralPath $PreviousExe) {
        try {
            # Remove whatever EXE the failed switch left behind -- it may carry a
            # different name than the one being restored -- before putting the
            # previous build's own EXE back.
            foreach ($name in @($CandidateExeName, $PreviousExeName) | Select-Object -Unique) {
                $leftover = Join-Path $Target $name
                if ($name -and (Test-Path -LiteralPath $leftover)) {
                    Remove-Item -LiteralPath $leftover -Force
                }
            }
            Move-Item -LiteralPath $PreviousExe -Destination (Join-Path $Target $PreviousExeName)
        }
        catch { [void]$problems.Add("EXE restore failed: $($_.Exception.Message)") }
    }
    else { [void]$problems.Add("no saved EXE at $PreviousExe") }
    return $problems
}

function Assert-RestoredBuild {
    param([string]$Target, [hashtable]$Program, [string]$ExeName)
    # "The old EXE is back" is not a rollback. Every program file must match the
    # snapshot again and the payload must hold exactly the listed files.
    $problems = Assert-InstalledMatches $Target $Program $ExeName
    return $problems
}

# --- 8. switch ------------------------------------------------------------
$stamp = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")
$previousExe = Join-Path $target ($PreviousExeName + ".prev-" + $stamp)
$previousInternal = Join-Path $target ("_internal.prev-" + $stamp)
$switched = $false

# Re-check right before the first move: the guard above ran before the candidate
# was verified, and a program started in between must still stop the switch. The
# same fail-closed rule applies: an unproven process state refuses, and nothing
# has been moved yet.
$lateFault = if ($InjectProcessQueryFault -eq "before_switch") { "query_failed" } else { "" }
$stopNow = Get-StopState $target $lateFault @($PreviousExeName, $CandidateExeName) $PreviousLabel
if ($null -eq $stopNow.Stopped) {
    Stop-Switch "cannot prove $PreviousLabel is stopped before the switch: $($stopNow.Detail). Nothing was changed."
}
if (-not $stopNow.Stopped) {
    Stop-Switch "$PreviousLabel started from $target while the candidate was being verified ($($stopNow.Detail)); nothing was changed."
}

try {
    Move-Item -LiteralPath $targetInternal -Destination $previousInternal
    if ($InjectSwitchFault) { throw "injected switch fault (offline test only)" }
    Copy-Item -LiteralPath $candidateInternal -Destination $targetInternal -Recurse
    Move-Item -LiteralPath $targetExe -Destination $previousExe
    Copy-Item -LiteralPath (Join-Path $candidate $CandidateExeName) -Destination (Join-Path $target $CandidateExeName)
    if ($InjectPostCopyCorruption) {
        # Bytes changed after the copy, file count unchanged: only a per-file
        # re-hash can notice this.
        Add-Content -LiteralPath (Join-Path $targetInternal "a.dll") -Value "corrupted after copy"
    }
    $switched = $true

    # Every installed file, not a count.
    $problems = Assert-InstalledMatches $target $approved $CandidateExeName
    if ($problems.Count -gt 0) {
        $detail = ($problems | Select-Object -First 5) -join "; "
        throw "post-copy verification failed ($($problems.Count) problem(s)): $detail"
    }
}
catch {
    $reason = $_.Exception.Message
    Write-Output "SWITCH_ERROR = $reason"
    if ($InjectRestoreFault) {
        # Offline-gate-test only: prove the recovery path can fail safely.
        try { throw "injected restore fault (offline test only)" } catch { $restoreNotes = @($_.Exception.Message) }
    }
    else {
        $restoreNotes = @(Restore-Previous $target $previousInternal $previousExe $PreviousExeName $CandidateExeName)
    }
    # The verdict is what the target looks like now, not which steps ran: a fault
    # can land before either `.prev-` item exists, and the old build can already
    # be in place.
    $restoreProblems = @(Assert-RestoredBuild $target $snapshotProgram $PreviousExeName)
    if ($restoreProblems.Count -eq 0) {
        Write-Output "restored_exe_sha256 = $expectedPrevious"
        Write-Output "restored_files_verified = $($snapshotProgram.Count)"
        foreach ($note in $restoreNotes) { Write-Output "restore_note = $note" }
        Write-Output "INSTALL_RESULT = FAIL_RESTORED"
        Write-Output "NOTE: the previous build is back in place and verified file by file. Nothing was started."
        exit 2
    }
    Write-Output "INSTALL_RESULT = ROLLBACK_REQUIRED"
    foreach ($note in $restoreNotes) { Write-Output "restore_note = $note" }
    foreach ($problem in $restoreProblems) { Write-Output "restore_problem = $problem" }
    Write-Output "restore_from = $previousInternal"
    Write-Output "restore_exe = $previousExe"
    Write-Output "snapshot_dir = $snapshotRoot"
    Write-Output "NOTE: the automatic restore could not be completed and verified. Restore the two .prev-$stamp items by hand (the snapshot is the reference copy), then re-run -VerifyInstalledOnly with the OLD manifest. Start nothing."
    exit 3
}

if (-not $switched) {
    Write-Output "INSTALL_RESULT = FAIL"
    exit 2
}

Write-Output "rollback_snapshot = $snapshotRoot"
Write-Output "rollback_database = $db"
Write-Output "rollback_database_report = $DatabaseReport"
Write-Output "previous_exe_sha256 = $expectedPrevious"
Write-Output "previous_exe = $previousExe"
Write-Output "previous_internal = $previousInternal"
Write-Output "installed_exe = $(Join-Path $target $CandidateExeName)"
Write-Output "installed_exe_sha256 = $(Get-Sha256 (Join-Path $target $CandidateExeName))"
Write-Output "installed_files_verified = $($approved.Count)"
Write-Output "INSTALL_RESULT = PASS"
Write-Output "NEXT: first launch must be the NEW exe with --safe-preview. The previous exe has no such flag."
Write-Output "COLD ROLLBACK and any post-rollback business restart are separate, separately approved steps."
