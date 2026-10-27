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
        page = self.context.new_page()  # Synthetic target-created event/fixture factory.
        page.url = params["url"]
        return {"targetId": "synthetic-target"}

    def detach(self):
        pass


def attach_background_protocol(context, browser=None):
    context.expect_event = lambda *_, **__: PendingPage(context)
    context.new_cdp_session = lambda page: SimpleNamespace(
        send=lambda _: {"targetInfo": {"targetId": "synthetic-target"}}, detach=lambda: None)
    context.browser = browser or SimpleNamespace()
    context.browser.new_browser_cdp_session = lambda: BackgroundSession(context)
    return context.browser
