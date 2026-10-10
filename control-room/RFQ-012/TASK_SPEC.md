# RFQ-012 Owner one-shot oldest unprocessed order
Status: REVIEW_REQUIRED / independent Review REQUIRED
Base: 671ef59770cbcb5202f9d2f918c5688d2ca6f451, RFQ-011 REVIEW_REQUIRED.
Authority: Owner updated requirements and three replies 2026-10-10.

Button click -> canonical Chrome maximized/foreground -> oldest unprocessed
INBOX order-mail (subject starts订单录单) -> existing strict Excel/package preflight
-> independently owned NEW sales tab/canonical guard -> header/details readback
-> mark locally filled -> end worker/re-enable button, retain protected tab.
Owner manually saves/submits/closes; program never saves/submits/uploads/deletes.
No polling or changes to inquiry/procurement execution. Old review tabs retained.
Successful full verification means locally processed; failures remain retryable.
Two prior samples are tests, not pre-seeded as processed; leave them for Owner's
button test. No live fill/SMTP test or deployment during this increment.
Mailbox read-only/PEEK, no flags; server-side order-subject search plus candidate
metadata only to choose receipt INTERNALDATE oldest (UID tie-break), then one body.
Local completion ledger stores opaque identity hashes only, independent ignored
runtime file, no production DB or new legacy notification enums. UIDVALIDITY-aware
UID/message identity; future conflicts/metadata failures stop without guessing.
Reuse existing ICNET/login/search/notification/9222 profile. No second pipeline.
Focused/full offline, Ruff/diff, sanitized report REVIEW_REQUIRED, commit/push.

Selection bound: server-side subject search, at most2000 matched candidates for
metadata ordering; exceeding cap fails closed rather than claiming oldest. No
body/attachment read for non-selected mail. Same Message-ID alias survives UID
validity reset; message-ID revision/reuse rules remain UNKNOWN. Tests do not seed
real sample completion records. Owner will test both samples with the new button.
