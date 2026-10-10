from types import SimpleNamespace

from src.launcher.browser_bootstrap import park_shared_cdp
from src.launcher.inso_session import _existing_or_new_login_page
from src.research.cdp_pages import mark_owned_page, page_owner


class Page:
    def __init__(self, url, name=""):
        self.url, self.name, self.closed = url, name, False
        self.main_frame = SimpleNamespace(url=url)

    def is_closed(self):
        return self.closed

    def close(self):
        self.closed = True

    def evaluate(self, script, value=None):
        if value is not None:
            self.name = value
        return self.name


def test_owned_marker_survives_another_client_and_parking():
    sales = Page("https://yingsuo.alperp.cn/")
    mark_owned_page(sales, "v14-sales")
    another_client = Page(sales.url, sales.name)
    assert page_owner(another_client) == "v14-sales"
    blank = Page("about:blank")
    inquiry = Page("https://yingsuo.alperp.cn/")
    context = SimpleNamespace(pages=[blank, sales, inquiry])
    browser = SimpleNamespace(contexts=[context], is_connected=lambda: True)
    park_shared_cdp(browser)
    assert inquiry.closed and not sales.closed and not blank.closed


def test_pending_creation_marker_protected_before_window_name_is_set():
    sales = Page("about:blank#INSO_OWNER_TAB:v14-sales")
    blank = Page("about:blank")
    browser = SimpleNamespace(contexts=[SimpleNamespace(pages=[sales, blank])],
                              is_connected=lambda: True)
    park_shared_cdp(browser)
    assert not sales.closed and page_owner(sales) == "v14-sales"


def test_default_login_ignores_sales_page(monkeypatch):
    from src.launcher import inso_session

    sales = Page("https://yingsuo.alperp.cn/login.aspx", "INSO_OWNER_TAB:v14-sales")
    login = Page("https://yingsuo.alperp.cn/login.aspx")
    context = SimpleNamespace(pages=[sales, login])
    assert _existing_or_new_login_page(context) == (login, False)
    context.pages = [sales]
    new = Page("about:blank")
    monkeypatch.setattr(inso_session, "_new_background_login_page", lambda c: new)
    assert _existing_or_new_login_page(context) == (new, True)
    assert not sales.closed
