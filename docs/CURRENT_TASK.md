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
- LCSC repair is committed and pushed: reuse an existing LCSC/JLC CDP tab when present, do not close it, do not mistake a public result page's visible login control for a failed search, and lazily use the existing Core Vault `szlcsc.com` credential for one normal account-login recovery. `passport.jlc.com` is only the SSO redirect host, not a second Vault identity.
- IC.net live recovery is now verified using the existing Vault login: LM358 returned 49 result rows after one normal relogin.
- HQEW fix is committed and pushed: its verified same-site `/yunquote?toUrl=...` redirect is accepted only when the declared model URL is exact. Live LM358 smoke read 19 offers.
- Bom.Ai recovery is committed and pushed: a visible normal login entry opens the account-login modal, uses only the configured selectors and existing Core Vault login once, verifies it closed, and re-runs the original model page once. A changed UI and an interactive challenge are explicit failures.
- HQEW and Findchips now reject a real login form as `LOGIN_REQUIRED`, rather than sending it to a quote parser. Live LM358 smokes read 19 HQEW offers and 287 Findchips offers; Bom.Ai returned its normal LM358 result page and LCSC public search returned LM358.
- Phase B live acceptance: Core Vault metadata confirms configured `szlcsc.com`; its SSO page showed `已登录账号 + 进入系统`, then a temporary same-context LM358 search returned the live result document without challenge. Bom.Ai's temporary controlled context showed the ordinary login entry, completed a normal Vault login, dismissed its login UI, reloaded LM358, and the retained session parsed 48 price records.
- The hotfix release was rebuilt at `dist/INSO_V1.1/INSO_V1.1.exe`; frozen `--self-check` and `--diagnose-vault` both exit 0 using a local junction to the existing ignored V1.1 runtime. The desktop automation surface did not expose the GUI window, so the Explorer-click/full GUI-to-Excel acceptance remains a manual final check.

Next:
- Owner opens the newly built EXE from Explorer and runs one full Research cycle, then confirms all five source results entered `调研价格.xlsx`. Do not copy credentials from screenshots or create a second credential file.

Blockers:
- The current automation session cannot access the packaged application's native GUI window, so it cannot click through a full production cycle or inspect the resulting Excel/GUI state. All code, frozen startup checks, credential readiness checks, deterministic tests and per-site live acquisition checks are complete.

Owner Decisions:
- Branch/worktree: `hotfix/v1-1-research-stability` from `be9d0a51d0375884dfa3e5e9e4317958899fdc75`.
- External scope: read-only public LM358 search only; never bypass CAPTCHA/OTP/device verification.

Branch: hotfix/v1-1-research-stability

Last Good Commit: a52a1231dc00fbc38373b6f044f952befc52e0f0
