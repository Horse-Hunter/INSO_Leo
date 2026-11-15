<#
Offline gate tests for the R5 installer (RFQ-021-R5).

Every case builds a throwaway installation under %TEMP% and exercises the real
scripts. The production install is never read or written; the process guard is
path-based, so a synthetic target is free to install while the real program
keeps running.

Cases: authorisation, snapshot completeness/identity, runtime junction
identity, configuration binding, database provenance and recency, post-copy
per-file verification, the injected mid-switch failure and its restore, and the
complete success path.

  powershell -ExecutionPolicy Bypass -File scripts\test_install_gates.ps1
#>
$ErrorActionPreference = "Stop"
$here = $PSScriptRoot
$root = Join-Path ([System.IO.Path]::GetTempPath()) ("rfq021-r5-gates-" + [Guid]::NewGuid().ToString("N"))
$failures = New-Object System.Collections.ArrayList
$skipped = New-Object System.Collections.ArrayList
$script:checks = 0
# Arms the installer's fault-injection switches for the child processes below.
# They can only ever force a failure; nothing here can make a bad install pass.
$env:RFQ021_OFFLINE_GATE_TESTS = "1"

$python = "C:\Users\Leo\AppData\Local\Programs\Python\Python312\python.exe"
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    $found = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($found) { $python = $found.Source } else { throw "no python interpreter for the fixtures" }
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

function Invoke-Child {
    param([string]$Script, [hashtable]$Values)
    $fileArgs = @()
    foreach ($key in $Values.Keys) {
        if ($Values[$key] -is [bool]) { if ($Values[$key]) { $fileArgs += "-$key" } }
        else { $fileArgs += "-$key"; $fileArgs += [string]$Values[$key] }
    }
    $previous = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $output = & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $here $Script) @fileArgs 2>&1
        $code = $LASTEXITCODE
    }
    finally { $ErrorActionPreference = $previous }
    return [pscustomobject]@{ ExitCode = $code; Output = ($output | Out-String) }
}

function Write-FixtureDatabaseScript {
    param([string]$Base)
    $code = @'
import sqlite3, sys
path = sys.argv[1]
when = sys.argv[2] if len(sys.argv) > 2 else "2026-11-15T08:00:00+00:00"
extra = sys.argv[3] if len(sys.argv) > 3 else ""
con = sqlite3.connect(path)
con.execute("DROP TABLE IF EXISTS workflow_v12_purchase_state")
con.execute("CREATE TABLE workflow_v12_purchase_state(inquiry_id TEXT PRIMARY KEY, outcome TEXT)")
con.execute("DROP TABLE IF EXISTS workflow_v13_holds")
con.execute("CREATE TABLE workflow_v13_holds(hold_key TEXT PRIMARY KEY, active INTEGER)")
con.execute("DROP TABLE IF EXISTS workflow_v12_events")
con.execute("CREATE TABLE workflow_v12_events(event_id TEXT PRIMARY KEY, occurred_at TEXT)")
con.execute("DROP TABLE IF EXISTS workflow_v12_active_alerts")
con.execute("CREATE TABLE workflow_v12_active_alerts(alert_id TEXT PRIMARY KEY, active INTEGER)")
con.execute("DROP TABLE IF EXISTS workflow_write_intents")
con.execute("CREATE TABLE workflow_write_intents(intent_id TEXT PRIMARY KEY, document_key TEXT, kind TEXT, state TEXT, created_at TEXT, settled_at TEXT, reason TEXT)")
con.execute("INSERT INTO workflow_v12_purchase_state VALUES('inq_x','SAVED')")
con.execute("INSERT INTO workflow_v12_events VALUES('evt_x',?)", (when,))
if extra:
    con.executescript(extra)
con.commit(); con.close()
'@
    # `python -c` mangles quotes on Windows, so the fixture is a real file.
    Write-TextNoBom -Path (Join-Path $Base "make_db.py") -Lines $code.Split("`n")
}

