<#
Install a verified candidate over the stopped release.

RFQ-021: prepared, not executed. It refuses to run while the program is alive,
refuses an unverified candidate, refuses to run without a verified backup, and
never touches the `runtime` junction (that is where production data lives).

It also never starts the new program -- the first launch is a separate, visible
acceptance step (`--safe-preview`), documented in INSTALL_AND_ROLLBACK.md.

Usage:
  powershell -ExecutionPolicy Bypass -File scripts\install_release_candidate.ps1 `
      -CandidateDir  build\windows-release-stage-1.6\dist\INSO_V1.6 `
      -Manifest      docs\evidence\rfq021\INSO_V1.6-artifact-manifest.sha256 `
      -TargetDir     D:\Program_Leo\INSO_Leo\dist\INSO_V1.6 `
      -BackupDir     D:\Program_Leo\INSO_Leo\dist\release-backups\RFQ-021-pre-switch-<UTC> `
      -ConfirmSwitch
#>
param(
    [Parameter(Mandatory = $true)][string]$CandidateDir,
    [Parameter(Mandatory = $true)][string]$Manifest,
    [Parameter(Mandatory = $true)][string]$TargetDir,
    [Parameter(Mandatory = $true)][string]$BackupDir,
    [switch]$ConfirmSwitch
)
$ErrorActionPreference = "Stop"

if (-not $ConfirmSwitch) {
    throw "Refusing to switch without -ConfirmSwitch (Owner authorisation for a maintenance window is required)."
}

$running = @(Get-Process -Name "INSO_V1.6" -ErrorAction SilentlyContinue)
if ($running.Count -gt 0) {
    throw "INSO_V1.6 is still running (PIDs: $($running.Id -join ', ')). Stop it normally first; never force-kill."
}

if (-not (Test-Path -LiteralPath $BackupDir -PathType Container)) {
    throw "Backup directory not found: $BackupDir. Run backup_running_release.ps1 first."
}
if (-not (Test-Path -LiteralPath (Join-Path $BackupDir "PROGRAM-MANIFEST.sha256") -PathType Leaf)) {
    throw "Backup has no PROGRAM-MANIFEST.sha256; it is not a verified snapshot."
}

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

$oldInternal = Join-Path $target ("_internal.prev-" + $stamp)
Move-Item -LiteralPath (Join-Path $target "_internal") -Destination $oldInternal
Copy-Item -LiteralPath (Join-Path $candidate "_internal") -Destination (Join-Path $target "_internal") -Recurse
Move-Item -LiteralPath (Join-Path $target "INSO_V1.6.exe") -Destination (Join-Path $target ("INSO_V1.6.exe.prev-" + $stamp))
Copy-Item -LiteralPath (Join-Path $candidate "INSO_V1.6.exe") -Destination (Join-Path $target "INSO_V1.6.exe")

$installed = (Get-FileHash -LiteralPath (Join-Path $target "INSO_V1.6.exe") -Algorithm SHA256).Hash.ToLowerInvariant()
$expected = (Get-FileHash -LiteralPath (Join-Path $candidate "INSO_V1.6.exe") -Algorithm SHA256).Hash.ToLowerInvariant()
if ($installed -ne $expected) { throw "Installed EXE hash mismatch: $installed" }

Write-Output "previous_internal = $oldInternal"
Write-Output "installed_exe_sha256 = $installed"
Write-Output "INSTALL_RESULT = PASS"
Write-Output "NEXT: run the first launch as a safe preview, then follow INSTALL_AND_ROLLBACK.md acceptance."
