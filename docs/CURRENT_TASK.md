# Current Task — V1.2 pre-save acceptance

**Stage:** PRE_SAVE_READY
**Production Write Gate:** CLOSED

## Final facts

- Shared INSO runtime: READY. Approved Chrome/CDP, Core Vault Site ID
  `yingsuo.alperp.cn`, ordinary recovery, and a unique authenticated shell are
  one launcher-owned path.
- Runtime regression tests: PASS. Field write/read-back, exact one-time
  submit, origin/control/shell ambiguity, manual verification, and secret
  redaction are covered.
- `PlaywrightParentProductFields`: READY. It requires the verified origin,
  unique named parent frame and unique visible/enabled PartNo, Brand and Qty
  inputs with immediate exact read-back.
- `PlaywrightReadOnlySaveReconciler`: READY. It uses the session lease, settled
  exact history and stable BillID/PENO/detail checks; multiple candidates are
  AMBIGUOUS and all non-authoritative outcomes remain UNKNOWN.
- Production composition: READY. Real parent-field and reconciliation seams
  are explicit; incomplete construction fails closed.
- `#btnSave2` and `#bcSend`: CLOSED. Neither has a dispatch path.

## Live acceptance

- Chrome/CDP: PASS.
- Core-Vault ordinary authentication recovery and unique shell: PASS.
- Exact INSO history query and settlement: PASS.
- Parent-form unsaved field read-back and reconciliation detail: PENDING GATE.
  The helper remains fail-closed until the approved runtime exposes the unique
  required frame and detail fields.
- REAL SAVE: NO. REAL SEND: NO. REAL SMTP: NO. SHEETS WRITE: NO.

## Verification and next gate

- Focused runtime, parent-field, composition and Phase-A tests: PASS.
- Full `tests/` regression: PASS (668 passed, 1 skipped). Ruff and final diff
  check: PASS.
- CEO/Safety performs First Real Save Gate Review only after the pending
  read-only live checks PASS. Production Write Gate remains CLOSED.