function New-Fixture {
    param([string]$Base, [switch]$RealRuntimeDirectory, [switch]$RelativeSqlitePath)

    $target = Join-Path $Base "target"
    $candidate = Join-Path $Base "candidate"
    $runtimeLive = Join-Path $Base "runtime-live"
    $liveDbDir = Join-Path $runtimeLive "production"
    $backupDir = Join-Path $Base "backup"
    foreach ($dir in @($target, (Join-Path $target "_internal\sub"),
                       $candidate, (Join-Path $candidate "_internal\sub"),
                       $runtimeLive, $liveDbDir, $backupDir)) {
        New-Item -ItemType Directory -Force -Path $dir | Out-Null
    }

    # Old build (installed) and new build (candidate).
    Write-TextNoBom -Path (Join-Path $target "INSO_V1.6.exe") -Lines @("old-exe", ("a" * 4000))
    Write-TextNoBom -Path (Join-Path $target "_internal\a.dll") -Lines @("old-a")
    Write-TextNoBom -Path (Join-Path $target "_internal\sub\b.dll") -Lines @("old-b")
    Write-TextNoBom -Path (Join-Path $candidate "INSO_V1.6.exe") -Lines @("new-exe", ("b" * 4000))
    Write-TextNoBom -Path (Join-Path $candidate "_internal\a.dll") -Lines @("new-a")
    Write-TextNoBom -Path (Join-Path $candidate "_internal\sub\b.dll") -Lines @("new-b")
    Write-Manifest -Root $candidate -Manifest (Join-Path $Base "candidate-manifest.sha256")

    # Live ledger, and a byte-identical copy beside it.
    Write-FixtureDatabaseScript $Base
    $liveDb = Join-Path $liveDbDir "workflow.sqlite3"
    & $python (Join-Path $Base "make_db.py") $liveDb
    if ($LASTEXITCODE -ne 0) { throw "fixture database failed" }
    $backupDb = Join-Path $backupDir "workflow.sqlite3"
    Copy-Item -LiteralPath $liveDb -Destination $backupDb

    # Configuration lives behind the junction; production.json points at the ledger.
    # The real installation may name it either absolutely or relative to the
    # install root; both must describe the same ledger.
    $sqliteReference = if ($RelativeSqlitePath) {
        "runtime/production/workflow.sqlite3"
    } else {
        $liveDb.Replace('\', '\\')
    }
    Write-TextNoBom -Path (Join-Path $runtimeLive "production.json") `
        -Lines @("{`"sqlite_path`": `"$sqliteReference`"}")
    Write-TextNoBom -Path (Join-Path $runtimeLive "research.json") -Lines @('{"cdp":{}}')

    if ($RealRuntimeDirectory) {
        New-Item -ItemType Directory -Force -Path (Join-Path $target "runtime") | Out-Null
    }
    else {
        New-Item -ItemType Junction -Path (Join-Path $target "runtime") -Target $runtimeLive | Out-Null
    }

    return [pscustomobject]@{
        Base = $Base; Target = $target; Candidate = $candidate; RuntimeLive = $runtimeLive
        LiveDatabase = $liveDb; BackupDatabase = $backupDb
        CandidateManifest = (Join-Path $Base "candidate-manifest.sha256")
        DatabaseReport = (Join-Path $backupDir "workflow.sqlite3.verify.json")
        Snapshot = (Join-Path $Base "snapshot")
        InstallDir = $target
    }
}

