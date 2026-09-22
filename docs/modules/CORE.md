# Core Module

## Public boundary

Core owns stable shared primitives and infrastructure capabilities. It must remain free of module-specific business rules and may not depend on a business module.

## Credential Provider

Business modules request authorized website login data through the Credential Provider using a stable `site_id`; they do not depend on DPAPI, file paths, or PowerShell details. The currently confirmed local interface is `Get-InsoVaultLogin -SiteId <id>`.

The current local vault uses Windows DPAPI CurrentUser and stores its runtime data outside Git at `%LOCALAPPDATA%\INSO_Leo\credential-vault.json`. It is single-user/local-machine only; cross-machine synchronization and multi-user sharing are not supported.

Returned credentials are bounded runtime values. They must never enter Git, Tasks, logs, fixtures, evidence, screenshots, or examples; callers also follow `BOUNDARIES.md`.

## UNKNOWN

- A language-neutral application API beyond the confirmed provider capability.
- Shared configuration, logging, time, identifier, and error contracts until concrete multi-module needs are confirmed.
