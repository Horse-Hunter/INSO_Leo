<#
Snapshot the RUNNING release (program + configuration) without touching it.

RFQ-021: this script never stops the program, never opens the database and
never replaces the runtime junction. The SQLite consistency copy needs a clean
stop and is a separate, explicitly authorised step (see INSTALL_AND_ROLLBACK.md).

Usage (read-only against the running install):
  powershell -ExecutionPolicy Bypass -File scripts\backup_running_release.ps1 `
      -SourceDir D:\Program_Leo\INSO_Leo\dist\INSO_V1.6 `
      -RuntimeConfigDir D:\Program_Leo\INSO_Leo\dist\INSO_V1.4\runtime `
      -Destination D:\Program_Leo\INSO_Leo\dist\release-backups\RFQ-021-pre-switch-<UTC>
#>
param(
    [Parameter(Mandatory = $true)][string]$SourceDir,
    [Parameter(Mandatory = $true)][string]$RuntimeConfigDir,
    [Parameter(Mandatory = $true)][string]$Destination
)
$ErrorActionPreference = "Stop"

$source = (Resolve-Path -LiteralPath $SourceDir).Path
if (Test-Path -LiteralPath $Destination) { throw "Destination already exists; refusing to overwrite: $Destination" }

$exe = Join-Path $source "INSO_V1.6.exe"
if (-not (Test-Path -LiteralPath $exe -PathType Leaf)) { throw "No INSO_V1.6.exe in $source" }

$runtime = Join-Path $source "runtime"
if (Test-Path -LiteralPath $runtime) {
    $item = Get-Item -LiteralPath $runtime -Force
    if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
        Write-Output "runtime_junction_target = $($item.Target)"
        Write-Output "runtime_junction_copied = FALSE (never copy or replace the junction)"
    }
}

New-Item -ItemType Directory -Force -Path $Destination | Out-Null
Copy-Item -LiteralPath $exe -Destination (Join-Path $Destination "INSO_V1.6.exe")

$internal = Join-Path $source "_internal"
if (Test-Path -LiteralPath $internal -PathType Container) {
    # robocopy mirrors the program payload only; it never follows the junction.
    $null = robocopy $internal (Join-Path $Destination "_internal") /E /COPY:DAT /R:1 /W:1 /NFL /NDL /NJH /NJS
    if ($LASTEXITCODE -ge 8) { throw "robocopy failed with $LASTEXITCODE" }
}

$configTarget = Join-Path $Destination "config"
New-Item -ItemType Directory -Force -Path $configTarget | Out-Null
foreach ($name in @("production.json", "research.json")) {
    $path = Join-Path $RuntimeConfigDir $name
    if (Test-Path -LiteralPath $path -PathType Leaf) {
        Copy-Item -LiteralPath $path -Destination (Join-Path $configTarget $name)
    }
}
Get-ChildItem -LiteralPath $RuntimeConfigDir -Filter "production.json.bak-*" -File -ErrorAction SilentlyContinue |
    ForEach-Object { Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $configTarget $_.Name) }

$dbPath = Join-Path $RuntimeConfigDir "production\workflow.sqlite3"
$dbNote = [ordered]@{
    path = $dbPath
    exists = (Test-Path -LiteralPath $dbPath -PathType Leaf)
    wal_present = (Test-Path -LiteralPath "$dbPath-wal")
    shm_present = (Test-Path -LiteralPath "$dbPath-shm")
    copied = $false
    reason = "A consistent copy requires a clean stop; see INSTALL_AND_ROLLBACK.md step 2."
}
if ($dbNote.exists) {
    $dbNote["size_bytes"] = (Get-Item -LiteralPath $dbPath).Length
}
$dbNote | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $Destination "database-state.json") -Encoding UTF8

$manifest = Join-Path $Destination "PROGRAM-MANIFEST.sha256"
$lines = New-Object System.Collections.ArrayList
Get-ChildItem -LiteralPath $Destination -Recurse -File |
    Where-Object { $_.Name -ne "PROGRAM-MANIFEST.sha256" } |
    ForEach-Object {
        $relative = $_.FullName.Substring($Destination.Length + 1).Replace('\', '/')
        $hash = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
        [void]$lines.Add("$hash  $relative")
    }
$lines | Set-Content -LiteralPath $manifest -Encoding UTF8

Write-Output "snapshot_dir = $Destination"
Write-Output "program_files = $((Get-ChildItem -LiteralPath $Destination -Recurse -File).Count)"
Write-Output "exe_sha256 = $((Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash.ToLowerInvariant())"
Write-Output "manifest = $manifest"
Write-Output "BACKUP_RESULT = PASS"
