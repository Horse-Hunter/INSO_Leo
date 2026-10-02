<#
.SYNOPSIS
  Ensure the ONE shared INSO CDP session is running, without ever creating a new one.

.DESCRIPTION
  Every INSO window / AI agent / build version must talk to the same Chrome
  DevTools Protocol endpoint backed by the same profile directory. That profile
  holds the Owner's authenticated INSO cookies (erp_token plus the multi-day
  SMS-verification memory cookie). The Owner will not provide a new SMS code, so
  this profile is an irreplaceable asset.

  This script only ever:
    1. reuses an already-running CDP endpoint on the configured port, or
    2. starts Chrome on the SAME configured profile directory and port, with a
       visible window so a one-off manual login is possible.

  It never creates a second profile, never uses another port, and never kills a
  browser. If the protected profile is missing it stops and tells you to restore
  it from the backup folder instead of silently starting a blank profile.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\open_cdp_session.ps1
#>
[CmdletBinding()]
param(
    [string]$ConfigPath = "",
    [switch]$NoWindow
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
if ([string]::IsNullOrWhiteSpace($ConfigPath)) {
    $ConfigPath = Join-Path $repoRoot "dist\INSO_V1.1\runtime\production.json"
}
$canonicalRoot = "D:\Program_Leo\INSO_CDP"
$backupRoot = Join-Path $canonicalRoot "session-backup"
$inosShell = "https://yingsuo.alperp.cn/skins/etaoerp//InnerEnquiry/YeWuXJ/List.aspx"

function Write-Status([string]$Message) {
    Write-Host ("[{0}] {1}" -f (Get-Date -Format "HH:mm:ss"), $Message)
}

if (-not (Test-Path -LiteralPath $ConfigPath)) {
    Write-Status "FATAL: production config not found at $ConfigPath"
    exit 2
}

$config = Get-Content -LiteralPath $ConfigPath -Raw | ConvertFrom-Json
$bootstrap = $config.browser_bootstrap
if (-not $bootstrap) {
    Write-Status "FATAL: browser_bootstrap is not configured in $ConfigPath"
    exit 2
}

$executable = [string]$bootstrap.executable
$profileDir = [string]$bootstrap.profile_dir
$port = [int]$bootstrap.debug_port
$endpoint = "http://127.0.0.1:$port"

Write-Status "config      : $ConfigPath"
Write-Status "profile_dir : $profileDir"
Write-Status "debug_port  : $port"

if (-not (Test-Path -LiteralPath $executable)) {
    Write-Status "FATAL: approved Chrome executable is missing: $executable"
    exit 2
}

# Guard 1: the profile directory must exist and look like a used Chrome profile.
if (-not (Test-Path -LiteralPath $profileDir)) {
    Write-Status "FATAL: protected CDP profile is MISSING: $profileDir"
    Write-Status "Do NOT start a blank profile. Restore from: $backupRoot"
    exit 3
}
if (-not (Test-Path -LiteralPath (Join-Path $profileDir "Default"))) {
    Write-Status "FATAL: $profileDir has no Default/ directory (blank or damaged profile)."
    Write-Status "Restore from: $backupRoot instead of starting a blank profile."
    exit 3
}

# Guard 2: the profile must stay where the canonical alias points, so no version
# silently diverges onto its own copy.
if (Test-Path -LiteralPath (Join-Path $canonicalRoot "chrome-profile")) {
    $aliasItem = Get-Item -LiteralPath (Join-Path $canonicalRoot "chrome-profile") -Force
    $target = ($aliasItem.Target | Select-Object -First 1)
    if ($target) {
        $resolvedAlias = (Resolve-Path -LiteralPath (Join-Path $canonicalRoot "chrome-profile")).Path
        $resolvedProfile = (Resolve-Path -LiteralPath $profileDir).Path
        if ($resolvedAlias -ne $resolvedProfile) {
            Write-Status "FATAL: profile_dir does not match the protected canonical profile."
            Write-Status "  canonical : $resolvedAlias"
            Write-Status "  configured: $resolvedProfile"
            Write-Status "Point browser_bootstrap.profile_dir back at $canonicalRoot\chrome-profile."
            exit 3
        }
        Write-Status "canonical alias verified -> $resolvedAlias"
    }
}

function Test-CdpReady {
    try {
        $version = Invoke-RestMethod -Uri "$endpoint/json/version" -TimeoutSec 3
        return [bool]$version.webSocketDebuggerUrl
    } catch {
        return $false
    }
}

if (Test-CdpReady) {
    Write-Status "CDP endpoint ALREADY RUNNING on $endpoint - reusing it, nothing was launched."
    try {
        $tabs = Invoke-RestMethod -Uri "$endpoint/json/list" -TimeoutSec 3
        $inos = @($tabs | Where-Object { $_.url -like "*alperp.cn*" })
        if ($inos.Count -gt 0) {
            Write-Status ("INSO tab present: " + $inos[0].url)
        } else {
            Write-Status "No INSO tab open; opening the authenticated shell in the shared session."
            Invoke-RestMethod -Method Put -Uri ("$endpoint/json/new?" + [uri]::EscapeDataString($inosShell)) -TimeoutSec 5 | Out-Null
        }
    } catch {
        Write-Status "Could not enumerate tabs (non-fatal): $($_.Exception.Message)"
    }
    exit 0
}

Write-Status "No CDP on $endpoint. Starting Chrome on the SAME protected profile (not a new one)."
$args = @(
    "--user-data-dir=$profileDir",
    "--remote-debugging-port=$port",
    "--remote-debugging-address=127.0.0.1",
    "--no-first-run",
    "--no-default-browser-check"
)
if (-not $NoWindow) {
    $args += $inosShell
    Start-Process -FilePath $executable -ArgumentList $args | Out-Null
    Write-Status "Chrome started WITH a visible window. Complete the INSO login in it if asked."
} else {
    $args += "--no-startup-window"
    Start-Process -FilePath $executable -ArgumentList $args -WindowStyle Hidden | Out-Null
    Write-Status "Chrome started without a window (automation default)."
}

for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Milliseconds 500
    if (Test-CdpReady) {
        Write-Status "CDP is ready on $endpoint using $profileDir"
        Write-Status "Leave this Chrome running. Do NOT force-kill it."
        exit 0
    }
}

Write-Status "WARNING: Chrome started but CDP did not become ready within 15s."
exit 4
