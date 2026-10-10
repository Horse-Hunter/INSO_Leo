"""Authorized unsaved sales HEADER only. No detail/upload/save/submit methods."""
from __future__ import annotations

from dataclasses import dataclass
from time import monotonic
from urllib.parse import urlsplit

FIELD_LABELS = {
    "customer": "客户名称", "currency": "币种", "payment": "付款方式",
    "freight": "运费承担", "delivery": "交货方式", "shipping": "配送方式",
    "destination": "出货目的地", "order_no": "客户订单号",
}
SELECTORS = {
    "customer": "CompanyName", "currency": "CurrencyID", "payment": "PayMethod",
    "freight": "DeliveryFeeBy_text", "delivery": "KuaiDiCompanyID",
    "shipping": "DeliveryAddress", "destination": "Extend1", "order_no": "VenPONO",
}
EXPECTED = {"currency": "RMB", "payment": "款到发货", "freight": "卖方付",
            "delivery": "国内交货", "shipping": "快递发货", "destination": "广东惠州"}


class HeaderStop(ValueError):
    def __init__(self, field, reason):
        self.field, self.reason = field, reason
        super().__init__(reason)


@dataclass(frozen=True)
class HeaderResult:
    status: str
    field: str | None = None
    reason: str | None = None
    checked_controls: int = 0


def fill_sales_header(page, pi_no: str) -> HeaderResult:
    """Use explicit public UI operations; stop on first error, no retries."""
    import re
    if not re.fullmatch(r"SHAWN\d{8}-\d{2,}", pi_no):
        return HeaderResult("STOPPED", "order_no", "PI_INVALID")
    try:
        page.open_for_header()
        selected = page.select_first_customer("阿尔克")
        if "阿尔克" not in selected or page.read("customer") != selected:
            raise HeaderStop("customer", "READBACK_MISMATCH")
        page.select("currency", "RMB")  # Owner correction: always select once, including existing RMB.
        if page.read("currency") != "RMB":
            raise HeaderStop("currency", "READBACK_MISMATCH")
        for field in ("payment", "freight", "delivery", "shipping"):
            page.select(field, EXPECTED[field])
            if page.read(field) != EXPECTED[field]:
                raise HeaderStop(field, "READBACK_MISMATCH")
        page.fill("destination", EXPECTED["destination"])
        if page.read("destination") != EXPECTED["destination"]:
            raise HeaderStop("destination", "READBACK_MISMATCH")
        page.fill("order_no", pi_no)
        if page.read("order_no") != pi_no:
            raise HeaderStop("order_no", "READBACK_MISMATCH")
        expected = dict(EXPECTED, customer=selected, order_no=pi_no)
        for field, value in expected.items():
            if page.read(field) != value:
                raise HeaderStop(field, "FINAL_READBACK_MISMATCH")
        page.preserve_for_owner()
        return HeaderResult("WAITING_OWNER", checked_controls=8)
    except HeaderStop as exc:
        return HeaderResult("STOPPED", exc.field, exc.reason)


