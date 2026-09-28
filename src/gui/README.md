# GUI

Production entry：

`python -m src.gui.main`

UI-only demo：

`python -m src.gui.main --mock`

GUI 只依赖 `GuiBackend` DTO，不解析 Excel、不操作浏览器、不计算业务阈值。Runtime composition、history cache、V1.2 state/alerts 都由 launcher/workflow 提供。

生产配置位于 Git-ignored `runtime/`。普通 browser/session/readiness 技术问题由 runtime 自行恢复或 fail closed；只有 CAPTCHA/OTP/设备验证等人工安全挑战需要 Owner。

V1.2 GUI 展示 sanitized order state、active alert 和 event history；业务规则见 `docs/PRODUCT_BASELINE.md` 与 `docs/V1_2_ARCHITECTURE.md`。
