<#
Recompute a staged release against its manifest before anyone installs it.

RFQ-021: the manifest proves what was built. This proves the bytes on disk are
still those bytes -- no partial copy, no rebuild, no extra file slipped in.

Usage:
  powershell -ExecutionPolicy Bypass -File scripts\verify_release_candidate.ps1 `
      -CandidateDir build\windows-release-stage-1.6\dist\INSO_V1.6 `
      -Manifest docs\evidence\rfq021\INSO_V1.6-artifact-manifest.sha256
#>
param(
    [Parameter(Mandatory = $true)][string]$CandidateDir,
    [Parameter(Mandatory = $true)][string]$Manifest
)
$ErrorActionPreference = "Stop"

$root = (Resolve-Path -LiteralPath $CandidateDir).Path
if (-not (Test-Path -LiteralPath $Manifest -PathType Leaf)) { throw "Manifest not found: $Manifest" }

$expected = @{}
foreach ($line in Get-Content -LiteralPath $Manifest -Encoding UTF8) {
    if (-not $line.Trim()) { continue }
    $split = $line.IndexOf("  ")
    if ($split -lt 1) { throw "Malformed manifest line: $line" }
    $hash = $line.Substring(0, $split).Trim().ToLowerInvariant()
    $path = $line.Substring($split + 2).Trim()
    if ($hash.Length -ne 64) { throw "Malformed manifest hash for $path" }
    $expected[$path] = $hash
}

$missing = New-Object System.Collections.ArrayList
$mismatched = New-Object System.Collections.ArrayList
$actualPaths = New-Object System.Collections.Generic.HashSet[string]

foreach ($file in Get-ChildItem -LiteralPath $root -Recurse -File) {
    $relative = $file.FullName.Substring($root.Length + 1).Replace('\', '/')
    [void]$actualPaths.Add($relative)
    if (-not $expected.ContainsKey($relative)) { continue }
    $actual = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actual -ne $expected[$relative]) { [void]$mismatched.Add($relative) }
}
foreach ($path in $expected.Keys) {
    if (-not $actualPaths.Contains($path)) { [void]$missing.Add($path) }
}
$extra = @($actualPaths | Where-Object { -not $expected.ContainsKey($_) })

Write-Output "candidate_dir = $root"
Write-Output "manifest_entries = $($expected.Count)"
Write-Output "files_on_disk = $($actualPaths.Count)"
Write-Output "missing = $($missing.Count)"
Write-Output "hash_mismatch = $($mismatched.Count)"
Write-Output "unexpected = $($extra.Count)"
foreach ($path in $missing) { Write-Output "MISSING $path" }
foreach ($path in $mismatched) { Write-Output "MISMATCH $path" }
foreach ($path in $extra) { Write-Output "UNEXPECTED $path" }

$exe = Join-Path $root "INSO_V1.6.exe"
if (Test-Path -LiteralPath $exe -PathType Leaf) {
    $exeHash = (Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash.ToLowerInvariant()
    Write-Output "candidate_exe_sha256 = $exeHash"
}

if ($missing.Count -or $mismatched.Count -or $extra.Count) {
    Write-Output "VERIFY_RESULT = FAIL"
    exit 1
}
Write-Output "VERIFY_RESULT = PASS"
exit 0
