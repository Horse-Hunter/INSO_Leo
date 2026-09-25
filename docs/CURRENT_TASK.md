# Current Task

Status: READY_FOR_CEO_REVIEW

Goal: Deliver the V1.2 architecture/design spike for seven-day INSO duplicate detection, post-Research routing, notifications/retry/alerts, controlled purchase-draft entry, GUI history, SQLite evolution, and explicit browser/session ownership. Do not implement production behavior in this stage.

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
- Design is ready for CEO and Safety Supervisor review.
- CEO decisions and remaining UNKNOWN items are listed at the end of `docs/V1_2_ARCHITECTURE.md`.

Next:
- CEO resolves product/business contract decisions; Safety Supervisor reviews production write and browser/session risks before any live write implementation or smoke.

Blockers: NONE for this design spike.

Owner Decisions: Review the decisions listed in `docs/V1_2_ARCHITECTURE.md`; no runtime/production action requested in this stage.

Branch: `feature/v1-2`

Last Good Commit: `be9d0a51d0375884dfa3e5e9e4317958899fdc75` (sealed V1.1 release baseline)
