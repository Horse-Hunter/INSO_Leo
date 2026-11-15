<#
Install a verified candidate over the stopped release.

RFQ-021-R4: the switch fails closed unless the *whole* rollback is proven,
before a single target file is touched:

  1. program+config snapshot whose manifest re-verifies file by file;
  2. that snapshot is the CURRENT build -- every file of the live target
     (`INSO_V1.6.exe` + all of `_internal`) is listed with the same hash, and the
     snapshot has no program file the target lacks;
  3. the operator names the old build explicitly
     (`-ExpectedPreviousExeSha256`) and the live EXE must equal it;
  4. `runtime` must be a junction pointing at exactly `-RuntimeTarget`;
  5. the database backup carries an independent `verify_database_backup.ps1`
     report bound to its SHA256 (integrity_check=ok, business tables present) --
     a magic header plus an acknowledgement is not verification.

It never starts anything, and it never pretends the previous build understands
`--safe-preview`: rollback is verified by hash, never by launching the old EXE.
Cold rollback and post-rollback business restart are separate approvals.

Usage:
  powershell -ExecutionPolicy Bypass -File scripts\install_release_candidate.ps1 `
      -CandidateDir        build\windows-release-stage-1.6\dist\INSO_V1.6 `
      -Manifest            docs\evidence\rfq021\INSO_V1.6-artifact-manifest.sha256 `
      -TargetDir           D:\Program_Leo\INSO_Leo\dist\INSO_V1.6 `
      -RuntimeTarget       D:\Program_Leo\INSO_Leo\dist\INSO_V1.4\runtime `
      -RollbackDir         D:\Program_Leo\INSO_Leo\dist\release-backups\RFQ-021-pre-switch-<UTC> `
      -DatabaseBackup      D:\...\RFQ-021-pre-switch-<UTC>\workflow.sqlite3 `
      -ExpectedPreviousExeSha256 <sha256 of the currently installed EXE> `
      -ConfirmDatabaseBackupVerified -ConfirmSwitch
#>
param(
    [Parameter(Mandatory = $true)][string]$CandidateDir,
    [Parameter(Mandatory = $true)][string]$Manifest,
    [Parameter(Mandatory = $true)][string]$TargetDir,
    [Parameter(Mandatory = $true)][string]$RuntimeTarget,
    [Parameter(Mandatory = $true)][string]$RollbackDir,
    [Parameter(Mandatory = $true)][string]$DatabaseBackup,
    [Parameter(Mandatory = $true)][string]$ExpectedPreviousExeSha256,
    [string]$DatabaseReport = "",
    [switch]$ConfirmDatabaseBackupVerified,
    [switch]$ConfirmSwitch
)
$ErrorActionPreference = "Stop"

function Stop-Switch([string]$message) {
    throw "Refusing to switch: $message"
}

function Read-Manifest([string]$path) {
    $entries = @{}
    foreach ($line in (Get-Content -LiteralPath $path -Encoding UTF8)) {
        if (-not $line.Trim()) { continue }
        $split = $line.IndexOf("  ")
        if ($split -lt 1) { Stop-Switch "malformed manifest line in $path" }
        $hash = $line.Substring(0, $split).Trim().ToLowerInvariant()
        $rel = $line.Substring($split + 2).Trim().Replace('\', '/')
        $entries[$rel] = $hash
    }
    return $entries
}

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

# The "is it still running?" refusal is deliberately placed immediately before
# the first mutation (see step 6) rather than here: the read-only proof below
# takes a while, and a program started in between must still be caught. It also
# keeps the failure message honest -- an incomplete rollback is reported as an
# incomplete rollback, not as "the program is running".

# --- 1. rollback half 1: program + config snapshot ---------------------------
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
    $actual = (Get-FileHash -LiteralPath $full -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actual -ne $snapshot[$rel]) { $snapshotBad++ }
}
if ($snapshotBad -gt 0) {
    Stop-Switch "rollback snapshot failed verification ($snapshotBad file(s)); do not switch."
}

