# Task: Stop automatic Chrome focus and desktop activation

status: complete
review_status: REVIEW_REQUIRED
owner: Codex
created: 2026-10-08
updated: 2026-10-08

## authority / goal
Owner requests a new version because Chrome steals focus and occupies the desktop. Keep automated production browser operations unobtrusive through the existing background target creation primitive.

## scope / requirements
- Reuse src/research/cdp_pages.py; remove foreground context.new_page calls in quote input, quote cleanup, INSO login/recovery and dedicated session parking.
- Background targets in an existing context do not activate/restore its window. If no page exists, explicitly create the first window minimized via supported CDP parameters; never switch profile, headless browser, cookies or CDP endpoint.
- Never fall back to foreground creation after protocol failure; retain existing failure handling and protected manual-auth pages.
- Explicit Owner one-click manual-login presentation remains available; automatic maintenance remains non-presenting.
- No persistent-window hider or focus-restoring timer; do not hide a window the Owner deliberately opened.
- Offline regression/full/Ruff and candidate BuildOnly/frozen/scan. Read-only local CDP version/protocol inspection permitted; a no-business blank-target focus probe is also permitted only with no running V1.3 and an existing single blank page, closing only probe-owned pages; no live login, purchase, mail, Sheets writes or production polling. Do not replace a running release or deploy a new unreviewed hash.

## acceptance
- [x] Quote input and last-tab cleanup, INSO fresh/recovery login, and parking blank use the shared background creator; no production launcher context.new_page remains.
- [x] Empty-context first target requests background + newWindow + minimized directly; no hide-after-show timer.
- [x] Failure never falls back to foreground creation. Existing protected-auth pages and fail-closed decisions retained.
- [x] Focused and full offline regressions; BuildOnly, release scan, frozen self-check and idle GUI PASS.
- [x] Actual fixed Chrome supports createTarget.windowState; three idle blank-target cycles preserved foreground, minimized bounds and original blank page.

## completion / CEO report
- Production code commit: `2e5387297d428ae836f4c10a04af7651ca491e67`.
- Root cause: `context.new_page()` remained in quotation input, quote last-tab cleanup, INSO login creation and shared-CDP parking, bypassing the existing background target path. Only Research/login-sweep paths were previously using the shared primitive.
- Files: src/launcher/browser_bootstrap.py, src/launcher/google_quote_update.py, src/launcher/inso_session.py, src/research/cdp_pages.py; launcher/research regressions and shared synthetic CDP fixture.
- Existing Chrome windows retain their state through background target creation. The first page in an empty context requests a minimized window at creation, avoiding a foreground-create-then-hide strategy. No focus-restoring loop, persistent window hider or browser/profile replacement introduced.
- Existing explicitly initiated manual one-click login failure presentation is preserved; automatic keepalive still sets present_failures=False. CAPTCHA/OTP pages remain available and are not closed or hidden by this repair.
- One existing dashboard DB-readonly test exposed a WAL-checkpoint byte-comparison false positive in full regression. Test now compares the entire SQLite logical schema/data via iterdump; production statistics implementation is unchanged. Notification/hold/episode no-mutation coverage remains.
- Focused: **201 passed**. Full safe/offline: **1576 passed / 1 skipped** (existing Windows symlink capability skip). Ruff and git diff --check PASS.
- V1.3 BuildOnly / release scan / frozen dependency self-check / isolated frozen idle GUI PASS.
- New candidate SHA256: `6A9D19DA23406C11AF810A19BBEFAAB0D89A58683A0B66E1E993FB0B2D8BE25A`.
- Formal EXE remains reviewed DB11A02BCB4929EA9B45A973AD086A163D4FE1ED09AF72ED9AB0C222A8819E5E, unchanged; no deployment performed.
- Live narrow probe: fixed 127.0.0.1:9222, no running V1.3, existing single blank page. Three probe-owned blank pages created/closed serially. All six post-create/post-close foreground samples matched; Chrome bounds unchanged; window state minimized before/after; one original blank page remained. No browser launch/close/window activation, business navigation, credentials, purchase, quote writes, SMTP or polling.
- Protocol evidence: local /json/protocol confirms windowState support; official ChromeDevTools browser_protocol.json documents windowState requiring newWindow. Reference: https://raw.githubusercontent.com/ChromeDevTools/devtools-protocol/master/json/browser_protocol.json
- Limits: live probe covers existing minimized Chrome and blank-target lifecycle, not actual purchase/quotation websites or browser cold launch. Fixed Chrome was not shut down or a second Chrome created to test cold startup; first-window behaviour is covered by protocol support and offline regression. No claim of universal OS focus immunity.
- Untracked evidence: main .tmp/v13-background-build.log, v13-background-frozen-report.json, v13-background-focus-probe.json. Only sanitized summary included here.
- State: REVIEW_REQUIRED; independent CEO approval and explicit approved-candidate deployment remain pending. Audit/report commit is local; no new remote upload is included without authorization.

## Owner release authorization update
Owner subsequently explicitly authorized direct deployment of this verified candidate without waiting for another CEO Review. See tasks/2026-10-08-chrome-background-deploy.md for completed controlled deployment and protection checks. This authorization does not change or invent a CEO independent Review verdict.
