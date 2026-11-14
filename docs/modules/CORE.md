# Core — shared infrastructure contracts

**Owner:** `src/core/`, public dependencies only; no business orchestration.

- **Credentials:** use existing Core Vault/credential provider. Never copy tokens/passwords/private keys into Git, logs, screenshots, report fixtures or chat. API Service Account key remains outside repo under original Windows protection; do not create another project/account/token store.
- **MPN:** shared matching rules used by Research/INSO/Workflow. Native search uses **original full source MPN**, normalized/truncated suffix only where original explicit result-matching contract permits. No duplicate source-specific MPN policy.
- **Browser-call budget:** reuse existing bounded native CDP call implementation/public API and ownership/event-loop guards. Timeouts are **not** proof of server-side cancellation or absence of a write; propagate UNKNOWN/hold. Do not confuse a recovered source read with a confirmed purchase/quotation.
- **Process and resources:** canonical Chrome `9222`, original app mutex/process lifetime and protected runtime. GUI disappearance, agent quota exhaustion, log timeout or remote disconnect are not guaranteed stop; independently verify OS process and real effects.
- **Reusable infrastructure** must have a single canonical owner; use it rather than adding new auth, retries, browser clients or release paths.

[Original detailed Credential Provider API and native browser-call technical documentation](https://github.com/Horse-Hunter/INSO_Leo/blob/0db292fe0cb79d5177f436c3f8cc9b87c75288ee/docs/modules/CORE.md) · [CDP policy](../CDP_SESSION_POLICY.md).
