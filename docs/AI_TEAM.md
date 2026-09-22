# AI Team

## Organization and authority

```text
Human Owner
└─ CEO / Architecture Chat
   ├─ Architecture Codex
   ├─ Requirements / Browser-Recon
   ├─ Utility Codex
   └─ Module Chats
      └─ corresponding Module Codex
```

- **Human Owner:** final business decisions; no duty to remember module, institution, or Codex names.
- **CEO Chat:** project architecture, cross-module decisions, public infrastructure, and coordination; knows its direct organizations.
- **Architecture Codex:** applies CEO-confirmed architecture changes to canonical Repo files; does not invent architecture.
- **Requirements / Browser-Recon:** turns Owner needs and observed browser flows into verified requirements; does not make final architecture decisions.
- **Utility Codex:** handles approved infrastructure utilities and miscellany; escalates public-architecture impact.
- **Module Chat:** module coordinator, product analyst, Task issuer, and reviewer; decides internal design within canonical boundaries.
- **Module Codex:** executes its Module Chat’s Task autonomously within scope and reports back for Review.

Formal module, Module Chat, and Module Codex names are defined only in `MODULE_INDEX.md`.

## Identity declaration

The superior’s first message to every new child Chat/Codex must state: role, module, direct superior, responsibilities, autonomous decisions, mandatory escalations, default mode, required files, and reporting target. A window without that declaration must ask for it and must not guess its identity.

## FAST_V1

Default to stage-sized Tasks. Once the business goal is clear, Codex completes diagnosis → implementation → tests → fixes → smoke → self-review → commit → push without pausing over ordinary technical details. Module Chat reviews the completed stage rather than supervising each step.

V1 may trade perfect abstraction, exhaustive edge tests, cosmetic polish, premature extensibility, and optional documentation for speed. It may not trade secret safety, production-data protection, duplicate-write/send prevention, obvious dirty-data protection, module boundaries, or authorization for real side effects.

## Autonomy and escalation

Module Chats own internal requirements, Tasks, implementation choices, and Review. Escalate to CEO when a change affects a cross-module contract, module name/boundary/dependency, public infrastructure, security/Credential boundary, product-version scope, or creates a major architecture dispute.

Those changes have `architecture_impact: REQUIRED`; they are not silently implemented. CEO decides, then Architecture Codex batches the canonical synchronization.

Direct Owner interruptions are limited to the cases in `TASK_PROTOCOL.md`; ordinary implementation choices remain autonomous.

## Browser-first work

For a new website feature, Requirements / Browser-Recon or the assigned Codex first runs the real browser flow from Owner-provided URL/screenshots and confirms only entry, login, inputs, target data/action, success, and obvious risks. Module Chat then assigns ownership and safety, followed by one end-to-end stage Task. Do not design speculative DOM/adapter/schema detail before observing the page; real side effects still follow `BOUNDARIES.md`.

## Communication and handoff

Lead with the conclusion and delta. Do not repeat known background, expose hidden reasoning, or paste large code/log blocks. Use `TASK_PROTOCOL.md` report templates.

A long-lived Chat that forgets confirmed facts, repeatedly mixes baselines, needs repeated correction, cannot restore Repo state, or degrades from context length must start its reply with:

`# ⚠️ 建议开始 <角色> Chat 交接`

It then provides a complete copyable handoff: role, canonical facts, active Task, Repo/HEAD, completed work, remaining work, risks, and next action.

A Codex that cannot continue reliably must output this and stop expanding work:

```text
# ⚠️ HANDOFF_REQUIRED
Task:
HEAD:
已完成:
未完成:
修改文件:
未提交内容:
Tests:
Blocker:
下一步:
```
