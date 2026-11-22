<#
Snapshot the RUNNING release (program + configuration) without touching it.

RFQ-021: this script never stops the program, never opens the database and
never replaces the runtime junction. The SQLite consistency copy needs a clean
stop and is a separate, explicitly authorised step (see INSTALL_AND_ROLLBACK.md).

RFQ-021-R5: the configuration is no longer taken from wherever the operator
points. It is taken from the target of the installation's own `runtime`
junction, and a `-RuntimeConfigDir` that disagrees with that junction is refused
-- a config snapshot from another install hashes perfectly and rolls back the
wrong settings.

Usage (read-only against the running install):
  powershell -ExecutionPolicy Bypass -File scripts\backup_running_release.ps1 `
      -SourceDir D:\Program_Leo\INSO_Leo\dist\INSO_V1.6 `
      -Destination D:\Program_Leo\INSO_Leo\dist\release-backups\RFQ-021-pre-switch-<UTC>
#>
param(
    [Parameter(Mandatory = $true)][string]$SourceDir,
    [string]$RuntimeConfigDir = "",
    [Parameter(Mandatory = $true)][string]$Destination
)
$ErrorActionPreference = "Stop"

function Get-Sha256([string]$path) {
    return (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
}

$source = (Resolve-Path -LiteralPath $SourceDir).Path
if (Test-Path -LiteralPath $Destination) { throw "Destination already exists; refusing to overwrite: $Destination" }

# The release this snapshot must be able to restore is whatever EXE the install
# actually holds. Reading it from the directory (exactly one root EXE) keeps the
# snapshot correct across a version rename instead of hardcoding one release.
$exeCandidates = @(Get-ChildItem -LiteralPath $source -File -Filter "*.exe")
if ($exeCandidates.Count -ne 1) {
    throw "$source holds $($exeCandidates.Count) root EXE(s); a snapshot needs exactly one"
}
$exe = $exeCandidates[0].FullName
$exeName = $exeCandidates[0].Name

# The configuration that belongs to THIS installation is whatever its runtime
# junction points at. Everything else is somebody else's settings.
$runtime = Join-Path $source "runtime"
if (-not (Test-Path -LiteralPath $runtime)) {
    throw "No runtime junction at $runtime; the installation layout is not the one this script protects."
}
$runtimeItem = Get-Item -LiteralPath $runtime -Force
if (($runtimeItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -eq 0) {
    throw "runtime at $runtime is a real directory, not a junction; refusing to guess which configuration is live."
}
if ($runtimeItem.LinkType -ne "Junction") {
    throw "runtime is a reparse point of type '$($runtimeItem.LinkType)', not a Junction."
}
$junctionTarget = @($runtimeItem.Target)[0]
if (-not $junctionTarget) { throw "runtime exposes no junction target." }
$resolvedRuntime = (Resolve-Path -LiteralPath ([string]$junctionTarget)).Path.TrimEnd('\')
if (-not [string]::IsNullOrWhiteSpace($RuntimeConfigDir)) {
    $given = (Resolve-Path -LiteralPath $RuntimeConfigDir).Path.TrimEnd('\')
    if ($given -ne $resolvedRuntime) {
        throw "The configuration directory you named ($given) is not the one runtime points at ($resolvedRuntime)."
    }
}
Write-Output "runtime_junction_target = $resolvedRuntime"
Write-Output "runtime_junction_copied = FALSE (never copy or replace the junction)"

$internal = Join-Path $source "_internal"
if (-not (Test-Path -LiteralPath $internal -PathType Container)) {
    throw "No _internal in $source; a snapshot without the program payload cannot roll the program back."
}
$sourceFiles = @(Get-ChildItem -LiteralPath $internal -Recurse -File)
if ($sourceFiles.Count -lt 1) {
    throw "_internal in $source is empty; a snapshot of it cannot roll the program back."
}

New-Item -ItemType Directory -Force -Path $Destination | Out-Null
Copy-Item -LiteralPath $exe -Destination (Join-Path $Destination $exeName)
$copiedExe = Join-Path $Destination $exeName
if ((Get-Sha256 $copiedExe) -ne (Get-Sha256 $exe)) {
    throw "The copied EXE does not hash to the running EXE; refusing to write a snapshot that cannot be trusted."
}

# robocopy mirrors the program payload only; it never follows the junction.
# Exit codes < 8 are "some degree of success" for robocopy, but 4 means a file
# could not be reconciled, so only 0-3 count as a copy that may be verified.
$null = robocopy $internal (Join-Path $Destination "_internal") /E /COPY:DAT /R:2 /W:1 /NFL /NDL /NJH /NJS
$robocopyCode = $LASTEXITCODE
if ($robocopyCode -ge 4) { throw "robocopy did not copy the payload cleanly (exit $robocopyCode)" }

# A copied tree is not a snapshot until it provably reproduces the running one:
# same file set, byte-identical content. A self-consistent manifest of a partial
# copy would otherwise verify perfectly and roll back a broken install.
$copiedRoot = Join-Path $Destination "_internal"
$copiedFiles = @(Get-ChildItem -LiteralPath $copiedRoot -Recurse -File)
if ($copiedFiles.Count -ne $sourceFiles.Count) {
    throw "The copy holds $($copiedFiles.Count) payload file(s) but the install has $($sourceFiles.Count); refusing a partial snapshot."
}
$payloadMismatch = 0
foreach ($file in $sourceFiles) {
    $relative = $file.FullName.Substring($internal.Length + 1)
    $copy = Join-Path $copiedRoot $relative
    if (-not (Test-Path -LiteralPath $copy -PathType Leaf)) { $payloadMismatch++; continue }
    if ((Get-Sha256 $copy) -ne (Get-Sha256 $file.FullName)) { $payloadMismatch++ }
}
if ($payloadMismatch -gt 0) {
    throw "The copied payload differs from the running payload in $payloadMismatch file(s); refusing to call it a snapshot."
}
Write-Output "payload_files_verified = $($sourceFiles.Count)"

$configTarget = Join-Path $Destination "config"
New-Item -ItemType Directory -Force -Path $configTarget | Out-Null
foreach ($name in @("production.json", "research.json")) {
    $path = Join-Path $resolvedRuntime $name
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "Missing mandatory configuration $path; the installer will refuse this snapshot, so it is not written."
    }
    Copy-Item -LiteralPath $path -Destination (Join-Path $configTarget $name)
    if ((Get-Sha256 (Join-Path $configTarget $name)) -ne (Get-Sha256 $path)) {
        throw "The copied $name does not hash to the live configuration behind runtime; refusing a snapshot that rolls back different settings."
    }
}
Get-ChildItem -LiteralPath $resolvedRuntime -Filter "production.json.bak-*" -File -ErrorAction SilentlyContinue |
    ForEach-Object { Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $configTarget $_.Name) }

# The ledger is wherever the live configuration says it is -- not a guessed
# `production\workflow.sqlite3` under this junction. On this machine the two
# differ (the installed runtime junction holds the config, while `sqlite_path`
# points into another runtime tree), and a backup taken from the guessed path
# would describe a file that does not exist.
$dbNote = [ordered]@{
    configured_path = ""
    resolved_path = ""
    path_source = "live production.json behind the runtime junction"
    exists = $false
    wal_present = $false
    shm_present = $false
    copied = $false
    reason = "A consistent copy requires a clean stop; see INSTALL_AND_ROLLBACK.md step 2 and 3."
}
$liveProductionJson = Join-Path $resolvedRuntime "production.json"
try {
    $liveConfig = Get-Content -LiteralPath $liveProductionJson -Raw -Encoding UTF8 | ConvertFrom-Json
}
catch {
    throw "Cannot read the live configuration $liveProductionJson; refusing to describe a ledger it does not name."
}
$configuredDb = [string]$liveConfig.sqlite_path
if ([string]::IsNullOrWhiteSpace($configuredDb)) {
    throw "The live configuration names no sqlite_path; refusing to guess which ledger to back up."
}
$dbPath = if ([System.IO.Path]::IsPathRooted($configuredDb)) {
    $configuredDb
} else {
    Join-Path $source $configuredDb
}
$dbNote["configured_path"] = $configuredDb
$dbNote["resolved_path"] = $dbPath
$dbNote["exists"] = (Test-Path -LiteralPath $dbPath -PathType Leaf)
$dbNote["wal_present"] = (Test-Path -LiteralPath "$dbPath-wal")
$dbNote["shm_present"] = (Test-Path -LiteralPath "$dbPath-shm")
if ($dbNote["exists"]) {
    $dbNote["size_bytes"] = (Get-Item -LiteralPath $dbPath).Length
}
$dbNote | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $Destination "database-state.json") -Encoding UTF8
Write-Output "configured_ledger = $dbPath"
if (-not $dbNote["exists"]) {
    Write-Output "WARNING = the configured ledger does not exist; a rollback snapshot without it is not a rollback."
}

$manifest = Join-Path $Destination "PROGRAM-MANIFEST.sha256"
$lines = New-Object System.Collections.ArrayList
Get-ChildItem -LiteralPath $Destination -Recurse -File |
    Where-Object { $_.Name -ne "PROGRAM-MANIFEST.sha256" } |
    ForEach-Object {
        $relative = $_.FullName.Substring($Destination.Length + 1).Replace('\', '/')
        $hash = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
        [void]$lines.Add("$hash  $relative")
    }
# No BOM: the installer parses "<hash>  <path>" and a leading BOM would corrupt
# the first hash, making a perfectly good snapshot unverifiable.
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllLines($manifest, $lines.ToArray(), $utf8NoBom)

Write-Output "snapshot_dir = $Destination"
Write-Output "program_files = $((Get-ChildItem -LiteralPath $Destination -Recurse -File).Count)"
Write-Output "source_internal_files = $($sourceFiles.Count)"
Write-Output "exe_sha256 = $((Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash.ToLowerInvariant())"
Write-Output "manifest = $manifest"
Write-Output "BACKUP_RESULT = PASS"
