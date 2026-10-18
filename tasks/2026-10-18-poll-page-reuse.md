# Reuse owned pages within one poll, with verified stage entry

status: REVIEW_REQUIRED
owner: Codex
created: 2026-10-18

## Owner scope and acceptance
Reuse one owned INSO quotation page across quotation queries, and one owned
Google spreadsheet page across inquiry/quotation operations in a normal poll.
Every stage must explicitly establish/verify its own target menu, worksheet,
query and identity. An unexpected prior menu/failure must never feed a later
write. Reuse existing session/login/navigation/query/write code; no business
rule, price, retry, identity or notification changes. Per-call behavior outside
a poll remains compatible. Normal poll completion closes its operation pages;
existing parking leaves one blank page when no protected Owner pages exist.
No business page is retained across normal polls. Owner further clarified:
quarantine an unsafe prior page; the next stage gets its own new page using the
existing login/navigation, then existing exception policy if that attempt fails.
Never blindly continue on the old page or add a login/retry loop. This does not
override existing global/security faults or permit automated human verification.
Human review/authentication,
unsaved edits and unresolved scripts keep existing safety protection, rather
than closing or reusing unsafe surfaces. Parallel sales entry remains separate.

## Reuse audit / implementation boundary
V13QuotationOperations currently opens/closes a fresh lease per query; existing
InsoSessionGuard can reopen/prove a specified page and attach can pin a fresh
lease to that same owned page. Existing quotation history queries fill/read
their target, select/check the lower procurement tab, and match fresh responses.
GoogleQuotationUpdateActions owns native navigation/auth/script settlement and
close; GoogleSheetsWebService selects/checks worksheet/gid, schema and readback.
Extend these existing owners with thread-local, poll-bounded retention, not
another navigation/login/reader implementation. Backend owns poll lifetime.

## Verification and limits
Focused synthetic tests: multi-query/multi-sheet reuse, wrong menu recovery or
safe stop, auth preservation, dirty/pending script exclusion, cleanup on error,
next-poll fresh pages, and separate threads/sales pages. Full offline regression
with real network/CDP/process launch blocked. No credentials/runtime/production
CDP, real Sheets/INSO operations, packaging or deployment in this task.
Preserve local HEAD/index/dirty work. Update this packet with results; normal
push to existing V1.4 branch, REVIEW_REQUIRED. Remove only task-owned temporary
test artifacts in this task. Live UI acceptance remains UNKNOWN.

## Implementation / offline evidence
Extended existing GoogleQuotationUpdateActions with a thread-local poll page
pool; each borrower rechecks document/auth/ownership and pending/dialog/save
state. Wrong or unknown prior surfaces are quarantined; the next phase opens a
fresh owned page. Existing worksheet selection/schema/identity/readback and script
input exclusion remain mandatory. GoogleSheetsWebService lazily pins its client
inside existing per-read exception boundaries; no eager startup bypass of retry.
No cached source rows, extra download retention or business rules introduced.
INSO quotation operations retain one owned page across both worksheets in the
poll; every new query reuses the original InsoSessionGuard login/native-menu
proof and pins a new lease. A lost old menu is not navigated blindly: a fresh
page is attached instead. Existing history query fills/readbacks query and
verifies lower tab plus fresh response. Reattach failures preserve the old page.
Poll-final cleanup reuses existing close and parking; normal business pages close,
protected sales/auth/unsaved/pending-script pages remain untouched. Per-call
manual/other-thread behavior remains unchanged. Actual backend scope wiring is
covered for normal, purchase-only pause and global-stop paths.

Final full offline run: **2189 passed, 1 skipped, 72.91s**. Production endpoint,
9222, actual browser launch/close blocked; only ephemeral test-owned loopback,
synthetic Vault DPAPI, local read-only Git archive and no-browser Playwright
driver tests allowed. Focused 229 PASS; after adding backend scope assertions,
63 focused PASS; after preserving physical failed-query reset before the existing
120-second wait, 85 focused PASS; Ruff PASS. Full combined regression will also
cover that final reset boundary in the follow-up Google-read fix. An initial over-broad test guard blocked legitimate
synthetic/local tests and sandbox Tcl; those preliminary failures were corrected
in the test runner/environment, never by weakening production safety code.
No live CDP, credentials, runtime writes, business actions, SMTP, package or
EXE overwrite. Live UI/performance acceptance remains UNKNOWN. Task-owned test copies/runner retired in this same work cycle with the
Owner-requested Google-stop diagnosis/regression. All unrelated dirty work kept.

Final combined regression after physical failed-query reset and Google recovery:
**2205 passed, 1 skipped, 74.47s**. Targeted failed-page retirement/recovery:
117 PASS. Ruff PASS. Normal source/script operations retain one page; failed
phases retire their page before a fresh next attempt. Ordinary failed read pages
close, while verification/unsaved/pending or unknown page state is preserved.
Code implementation first published as 399eab9943685cb005c7100667271c066174912b;
final follow-up evidence accompanies the Google recovery commit. Both scopes
remain REVIEW_REQUIRED, with no package/deployment or actual business replay.
