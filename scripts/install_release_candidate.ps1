<#
Install a verified candidate over the stopped release.

RFQ-021-R3: the switch now fails closed unless the operator proves both halves
of a rollback:
  * a program+config snapshot whose manifest re-verifies, and
  * a database backup that is explicitly acknowledged as verified.

It also never starts anything, and it no longer pretends the *previous* build
understands `--safe-preview` -- that flag exists only in this release line, so
rollback is verified by hash, never by launching the old binary.

Usage:
  powershell -ExecutionPolicy Bypass -File scripts\install_release_candidate.ps1 `
      -CandidateDir   build\windows-release-stage-1.6\dist\INSO_V1.6 `
      -Manifest       docs\evidence\rfq021\INSO_V1.6-artifact-manifest.sha256 `
      -TargetDir      D:\Program_Leo\INSO_Leo\dist\INSO_V1.6 `
      -RollbackDir    D:\Program_Leo\INSO_Leo\dist\release-backups\RFQ-021-pre-switch-<UTC> `
      -DatabaseBackup D:\Program_Leo\INSO_Leo\dist\release-backups\RFQ-021-pre-switch-<UTC>\workflow.sqlite3 `
      -ConfirmDatabaseBackupVerified `
      -ConfirmSwitch
#>
param(
    [Parameter(Mandatory = $true)][string]$CandidateDir,
    [Parameter(Mandatory = $true)][string]$Manifest,
    [Parameter(Mandatory = $true)][string]$TargetDir,
    [Parameter(Mandatory = $true)][string]$RollbackDir,
    [Parameter(Mandatory = $true)][string]$DatabaseBackup,
    [switch]$ConfirmDatabaseBackupVerified,
    [switch]$ConfirmSwitch
)
$ErrorActionPreference = "Stop"

if (-not $ConfirmSwitch) {
    throw "Refusing to switch without -ConfirmSwitch (Owner authorisation for a maintenance window is required)."
}
if (-not $ConfirmDatabaseBackupVerified) {
    throw "Refusing to switch: -ConfirmDatabaseBackupVerified is required. A program snapshot alone is not a rollback."
}

$running = @(Get-Process -Name "INSO_V1.6" -ErrorAction SilentlyContinue)
if ($running.Count -gt 0) {
    throw "INSO_V1.6 is still running (PIDs: $($running.Id -join ', ')). Stop it normally first; never force-kill."
}

# --- rollback half 1: program + config snapshot -----------------------------
if (-not (Test-Path -LiteralPath $RollbackDir -PathType Container)) {
    throw "Rollback snapshot not found: $RollbackDir. Run backup_running_release.ps1 first."
}
$snapshotManifest = Join-Path $RollbackDir "PROGRAM-MANIFEST.sha256"
if (-not (Test-Path -LiteralPath $snapshotManifest -PathType Leaf)) {
    throw "Rollback snapshot has no PROGRAM-MANIFEST.sha256; it cannot be verified."
}
$snapshotRoot = (Resolve-Path -LiteralPath $RollbackDir).Path
$snapshotEntries = @(Get-Content -LiteralPath $snapshotManifest -Encoding UTF8 |
    Where-Object { $_.Trim() })
if ($snapshotEntries.Count -lt 2) {
    throw "Rollback manifest is empty or truncated; refusing to treat it as a snapshot."
}
$snapshotBad = 0
foreach ($line in $snapshotEntries) {
    $split = $line.IndexOf("  ")
    if ($split -lt 1) { throw "Malformed rollback manifest line: $line" }
    $expectedHash = $line.Substring(0, $split).Trim().ToLowerInvariant()
    $rel = $line.Substring($split + 2).Trim()
    $full = Join-Path $snapshotRoot $rel
    if (-not (Test-Path -LiteralPath $full -PathType Leaf)) { $snapshotBad++; continue }
    $actual = (Get-FileHash -LiteralPath $full -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actual -ne $expectedHash) { $snapshotBad++ }
}
if ($snapshotBad -gt 0) {
    throw "Rollback snapshot failed verification ($snapshotBad file(s)); do not switch."
}

# --- rollback half 2: a database backup the operator vouches for -------------
if (-not (Test-Path -LiteralPath $DatabaseBackup -PathType Leaf)) {
    throw "Database backup not found: $DatabaseBackup. A switch without a database rollback is refused."
}
$dbItem = Get-Item -LiteralPath $DatabaseBackup
if ($dbItem.Length -lt 4096) {
    throw "Database backup is implausibly small ($($dbItem.Length) bytes); refusing."
}
$header = New-Object byte[] 16
$stream = [System.IO.File]::OpenRead($DatabaseBackup)
try { $null = $stream.Read($header, 0, 16) } finally { $stream.Dispose() }
$magic = [System.Text.Encoding]::ASCII.GetString($header)
if (-not $magic.StartsWith("SQLite format 3")) {
    throw "Database backup is not a SQLite file (header: $magic); refusing."
}

# --- candidate ---------------------------------------------------------------
& (Join-Path $PSScriptRoot "verify_release_candidate.ps1") -CandidateDir $CandidateDir -Manifest $Manifest
if ($LASTEXITCODE -ne 0) { throw "Candidate verification failed; nothing was changed." }

$target = (Resolve-Path -LiteralPath $TargetDir).Path
$candidate = (Resolve-Path -LiteralPath $CandidateDir).Path
$stamp = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")

$runtime = Join-Path $target "runtime"
if (Test-Path -LiteralPath $runtime) {
    $item = Get-Item -LiteralPath $runtime -Force
    if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -eq 0) {
        throw "Expected a runtime junction at $runtime; refusing to touch an unexpected layout."
    }
}

$previousExe = Join-Path $target ("INSO_V1.6.exe.prev-" + $stamp)
$previousInternal = Join-Path $target ("_internal.prev-" + $stamp)
Move-Item -LiteralPath (Join-Path $target "_internal") -Destination $previousInternal
Copy-Item -LiteralPath (Join-Path $candidate "_internal") -Destination (Join-Path $target "_internal") -Recurse
Move-Item -LiteralPath (Join-Path $target "INSO_V1.6.exe") -Destination $previousExe
Copy-Item -LiteralPath (Join-Path $candidate "INSO_V1.6.exe") -Destination (Join-Path $target "INSO_V1.6.exe")

$installed = (Get-FileHash -LiteralPath (Join-Path $target "INSO_V1.6.exe") -Algorithm SHA256).Hash.ToLowerInvariant()
$expected = (Get-FileHash -LiteralPath (Join-Path $candidate "INSO_V1.6.exe") -Algorithm SHA256).Hash.ToLowerInvariant()
if ($installed -ne $expected) { throw "Installed EXE hash mismatch: $installed" }

Write-Output "rollback_snapshot = $snapshotRoot"
Write-Output "rollback_database = $DatabaseBackup"
Write-Output "previous_exe = $previousExe"
Write-Output "previous_internal = $previousInternal"
Write-Output "installed_exe_sha256 = $installed"
Write-Output "INSTALL_RESULT = PASS"
Write-Output "NEXT: first launch must be the NEW exe with --safe-preview. The previous exe has no such flag."
Write-Output "COLD ROLLBACK is a separate, separately approved step; see INSTALL_AND_ROLLBACK.md."
