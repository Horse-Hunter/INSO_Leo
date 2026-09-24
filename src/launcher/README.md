# Production Launcher

Composition root for the `GuiBackend` contract. It depends on GUI contracts and the public runtime APIs of Sheets, Workflow and Research. It owns run-session observation, readiness display and graceful lifecycle only; business behavior stays in the owning modules.
