# CDP Session Policy — the one shared INSO browser session

RFQ-003 (2026-10-07): human-needed pages are not closed orders. INSO manual
verification is GLOBAL_STOP; IC.net is a V1.2 module pause. Preserve the page
through final worker cleanup, detach only the client, and never park the paused
session. Successful closed rows keep the existing fresh-owned-tab cleanup.
Query retries use the same endpoint/profile, never overlapping INSO operations.

Status: **BINDING**. Applies to every window, every AI agent, and every build
version (V1.1 hotfix, V1.2, and anything after) that reads INSO.

## Why this exists

INSO (`yingsuo.alperp.cn`) now enforces an SMS verification code at login. The
Owner has completed that login **once** and **will not provide another code**.
The authenticated session now lives in a Chrome profile on disk, in the form of
persistent cookies:

| cookie | domain | lifetime | notes |
| --- | --- | --- | --- |
| `erp_token` | `.yingsuo.alperp.cn` | 1 day | the actual session token |
| `Shawn_yzm_v2_` | `yingsuo.alperp.cn` | 15 days | the SMS-verification memory (httpOnly, secure) |
| `erp_username`, `erp_password`, `erp_company`, `erp_companyno`, `erp_grouppin`, `erp_companypin`, `erp_userpin`, `QieHuanMain`, `____erp_*` | `.yingsuo.alperp.cn` | 1 day | prefill / switching state |

Losing this profile means the whole delivery stops until the Owner supplies a
new SMS code — which will not happen. **The profile is an irreplaceable asset.**

## The one canonical location

