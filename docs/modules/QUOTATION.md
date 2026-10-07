# Quotation module

RFQ-005 adds only `update_result.parse_update_popup`: pure parsing of the
Owner-confirmed 报价更新完成 title/counts into INSERTED/ALREADY_EXISTS/UNCONFIRMED.
Display whitespace is ignored for this popup alone; raw quotation fields are not
normalized. Generic success, zero/zero, malformed/duplicate/abnormal counts do not
prove success. No pricing, formula, tax, margin, network, Sheets, browser or login
implementation belongs here. Orchestration remains workflow; UI remains launcher;
input/range/status read remains sheets. Live dialog/role acceptance is UNKNOWN.

Owner correction 2026-10-07: the actual target is `报价输入`; the former
“报价输入子表” is an incorrect historical name, never an alias. Sheets owns the
minimal metadata title/gid binding plus exact14 headers, validated before Workflow
opens the UI or writes input. Popup parsing and inserted/existing success remain
unchanged. Live-only geometry, DOM, Script delay and session remain UNKNOWN.