# --- 2. the snapshot must be the build that is installed right now ----------
$target = (Resolve-Path -LiteralPath $TargetDir).Path
$targetExe = Join-Path $target "INSO_V1.6.exe"
$targetInternal = Join-Path $target "_internal"
if (-not (Test-Path -LiteralPath $targetExe -PathType Leaf)) { Stop-Switch "no installed EXE at $targetExe" }
if (-not (Test-Path -LiteralPath $targetInternal -PathType Container)) {
    Stop-Switch "no installed _internal at $targetInternal"
}
if (-not $snapshot.ContainsKey("INSO_V1.6.exe")) {
    Stop-Switch "rollback snapshot does not contain the old EXE; it cannot roll the program back."
}
if ($snapshot["INSO_V1.6.exe"] -ne $expectedPrevious) {
    Stop-Switch "snapshot EXE ($($snapshot['INSO_V1.6.exe'])) is not the build named by -ExpectedPreviousExeSha256"
}
$liveHash = (Get-FileHash -LiteralPath $targetExe -Algorithm SHA256).Hash.ToLowerInvariant()
if ($liveHash -ne $expectedPrevious) {
    Stop-Switch "installed EXE is $liveHash, not the expected $expectedPrevious; the snapshot is of a different build"
}

$targetFiles = @(Get-ChildItem -LiteralPath $targetInternal -Recurse -File)
if ($targetFiles.Count -lt 1) { Stop-Switch "_internal is empty; refusing to snapshot-match an empty install" }
$listedInternal = @($snapshot.Keys | Where-Object { $_ -like "_internal/*" })
if ($listedInternal.Count -ne $targetFiles.Count) {
    Stop-Switch "snapshot lists $($listedInternal.Count) _internal file(s) but the install has $($targetFiles.Count); the snapshot is incomplete or stale"
}
$missing = 0
foreach ($file in $targetFiles) {
    $rel = $file.FullName.Substring($target.Length + 1).Replace('\', '/')
    if (-not $snapshot.ContainsKey($rel)) { $missing++; continue }
    $actual = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actual -ne $snapshot[$rel]) { $missing++ }
}
if ($missing -gt 0) {
    Stop-Switch "the snapshot does not reproduce the installed program ($missing file(s) missing or different)"
}
$unknown = 0
foreach ($rel in $snapshot.Keys) {
    if ($rel -eq "INSO_V1.6.exe" -or $rel -like "_internal/*") {
        if (-not (Test-Path -LiteralPath (Join-Path $target $rel) -PathType Leaf)) { $unknown++ }
    }
}
if ($unknown -gt 0) {
    Stop-Switch "the snapshot holds $unknown program file(s) the install does not have; it is not this build"
}
foreach ($required in @("config/production.json", "config/research.json")) {
    if (-not $snapshot.ContainsKey($required)) {
        Stop-Switch "rollback snapshot is missing the mandatory $required"
    }
}