| item | value |
| --- | --- |
| Canonical alias (used by every config) | `D:\Program_Leo\INSO_CDP\chrome-profile` |
| Physical data on disk | `D:\Program_Leo\INSO_Leo\.worktrees\research-v1-production-runtime-buddy\.browser-profile\cdp` |
| Debug endpoint | `http://127.0.0.1:9222` |
| Approved executable | `C:\Program Files (x86)\Google\Chrome\Application\chrome.exe` |
| Session backup | `D:\Program_Leo\INSO_CDP\session-backup\` |
| Sentinel files | `D:\Program_Leo\INSO_CDP\README-DO-NOT-DELETE.txt`, plus one inside the physical profile |

The alias is a Windows directory junction (`chrome-profile` → the physical
path). Configs reference the **alias**, so the physical location can be moved
later without editing any config — only the junction is repointed.

## Rules (non-negotiable)

1. **One profile, one port.** Every `browser_bootstrap.profile_dir` must be
   `D:\Program_Leo\INSO_CDP\chrome-profile`; every `debug_port` must be `9222`.
   No version, worktree, AI session, or test may point anywhere else.
2. **Never start a new CDP.** `browser_bootstrap.persistent_session` is set to
   `true` in every production config. In that mode the launcher:
   - attaches to the running endpoint when present (`owned=False`), and
   - if the endpoint is down, starts Chrome on **the same profile and port**
     (resuming *this* CDP, not creating another one), and
   - **refuses to start a blank profile**: a profile directory without a
     `Default/` sub-directory raises `protected CDP session profile is missing`.
3. **Never force-kill the session browser.** A persistent handle is never
   `owned`, so no shutdown path (`_release_idle_browser`,
   `_discard_unready_browser`, the INSO session lease, or the bootstrap timeout)
   can stop it. The window hider is not installed either. The only process the
   code may reap is one it just launched itself that never served CDP.
4. **Never delete or move** the canonical folder, its junction, or the physical
   profile. The `DO_NOT_DELETE-CDP-SESSION.txt` sentinel marks it.
5. **Do not open the profile in a second Chrome.** A second instance on the same
   `--user-data-dir` steals file locks and can leave the cookie database
   inconsistent.
6. **Stop Playwright only on the thread that started it.** Playwright's
   synchronous client is bound to the greenlet of the thread that called
   `sync_playwright().start()`. Stopping it elsewhere raises
   `greenlet.error: Cannot switch to a different thread`. That error is
   unrecoverable (the reference is already dropped) and it **orphans the
   Playwright driver process** — measured at ~126 MB, one per release, surviving
   until the host process exits. The production runtime starts the client on the
   poller thread (the V1.2 duplicate check prepares the session first) and
   releases the idle session from the worker thread, so `BrowserHandle`
   (`src/launcher/browser_bootstrap.py`) parks a foreign-thread release and the
   owning thread stops it at its next `drain_deferred_stops()`. Any new teardown
   path must do the same, and every runtime loop that can own a client must
   drain.

   Reading through the browser is *not* affected: `browser.contexts`,
   `context.pages`, `page.url` and `browser.is_connected()` were all verified to
   work from a non-owning thread. Only `stop()` is thread-bound.

## How to use it

### Owner's idle-tab rule (2026-10-06)

Trigger: before starting an inquiry and after a row's normal closed-loop finish.
Owner: production launcher. Procedure/source: `park_shared_cdp` in the existing
browser bootstrap module; select the unique dedicated 9222 context, retain or
create ONE about:blank BEFORE closing other tabs, then verify it is the sole
live page. Owner explicitly allows cleanup of pre-existing business tabs here;
this does not apply to unrelated Chrome profiles/windows. Cookies, context,
browser process, profile and port stay untouched. A row awaiting manual
CAPTCHA/OTP/device verification is not closed: stop and keep its human-needed
page until Owner resolves it. Evidence/enforcement: offline last-tab/context
safety tests, actual page inventory and closed-loop callback cleanup; inability
to establish the blank-only state fails closed rather than advancing orders.

```powershell
# Ensure the shared session is up (reuses it if already running; never creates a new one)
powershell -ExecutionPolicy Bypass -File scripts\open_cdp_session.ps1
```

Then run the candidate launcher as usual. The launcher detects the endpoint,
attaches with `owned=False`, and leaves the browser alone afterwards.

## Recovery

Every successful attach/launch in persistent mode automatically refreshes
`session-backup\inso-cookies-latest.json` next to the profile, so a recoverable
snapshot always exists without any manual step.

Only if the session is genuinely gone (navigating to the authenticated shell
bounces back to `login.aspx`):

1. The backup folder holds `inso-cookies-<stamp>.json` (full cookie values) and
   `Local State-<stamp>` (Chrome's cookie-encryption key).
2. Run `scripts\open_cdp_session.ps1` to get a **visible** window on the shared
   profile, and complete the INSO login there once (an SMS code may be required
   — this is the one case that needs the Owner).
3. Never "fix" the problem by pointing a config at a fresh profile directory.

## What "reuse" means in code

- `src/launcher/browser_bootstrap.py` — `persistent_session` handling, the
  blank-profile guard, `_reap_failed_launch`, `_snapshot_session_cookies`, and
  the thread-bound `BrowserHandle.disconnect()` / `drain_deferred_stops()`.
- `src/launcher/backend.py` — releases idle browsers; with a persistent handle
  this only disconnects Playwright, and both runtime loops drain the clients
  their own thread owns.
- `src/launcher/inso_session.py` — `BrowserOwnership.REUSED` (from `owned=False`)
  makes every lease teardown a plain disconnect.

## Known fragility and planned cutover

The physical profile still lives under
`.worktrees/research-v1-production-runtime-buddy/`, which is a retired worktree
shell. It could not be moved while Chrome held the (locked) cookie database.

Mitigations in place: the sentinel file, the junction alias so configs never
need editing, the automatic cookie snapshot, and `open_cdp_session.ps1` refusing
to start a blank profile.

When Chrome is next stopped gracefully, do the real relocation and repoint the
junction (configs stay untouched):

1. Confirm nothing is listening on `9222`.
2. `Move-Item` the physical profile to a stable real directory.
3. `Remove-Item` the `chrome-profile` junction and recreate it against the new
   real directory.
4. Start Chrome via `scripts\open_cdp_session.ps1` and confirm the authenticated
   shell still opens without a login.
