# Boundaries

This is the canonical safety boundary. One Task authorization covers that bounded action; do not ask again for each mechanical step. If target, identity, or authority is uncertain, fail closed.

## GREEN — autonomous

- Read Repo files, docs, code, and Git history.
- Change Task-scoped code; run tests with local synthetic/fake data.
- Browse approved websites read-only and create safe local output.
- Run normal `git status`, `diff`, `log`, `commit`, and Task-branch push.

## YELLOW — explicit authorization required

- Write a real Google Sheet or modify other real production data.
- Perform a first or previously unauthorized external write.
- Delete, move, overwrite, or migrate real user files/data at scale.
- Submit forms; change website data; send customer messages; create orders; pay.
- Change Credential behavior or perform a high-risk Git operation.

After a Task authorizes a bounded YELLOW action, execute it without repeated confirmation unless target or risk changes.

## RED — prohibited

- Put a real password, secret, token, cookie, vault value, or customer data in Git, Tasks, logs, fixtures, evidence, screenshots, or examples.
- Bypass CAPTCHA, OTP, device verification, or another security challenge.
- Guess an uncertain target and write, or silently fall back after a safety check fails.
- Delete unknown untracked files; overwrite unknown work with `git reset --hard`; run `git clean -fd`; force-push `main`; delete an unknown branch/worktree.
- Modify real orders, payments, customer records, or another system without authorization.

## System rules

- **Google Sheets:** read actively. Before a write, uniquely relocate and validate the record; update only the targeted field; do not write on conflict.
- **Web/browser:** browsing, authorized login, search, and read are allowed. Submit/send/buy/delete/modify/pay actions are YELLOW; never bypass challenges.
- **Local files:** keep runtime/data separate from source; do not delete, move, or overwrite an unknown file.
- **Git:** inspection, commit, and normal Task-branch push are GREEN. Merge, rebase, and dirty-tree switching require caution and authorization when user work could be affected. RED Git actions remain prohibited by default.
- **Credential:** AI may call the approved Credential Provider for an authorized flow but must not print, copy, persist, or commit the returned credential.

Practical rule: read, test, and change scoped code freely; never expose credentials or change real data, external systems, or unknown user files without clear authority.
