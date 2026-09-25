param([switch]$BuildOnly)
$ErrorActionPreference = "Stop"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $repo
$python = Join-Path $repo ".venv-release/Scripts/python.exe"
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw "Release Python environment is missing. Create it and install requirements-windows-release.lock first."
}

if (-not (Test-Path "packaging/INSO_V1.1.spec" -PathType Leaf)) {
    throw "Release spec is missing."
}
if (-not (Test-Path "packaging/assets/inso-v1.1.ico" -PathType Leaf)) {
    throw "Release icon is missing."
}
# PyInstaller silently excludes tkinter when Tcl cannot initialize in the
# build process. Import alone is insufficient: Tcl() must find init.tcl.
& $python -c "import tkinter; tkinter.Tcl().eval('info patchlevel')"
if ($LASTEXITCODE -ne 0) {
    throw "Tcl/Tk is unavailable to the build process; refusing a broken GUI artifact."
}

$release = Join-Path $repo "dist/INSO_V1.1"
if (-not $BuildOnly -and (Test-Path -LiteralPath $release)) {
    throw "Refusing to replace an existing release directory, which may contain local runtime data: $release"
}
$buildId = [guid]::NewGuid().ToString("N")
$stageDist = Join-Path $repo "build/release-dist-$buildId"
$stageWork = Join-Path $repo "build/pyinstaller-$buildId"

& $python -m PyInstaller --noconfirm --clean --distpath $stageDist `
    --workpath $stageWork `
    "packaging/INSO_V1.1.spec"

$stagedRelease = Join-Path $stageDist "INSO_V1.1"
$exe = Join-Path $stagedRelease "INSO_V1.1.exe"
if (-not (Test-Path $exe -PathType Leaf)) {
    throw "Expected release executable was not produced: $exe"
}
$selfCheck = Start-Process -FilePath $exe -ArgumentList "--self-check" `
    -PassThru -Wait -WindowStyle Hidden
if ($selfCheck.ExitCode -ne 0) {
    throw "Frozen GUI dependency self-check failed; refusing a broken release artifact."
}
if ($BuildOnly) {
    Write-Output "Built staging artifact $exe"
} else {
    if (Test-Path -LiteralPath $release) {
        throw "Refusing to replace an existing release directory: $release"
    }
    New-Item -ItemType Directory -Force (Join-Path $repo "dist") | Out-Null
    Move-Item -LiteralPath $stagedRelease -Destination $release
    Write-Output "Built $release\INSO_V1.1.exe"
}
