<#
Offline negative tests for the install gates (RFQ-021-R4).

Builds a synthetic release layout in a temporary directory and proves the
installer refuses every incomplete rollback before touching the target:

  * no -ConfirmSwitch / no -ConfirmDatabaseBackupVerified / bad identity value
  * a snapshot manifest that no longer matches its files
  * a snapshot missing one _internal file (incomplete)
  * a snapshot from a different build (EXE identity)
  * a missing runtime junction, and a junction pointing elsewhere
  * a database backup with no verification report
  * a report bound to different bytes
  * the happy path, which must still pass

Nothing here reads or writes the production install. Usage:
  powershell -ExecutionPolicy Bypass -File scripts\test_install_gates.ps1
#>
$ErrorActionPreference = "Stop"
$here = $PSScriptRoot
$root = Join-Path ([System.IO.Path]::GetTempPath()) ("rfq021-r4-gates-" + [Guid]::NewGuid().ToString("N"))
$failures = New-Object System.Collections.ArrayList
$script:skipped = New-Object System.Collections.ArrayList
$script:checks = 0

$python = "C:\Users\Leo\AppData\Local\Programs\Python\Python312\python.exe"
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    $found = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($found) { $python = $found.Source } else { throw "no python interpreter to build the sqlite fixture" }
}

function Write-TextNoBom {
    param([string]$Path, [string[]]$Lines)
    $utf8 = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllLines($Path, $Lines, $utf8)
}

function Write-Manifest {
    param([string]$Root, [string]$Manifest)
    $lines = New-Object System.Collections.ArrayList
    Get-ChildItem -LiteralPath $Root -Recurse -File |
        Where-Object { $_.Name -ne "PROGRAM-MANIFEST.sha256" } |
        ForEach-Object {
            $rel = $_.FullName.Substring($Root.Length + 1).Replace('\', '/')
            $hash = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
            [void]$lines.Add("$hash  $rel")
        }
    Write-TextNoBom -Path $Manifest -Lines $lines.ToArray()
}

function New-Fixture {
    param([string]$Base)

    $target = Join-Path $Base "target"
    $candidate = Join-Path $Base "candidate"
    $snapshot = Join-Path $Base "snapshot"
    $runtimeTarget = Join-Path $Base "runtime-live"
    foreach ($dir in @($target, $candidate, $runtimeTarget,
                       (Join-Path $target "_internal\sub"),
                       (Join-Path $candidate "_internal\sub"),
                       $snapshot,
                       (Join-Path $snapshot "config"))) {
        New-Item -ItemType Directory -Force -Path $dir | Out-Null
    }

    # Old build (installed) and new build (candidate): same shape, other bytes.
    Write-TextNoBom -Path (Join-Path $target "INSO_V1.6.exe") -Lines @("old-build-exe", ("a" * 4000))
    Write-TextNoBom -Path (Join-Path $target "_internal\a.dll") -Lines @("old-a")
    Write-TextNoBom -Path (Join-Path $target "_internal\sub\b.dll") -Lines @("old-b")

    Write-TextNoBom -Path (Join-Path $candidate "INSO_V1.6.exe") -Lines @("new-build-exe", ("b" * 4000))
    Write-TextNoBom -Path (Join-Path $candidate "_internal\a.dll") -Lines @("new-a")
    Write-TextNoBom -Path (Join-Path $candidate "_internal\sub\b.dll") -Lines @("new-b")

    # Snapshot of the installed build, plus the mandatory configuration.
    Copy-Item -LiteralPath (Join-Path $target "INSO_V1.6.exe") -Destination (Join-Path $snapshot "INSO_V1.6.exe")
    Copy-Item -LiteralPath (Join-Path $target "_internal") -Destination (Join-Path $snapshot "_internal") -Recurse
    Write-TextNoBom -Path (Join-Path $snapshot "config\production.json") -Lines @('{"sqlite_path":"x"}')
    Write-TextNoBom -Path (Join-Path $snapshot "config\research.json") -Lines @('{"cdp":{}}')
    Write-Manifest -Root $snapshot -Manifest (Join-Path $snapshot "PROGRAM-MANIFEST.sha256")
    Write-Manifest -Root $candidate -Manifest (Join-Path $Base "candidate-manifest.sha256")

    New-Item -ItemType Junction -Path (Join-Path $target "runtime") -Target $runtimeTarget | Out-Null

    $db = Join-Path $Base "workflow.sqlite3"
    $code = @'
import sqlite3, sys
con = sqlite3.connect(sys.argv[1])
con.execute("CREATE TABLE workflow_v12_purchase_state(inquiry_id TEXT PRIMARY KEY, outcome TEXT)")
con.execute("CREATE TABLE workflow_v13_holds(hold_key TEXT PRIMARY KEY, active INTEGER)")
con.execute("CREATE TABLE workflow_v12_events(event_id TEXT PRIMARY KEY, occurred_at TEXT)")
con.execute("INSERT INTO workflow_v12_purchase_state VALUES('inq_x','SAVED')")
con.execute("INSERT INTO workflow_v12_events VALUES('evt_x','2026-11-14T21:52:00')")
con.commit(); con.close()
'@
    # `python -c` mangles the quotes on Windows, so the fixture is a real file.
    Write-TextNoBom -Path (Join-Path $Base "make_db.py") -Lines $code.Split("`n")
    & $python (Join-Path $Base "make_db.py") $db
    if ($LASTEXITCODE -ne 0) { throw "could not build the sqlite fixture" }

    return [pscustomobject]@{
        Base = $Base; Target = $target; Candidate = $candidate; Snapshot = $snapshot
        RuntimeTarget = $runtimeTarget; Database = $db
        CandidateManifest = (Join-Path $Base "candidate-manifest.sha256")
        DatabaseReport = "$db.verify.json"
    }
}

function Invoke-Installer {
    param([pscustomobject]$Fixture, [hashtable]$Override = @{})
    $values = [ordered]@{
        CandidateDir = $Fixture.Candidate
        Manifest = $Fixture.CandidateManifest
        TargetDir = $Fixture.Target
        RuntimeTarget = $Fixture.RuntimeTarget
        RollbackDir = $Fixture.Snapshot
        DatabaseBackup = $Fixture.Database
        DatabaseReport = $Fixture.DatabaseReport
        ExpectedPreviousExeSha256 = (Get-FileHash -LiteralPath (Join-Path $Fixture.Target "INSO_V1.6.exe") -Algorithm SHA256).Hash.ToLowerInvariant()
        ConfirmDatabaseBackupVerified = $true
        ConfirmSwitch = $true
    }
    foreach ($key in $Override.Keys) { $values[$key] = $Override[$key] }

    # A child process, because the installer's refusals are terminating throws
    # and this harness must observe them as an exit code, not die with them.
    $fileArgs = @()
    foreach ($key in $values.Keys) {
        if ($values[$key] -is [bool]) {
            if ($values[$key]) { $fileArgs += "-$key" }
        }
        else { $fileArgs += "-$key"; $fileArgs += [string]$values[$key] }
    }
    # The refusals arrive on stderr; with ErrorActionPreference=Stop that would
    # surface as a NativeCommandError in this harness instead of an exit code.
    $previous = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $output = & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $here "install_release_candidate.ps1") @fileArgs 2>&1
        $code = $LASTEXITCODE
    }
    finally { $ErrorActionPreference = $previous }
    return [pscustomobject]@{ ExitCode = $code; Output = ($output | Out-String) }
}