function New-Snapshot {
    param([pscustomobject]$Fixture)
    $out = Invoke-Child "backup_running_release.ps1" @{
        SourceDir = $Fixture.Target
        Destination = $Fixture.Snapshot
    }
    if ($out.ExitCode -ne 0) { throw "backup fixture failed: $($out.Output)" }
    # The snapshot must be the running payload byte for byte, not merely a
    # self-consistent manifest of whatever was copied.
    $script:checks++
    $sourceFiles = @(Get-ChildItem -LiteralPath (Join-Path $Fixture.Target "_internal") -Recurse -File)
    $copyFiles = @(Get-ChildItem -LiteralPath (Join-Path $Fixture.Snapshot "_internal") -Recurse -File)
    if ($sourceFiles.Count -ne $copyFiles.Count) {
        [void]$failures.Add("snapshot payload count $($copyFiles.Count) != source $($sourceFiles.Count)")
    }
    foreach ($file in $sourceFiles) {
        $rel = $file.FullName.Substring((Join-Path $Fixture.Target "_internal").Length + 1)
        $copy = Join-Path (Join-Path $Fixture.Snapshot "_internal") $rel
        if (-not (Test-Path -LiteralPath $copy -PathType Leaf)) {
            [void]$failures.Add("snapshot payload missing $rel"); continue
        }
        if ((Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash -ne
            (Get-FileHash -LiteralPath $copy -Algorithm SHA256).Hash) {
            [void]$failures.Add("snapshot payload differs at $rel")
        }
    }
    $script:checks++
    if ((Get-FileHash -LiteralPath (Join-Path $Fixture.Target "INSO_V1.6.exe") -Algorithm SHA256).Hash -ne
        (Get-FileHash -LiteralPath (Join-Path $Fixture.Snapshot "INSO_V1.6.exe") -Algorithm SHA256).Hash) {
        [void]$failures.Add("snapshot EXE is not the running EXE")
    }
    # The snapshot must describe the ledger the *live configuration* names, not a
    # guessed path under the junction.
    $script:checks++
    $statePath = Join-Path $Fixture.Snapshot "database-state.json"
    try { $state = Get-Content -LiteralPath $statePath -Raw -Encoding UTF8 | ConvertFrom-Json }
    catch { [void]$failures.Add("snapshot has no readable database-state.json"); return $out }
    if (-not $state.exists -or -not (Test-Path -LiteralPath $state.resolved_path -PathType Leaf)) {
        [void]$failures.Add("snapshot database-state does not resolve the configured ledger ($($state.resolved_path))")
    }
    elseif ((Get-FileHash -LiteralPath $state.resolved_path -Algorithm SHA256).Hash -ne
            (Get-FileHash -LiteralPath $Fixture.LiveDatabase -Algorithm SHA256).Hash) {
        [void]$failures.Add("snapshot database-state resolves a different file than the fixture ledger")
    }
    return $out
}

function Get-DatabaseReport {
    param([pscustomobject]$Fixture, [int]$MaxAgeHours = 72)
    return Invoke-Child "verify_database_backup.ps1" @{
        DatabaseBackup = $Fixture.BackupDatabase
        SourceDatabase = $Fixture.LiveDatabase
        InstallDir = $Fixture.Target
        Report = $Fixture.DatabaseReport
        PythonExecutable = $python
        MaxAgeHours = $MaxAgeHours
    }
}

function New-InstallArgs {
    param([pscustomobject]$Fixture, [hashtable]$Extra = @{})
    $values = [ordered]@{
        CandidateDir = $Fixture.Candidate
        Manifest = $Fixture.CandidateManifest
        TargetDir = $Fixture.Target
        RuntimeTarget = $Fixture.RuntimeLive
        RollbackDir = $Fixture.Snapshot
        DatabaseBackup = $Fixture.BackupDatabase
        DatabaseReport = $Fixture.DatabaseReport
        ExpectedPreviousExeSha256 = (Get-FileHash -LiteralPath (Join-Path $Fixture.Target "INSO_V1.6.exe") -Algorithm SHA256).Hash.ToLowerInvariant()
        ConfirmDatabaseBackupVerified = $true
        ConfirmSwitch = $true
    }
    foreach ($key in $Extra.Keys) { $values[$key] = $Extra[$key] }
    return $values
}

function Assert-Refused {
    param([string]$Name, [pscustomobject]$Result, [string]$Expected)
    $script:checks++
    if ($Result.ExitCode -eq 0) {
        [void]$failures.Add("$Name : passed but should have refused")
        return
    }
    if ($Expected -and ($Result.Output -notmatch [regex]::Escape($Expected))) {
        [void]$failures.Add("$Name : refused for the wrong reason (wanted '$Expected')`n$($Result.Output)")
    }
}

function Assert-Output {
    param([string]$Name, [pscustomobject]$Result, [string]$Expected)
    $script:checks++
    if ($Result.Output -notmatch [regex]::Escape($Expected)) {
        [void]$failures.Add("$Name : missing '$Expected'`n$($Result.Output)")
    }
}

try {
    # --- authorisation -------------------------------------------------------
    $f = New-Fixture (Join-Path $root "auth")
    New-Snapshot $f | Out-Null
    Get-DatabaseReport $f | Out-Null
    Assert-Refused "no ConfirmSwitch" (Invoke-Child "install_release_candidate.ps1" (New-InstallArgs $f @{ ConfirmSwitch = $false })) "ConfirmSwitch"

    $f = New-Fixture (Join-Path $root "auth2")
    New-Snapshot $f | Out-Null
    Get-DatabaseReport $f | Out-Null
    Assert-Refused "no ConfirmDatabaseBackupVerified" (Invoke-Child "install_release_candidate.ps1" (New-InstallArgs $f @{ ConfirmDatabaseBackupVerified = $false })) "ConfirmDatabaseBackupVerified"

    $f = New-Fixture (Join-Path $root "auth3")
    New-Snapshot $f | Out-Null
    Get-DatabaseReport $f | Out-Null
    Assert-Refused "short expected sha" (Invoke-Child "install_release_candidate.ps1" (New-InstallArgs $f @{ ExpectedPreviousExeSha256 = "abc" })) "64-hex"

    # --- snapshot ------------------------------------------------------------
    $f = New-Fixture (Join-Path $root "snapshot-changed")
    New-Snapshot $f | Out-Null
    Get-DatabaseReport $f | Out-Null
    Add-Content -LiteralPath (Join-Path $f.Snapshot "config\production.json") -Value " "
    Assert-Refused "snapshot file changed" (Invoke-Child "install_release_candidate.ps1" (New-InstallArgs $f)) "failed verification"

    $f = New-Fixture (Join-Path $root "snapshot-partial")
    New-Snapshot $f | Out-Null
    Get-DatabaseReport $f | Out-Null
    $manifest = Get-Content -LiteralPath (Join-Path $f.Snapshot "PROGRAM-MANIFEST.sha256") |
        Where-Object { $_ -notmatch "_internal/sub/b\.dll" }
    Write-TextNoBom -Path (Join-Path $f.Snapshot "PROGRAM-MANIFEST.sha256") -Lines $manifest
    Assert-Refused "snapshot incomplete" (Invoke-Child "install_release_candidate.ps1" (New-InstallArgs $f)) "incomplete or stale"

    $f = New-Fixture (Join-Path $root "identity")
    New-Snapshot $f | Out-Null
    Get-DatabaseReport $f | Out-Null
    Assert-Refused "wrong expected EXE identity" (Invoke-Child "install_release_candidate.ps1" (New-InstallArgs $f @{ ExpectedPreviousExeSha256 = ("a" * 64) })) "not the build named by"

    # --- configuration binding ----------------------------------------------
    $f = New-Fixture (Join-Path $root "config-stale")
    New-Snapshot $f | Out-Null
    Get-DatabaseReport $f | Out-Null
    Write-TextNoBom -Path (Join-Path $f.RuntimeLive "research.json") -Lines @('{"cdp":{"changed":true}}')
    Assert-Refused "snapshot config is not the live config" (Invoke-Child "install_release_candidate.ps1" (New-InstallArgs $f)) "not the live configuration behind runtime"

    $f = New-Fixture (Join-Path $root "config-wrong-dir")
    $other = Join-Path $f.Base "other-config"
    New-Item -ItemType Directory -Force -Path $other | Out-Null
    Write-TextNoBom -Path (Join-Path $other "production.json") -Lines @('{"sqlite_path":"x"}')
    Write-TextNoBom -Path (Join-Path $other "research.json") -Lines @('{}')
    Assert-Refused "backup script refuses a foreign config dir" (Invoke-Child "backup_running_release.ps1" @{
        SourceDir = $f.Target; RuntimeConfigDir = $other; Destination = $f.Snapshot
    }) "is not the one runtime points at"

    # --- runtime junction ----------------------------------------------------
    $f = New-Fixture (Join-Path $root "junction-missing")
    New-Snapshot $f | Out-Null
    Get-DatabaseReport $f | Out-Null
    [System.IO.Directory]::Delete((Join-Path $f.Target "runtime"), $false)
    Assert-Refused "missing runtime junction" (Invoke-Child "install_release_candidate.ps1" (New-InstallArgs $f)) "runtime junction"

    $f = New-Fixture (Join-Path $root "junction-elsewhere")
    New-Snapshot $f | Out-Null
    Get-DatabaseReport $f | Out-Null
    $other = Join-Path $f.Base "runtime-other"
    New-Item -ItemType Directory -Force -Path $other | Out-Null
    [System.IO.Directory]::Delete((Join-Path $f.Target "runtime"), $false)
    New-Item -ItemType Junction -Path (Join-Path $f.Target "runtime") -Target $other | Out-Null
    Assert-Refused "junction points elsewhere" (Invoke-Child "install_release_candidate.ps1" (New-InstallArgs $f)) "runtime points at"

    $f = New-Fixture (Join-Path $root "junction-not-a-junction") -RealRuntimeDirectory
    Assert-Refused "runtime is a real directory" (Invoke-Child "backup_running_release.ps1" @{
        SourceDir = $f.Target; Destination = $f.Snapshot
    }) "not a junction"

    # --- database provenance -------------------------------------------------
    $f = New-Fixture (Join-Path $root "db-report-missing")
    New-Snapshot $f | Out-Null
    $args = New-InstallArgs $f
    $args["DatabaseReport"] = (Join-Path $f.Base "absent.json")
    Assert-Refused "no database report" (Invoke-Child "install_release_candidate.ps1" $args) "no verification report"

    $f = New-Fixture (Join-Path $root "db-report-foreign-install")
    New-Snapshot $f | Out-Null
    Get-DatabaseReport $f | Out-Null
    $report = Get-Content -LiteralPath $f.DatabaseReport -Raw -Encoding UTF8 | ConvertFrom-Json
    $report.install_dir = (Join-Path $f.Base "some-other-install")
    $report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $f.DatabaseReport -Encoding UTF8
    Assert-Refused "report from another install" (Invoke-Child "install_release_candidate.ps1" (New-InstallArgs $f)) "belongs to"

    $f = New-Fixture (Join-Path $root "db-report-foreign-source")
    New-Snapshot $f | Out-Null
    Get-DatabaseReport $f | Out-Null
    $report = Get-Content -LiteralPath $f.DatabaseReport -Raw -Encoding UTF8 | ConvertFrom-Json
    $report.source_database = (Join-Path $f.Base "elsewhere\workflow.sqlite3")
    $report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $f.DatabaseReport -Encoding UTF8
    Assert-Refused "report names another source path" (Invoke-Child "install_release_candidate.ps1" (New-InstallArgs $f)) "source path"

    $f = New-Fixture (Join-Path $root "db-held-open")
    New-Snapshot $f | Out-Null
    $hold = [System.IO.File]::Open($f.LiveDatabase, [System.IO.FileMode]::Open,
        [System.IO.FileAccess]::Read, [System.IO.FileShare]::ReadWrite)
    try {
        Assert-Refused "live ledger still held open" (Get-DatabaseReport $f) "still holds the live ledger open"
    }
    finally { $hold.Dispose() }

    $f = New-Fixture (Join-Path $root "db-open-write-intent")
    New-Snapshot $f | Out-Null
    & $python (Join-Path $f.Base "make_db.py") $f.LiveDatabase "2026-11-15T08:00:00+00:00" `
        "INSERT INTO workflow_write_intents(intent_id,document_key,kind,state,created_at) VALUES('wi_x','doc','sheets','PENDING','2026-11-15T08:00:00+00:00');"
    if ($LASTEXITCODE -ne 0) { throw "write-intent fixture database failed" }
    Copy-Item -LiteralPath $f.LiveDatabase -Destination $f.BackupDatabase -Force
    Assert-Refused "unresolved write intent blocks the snapshot" (Get-DatabaseReport $f) "unresolved write intent"

    $f = New-Fixture (Join-Path $root "db-foreign-copy")
    New-Snapshot $f | Out-Null
    Add-Content -LiteralPath $f.BackupDatabase -Value "not the same bytes"
    Assert-Refused "copy is not the live ledger" (Get-DatabaseReport $f) "not the live ledger"

    $f = New-Fixture (Join-Path $root "db-stale")
    New-Snapshot $f | Out-Null
    Remove-Item -LiteralPath $f.LiveDatabase -Force
    & $python (Join-Path $f.Base "make_db.py") $f.LiveDatabase "2026-11-01T00:00:00+00:00"
    if ($LASTEXITCODE -ne 0) { throw "stale fixture database failed" }
    Copy-Item -LiteralPath $f.LiveDatabase -Destination $f.BackupDatabase -Force
    Assert-Refused "stale but valid ledger" (Get-DatabaseReport $f) "not current"

    $f = New-Fixture (Join-Path $root "db-no-installdir")
    New-Snapshot $f | Out-Null
    Assert-Refused "clean stop cannot be claimed without -InstallDir" (Invoke-Child "verify_database_backup.ps1" @{
        DatabaseBackup = $f.BackupDatabase
        SourceDatabase = $f.LiveDatabase
        Report = $f.DatabaseReport
        PythonExecutable = $python
    }) "clean-stop state cannot be proven"

    $f = New-Fixture (Join-Path $root "db-wal-open")
    New-Snapshot $f | Out-Null
    Set-Content -LiteralPath "$($f.LiveDatabase)-wal" -Value "uncheckpointed" -NoNewline
    Copy-Item -LiteralPath $f.LiveDatabase -Destination $f.BackupDatabase -Force
    Assert-Refused "uncheckpointed WAL" (Get-DatabaseReport $f) "not quiescent"

    # --- success path, then post-copy verification ---------------------------
    $f = New-Fixture (Join-Path $root "success")
    New-Snapshot $f | Out-Null
    Get-DatabaseReport $f | Out-Null
    $install = Invoke-Child "install_release_candidate.ps1" (New-InstallArgs $f)
    Assert-Output "success path" $install "INSTALL_RESULT = PASS"
    $script:checks++
    if ((Get-FileHash -LiteralPath (Join-Path $f.Target "INSO_V1.6.exe") -Algorithm SHA256).Hash.ToLowerInvariant() -ne
        (Get-FileHash -LiteralPath (Join-Path $f.Candidate "INSO_V1.6.exe") -Algorithm SHA256).Hash.ToLowerInvariant()) {
        [void]$failures.Add("success path : installed EXE is not the candidate")
    }
    $script:checks++
    if (-not (Test-Path -LiteralPath (Join-Path $f.Target "runtime"))) {
        [void]$failures.Add("success path : the runtime junction disappeared")
    }
    Assert-Output "installed verify after success" (Invoke-Child "install_release_candidate.ps1" @{
        TargetDir = $f.Target; Manifest = $f.CandidateManifest; VerifyInstalledOnly = $true
    }) "INSTALLED_VERIFY = PASS"
    # Cold rollback material must still be in the target after a good install.
    $script:checks++
    $previousPayload = @(Get-ChildItem -LiteralPath $f.Target -Directory -Filter "_internal.prev-*")
    $previousExe = @(Get-ChildItem -LiteralPath $f.Target -File -Filter "INSO_V1.6.exe.prev-*")
    if ($previousPayload.Count -ne 1 -or $previousExe.Count -ne 1) {
        [void]$failures.Add("success path : the previous build was not kept for a cold rollback")
    }

    # Corrupt one DLL: the file count is unchanged, the bytes are not.
    Add-Content -LiteralPath (Join-Path $f.Target "_internal\sub\b.dll") -Value "tampered"
    Assert-Refused "post-copy mismatch is detected" (Invoke-Child "install_release_candidate.ps1" @{
        TargetDir = $f.Target; Manifest = $f.CandidateManifest; VerifyInstalledOnly = $true
    }) "mismatch _internal/sub/b.dll"

    # --- a relative sqlite_path names the same ledger through the junction ----
    $f = New-Fixture (Join-Path $root "relative-ledger") -RelativeSqlitePath
    New-Snapshot $f | Out-Null
    Get-DatabaseReport $f | Out-Null
    Assert-Output "relative sqlite_path is resolved to the live ledger" (Invoke-Child "install_release_candidate.ps1" (New-InstallArgs $f)) "INSTALL_RESULT = PASS"

    # --- injected mid-switch failure ----------------------------------------
    $f = New-Fixture (Join-Path $root "switch-fault")
    New-Snapshot $f | Out-Null
    Get-DatabaseReport $f | Out-Null
    $before = (Get-FileHash -LiteralPath (Join-Path $f.Target "INSO_V1.6.exe") -Algorithm SHA256).Hash.ToLowerInvariant()
    $fault = Invoke-Child "install_release_candidate.ps1" (New-InstallArgs $f @{ InjectSwitchFault = $true })
    Assert-Output "mid-switch failure is not PASS" $fault "INSTALL_RESULT = FAIL_RESTORED"
    $script:checks++
    $after = (Get-FileHash -LiteralPath (Join-Path $f.Target "INSO_V1.6.exe") -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($before -ne $after) { [void]$failures.Add("mid-switch failure : the old EXE was not restored") }
    $script:checks++
    if (-not (Test-Path -LiteralPath (Join-Path $f.Target "_internal\sub\b.dll"))) {
        [void]$failures.Add("mid-switch failure : the old payload was not restored")
    }
    Assert-Output "restored payload is verified file by file" $fault "restored_files_verified"

    # --- corruption after the copy: same file count, different bytes ---------
    $f = New-Fixture (Join-Path $root "post-copy-corruption")
    New-Snapshot $f | Out-Null
    Get-DatabaseReport $f | Out-Null
    $oldExe = (Get-FileHash -LiteralPath (Join-Path $f.Target "INSO_V1.6.exe") -Algorithm SHA256).Hash.ToLowerInvariant()
    $oldDll = (Get-FileHash -LiteralPath (Join-Path $f.Target "_internal\a.dll") -Algorithm SHA256).Hash.ToLowerInvariant()
    $corrupt = Invoke-Child "install_release_candidate.ps1" (New-InstallArgs $f @{ InjectPostCopyCorruption = $true })
    Assert-Output "post-copy corruption is caught" $corrupt "INSTALL_RESULT = FAIL_RESTORED"
    Assert-Output "post-copy corruption names the mismatch" $corrupt "mismatch _internal/a.dll"
    $script:checks++
    if ((Get-FileHash -LiteralPath (Join-Path $f.Target "INSO_V1.6.exe") -Algorithm SHA256).Hash.ToLowerInvariant() -ne $oldExe) {
        [void]$failures.Add("post-copy corruption : the old EXE was not restored")
    }
    $script:checks++
    if ((Get-FileHash -LiteralPath (Join-Path $f.Target "_internal\a.dll" -ErrorAction SilentlyContinue) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $oldDll) {
        [void]$failures.Add("post-copy corruption : the old payload bytes were not restored")
    }

    # --- a restore that cannot finish must say so ----------------------------
    $f = New-Fixture (Join-Path $root "restore-interrupted")
    New-Snapshot $f | Out-Null
    Get-DatabaseReport $f | Out-Null
    $broken = Invoke-Child "install_release_candidate.ps1" (New-InstallArgs $f @{
        InjectSwitchFault = $true; InjectRestoreFault = $true })
    Assert-Output "a failed restore is never reported as restored" $broken "INSTALL_RESULT = ROLLBACK_REQUIRED"
    Assert-Output "a failed restore names the manual restore source" $broken "restore_from"
    $script:checks++
    if ($broken.Output -match "INSTALL_RESULT = PASS") {
        [void]$failures.Add("a failed restore printed PASS")
    }
}
finally {
    if (-not $env:KEEP_GATE_ROOT) {
        Remove-Item -LiteralPath $root -Recurse -Force -ErrorAction SilentlyContinue
    }
    else { Write-Output "gate_root = $root" }
}

if ($failures.Count) {
    Write-Output "GATE_TEST_RESULT = FAIL"
    foreach ($failure in $failures) { Write-Output $failure }
    foreach ($note in $skipped) { Write-Output $note }
    exit 1
}
Write-Output "checks = $($script:checks)"
foreach ($note in $skipped) { Write-Output $note }
Write-Output "GATE_TEST_RESULT = PASS"
exit 0
