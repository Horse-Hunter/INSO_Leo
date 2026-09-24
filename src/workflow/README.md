# Workflow

V1 uses a local SQLite state store, a non-overlapping all-worksheet poller, and a
single Research worker. `service.py` contains orchestration boundaries while
`store.py` owns durable deduplication and transitions.

Canonical contract: `docs/modules/WORKFLOW.md`; module ownership:
`docs/MODULE_INDEX.md`.
