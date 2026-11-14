# One protected INSO Chrome / CDP session — binding

**Trigger:** all browser, INSO, site research, quotation, login, Windows release and cleanup operations. **Owner:** the **single** active Executor. **Source:** this policy + existing launcher/browser-bootstrap code. **Evidence:** exact connection/ownership, old and new PID/target and any unresolved effects in RFQ Execution Log. **CEO enforcement:** fail Review on clone/reset/forced close or loss of the only authenticated session.

| Property | Mandatory value |
| --- | --- |
| CDP endpoint | `127.0.0.1:9222` |
| Canonical profile | `D:\\Program_Leo\\INSO_CDP\\chrome-profile` |
| Reuse | `persistent_session: true`; attach same existing browser/profile |
| Supported session bootstrap | `scripts/open_cdp_session.ps1` |
| Backup folder | `D:\\Program_Leo\\INSO_CDP\\session-backup` (not proven full cold restore) |

1. Never create another browser profile/CDP port, never force-kill the protected Chrome, delete/move/junction-follow the profile or assume backup alone can reproduce logged-in state. Owner has already completed a difficult phone-code login.
2. Reuse the browser via **original program** and explicit owned-target protocol. Only close tabs created and reliably owned by that operation. Human-owned, shared, ambiguous or authentication-challenge pages remain untouched and need accurate state reporting.
3. On program stop/timeout, distinguish app worker exit from Chrome exit. Normal drain/Stop can be slow; don't bypass live effects with blind force-kill. A model-window crash does not terminate CDP or its business process.
4. A replacement Executor first observes old PID, 9222 endpoint, tabs ownership and pending native actions; never runs a second conflicting app/profile. Original launch/idle-tab details are in [pinned policy](https://github.com/Horse-Hunter/INSO_Leo/blob/0db292fe0cb79d5177f436c3f8cc9b87c75288ee/docs/CDP_SESSION_POLICY.md) and [CEO handover](../control-room/CEO_HANDOVER.md).
5. Agent Computer Use was permitted 2026-11-14; this **does not** override the one-profile/single-owner rule, login challenges or per-order effect authorization.

**Do not expose cookies, tokens or credentials in evidence or chat.** Current physical profile may live under an older Research worktree; old directory names never justify deletion.
