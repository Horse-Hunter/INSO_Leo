param()

$ErrorActionPreference = "Stop"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$runtimeCandidates = @(
    (Join-Path $repo "dist\INSO_V1.1"),
    (Join-Path $repo ".worktrees\v1-1-windows-release\dist\INSO_V1.1"),
    (Join-Path (Split-Path $repo -Parent) "v1-1-windows-release\dist\INSO_V1.1")
)
$runtimeRoot = $runtimeCandidates | Where-Object {
    (Test-Path -LiteralPath (Join-Path $_ "runtime\production.json") -PathType Leaf) -and
    (Test-Path -LiteralPath (Join-Path $_ "runtime\research.json") -PathType Leaf)
} | Select-Object -First 1
$required = @(
    (Join-Path $runtimeRoot "runtime\production.json"),
    (Join-Path $runtimeRoot "runtime\research.json")
)
$missingRequired = @($required | Where-Object {
    -not (Test-Path -LiteralPath $_ -PathType Leaf)
})
if (-not $runtimeRoot -or $missingRequired.Count -ne 0) {
    throw "The existing V1.1 local runtime is unavailable; V1.2 source candidate was not started."
}

$python = Join-Path $repo ".venv-release\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    $python = "py"
    $arguments = @("-3", "-m", "src.gui.main")
} else {
    $arguments = @("-m", "src.gui.main")
}

$env:INSO_RUNTIME_ROOT = $runtimeRoot
Push-Location $repo
try {
    & $python @arguments
    exit $LASTEXITCODE
} finally {
    Pop-Location
    Remove-Item Env:INSO_RUNTIME_ROOT -ErrorAction SilentlyContinue
}
