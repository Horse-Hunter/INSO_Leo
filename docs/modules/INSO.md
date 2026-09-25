# INSO Module — V1.2 Stage 2A

## Scope

`src/inso` now contains additive fake-only safety contracts for shared browser
ownership, allowlisted purchase actions, and a separately bounded read-only
discovery protocol. It contains no live duplicate-history adapter, selector
registry for production controls, Save Data writer, or Save-and-Send capability.

## Session ownership contract

The launcher/composition root attaches Research to the configured CDP endpoint
and proceeds only when it exposes exactly one context. It never enumerates or
selects an existing tab. The root creates an `InsoSessionLease` with explicit
endpoint, browser, context and operation-page identities, and records
`APP_OWNED` or `REUSED`. Research receives only `InsoOperationAccess` and uses
lease-created child pages. A reused browser is disconnected from Playwright
after the cycle but is never closed; an app-owned browser closes only after its
child pages drain and the launcher confirms the cycle is drained. Stale or
mismatched identity fails closed.

This wiring restores the existing V1.1 INSO read-only Research source. It does
not add an INSO purchase writer, live discovery selectors, or any new external
write capability. Do not restore arbitrary CDP context/page enumeration to
regain availability.

## Write safety seam

The closed `WriteAction` enum includes only the explicitly allowlisted draft
actions through `SAVE_DATA`. There is no `SEND`, `SUBMIT`, `FINAL_SUBMIT`, or
`SAVE_AND_SEND` enum member or public method. `InsoDraftActions` exposes only
business-named methods; it resolves a unique exact selector within a verified
scope, rejects deny-listed identities, re-reads semantic role/name/text/stable
attributes before dispatch, and raises `SecurityViolation` on drift or
ambiguity. The production feature gate is unconditionally closed. The only
dispatcher exercised by tests is fake.

The current Stage 2A action boundary is not a production WRITE ALLOWLIST
approval. Page/current-order identity, current/target values, approved selectors,
read-back, Save Data recovery and evidence rules need independent Safety
Supervisor review. Save-and-Send remains prohibited in every stage.

## Discovery and UNKNOWNs

`ReadOnlyDiscoveryInspector` accepts only a protocol with metadata-reading
methods. It has no click, fill, clear, save, send, Sheets writer, or SMTP method.
Only deterministic fake input has been used; live discovery is not authorized.

Live endpoint/account/company/context identity, selectors, stable history record
identity and timestamp-tie policy, saved-record identity/read-back fields, AI
recognition page readiness/result DOM, and screenshot crop/redaction safety are
still `UNKNOWN`. Required control IDs must be named by an explicitly authorized
inspector call; missing, duplicate, or non-unique required controls keep its
report non-ready. The inspector remains fake-only and has not been run against
a browser or INSO.
