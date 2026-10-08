"""Synthetic CDP target events for browser adapter tests; no real browser."""
from types import SimpleNamespace


class PendingPage:
    def __init__(self, context):
        self.context = context

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    @property
    def value(self):
        return self.context.pages[-1]


class BackgroundSession:
    def __init__(self, context):
        self.context = context

    def send(self, command, params):
        assert command == "Target.createTarget" and params["background"] is True
        self.context.new_page()  # Synthetic target-created event/fixture factory.
        return {"targetId": "synthetic-target"}

    def detach(self):
        pass


def attach_background_protocol(context, browser=None):
    context.expect_page = lambda **_: PendingPage(context)
    context.browser = browser or SimpleNamespace()
    context.browser.new_browser_cdp_session = lambda: BackgroundSession(context)
    return context.browser
