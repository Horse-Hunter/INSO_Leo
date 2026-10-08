# RFQ-008 execution log

## Canonical reuse
- gui/app + contracts: optional command DTO/capabilities, row menu, individual editor; no business I/O in GUI.
- launcher/backend: existing poll thread services one command during countdown; no second browser/workflow worker.
- launcher/manual_order: selected original-row reader/current source projection only; no purchase/quote implementation.
- sheets/google_writer: existing schema mapping and RAW single-cell writer; no status field or range edit.
- workflow/v12_flow: rerun_unsubmitted delegates process_pending; same inquiry and immutable event history.
- workflow/store: explicit manual retry refreshes queued input via existing revive API.
- workflow/v12_store: refuses any armed/clicked/unknown/saved evidence; resets only mutable pre-submit projection.
- V1.3 existing cycle/updater reused with scoped source projection and same hold ledger.
- Prior confirmed Script + unchanged source pending status cannot repeat; other inquiry holds remain active.

## Limits
Source status gates unchanged. SHAHAB importance is fixedA/no cell and edit is rejected.
Input edits do not automatically rerun business or recalculate prior result prices. Google stores new
values; current GUI source view refreshes, while historical purchase evidence remains unchanged.
On restart historical audit may display previous input until a fresh selected-row operation.
Row deletion/ambiguous original row rejects; original-row reuse after relocation is Owner responsibility.
No real Google/CDP/SMTP test, no deployment; new contract waits independent CEO review.

## Validation
Final focused523 PASS; full1475 PASS/1 SKIP; targeted45 PASS. Ruff/diff PASS.
BuildOnly + frozen self-check + release scan PASS; no deployment. See FINAL_REPORT.


## CEO B1/B2 repair
- Fetch/pull ff-only: started latest43b9bcc local=remote; no reset to prior implementation.
- CEO REVIEW.md read, preserved SHA256485CDFD7BD0DC33408746AB03CE2FF4BD8D939477CBE362DFB00483022AB55F0.
- B1 reuses set_business_state transaction/_recover_alerts and the single existing manual retry
  HUMAN_RESOLUTION_RECORDED event. Additional scopes only ai-recognition and duplicate-empty.
  No alert/event deletion; ordinary input repair retains defaultFalse. Existing invalid-input recovery intact.
- B1 tests: actual coordinator validation/duplicate episode, fake-only durable successful submission,
  new failure episodes, customer/security/notification/other data-quality/purchase alerts remain,
  original event equality by ID, single manual resolution evidence, stale alert excluded from GUI/red style.
- B2 ManualRetryHolds replaces narrow InquiryHolds adapter. Reads matching old bound/unbound keys;
  hides them only in selected invocation, does not mutate them before runner returns.
- Existing run_quotation returns integrated.run tuple; normal CombinedCycle ignores return as before.
- Finalizer validates selected result/location and terminal state; failed-row canonical hold must be
  durably active with current reason. New key never closed, unresolved old key superseded after verification.
- No-repeat guard checks every matching old pending-status hold, including unbound, against exact snapshot.
- close_many adds atomic canonical-store settlement only; normal automatic close/hold semantics unchanged.
- SQLite mid-close failure test proves transaction rollback preserves BOTH bound/unbound prior barriers.
- Other inquiries, worksheets and different original-row unresolved records remain bytewise unchanged.
- First focused450 PASS, final hold-specific27 PASS. Final focused/full/build outcomes in FINAL_REPORT.
- All accepted RFQ008 GUI/raw-edit/counters/scheduler behavior retained; no production or deployment.

Final repair:focused451 PASS; full1507 PASS/1 SKIP; Ruff/diff PASS; BuildOnly/frozen/scan PASS.
New candidate:7ECE6917BF77E263E1E56BC528A63EE0798404DB1D03D494499B94A4A16B663F; supersedes136902DD...; not deployed.
