# Task: Local credential vault

status: complete
owner: Codex
created: 2026-09-21
updated: 2026-09-21

## problem

The repository root contains an untracked `password.txt` with five HTTPS website URLs. Automation needs a safe way to retrieve website credentials, and the user needs a way to add websites and change credentials without storing plaintext secrets in the repository.

## goal

Provide a local Windows credential vault with a graphical manager and a programmatic PowerShell interface, while keeping all live secrets outside Git.

## current_facts

- `password.txt` is untracked and has never appeared in Git history.
- Its five lines are HTTPS URLs without query strings, fragments, or embedded user information.
- Windows DPAPI CurrentUser encryption and Windows Forms are available on this computer.
- The Explorer/CMD environment does not have `pwsh` on PATH; the launcher therefore falls back to Windows PowerShell.
- Project language and future browser-automation runtime remain UNKNOWN.

## scope

- A PowerShell module under `src/core/` for vault CRUD operations.
- A local Windows Forms manager for adding and editing entries.
- A command-line helper for initialization, listing, and import.
- Importing website URLs from `password.txt` without treating them as credentials.
- Tests using only dummy credentials and a temporary vault.
- Ignore rules preventing legacy plaintext or vault JSON files from entering Git.

## non_scope

- Logging into any website.
- Reading, requesting, or migrating live usernames or passwords.
- Browser automation implementation.
- Cloud synchronization, credential sharing, or multi-user access.
- Rewriting Git history.

## requirements

- Encrypt passwords with Windows DPAPI CurrentUser scope.
- Store the vault outside the repository by default.
- Never print plaintext passwords.
- Return credentials to automation as `PSCredential` objects.
- Allow website metadata to exist before credentials are configured.
- Do not add third-party dependencies.

## acceptance

- [x] A user can open a local manager and add, edit, or delete a website credential.
- [x] Automation can retrieve a configured credential by site ID.
- [x] The default vault is outside the repository and contains no plaintext password.
- [x] Existing website URLs can be imported without exposing their text in logs.
- [x] Tests pass with dummy data.
- [x] `password.txt` remains untracked and unchanged.

## verification

- Run `pwsh -File tests/core/CredentialVault.Tests.ps1`.
- Initialize the default vault and import `password.txt` website metadata.
- Inspect `git status`, `git diff`, and the local vault schema without displaying ciphertext or secrets.

## completion

- status: complete
- changed: Added the DPAPI vault module, CLI, Windows Forms manager, double-click launcher, tests, documentation, and secret ignore rules.
- verified: Parser checks passed; dummy credential round-trip/update/delete tests passed under PowerShell 7 and Windows PowerShell 5.1; the manager smoke test passed under both runtimes; five source URLs were imported to the default external vault; the source file hash was unchanged.
- limitations: Future browser automation runtime is UNKNOWN; it may need a small adapter around the PowerShell public contract. Live usernames and passwords still need to be entered by the user.
