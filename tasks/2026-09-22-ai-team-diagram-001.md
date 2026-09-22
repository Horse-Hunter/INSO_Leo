# Task: AI-TEAM-DIAGRAM-001

status: complete
actor_role: Utility Codex
module: utility
reports_to: CEO / Architecture Chat
execution_mode: FAST_V1
architecture_impact: NONE

## Problem

Human Owner lacks a single visual reference for the canonical AI team hierarchy, Module Chat / Module Codex relationships, and the special non-resident Core ownership model.

## Goal

Add a concise Chinese-first AI team and module architecture diagram, with editable Mermaid source, rendered SVG, and canonical navigation.

## Current Facts

- AI organization and role relationships are defined by `docs/AI_TEAM.md`.
- Formal modules and Module Chat / Module Codex names are defined by `docs/MODULE_INDEX.md`.
- Core is a code/public-capability module without a resident Core Chat or Core Codex.
- This Task reflects existing canonical structure and does not change it.

## Required Context

- `AGENTS.md`
- `docs/AI_TEAM.md`
- `docs/MODULE_INDEX.md`
- `docs/AI_START_HERE.md`

## Write Scope

- `docs/AI_TEAM.md`
- `docs/diagrams/ai-team-architecture.mmd`
- `docs/diagrams/ai-team-architecture.svg`
- This Task Packet

## Scope

- Show Human Owner, CEO / Architecture Chat, all CEO direct institutions, all module institutions, formal code modules, and the Core special case.
- Add navigation and a synchronization rule to the canonical AI team document.
- Verify source/rendered consistency, SVG validity, canonical names, and Git formatting.

## Non-scope

- Team, role, module, responsibility, dependency, Public Contract, or business-code changes.

## Requirements

- Chinese-first, concise, and directly understandable.
- Mermaid is the editable source; SVG is the reviewable rendered asset.
- Team or module architecture changes require both assets to be updated.

## Acceptance

- [x] Diagram shows the complete canonical team hierarchy.
- [x] Diagram shows research, sheets, workflow, inso, quotation, and core.
- [x] Core is clearly marked as non-resident and CEO-assigned to Architecture Codex or Utility Codex.
- [x] Mermaid source and SVG are present.
- [x] Canonical navigation and synchronization rule are present.
- [x] No business code is modified.

## Execution

- Work from current remote main in an isolated worktree.
- Validate XML, canonical labels, diff scope, and `git diff --check`.
- Commit and push to main after verification.

## Final Report

Report status, changed files, structure summary, navigation, commit, push, and remaining gap.
