# Task: Company login field

status: complete
owner: Codex
created: 2026-09-21
updated: 2026-09-21

## problem

The bom.ai login flow requires a company name in addition to username and password, but the local credential vault only models username and password.

## goal

Allow a company name to be stored and retrieved with each website login without disrupting existing encrypted credentials.

## current_facts

- Existing vault entries may not contain a company property.
- Existing passwords are DPAPI encrypted and must not be read, logged, or re-encrypted during this change.
- The exact company name for bom.ai is UNKNOWN and must be entered by the user.
- Windows PowerShell 5.1 must read the UTF-8 vault with an explicit encoding; its default decoding corrupts non-ASCII JSON text.
- The legacy site list uses full-width commas to separate URL, optional company, username, and password.

## scope

- Add an optional company field to vault entries, CLI, and graphical manager.
- Add a programmatic login object containing company metadata and a PSCredential.
- Preserve backward compatibility with existing vault JSON.
- Correctly parse legacy full-width-comma credential records instead of treating the entire line as a URL.
- Extend dummy-data tests under both supported PowerShell runtimes.

## non_scope

- Logging in to bom.ai.
- Discovering or guessing the user's company name.
- Changing any live username or password.

## requirements

- Company is optional because not every site requires it.
- Existing entries without company data display an empty value.
- Plaintext passwords remain absent from logs and repository files.

## acceptance

- [x] The manager displays and edits Company.
- [x] Existing vault entries remain readable.
- [x] Automation can retrieve Company with the encrypted credential.
- [x] Tests pass in PowerShell 7 and Windows PowerShell 5.1.

## verification

- Run the core vault test suite under both PowerShell runtimes.
- Run the manager smoke test under both runtimes.
- Inspect the final diff.

## completion

- status: complete
- changed: Added optional company metadata to the vault model, CLI, manager, and automation login contract.
- verified: Parser checks, credential tests, Chinese company round-trip tests, and manager smoke tests passed under PowerShell 7 and Windows PowerShell 5.1. Five legacy records were atomically migrated to encrypted credentials, all five URLs were sanitized, and the previously configured credential was preserved.
- limitations: No live website login was attempted. The ignored legacy `password.txt` still exists locally in plaintext pending an explicit user decision to remove it.
