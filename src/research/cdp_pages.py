"""Create CDP tabs without raising the Owner's Chrome window."""

from __future__ import annotations

from typing import Any


def new_background_page(browser: Any, context: Any, *, timeout_ms: int) -> Any:
    """Return a tab in the attached context without foreground activation.

    Playwright ``context.new_page`` focuses Chrome and can restore a minimized
    dedicated window. CDP's background target preserves its window state.
    """

    session = browser.new_browser_cdp_session()
    target_id: str | None = None
    try:
        with context.expect_page(timeout=timeout_ms) as pending:
            target_id = session.send(
                "Target.createTarget", {"url": "about:blank", "background": True}
            )["targetId"]
        return pending.value
    except Exception:
        if target_id is not None:
            session.send("Target.closeTarget", {"targetId": target_id})
        raise
    finally:
        session.detach()
