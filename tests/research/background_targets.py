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
        if command == "Target.getTargetInfo":
            matches = [p for p in self.context.pages
                       if str(id(p)) == params["targetId"] and not p.is_closed()]
            assert len(matches) == 1, "unknown synthetic native target"
            return {"targetInfo": {"targetId": params["targetId"], "type": "page"}}
        assert command == "Target.createTarget" and params["background"] is True
        page = self.context.new_page()  # Synthetic target-created event/fixture factory.
        page.url = params["url"]
        original_evaluate = getattr(page, "evaluate", None)
        def evaluate(script, *args, **kwargs):
            if script == "() => history.replaceState(null, '', 'about:blank')":
                page.url = "about:blank"
                return None
            if original_evaluate is not None:
                return original_evaluate(script, *args, **kwargs)
            if script == "() => window.name":
                return None
            raise AssertionError("unexpected synthetic evaluation")
        page.evaluate = evaluate
        return {"targetId": str(id(page))}

    def detach(self):
        pass


def attach_background_protocol(context, browser=None):
    context.expect_event = lambda *_, **__: PendingPage(context)
    context.new_cdp_session = lambda page: SimpleNamespace(
        send=lambda _: {"targetInfo": {"targetId": str(id(page))}}, detach=lambda: None)
    context.browser = browser or SimpleNamespace()
    context.browser.new_browser_cdp_session = lambda: BackgroundSession(context)
    return context.browser
