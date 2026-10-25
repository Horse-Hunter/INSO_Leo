# Task: Investigate INSO unavailable alert while Owner can log in

status: INVESTIGATION_COMPLETE
owner: Codex
created: 2026-10-25

Owner requests investigation first, no repair/deployment/restart. Read current
sanitized logs, process metadata, source and existing local CDP page metadata/
authentication-marker counts only. Do not navigate, click, refresh, query a model,
read customer/order/table contents, access credentials/cookies, send mail, change
business data or interrupt the running app/browser. No additional Playwright
client/driver attachment to shared CDP. No claim that login success proves
necessary business-read success. Report evidence vs UNKNOWN; no follow-on fix.

Known: current installed V1.4 matches Oct23 diagnostics release; on Oct25
00:53:45 INSO_WAITING_RECOVERY/V12Fault then01:08:46 and01:23:47
INSO_WAITING_RECOVERY/InsoAuthenticationError. Main PID55316 and its observer
are alive. Source manual-verification gate requires authenticated inquiry shell
and rejects any remaining INSO login/challenge tab. Need compare current state;
historical first cause is not captured in the generic log.

## findings / limitations

Owner reports mail41minutes earlier; observed local time about01:35–01:37
Asia/Shanghai, consistent with00:53:45 alert. No direct mailbox access performed.
Current CDP metadata read only:4page targets,2Google Sheets, one newtab and one
hostless page; zero yingsuo.alperp.cn pages. Query strings/titles/body/table data
omitted. No DOM read needed because no INSO target exists. Main and observer live;
logs show15minute INSO recovery attempts, not evidence of process exit.

Confirmed code gap: _defer_website_poll can classify AUTHENTICATION_REQUIRED as
manual INSO wait without proof of a visible human challenge. Once in that state,
_check_site_recovery only looks for an existing authenticated inquiry shell and
raises MANUAL_VERIFICATION_REQUIRED when none exists, leaving the wait set. It
does not create a fresh login/inquiry page. This can persist when a page has been
closed or the usable login is in another browser/session. The actual original
page lifetime and current in-memory manual-wait flag were not directly inspected;
repeated authentication errors and missing current page are consistent with this
path, not proof of the historical first failure reason.

Offline synthetic probe, no ProductionBackend construction: connected fake browser
with no INSO pages, manual wait already set; canonical recovery method raises
MANUAL_VERIFICATION_REQUIRED and retains wait. No credential/login/navigation/
business access. Shell requires business enquiry controls rather than mere home
or login availability. First00:53V12Fault drops detailed reason in safe runtime
log; original password/network/render/session failure remains UNKNOWN.

No source repair, tests added, restart, build/deployment, browser/tab operation,
mail sending, database/customer/credential reads or business data changes. Only
this investigation Task Packet added/updated. No live business verification or
claim that website itself was down. A follow-up repair requires Owner request.
