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
- LCSC repair is committed and pushed: reuse an existing LCSC/JLC CDP tab when present, do not close it, do not mistake a public result page's visible login control for a failed search, and lazily use `passport.jlc.com` through the existing Core Vault for one normal account-login recovery. A missing optional JLC credential returns `LOGIN_REQUIRED` without blocking Research startup.
- IC.net live recovery is now verified using the existing Vault login: LM358 returned 49 result rows after one normal relogin.
- HQEW fix is committed and pushed: its verified same-site `/yunquote?toUrl=...` redirect is accepted only when the declared model URL is exact. Live LM358 smoke read 19 offers.
- Bom.Ai recovery is committed and pushed: a visible normal login entry opens the account-login modal, uses only the configured selectors and existing Core Vault login once, verifies it closed, and re-runs the original model page once. A changed UI and an interactive challenge are explicit failures.
- HQEW and Findchips now reject a real login form as `LOGIN_REQUIRED`, rather than sending it to a quote parser. Live LM358 smokes read 19 HQEW offers and 287 Findchips offers; Bom.Ai returned its normal LM358 result page and LCSC public search returned LM358.

Next:
- Owner adds the existing normal JLC account to the canonical Core Vault under `passport.jlc.com`, then continue the LCSC expired-session recovery smoke. Do not copy credentials from screenshots or create a second credential file.

Blockers:
- `passport.jlc.com` is absent from the canonical Core Vault. The code and deterministic recovery test are complete, but a real expired-session login smoke cannot run until Owner creates that existing-Vault entry. No CAPTCHA/OTP bypass will be attempted.

Owner Decisions:
- Branch/worktree: `hotfix/v1-1-research-stability` from `be9d0a51d0375884dfa3e5e9e4317958899fdc75`.
- External scope: read-only public LM358 search only; never bypass CAPTCHA/OTP/device verification.

Branch: hotfix/v1-1-research-stability

Last Good Commit: 33484a030187c3708924afbfdee7147afdda5b3c
