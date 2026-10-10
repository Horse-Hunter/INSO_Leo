# RFQ-012 Execution Log

2026-10-10. Entry/task/module/CDP navigation read. Starting branch clean and
local/remote671ef59770cbcb5202f9d2f918c5688d2ca6f451 equal. Owner explicitly changed
oldest-unprocessed semantics, success-after-fill receipt, prior samples not seeded,
and new independent tab while prior review tab remains. RFQ-011 stays historical
REVIEW_REQUIRED; no claim of CEO approval of the new increment.

Changes: GUI removes sample selector, returns idle button after worker; same single
serialized worker independent of inquiry state. Canonical CDP creates an owned
blank then restores/maximizes/readbacks window before reading mail. Existing guard
runs on each new order tab after existing full parse/package preflight. Prior tabs
not inspected/navigated/closed. Shared parking/default login already protect owners.
No-order response closes only invocation's unused blank, no exception email.

Mail selection extends same IMAP module/helpers/Vault; readonly INBOX, server
subject candidate search, prefix check, INTERNALDATE sorting, one PEEK body. FLAGS
before/after confirmed. Identity metadata failure/too many candidates stops.
Local completion SQLite stores only opaque hashes/time, atomic receipt writes,
no customer/PI/raw output. Alias for Message-ID handles UIDVALIDITY rollover;
future duplicate/revised Message-ID policy remains UNKNOWN. Max2000 order candidates
metadata checked, no whole mailbox body scan/export. Reopening app preserves receipts.
Failures don't mark; business exceptions retain existing safe notification wiring.
Window foreground occurs before committing success so a UI presentation failure
cannot falsely mark mail processed. Callback/transport data never copied to logs.

Offline synthetic tests: receipt ordering vs UID, one body only, successful skip,
restart, empty queue, retry without mark, FLAGS/UIDVALIDITY failure, old review page
not blocking next independent invocation, maximization before business, button
restored despite WAITING_OWNER and independent RUNNING inquiry. Phase3 fields,
ICNET and old notification behaviors preserved. Initial focused153 passed; broader
final focused299 passed in18.58s. Ruff and diff checks PASS. First full1812 passed/
1 skipped. Final full count follows after last attribution/receipt tests.
Safe tests use existing Python + bundled site-packages for Windows tzdata, no new
dependency installed. Real samples not read/filled/marked by this change; no genuine
SMTP exception induced. New button acceptance is left to Owner as requested.
No package build, production config/EXE edit, Save/submit/PDF/Google write/polling.

Final full1814 passed/1 skipped in71.09s; focused299 passed; Ruff/diff PASS.
Owner GUI can use the existing guarded source entry with reviewed release runtime
config selected via existing INSO_RUNTIME_ROOT, without editing that config/EXE.
No automatic button invocation or sample success receipt is seeded.
