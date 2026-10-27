# V1.6 page concurrency — stage C safety design

Status: **DEFERRED implementation / NOT_VERIFIED actual webpage overlap**.
This document is independent of P1 corrections. No production browser was
attached, pages opened, profile copied, locks removed or concurrent mode enabled.
Independent module deadlines and SMTP overlap are not browser parallelism.

## Reuse audit and concrete blockers

Existing `research.cdp_pages.new_background_page`, owner marks, preserved-human
surfaces, BrowserHandle fixed-thread lifecycle and existing source adapters are
the starting point. All data, matching, pricing/FX/stock, date and outbox rules
remain unchanged. Source inspection found these incomplete parallel contracts:

1. `new_background_page` uses context-wide `expect_page` and takes the first
   pending page. Two CDP clients attached to the same context can receive each
   other's page events. It does not correlate the resulting Page to the exact
   Target.createTarget targetId. A site tag alone is not unique per task. The
   current helper therefore cannot yet prove that a concurrent caller navigates
   and closes only its own target. This is a source-derived risk, not a measured
   production incident or actual overlapping-page experiment.
2. Existing adapters can intentionally find the first same-URL context page
   when navigation is disabled (IC.net/HQ). Concurrent jobs must not use that
   branch or borrow another task's page; authenticated ownership must be explicit.
3. Shared service composition/providers, source observers and recovery callbacks
   capture the backend actor and its sync Playwright/session state. Running those
   closures on other threads would violate current ownership, despite P1 scopes
   making same-thread nesting safe. P1 scopes are not cross-thread isolation.
4. INSO operation leases and native Google grid/script settlement are exclusive.
   Different tabs do not make these session/write responsibilities parallel-safe.
   Source login and per-site pacing may also be shared across authenticated tabs.
   Independent adapter instances must not silently multiply the request rate.
5. Existing SQLite claims protect their own task/mail commands. Cross-module
   per-order exclusion still needs one common verified source key for inquiry,
   quotation and independent TP identities; separate inquiry_id/tp_task_id locks
   do not establish that property. Never fabricate legacy inquiry IDs to fix it.

The installed sync implementation stores an owning event loop and greenlet in
SyncBase and switches back to that dispatcher on every call. BrowserHandle
already queues client teardown to its creating thread. No sync Page/Browser/
Context/Locator/Session may cross a worker boundary.

## Options and minimum viable direction

| Option | Reuse | Cost/risk | Decision |
| --- | --- | --- | --- |
| Bounded independent sync client actors, same existing9222 Chrome/context | Existing source adapters and non-owned BrowserHandle; each client created/used/stopped on one fixed actor | Add exact target correlation, verified per-order leases, per-site auth/pacing exclusion, immutable result/event handoff; no backend closures shared | Preferred incremental direction, not implemented/enabled |
| One async event loop | Natural page operation overlap | Existing synchronous adapters, native Sheets/INSO guards and error/recovery callbacks require substantial conversion; mixing nested sync calls into that loop is unsafe | Defer broad migration |

These are source-based cost estimates, not measured throughput benchmarks.
Do not introduce a second profile, Chrome launcher, daemon, credential system,
business ledger or independent browser-management framework. Extend the existing
WorkflowRuntime and page factory; source parsers/collectors stay canonical.

## Proposed resource and ownership contract

- Original browser actor exclusively owns INSO/Google and all external writes.
  Only independent authenticated market read-only queries are candidates for
  off-thread overlap. INSO protected session remains exclusive at all times.
- Start with a finite resource bound (e.g. two market-query slots, not an order
  throughput cap), with a separately accounted preserved-human-page budget.
  Fair waiting is on resource availability; no artificial batch release limit.
- Each actor constructs and tears down its own sync client, attached to the
  already-running canonical9222 endpoint. It never launches or closes Chrome.
  No Page/Context/Browser or mutable adapter instance is handed across actors.
- Runtime grants source-based order leases before dispatch, using the existing
  verified spreadsheet/sheet/row identity, regardless of requirement type.
  Same-order jobs queue. Durable business/SMTP permissions still revalidate on
  the existing owner path immediately before effects; a lease is not authority.
- Factory creates one task-unique marker and correlates **that exact targetId**
  before navigation. Mismatch/timeouts fail closed. Closing uses an exact lease
  target and rechecks preservation flags; never enumerates and cleans others.
- Site login/session changes remain serialized with existing site pacing and
  manual verification. Already-authenticated independent read-only pages may
  overlap only after those contracts are proven; auth failure blocks that site.
- Workers return immutable existing source results and explicit task/module/cycle
  progress events to the original scheduler. They never mutate backend global
  identity/pause/cache state or publish a result under another module's context.
- Keep progress/timeline in existing bounded observation/logging structures.
  Concurrent cards must retain independent active stages; current serial focus
  behavior cannot be reused unchanged for genuinely concurrent browser queries.
- Shutdown stops admissions, drains bounded reads with existing timeouts and
  closes only owned unprotected pages/clients on their actor threads. Unknown
  external outcomes retain existing durable protections. No thread termination.

## Required verification before claiming parallel capability

1. Exact-target race tests: interleaved same-site and different-site page events,
   unrelated human tabs, actor/client identity and owner-only cleanup.
2. Same-source-order exclusion across all three business task kinds; independent
   orders can proceed, no new IDs or replacement ledger.
3. Actual browser timeline: job/cycle/owner token, native thread identity,
   navigation/request start and finish, exact target proof. Two request intervals
   overlap; same-order conflict intervals do not. Callback or sleep overlap is
   explicitly insufficient. No credentials/customer content in evidence.
4. Auth change, slow site, timeout, cancellation, preserved manual page, SQLite
   fault, cleanup failure, UNKNOWN/SENT and ordered shutdown fault cases.
5. Finite tab/client bounds, child-process CPU/memory, and recovery to baseline.

Current command forbids production browser access and replacement. Existing
factory/composition cannot safely provide the proof above; inventing a second
test profile/Chrome would violate the protected-session constraint. Therefore
no guessed or callback-only parallel implementation is delivered as production
capability. A future dedicated safe browser acceptance window is needed after
the ownership/composition changes; it must not commandeer the live session.
No fabricated real-browser timeline is included. C remains explicitly open.
