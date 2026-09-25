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
$buildRoot = Join-Path $repo "build"
$stageRoot = Join-Path $buildRoot "windows-release-stage"
$stageMarker = Join-Path $stageRoot ".inso-release-stage"
$stageDist = Join-Path $stageRoot "dist"
$stageWork = Join-Path $stageRoot "work"
$markerValue = "INSO_V1.1 release script staging v1"
$scanner = Join-Path $repo "scripts/scan_release_artifact.py"

function Test-ReleaseArtifact([string]$Path) {
    & $python $scanner $Path
    if ($LASTEXITCODE -ne 0) {
        throw "Release artifact scan failed; preserving staging for inspection."
    }
}

function Remove-PreviousOwnedStage {
    if (-not (Test-Path -LiteralPath $stageRoot)) { return }

    $rootItem = Get-Item -LiteralPath $stageRoot -Force
    if (($rootItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
        throw "Release staging path is a reparse point; refusing cleanup."
    }
    if (-not (Test-Path -LiteralPath $stageMarker -PathType Leaf) -or
        (Get-Content -LiteralPath $stageMarker -Raw).Trim() -ne $markerValue) {
        throw "Release staging exists without its ownership marker; preserving it."
    }

    if (Test-Path -LiteralPath $stageWork) {
        throw "Release staging contains an uncleared PyInstaller work tree; preserving it."
    }
    $allowedChildren = @('.inso-release-stage', 'dist')
    $unexpected = @(Get-ChildItem -LiteralPath $stageRoot -Force | Where-Object { $_.Name -notin $allowedChildren })
    if ($unexpected.Count -gt 0) {
        throw "Release staging contains unrecognized items; preserving it."
    }
    $stagedApp = Join-Path $stageDist "INSO_V1.1"
    if (Test-Path -LiteralPath (Join-Path $stagedApp "runtime")) {
        throw "Build staging contains runtime data; preserving it."
    }
    if (Test-Path -LiteralPath $stageDist) {
        $distChildren = @(Get-ChildItem -LiteralPath $stageDist -Force)
        if ($distChildren.Count -gt 0 -and
            ($distChildren.Count -ne 1 -or $distChildren[0].Name -ne 'INSO_V1.1' -or -not $distChildren[0].PSIsContainer)) {
            throw "Release staging dist has unrecognized items; preserving it."
        }
        if (Test-Path -LiteralPath $stagedApp) { Test-ReleaseArtifact $stageDist }
    }

    # This exact, marked path is the release script's throwaway staging only.
    Remove-Item -LiteralPath $stageRoot -Recurse -Force
}

Remove-PreviousOwnedStage
New-Item -ItemType Directory -Path $stageRoot | Out-Null
Set-Content -LiteralPath $stageMarker -Value $markerValue -NoNewline
New-Item -ItemType Directory -Path $stageDist | Out-Null
$buildSucceeded = $false
try {
    & $python -m PyInstaller --noconfirm --clean --distpath $stageDist `
        --workpath $stageWork `
        "packaging/INSO_V1.1.spec"
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller failed with exit code $LASTEXITCODE."
    }

    $stagedRelease = Join-Path $stageDist "INSO_V1.1"
    $exe = Join-Path $stagedRelease "INSO_V1.1.exe"
    if (-not (Test-Path -LiteralPath $exe -PathType Leaf)) {
        throw "Expected release executable was not produced: $exe"
    }
    $selfCheck = Start-Process -FilePath $exe -ArgumentList "--self-check" `
        -PassThru -Wait -WindowStyle Hidden
    if ($selfCheck.ExitCode -ne 0) {
        throw "Frozen GUI dependency self-check failed; refusing a broken release artifact."
    }
    Test-ReleaseArtifact $stagedRelease

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
    $buildSucceeded = $true
} finally {
    # PyInstaller's work tree is always disposable and never retained.
    if (Test-Path -LiteralPath $stageWork) {
        Remove-Item -LiteralPath $stageWork -Recurse -Force
    }
    # Keep only a successfully verified BuildOnly artifact; failed or normal
    # deployment builds clean the exact marked staging tree they just created.
    if (-not $BuildOnly -or -not $buildSucceeded) {
        if (Test-Path -LiteralPath $stageRoot) {
            if (-not (Test-Path -LiteralPath $stageMarker -PathType Leaf) -or
                (Get-Content -LiteralPath $stageMarker -Raw).Trim() -ne $markerValue) {
                throw "Release staging ownership marker changed; preserving staging."
            }
            if (Test-Path -LiteralPath (Join-Path $stageDist "INSO_V1.1/runtime")) {
                throw "Build staging contains runtime data; preserving it."
            }
            if (Test-Path -LiteralPath $stageDist) { Test-ReleaseArtifact $stageDist }
            Remove-Item -LiteralPath $stageRoot -Recurse -Force
        }
    }
}
