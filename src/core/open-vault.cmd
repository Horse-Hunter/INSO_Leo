@echo off
where pwsh >nul 2>nul
if errorlevel 1 (
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0vault-manager.ps1" %*
) else (
  pwsh -NoProfile -File "%~dp0vault-manager.ps1" %*
)
if errorlevel 1 pause