function Assert-Refused {
    param([string]$Name, [pscustomobject]$Result, [string]$Expected)
    $script:checks++
    if ($Result.ExitCode -eq 0) {
        [void]$failures.Add("$Name : installer PASSED but should have refused")
        return
    }
    if ($Expected -and ($Result.Output -notmatch [regex]::Escape($Expected))) {
        [void]$failures.Add("$Name : refused for the wrong reason (wanted '$Expected')`n$($Result.Output)")
    }
}

function Assert-Passed {
    param([string]$Name, [pscustomobject]$Result)
    $script:checks++
    if ($Result.ExitCode -ne 0 -or $Result.Output -notmatch "INSTALL_RESULT = PASS") {
        [void]$failures.Add("$Name : expected PASS, got exit $($Result.ExitCode)`n$($Result.Output)")
    }
}

function Initialize-DatabaseReport {
    param([pscustomobject]$Fixture)
    $previous = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $out = & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $here "verify_database_backup.ps1") `
            -DatabaseBackup $Fixture.Database -Report $Fixture.DatabaseReport -PythonExecutable $python 2>&1
        $code = $LASTEXITCODE
    }
    finally { $ErrorActionPreference = $previous }
    if ($code -ne 0) { throw "database verification fixture failed: $out" }
}

try {
    # --- authorisation switches ---------------------------------------------
    $f = New-Fixture (Join-Path $root "auth")
    Assert-Refused "no ConfirmSwitch" (Invoke-Installer $f @{ ConfirmSwitch = $false }) "ConfirmSwitch"
    $f = New-Fixture (Join-Path $root "auth2")
    Assert-Refused "no ConfirmDatabaseBackupVerified" (Invoke-Installer $f @{ ConfirmDatabaseBackupVerified = $false }) "ConfirmDatabaseBackupVerified"
    $f = New-Fixture (Join-Path $root "auth3")
    Assert-Refused "short expected sha" (Invoke-Installer $f @{ ExpectedPreviousExeSha256 = "abc" }) "64-hex"

    # --- database proof ------------------------------------------------------
    $f = New-Fixture (Join-Path $root "db-report-missing")
    Assert-Refused "no database report" (Invoke-Installer $f @{ DatabaseReport = (Join-Path $f.Base "absent.json") }) "no verification report"

    $f = New-Fixture (Join-Path $root "db-report-foreign")
    Initialize-DatabaseReport $f
    $report = Get-Content -LiteralPath $f.DatabaseReport -Raw -Encoding UTF8 | ConvertFrom-Json
    $report.database_sha256 = ("0" * 64)
    Write-TextNoBom -Path $f.DatabaseReport -Lines @($report | ConvertTo-Json -Depth 6)
    Assert-Refused "report bound to other bytes" (Invoke-Installer $f) "different bytes"

    # --- snapshot completeness ----------------------------------------------
    $f = New-Fixture (Join-Path $root "snapshot-tampered")
    Initialize-DatabaseReport $f
    Add-Content -LiteralPath (Join-Path $f.Snapshot "config\production.json") -Value " "
    Assert-Refused "snapshot file changed" (Invoke-Installer $f) "failed verification"

    $f = New-Fixture (Join-Path $root "snapshot-partial")
    Initialize-DatabaseReport $f
    $manifest = Get-Content -LiteralPath (Join-Path $f.Snapshot "PROGRAM-MANIFEST.sha256") |
        Where-Object { $_ -notmatch "_internal/sub/b\.dll" }
    Write-TextNoBom -Path (Join-Path $f.Snapshot "PROGRAM-MANIFEST.sha256") -Lines $manifest
    Assert-Refused "snapshot incomplete" (Invoke-Installer $f) "incomplete or stale"

    # --- old build identity --------------------------------------------------
    $f = New-Fixture (Join-Path $root "identity")
    Initialize-DatabaseReport $f
    Assert-Refused "wrong expected EXE identity" (Invoke-Installer $f @{ ExpectedPreviousExeSha256 = ("a" * 64) }) "not the build named by"

    # --- runtime junction ----------------------------------------------------
    $f = New-Fixture (Join-Path $root "junction-missing")
    Initialize-DatabaseReport $f
    [System.IO.Directory]::Delete((Join-Path $f.Target "runtime"), $false)
    Assert-Refused "missing runtime junction" (Invoke-Installer $f) "runtime junction"

    $f = New-Fixture (Join-Path $root "junction-elsewhere")
    Initialize-DatabaseReport $f
    $other = Join-Path $f.Base "runtime-other"
    New-Item -ItemType Directory -Force -Path $other | Out-Null
    [System.IO.Directory]::Delete((Join-Path $f.Target "runtime"), $false)
    New-Item -ItemType Junction -Path (Join-Path $f.Target "runtime") -Target $other | Out-Null
    Assert-Refused "junction points elsewhere" (Invoke-Installer $f) "runtime points at"

    # --- happy path ----------------------------------------------------------
    # The installer refuses while any INSO_V1.6 is running, and the production
    # program is running right now. That refusal is the correct behaviour and it
    # cannot be exercised around without weakening the gate, so a live process
    # makes this one case NOT_VERIFIED rather than silently skipped.
    $f = New-Fixture (Join-Path $root "happy")
    Initialize-DatabaseReport $f
    $before = (Get-FileHash -LiteralPath (Join-Path $f.Target "INSO_V1.6.exe") -Algorithm SHA256).Hash
    $result = Invoke-Installer $f
    if ($result.Output -match "still running") {
        $script:skipped += "happy path : NOT_VERIFIED - a real INSO_V1.6 process is running, and the installer must refuse"
    }
    else {
        Assert-Passed "complete rollback material" $result
        $after = (Get-FileHash -LiteralPath (Join-Path $f.Target "INSO_V1.6.exe") -Algorithm SHA256).Hash
        $script:checks++
        if ($before -eq $after) { [void]$failures.Add("happy path : the installed EXE did not change") }
        $script:checks++
        if (-not (Test-Path -LiteralPath (Join-Path $f.Target "runtime"))) {
            [void]$failures.Add("happy path : the runtime junction disappeared")
        }
    }
}
finally {
    Remove-Item -LiteralPath $root -Recurse -Force -ErrorAction SilentlyContinue
}

if ($failures.Count) {
    Write-Output "GATE_TEST_RESULT = FAIL"
    foreach ($failure in $failures) { Write-Output $failure }
    foreach ($note in $script:skipped) { Write-Output $note }
    exit 1
}
Write-Output "checks = $($script:checks)"
foreach ($note in $script:skipped) { Write-Output $note }
Write-Output "GATE_TEST_RESULT = PASS"
exit 0
