# Windows release build and local deployment

The generic release is a PyInstaller onedir/windowed folder. Install the fully
locked dependency set in `requirements-windows-release.lock` (or review the
direct dependencies in `requirements-windows-release.txt`), then run
`scripts/build_windows_release.ps1`. The executable is
`dist/INSO_V1.1/INSO_V1.1.exe`. The build contains the same Python launcher,
Workflow, Research, Sheets and GUI modules as development mode. It does not
contain runtime configuration or production data.

Build from a normal Windows user session with a working Tcl/Tk installation.
The build script initializes Tcl before PyInstaller and runs the frozen
`--self-check` afterwards. A restricted build process that cannot initialize
Tcl fails instead of producing an EXE without `tkinter`. The self-check opens
no GUI or production runtime. Vault PowerShell subprocesses use a hidden
console in the windowed release.

Create the ignored `runtime/research.json` and `runtime/production.json` beside
the executable for local deployment. Existing paths in those files may be
absolute or relative to the release directory. `production.json` may optionally
include an explicit approved Chrome bootstrap section:

```json
{
  "browser_bootstrap": {
    "executable": "C:/Approved/Chrome/Application/chrome.exe",
    "profile_dir": "C:/Approved/INSO-CDP-Profile",
    "debug_port": 9222,
    "ready_timeout_seconds": 30
  }
}
```

The profile directory must already exist. The application never guesses or
creates it. If configured CDP is reachable, the app reuses it and does not close
it. Otherwise, Chrome is launched only with this explicit configuration and is
closed after the backend has drained and stopped. INSO starts owned Chrome as a
normal Chrome process without an initial window, while CDP creates research
targets in the background. Authenticated supplier sites therefore receive a
regular session without taking the Owner's foreground or display space. It
closes an app-owned session after the current due-work batch drains; the next
due inquiry starts it again. Login, CAPTCHA, OTP, and device verification remain
fail-closed and require a separate human action. Do not use a profile that is
also used by an ordinary Chrome session.

Startup and sanitized launcher diagnostics are written to
`runtime/logs/INSO_V1.1.log` with three 1 MB backups. The release directory must
be writable. Do not copy runtime configuration, the OAuth client file, the
protected OAuth grant, browser profile, workflow database, or Excel results into
a generic release artifact.

To verify frozen access to the existing canonical Credential Vault, run
`INSO_V1.1.exe --diagnose-vault`. It exits without opening the GUI or browser and
writes `runtime/logs/credential-readiness.json`. This report contains only
component presence, override flags, Site IDs, availability booleans, and safe
error class names; it does not include login values. The release bundles the
canonical `CredentialVault.psm1` module beside the frozen Core Provider. The
Vault file stays in the current user's local application data directory.