# --- 3. the runtime junction must point where the release expects ------------
$runtime = Join-Path $target "runtime"
if (-not (Test-Path -LiteralPath $runtime)) {
    Stop-Switch "expected a runtime junction at $runtime; its absence means the layout changed"
}
$runtimeItem = Get-Item -LiteralPath $runtime -Force
if (($runtimeItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -eq 0) {
    Stop-Switch "expected a runtime junction at $runtime; refusing to touch an unexpected layout."
}
$junctionTarget = @($runtimeItem.Target)[0]
if (-not $junctionTarget) { Stop-Switch "runtime exists but exposes no junction target" }
$normalizedJunction = ([string]$junctionTarget).TrimEnd('\')
$normalizedExpected = (Resolve-Path -LiteralPath $RuntimeTarget).Path.TrimEnd('\')
if ($normalizedJunction -ne $normalizedExpected) {
    Stop-Switch "runtime points at $normalizedJunction, not $normalizedExpected"
}

# --- 4. rollback half 2: an independently verified database backup ----------
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
if ($report.integrity_check -ne "ok") { Stop-Switch "database integrity_check was $($report.integrity_check)" }
if ([int]$report.purchase_rows -lt 1) {
    Stop-Switch "database backup has no purchase rows; it is not the business ledger"
}
$dbHash = (Get-FileHash -LiteralPath $db -Algorithm SHA256).Hash.ToLowerInvariant()
if ($report.database_sha256 -ne $dbHash) {
    Stop-Switch "the verification report describes different bytes ($($report.database_sha256)) than $dbHash"
}
foreach ($table in @("workflow_v12_purchase_state", "workflow_v13_holds", "workflow_v12_events")) {
    $entry = $report.tables.$table
    if (-not $entry -or -not $entry.present) { Stop-Switch "database backup is missing table $table" }
}
$wal = "$db-wal"
if ((Test-Path -LiteralPath $wal -PathType Leaf) -and ((Get-Item -LiteralPath $wal).Length -gt 0)) {
    Stop-Switch "a non-empty -wal sits beside the database backup; the copy is inconsistent"
}

# --- 5. the candidate, verified before anything is moved --------------------
& (Join-Path $PSScriptRoot "verify_release_candidate.ps1") -CandidateDir $CandidateDir -Manifest $Manifest
if ($LASTEXITCODE -ne 0) { throw "Candidate verification failed; nothing was changed." }

$candidate = (Resolve-Path -LiteralPath $CandidateDir).Path
if ($candidate -eq $target) { Stop-Switch "candidate and target are the same directory" }

# Last gate before any file moves: the program must not be running.
$running = @(Get-Process -Name "INSO_V1.6" -ErrorAction SilentlyContinue)
if ($running.Count -gt 0) {
    Stop-Switch "INSO_V1.6 is still running (PIDs: $($running.Id -join ', ')). Stop it normally first; never force-kill."
}

$candidateInternal = Join-Path $candidate "_internal"
$candidateCount = @(Get-ChildItem -LiteralPath $candidateInternal -Recurse -File).Count
$stamp = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")

# --- 6. switch (all gates passed) -------------------------------------------
$previousExe = Join-Path $target ("INSO_V1.6.exe.prev-" + $stamp)
$previousInternal = Join-Path $target ("_internal.prev-" + $stamp)
Move-Item -LiteralPath $targetInternal -Destination $previousInternal
Copy-Item -LiteralPath $candidateInternal -Destination (Join-Path $target "_internal") -Recurse
Move-Item -LiteralPath $targetExe -Destination $previousExe
Copy-Item -LiteralPath (Join-Path $candidate "INSO_V1.6.exe") -Destination $targetExe

$installed = (Get-FileHash -LiteralPath $targetExe -Algorithm SHA256).Hash.ToLowerInvariant()
$expectedNew = (Get-FileHash -LiteralPath (Join-Path $candidate "INSO_V1.6.exe") -Algorithm SHA256).Hash.ToLowerInvariant()
if ($installed -ne $expectedNew) { throw "Installed EXE hash mismatch: $installed" }
$installedCount = @(Get-ChildItem -LiteralPath (Join-Path $target "_internal") -Recurse -File).Count
if ($installedCount -ne $candidateCount) {
    throw "Installed _internal has $installedCount file(s); the candidate has $candidateCount"
}

Write-Output "rollback_snapshot = $snapshotRoot"
Write-Output "rollback_database = $db"
Write-Output "rollback_database_report = $DatabaseReport"
Write-Output "previous_exe_sha256 = $expectedPrevious"
Write-Output "previous_exe = $previousExe"
Write-Output "previous_internal = $previousInternal"
Write-Output "installed_exe_sha256 = $installed"
Write-Output "installed_internal_files = $installedCount"
Write-Output "INSTALL_RESULT = PASS"
Write-Output "NEXT: first launch must be the NEW exe with --safe-preview. The previous exe has no such flag."
Write-Output "COLD ROLLBACK and any post-rollback business restart are separate, separately approved steps."