class PlaywrightSalesHeaderPage:
    """Pinned owned shell, native controls only, retained on every outcome."""
    def __init__(self, page, *, owns_page):
        self.page = page
        self._owns_page = owns_page
        self.frame = None
        self.cancelled_existing_prompt = False
        self.currency_switched = False
        self.customer_candidates = 0

    def _assert_owner(self):
        if self.page.is_closed() or not self._owns_page(self.page):
            raise HeaderStop("page", "TAB_OWNERSHIP_LOST")

    def _frames(self, kind):
        self._assert_owner()
        path = f"/sale/xiaoshou/{kind}.aspx"
        return [f for f in self.page.frames
                if urlsplit(f.url).hostname == "yingsuo.alperp.cn"
                and urlsplit(f.url).path.casefold().endswith(path)
                and f.frame_element().is_visible()]

    def _bill(self):
        frames = self._frames("bill")
        if len(frames) != 1:
            raise HeaderStop("page", "SALES_FORM_UNCONFIRMED")
        return frames[0]

    def open_for_header(self):
        self._assert_owner()
        bills = self._frames("bill")
        if bills:
            if self.page.evaluate("() => window.__INSO_sales_owner_review === true"):
                raise HeaderStop("page", "OWNER_RETURN_REQUIRED")
            self.frame = self._bill()
            return
        lists = self._frames("list")
        if not lists:
            menu = self.page.locator("a#iframe_XiaoShou_menu")
            if menu.count() != 1:
                raise HeaderStop("page", "SALES_MENU_UNCONFIRMED")
            menu.click(timeout=10000)
            self.page.locator("iframe#iframe_XiaoShou_frame").wait_for(state="attached", timeout=15000)
            lists = self._frames("list")
        if len(lists) != 1:
            raise HeaderStop("page", "SALES_LIST_UNCONFIRMED")
        # Native confirm is always cancelled, never accept a fresh XS allocation.
        def cancel_native(dialog):
            dialog.dismiss()
            self.cancelled_existing_prompt = True
        self.page.on("dialog", cancel_native)
        try:
            add = lists[0].locator("button#product_add_:visible")
            if add.count() != 1:
                raise HeaderStop("page", "ADD_DOCUMENT_UNCONFIRMED")
            add.click(timeout=10000)
            deadline = monotonic() + 15
            while monotonic() < deadline:
                for frame in self.page.frames:
                    dialogs = frame.locator(".layui-layer-dialog:visible")
                    for i in range(dialogs.count()):
                        dialog = dialogs.nth(i)
                        cancel = dialog.locator(".layui-layer-btn1")
                        if cancel.count() != 1 or cancel.inner_text().strip() != "取消":
                            raise HeaderStop("page", "UNEXPECTED_ADD_PROMPT")
                        cancel.click(timeout=5000)
                        self.cancelled_existing_prompt = True
                bills = self._frames("bill")
                if len(bills) == 1 and bills[0].locator("#CompanyName:visible").count() == 1:
                    self.frame = bills[0]
                    self.page.evaluate("() => { window.__INSO_sales_owner_review = false; }")
                    return
                self.page.wait_for_timeout(100)  # Pump native frame/dialog events; no business retry.
            raise HeaderStop("page", "SALES_FORM_UNCONFIRMED")
        finally:
            self.page.remove_listener("dialog", cancel_native)

    def _control(self, field):
        self._assert_owner()
        if field not in SELECTORS or self.frame is not self._bill():
            raise HeaderStop(field, "SALES_FORM_UNCONFIRMED")
        control = self.frame.locator("#" + SELECTORS[field] + ":visible")
        if control.count() != 1 or not control.is_enabled():
            raise HeaderStop(field, "CONTROL_UNCONFIRMED")
        return control

    def read(self, field):
        return self._control(field).input_value()

    def _dropdown(self, field):
        control = self._control(field)
        summary = control.locator("..").locator("summary")
        if summary.count() != 1:
            raise HeaderStop(field, "DROPDOWN_UNCONFIRMED")
        summary.click(timeout=5000)

    def _table(self, field):
        table = self._control(field).locator("..").locator("div.tbody > table.js-active-navigation-container.layui-table:visible")
        try:
            table.wait_for(state="visible", timeout=10000)
        except Exception:  # noqa: BLE001 - suppress provider/customer content
            raise HeaderStop(field, "DROPDOWN_UNCONFIRMED") from None
        if table.count() != 1:
            raise HeaderStop(field, "DROPDOWN_AMBIGUOUS")
        return table

    def select_first_customer(self, needle):
        self._dropdown("customer")
        table = self._table("customer")
        rows = table.locator("tr")
        candidates = [(rows.nth(i).locator("td.textField"),
                       rows.nth(i).locator("td.textField").inner_text().strip())
                      for i in range(rows.count()) if rows.nth(i).locator("td.textField").count() == 1]
        candidates = [(cell, name) for cell, name in candidates if needle in name]
        self.customer_candidates = len(candidates)
        if not candidates:
            raise HeaderStop("customer", "CUSTOMER_NOT_FOUND")
        cell, name = candidates[0]
        cell.click(timeout=5000)
        return name

    def select(self, field, value):
        if field not in {"currency", "payment", "freight", "delivery", "shipping"}:
            raise HeaderStop(field, "FIELD_NOT_AUTHORIZED")
        self._dropdown(field)
        if field == "delivery":
            rows = self._table(field).locator("tr")
            cells = [rows.nth(i).locator("td.textField") for i in range(rows.count())
                     if rows.nth(i).locator("td.textField").count() == 1
                     and rows.nth(i).locator("td.textField").inner_text().strip() == value]
            if len(cells) != 1:
                raise HeaderStop(field, "OPTION_UNCONFIRMED")
            cells[0].click(timeout=5000)
        else:
            option = self._control(field).locator("..").locator("a.select-menu-item:visible").filter(has_text=value)
            try:
                option.first.wait_for(state="visible", timeout=10000)
            except Exception:  # noqa: BLE001 - suppress provider/customer content
                raise HeaderStop(field, "OPTION_UNCONFIRMED") from None
            exact = [option.nth(i) for i in range(option.count()) if option.nth(i).inner_text().strip() == value]
            if len(exact) != 1:
                raise HeaderStop(field, "OPTION_UNCONFIRMED")
            exact[0].click(timeout=5000)
        if field == "currency":
            self.currency_switched = True

    def fill(self, field, value):
        if field not in {"destination", "order_no"}:
            raise HeaderStop(field, "FIELD_NOT_AUTHORIZED")
        self._control(field).fill(value)

    def preserve_for_owner(self):
        self._assert_owner()
        self.page.evaluate("() => { window.__INSO_sales_owner_review = true; }")
