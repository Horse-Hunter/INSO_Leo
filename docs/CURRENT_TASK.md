# V1.1 Research Stability Hotfix

Status: CLOSED

V1.1 Research Stability Hotfix: PASS

Packaged GUI: PASS
Research → 调研价格.xlsx: PASS

IC.net: PASS
LCSC: PASS
HQEW: PASS
Findchips: PASS
Bom.Ai: PASS

Session recovery:
- IC.net: LIVE PASS
- LCSC: SSO LIVE PASS; Vault recovery deterministic PASS
- Bom.Ai: LIVE PASS

CAPTCHA/OTP/device verification remains manual and fail-closed.

No Research business rules were changed.

Verification:
- Ruff: PASS
- Tests: 403 passed, 10 skipped
- git diff --check: PASS
- Packaged --self-check: PASS (exit 0)
- Packaged --diagnose-vault: PASS (exit 0)

Branch: hotfix/v1-1-research-stability
