# Current Task

Status: ACTIVE

Goal: Complete the V1.2 architecture/design spike and independent static Safety Review for seven-day INSO duplicate detection, post-Research routing, notifications/retry/alerts, controlled purchase-draft entry, GUI history, SQLite evolution, and explicit browser/session ownership. Do not implement production behavior in this stage.

Business Outcome:
- Give CEO and Safety Supervisor a reviewable design and stable public-contract proposal before implementation.
- Preserve V1.1 Research business rules and keep `release/v1.1` independently recoverable.

Acceptance:
- [x] `docs/V1_2_ARCHITECTURE.md` defines state/routing, DuplicateCheckResult, notification and purchase contracts, events/alerts, Sheets customer schema, browser/session lifecycle, WRITE ALLOWLIST, GUI seam, additive SQLite strategy, evidence path, test matrix, implementation plan and approval gates.
- [x] Design records confirmed Owner rules and exposes unresolved items as decisions/UNKNOWN.
- [x] No V1.2 runtime behavior, production access, real Sheet write, INSO action or business email was performed.
- [x] Design and task record are committed and pushed on `feature/v1-2`; no merge to main.

Constraints:
- Keep V1.1 Research price, MPN, stock, FX, retry and output rules unchanged.
- Do not operate a real INSO page, create/save/send a purchase inquiry, send business email, or modify Google Sheets.
- `保存并发送` is prohibited. Production Brand write stays disabled.
- Runtime evidence remains Git-ignored; no secrets or production data in Git, logs, or fixtures.

Done:
- Confirmed `origin/main`, `origin/release/v1.1`, and `origin/feature/v1-2` initially pointed to `be9d0a51d0375884dfa3e5e9e4317958899fdc75`; target branch included latest main.
- Built an isolated `feature/v1-2` worktree to protect unrelated dirty files in the original checkout.
- Read relevant V1.1 workflow, Research/INSO history, Sheets schema, launcher/CDP, GUI contracts and safety docs.
- Wrote the V1.2 architecture proposal and this task record.

Current:
- CEO architecture review passed on commit `60d6a84214389d09d1d566087711b619f520fbaf`.
- CEO product decisions are frozen in `docs/V1_2_ARCHITECTURE.md` by commit `763ffc0e7045eaee59f793cb09b58b5a246cc74d`.
- Independent static Safety Review is recorded in `docs/V1_2_SAFETY_REVIEW.md` and accepted by CEO at commit `72b60c72738ed19c05e010bb592d9301a6af74d3`.
- Safety verdict: `DESIGN_SAFE` approved for fake-only additive contracts/persistence. Blockers B1–B4 prevent live-capable browser/write/notification paths: unsafe CDP page/browser ownership; no proven Save Data unknown-outcome reconciliation identity; no layered Save-and-Send prohibition yet; raw exception text can reach durable state/GUI.
- Approved gate: `DESIGN_SAFE` only. The bounded `READ_ONLY_DISCOVERY_PLAN` is documented, but discovery execution is not approved in this stage and needs separate CEO/Owner authorization. `WRITE_IMPLEMENTATION_ALLOWED`, `REAL_SAVE_DATA_SMOKE_ALLOWED`, and `REAL_NOTIFICATION_SMOKE_ALLOWED` are not approved.
- Remaining UNKNOWNs include live INSO page/account/company/context identities and selectors; stable history and saved-record identity/read-back fields; lease compatibility with Research adapters; safe screenshot/redaction regions; AI-recognition MPN comparator; and backup/restore operator details.

Next:
- Main Programmer stage 2A is authorized for fake-only/additive implementation: resolve B1, B3 and B4; implement the durable B2 UNKNOWN_WRITE_OUTCOME/reconciliation state without enabling live Save Data; implement/test SQLite-consistent timestamped backup + additive migration on synthetic databases; implement contracts/events/alerts and deterministic safety tests. Keep V1.1 behavior and table semantics unchanged.
- AI-recognition comparator is frozen as `ai-mpn-v1`: Unicode NFKC + outer trim + ASCII uppercase, exact equality while preserving all internal separators/punctuation/whitespace; distinct policy name/version from `dup-mpn-v1`.
- Main may prepare, but must not execute, the bounded read-only discovery inspector/plan.
- Proposed discovery scope is restricted to read-only page/browser/context metadata, page identity, control semantics/safe selector candidates, history stable-ID/tie behavior, saved-draft identity/read-back feasibility, and screenshot crop/redaction feasibility. No clicks, field entry, AI action, save/send, Sheet write, SMTP, or data export. CEO/Owner must separately authorize target, session, and scope before execution.
- After CEO review, fake-only contract/persistence work may proceed under `DESIGN_SAFE`; live discovery, write implementation and either real smoke remain separately gated.

Blockers: B1–B4 remain blockers for live-capable behavior until resolved and independently re-reviewed. Stable live saved-record identity/read-back and screenshot safety remain UNKNOWN. No live discovery, live write, real SMTP delivery, or production smoke is approved.

Owner Decisions: Business rules and CEO architecture/safety decisions are frozen in `docs/V1_2_ARCHITECTURE.md`. Save-and-Send remains prohibited in every stage. Stage 2A fake-only/additive implementation is authorized; no live discovery or runtime/production action is authorized.

Branch: `feature/v1-2`

Last Good Commit: `be9d0a51d0375884dfa3e5e9e4317958899fdc75` (sealed V1.1 release baseline)

Safety Review handoff: `f38fc73cf788b818351db107c2e91e23503eabe9`; pending CEO review of `docs/V1_2_SAFETY_REVIEW.md` and its blockers/gates.
