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
- IC.net fix is committed and pushed: the parser accepts the current `#resultList` container, and the CDP client performs one Vault-backed relogin before re-running the search. Deterministic valid-session, expired-session and no-provider cases pass. Live LM358 smoke reaches the normal login page and returns `LOGIN_REQUIRED` because the existing Core Vault has no IC.net login; no CAPTCHA or failure was misclassified as no-result.
- Live discovery: LCSC currently renders normal public search results while its visible login control remains present; the current client incorrectly treats that control as `AUTHENTICATED_SESSION_REQUIRED`.
- Live discovery: HQEW redirects the historical URL to `/yunquote?toUrl=...`; its rendered page still contains parseable `input.list-data` offers, while the current exact-path check rejects it.

Next:
- Obtain the one approved IC.net Chrome login or add its ordinary login to the existing Vault, then verify the actual result rows. Continue LCSC and HQEW acquisition repairs.

Blockers:
- IC.net live completion requires one normal Owner login in the approved CDP Chrome or an existing Core Vault IC.net login.

Owner Decisions:
- Branch/worktree: `hotfix/v1-1-research-stability` from `be9d0a51d0375884dfa3e5e9e4317958899fdc75`.
- External scope: read-only public LM358 search only; never bypass CAPTCHA/OTP/device verification.

Branch: hotfix/v1-1-research-stability

Last Good Commit: f8781a7b4a2e31a931206fdb318371300461aeac
