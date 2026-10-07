# Task: RFQ-004 V1.3 INSO quotation read

status: complete
owner: Owner/CEO (requirements); Executor (implementation)
created: 2026-10-07
updated: 2026-10-07

## problem / goal
Implement the independent read-only quotation stage for source status 发给采购.
The complete unchanged Owner request is control-room/RFQ-004/TASK_SPEC.md;
that file owns requirement meaning and COORDINATION.md owns Review status.

## current_facts
Stable reviewed baseline c8d514ed7aff2542dda685d476cd6e92ff97a85d.
Existing lower native full-pagination query, fixed-CDP authentication, Sheet
schema/relocation and workflow ledger must be reused. Identity contains original
row position: resolve original ledger identity rather than deriving another ID.

## scope / requirements
Exact status read, original inquiry_id/source identity, fresh owned tab per row,
full lower-history read, inclusive rolling Shanghai 72h latest selection,
raw fourteen display fields, normal NO_RECENT_QUOTE, shared bounded retry and
GLOBAL_STOP, protected human-needed page. No normal row cooldown.

## non_scope
Google/INSO/SMTP writes, Apps Script, scheduler/GUI/mail integration, packaging,
V1.2 deployment replacement, live production access or final CEO Review.

## acceptance / verification
All 27 Owner offline acceptance categories in canonical Task Spec. Fixed aware
ZoneInfo clocks; fake 180-second waits; focused/full pytest, Ruff, diff check,
scoped commit/push and local/remote equality. Details/evidence in Execution Log.

## completion
status: complete (Executor delivery; independent CEO Review still required)
changed: see RFQ-004 Execution Log / Git diff
verified: see RFQ-004 Execution Log
limitations: live display/header layout and actual operational quotation read
remain UNKNOWN. Orphan/ambiguous source identity fails closed without new ID.
