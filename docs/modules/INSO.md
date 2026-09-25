# INSO Module — V1.2 Stage 2A

## Scope

`src/inso` now contains additive fake-only safety contracts for shared browser
ownership, allowlisted purchase actions, and a separately bounded read-only
discovery protocol. It contains no live duplicate-history adapter, selector
registry for production controls, Save Data writer, or Save-and-Send capability.

## Session ownership contract

The launcher/composition root creates one `InsoSessionLease` for a cycle and
supplies explicit endpoint, browser, context, and page identity probes. The lease
records `APP_OWNED` or `REUSED`, the cycle ID, and each operation-owned child
page. Adapters receive only `InsoOperationAccess`; they can open and close their
own child page and cannot close the browser. Stale/mismatched endpoint, browser,
context, or child identity fails closed. An app-owned browser can close only
after child pages drain and the composition root confirms that the complete
cycle has drained. A reused browser is never closed by this module.

Production wiring is not present. Research's INSO history source requires an
injected verified operation lease and otherwise returns a fail-closed result.
Do not restore arbitrary CDP context/page enumeration to regain availability.

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
still `UNKNOWN`. These require separately approved read-only discovery before
live-capable work can be considered.
