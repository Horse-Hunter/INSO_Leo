# RFQ-006 Owner closeout increment — 2026-10-07

Status: REVIEW_REQUIRED. Branch: feature/v1-3-integration.
Base: RFQ-007 CEO reviewed2c9f7043313ab0092c29c7a54a76dfd176645ef5, including
RFQ-006 reviewed2a32007. Fast-forward reuse of approved sync, with pending Owner quotation
changes restored without conflict. CEO REVIEW.md files are preserved. This report supersedes
older baseline-only release/live-UNKNOWN reports; historical delivery facts remain in git/log.

## Final implementation
| File / location | Change |
| --- | --- |
| src/inso/quotation_read.py:50 | Exact inclusive72h lowest positive supplier net (column8), existing RMB FX comparison, newest/stable tie and newest zero fallback; raw14 untouched; column6供方税点. |
| src/workflow/v13_quotation.py | Existing FX provider integrated, typed unsupported-price row failure and unavailable-FX global stop. |
| src/launcher/google_quote_update.py:71 | Observed menu readiness30s, unique drawing/actionable click, strict stale-result guard; independent result wait30s. |
| src/launcher/google_quote_update.py:119 | Exact confirmation followed by bounded Script settlement; no input clearing. Unconfirmed settlement preserves page and globally stops. |
| src/quotation/update_result.py | Actual 更新完成 / 已有价跳过 aliases with unchanged strict single-row outcome counts. |
| src/workflow/v13_quote_update.py:193 | Both inserted1 and existing-skip1 require source采购已报价 within30s; source remains read-only; no confirmed-Script repeat. |
| src/launcher/v13_integration.py:40; src/gui/app.py:77 | SOURCE_STATUS_NOT_UPDATED projects pale-yellow warning; existing durable hold/outbox notifies229, with fixed warning log in backend. Other failures unchanged. |
| src/launcher/purchase_completion.py:83 | Only RESEARCH / NO_MATCHING_PRODUCT adds shawn@inso-hk.com alongside229. Version only that immutable command payload; existing worker/retry reused. |

The latest Owner30s rule supersedes earlier unconditional manually-restored existing-price success.
A successful popup confirms Script execution; unresolved source status is a separate warning/hold.
Notification is queued durably, not claimed delivered. No alternate mail/cooldown/browser/identity
system and no dependency were introduced. V1.2 purchase and V1.3 quotation terminal states remain
independent. A/B/C eligibility unchanged; S is never automatically mapped.

## Approved RFQ-007 preservation
Five original production patches remain in the approved base: v12_store direct recovery,
v12_gui legacy read-only projection, contracts additive deadline, backend V1.2-only wrapper,
and app minimum QUOTATION_RUNNING compatibility. RFQ-003 B1 remains equivalent/unchanged.
Focused/full PASS includes corrected S→A recovery, unrelated customer alert retained, read-only
legacy projection, stop-interruptible180s deadline and no cooldown after last purchase.
V1.3 normal rows remain0s; RFQ006 backend binding/projection asserts no inherited180s.
RFQ007 GUI RUNNING/cooldown/in-progress/countdown and QUOTATION_RUNNING cases all PASS.
No cherry-pick of f515a14 whole commit and no whole-file V1.3 overwrite.

## Actual live evidence and limits
One previously authorized DRV8833PWR existing-price click was actually confirmed:
更新完成 / 成功填入0行 / 已有价跳过1行, then exact确定 and Script completion.
Source stayed发给采购 after Owner manual reset. Owner confirms Script deletes input after popup.
The new30s warning behavior is verified offline; no repeat live click or real SMTP test was made.
First-new-insert live transition, live mixed-currency acceptance and actual SMTP delivery remain
UNKNOWN. Production payload/screenshots/helper outputs remain ignored and are not committed.
During this closeout no history replay, real procurement, Save/Save-and-Send or real SMTP.
The earlier single authorized quote input/update test is recorded separately; do not claim it never
occurred. No source status force-write, Script modification or manual input clear.

## Exact-source verification
- Final focused:462 passed24.32s, including RFQ003/004/005/006 shared regressions, GUI,
  button/results/status windows, lowest-price/raw14 and narrowly scoped Research recipients.
- Final full safe/offline:1393 passed,1 skipped55.85s; exit0, SMTP guards enabled.
- Ruff src/tests --no-cache PASS; git diff --check PASS.
- Canonical build_windows_release.ps1 -Version1.3 -BuildOnly exit0.
- Frozen --self-check exit0; RELEASE_SCAN_OK.
- Separate ignored candidate --idle-self-check exit0: INSO_V1.3, 已停止,
  gui_rendered=true, business_thread_started=false; Start disabled by diagnostic.
- Candidate EXE SHA256:6B9248BB591F4A43885CA32399F2835F9FB3051AFF20BB31A4633B9F8C3625EB.
- Candidate path: build/windows-release-stage-1.3/dist/INSO_V1.3/INSO_V1.3.exe.
- Installed V1.3/V1.2 releases/configs were not replaced. This new increment requires independent
  CEO Review before deployment, as previously specified. No profile/cookie/manual verification changes.

## Delivery
Commit/push feature/v1-3-integration; verify local==remote HEAD and clean active worktree.
RFQ-006 increment remains REVIEW_REQUIRED; RFQ-007 approved record remains REVIEWED_DONE.
No new CEO product decision conflict was found. Remaining approval is independent review and then
release installation; no further source implementation issue is known after these checks.

## Latest Owner120-second increment — 2026-10-07
Base e8ae7e9880fdcce4ffd200c1366b1bb5b1c02a71; current branch feature/v1-3-integration.
Owner expanded the normal Research row request to all fixed180-second waits. Production diff:
- src/workflow/v12_flow.py:168: normal Research/purchase row wait120s.
- src/workflow/inso_query.py:30: shared INSO duplicate/history/quotation query retry120s.
- Existing backend deadline and GUI rendering reused unchanged: 冷却02:00 then01:59.
- Existing interruptible Event.wait, four total query attempts, close-before-retry, no final-row
  cooldown, V1.3 normal row0s and combined scheduler900s preserved.
- Chrome configured timeout maximum180s remains a validation bound, not a fixed180s wait;
  default30s and fixed browser/session protections remain unchanged.
Latest exact-source focused289 PASS12.18s; full1394 PASS/1 SKIP58.08s; Ruff/diff PASS.
BuildOnly/frozen self-check/RELEASE_SCAN_OK PASS. New candidate EXE SHA256:
BFD2BAFF59E19D46D31DA3E8BFEE81968B5C860D4EF0A3FF2A54F7EA21F52F30.
This candidate supersedes the prior candidate hash/test totals; prior idle diagnostic remains
historical evidence only, not a new idle run. Installed release/configs not overwritten.
All earlier quote robustness/status-warning/Research-mail changes remain in this branch.
No real business action/SMTP/order replay; no dependencies. Independent review remains REQUIRED.
