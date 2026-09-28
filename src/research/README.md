# Research

Canonical contract：`docs/modules/RESEARCH.md`。

Tests：

`python -m pytest tests/research`

Production runtime 由 `src/research/runtime.py` 从 Git-ignored `runtime/research.json` 组装。Credential 只走 `src.core`。INSO 使用共享 authenticated runtime/session 能力；普通 readiness 问题不得要求 Owner 手工重建，只有 CAPTCHA/OTP/设备验证等人工安全挑战例外。
