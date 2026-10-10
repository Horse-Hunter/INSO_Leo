# RFQ-009 Execution Log

## Baseline and reuse
Read root docs/AI_START_HERE.md, task protocol, module index/product baseline,
then current V1.3 AI_START_HERE/AGENTS/module/Core/GUI/launcher/review evidence.
Latest independently reviewed source located: df64762. Later branch 1bf4ee0
contains Owner-deployed but REVIEW_REQUIRED increments. Created isolated
D:/Program_Leo/INSO_Leo/.worktrees/v1-4-order-mail-inspection on
codex/v1-4-order-mail-inspection at df64762. Existing dirty root and V1.3 trees
preserved. No stale handoff consumed; no other worktrees removed.

Reused existing Core Credential Provider, encrypted Vault update API, GUI shell,
GuiBackend optional-capability pattern, launcher locking/background threads,
openpyxl. No prior IMAP receiver found. Added minimum order_mail integration
boundary; launcher assembly and sanitized text contract, no workflow state.
No new dependencies installed. No second config, credential store or launcher.

## Live evidence (sanitized)
Initial provider reported CredentialSiteNotFoundError. Opened Vault folder/manager
at Owner request. Owner explicitly authorized configuration. Stored supplied
secret via Read-Host -AsSecureString and existing Set-InsoVaultCredential.
The secret was never in shell command text, source, log or repo files.
Only masked terminal output and completion status emitted.

Canonical inspect_order_mail path connected to QQ IMAP SSL993 with validated TLS.
EXAMINE read-only INBOX confirmed via is_readonly; UID SEARCH restricted by
SINCE 30 days and last200 sequence range; newest5 candidates maximum. Decoded
subject must start exactly with 订单录单 before BODY.PEEK[]. RFC822.SIZE guard
20MB; archive expansion80MB; sheet100k-cell and attachment20 inspection caps.
All candidate FLAGS recorded and compared after reads; unchanged in each check.
Only UID SEARCH/FETCH + LOGIN/EXAMINE/LOGOUT commands; no CLOSE/STORE/COPY/MOVE/
EXPUNGE/reply/SMTP. Two matching messages, two attachments each. Structure in
FINAL_REPORT; no raw IDs, subjects, names, values, body or attachments retained.
Sanitized local summary only at ignored .tmp/order-mail-sanitized.txt.

PDF live analysis used preinstalled bundled pypdf via ephemeral interpreter
sys.path append. No dependency installation or machine config edits. Parser
uses text layer only to classify fixed contract vocabulary, never returns text.
GUI ordinary runtime reports UNKNOWN if parser absent; XLS parser absent and
explicitly UNKNOWN. No production writes/business work during live check.

Actual GUI/backend flow ran with isolated .tmp/gui-live-isolated runtime root,
no production config, workflow DB or inquiry worker. Button invoked canonical
receiver and displayed sanitized report. Initial geometry observation happened
before CTk window realization; it was not treated as final layout acceptance.
New real-Tk regression waits for realized widgets, checks width>100, equal width,
non-overlap/same row, main-thread result presentation and disabled busy button.

## Verification
- Focused pre-layout: 128 passed; safety/GUI/login compatibility.
- Initial full default Python: collection blocked by pre-existing missing tzdata.
- Reused installed bundled site-packages, no installation: 1582 passed/1 skipped,
  one new Tk geometry test failed because the window was not yet realized.
- Fixed only the test realization wait; focused new tests12 passed.
- Ruff src/tests and diff --check PASS.
- Final full: 1583 passed / 1 skipped in 69.74s. Command: normal Python3.12
  with ephemeral sys.path append to preinstalled bundled Lib/site-packages;
  pytest.main([tests, -q, --basetemp=.tmp/pytest-all-v14-final]).
- Final Ruff src/tests PASS; staged diff --check PASS; staged file inventory
  reviewed. git check-ignore confirms local sanitized summary/runtime excluded.
- Actual realized equal-width Tk layout regression PASS, no business side effects.
- Final status: REVIEW_REQUIRED; local development commit only, no push/deploy.

## Changed scope / remaining UNKNOWN
GUI app/contracts, launcher one-shot worker/close join, order_mail module/tests,
module boundary and scoped task/Control Room records only. SMTP, INSO, Sheets,
workflow state/config/release/production runtime untouched. No V1.4 packaging,
deployment, external push or subsequent business task performed.
Business mapping, global subject contract grammar, customer identity/currency/
tax/rounding/dedup/revisions remain UNKNOWN. Executor does not issue CEO PASS.
