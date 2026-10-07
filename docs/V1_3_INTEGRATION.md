# V1.3 integration / local deployment

RFQ-006 extends the same ProductionBackend poller. One cycle runs all V1.2 worksheets
then all V1.3 worksheets, then the existing interruptible 900-second wait. No overlapping
business worker. V1.2 local pause leaves V1.3 polling; shared faults stop both.
V1.2 reviewed row cooldown/restart/one-click submission behavior remains canonical.
V1.3 read results settle through RFQ-005 immediately, with no ordinary row cooldown.

## Production configuration
Use the existing runtime/production.json. V1.3 frozen releases always require the
quotation configuration; source composition enables it with v13_enabled=true.
No new credentials/configuration files. Required quotation_input keys:
- gid: exact string from metadata for title 报价输入
- header_row, input_row, first_column: verified positive integer geometry
Missing/null geometry is QUOTE_INPUT_CONFIGURATION_REQUIRED (GLOBAL_STOP before polling).
Metadata and exact14 headers are revalidated by the reviewed writer before business writes.
No popup/button selector is claimed accepted by offline tests.

READ_ONLY_LIVE_ACCEPTANCE 2026-10-07: exact target count1, gid489913321; A1:AZ40
returned zero rows (actual grid limited range to A1:Z40). Header/input/first-column
UNKNOWN. No inferred header row or guessed blank input row. Button/popup/Script/session
behavior UNKNOWN. Fixed CDP endpoint reachable; canonical production profile unchanged.
BLOCKED LIVE CONFIG. Owner must establish/confirm actual input geometry. A controlled
single-order live acceptance requires separate Owner authorization before any quote
input write, update click or Script run.

## Durable state / rollback
V13 holds share the existing workflow DB, with a single additive table. Final ROW_FAILED
only; no-quote and interrupted unfinished quote operations do not create holds.
Holds reconcile by snapshot/identity with safe relocation. Deleted/ambiguous sources
retain the hold/log; row number alone cannot close it. 采购已报价 closes the hold.
Notification enqueue is recoverable after a crash between hold and outbox commits.
Existing notification ledger/SMTP is reused; operational notifications have NULL inquiry
rather than invented business identities. Operational pending/sending/retry statuses
are ignored by the old V1.2 worker, preserving rollback. Existing business commands remain
unchanged. Migration uses a verified backup, one transaction and unchanged V1.2
user_version; new code still accepts original V1.2 schema. No history table is dropped.

V1.3 has its own runtime/config files using the same production.json/research.json format.
V1.2 config files remain byte-for-byte unchanged. Existing SQLite/history/notification/OAuth/
profile/research output are referenced through resolved absolute paths, without copying a
diverging workflow database. Existing V1.2 logs are retained; V1.3 logs use its own runtime.
V1.2 EXE remains installed. Single-instance mutex is intentionally shared between versions.
Do not run both production GUIs/cycles. The bounded --idle-self-check constructs the real
hidden dashboard with Start disabled, never runs business workers, and exits; it can verify
widgets while the Owner's original V1.2 GUI remains open. It is not a live-business acceptance.
