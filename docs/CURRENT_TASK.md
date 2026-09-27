# Current Task

Status: ACTIVE

Goal: V1.1 Research Stability Hotfix — make the read-only Research clients follow the same authenticated Chrome paths that an Owner can use normally.

Business Outcome:
- IC.net, LCSC and HQEW must not report ordinary session/page-shape changes as a generic unavailable site.
- Browser identity remains in Owner-approved Chrome/CDP; ordinary session expiry may use only the existing Core Vault login and stops for CAPTCHA/OTP/device verification.

Acceptance:
- First repair IC.net after live discovery, then LCSC and HQEW; preserve all accepted price, stock, brand, Excel, Workflow, Sheets and GUI rules.
- Each repair has deterministic tests and a limited live, read-only LM358 smoke when the site is accessible.
- No new credential store, browser framework, external write, secret, cookie, token or customer data is committed.

Current:
- IC.net fix is committed and pushed: the parser accepts the current `#resultList` container, and the CDP client performs one Vault-backed relogin before re-running the search. Deterministic valid-session, expired-session and no-provider cases pass.
- LCSC repair is committed and pushed: reuse an existing LCSC/JLC CDP tab when present, do not close it, and do not mistake a public result page's visible login control for a failed search. A new background tab is still initialized and closed only when no site tab exists.
- IC.net live recovery is now verified using the existing Vault login: LM358 returned 49 result rows after one normal relogin.
- HQEW fix is committed and pushed: its verified same-site `/yunquote?toUrl=...` redirect is accepted only when the declared model URL is exact. Live LM358 smoke read 19 offers.

Next:
- Owner completes the existing LCSC/JLC SSO login once in the approved CDP Chrome, then continue the LCSC live smoke and remaining Research source regressions.

Blockers:
- LCSC/JLC session is at its normal SSO login page and no LCSC Vault credential exists. It requires one normal Owner login; no CAPTCHA/OTP bypass will be attempted.

Owner Decisions:
- Branch/worktree: `hotfix/v1-1-research-stability` from `be9d0a51d0375884dfa3e5e9e4317958899fdc75`.
- External scope: read-only public LM358 search only; never bypass CAPTCHA/OTP/device verification.

Branch: hotfix/v1-1-research-stability

Last Good Commit: f8781a7b4a2e31a931206fdb318371300461aeac
