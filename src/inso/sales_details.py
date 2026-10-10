"""Native unsaved detail edit surface: no delete/amount/save/submit/upload."""
from decimal import Decimal, InvalidOperation

from .sales_header import HeaderStop

DETAIL_FIELDS = {
    "model": ("PartNo", "型号"), "quantity": ("Qty", "订单量"),
    "price": ("UPNoTax", "未税单价"), "brand": ("Brand", "品牌"),
    "dc": ("DC", "批号"), "package": ("Pack", "封装"),
    "due": ("DeliveryDate", "交期"), "packing": ("S3", "包装情况"),
    "developer": ("NewOld", "开发人"), "moisture": ("S4", "湿敏等级"),
    "unpack": ("PartMemo1", "是否拆包"),
}


class DetailStop(HeaderStop):
    def __init__(self, field, reason, row=None):
        super().__init__(field, reason)
        self.row = row


def same_value(field, actual, expected):
    if field in {"quantity", "price"}:
        try:
            return Decimal(actual.replace(",", "")) == Decimal(expected)
        except (InvalidOperation, ValueError):
            return False
    return actual == expected


def fill_sales_details(page, expected_rows):
    total = len(expected_rows)
    if total < 1 or any(set(row) != set(DETAIL_FIELDS) for row in expected_rows):
        raise DetailStop("rows", "DETAILS_UNCONFIRMED")
    count = page.row_count()
    if count < 1 or count > total:
        raise DetailStop("rows", "EXISTING_ROWS_EXCEED")
    while count < total:
        page.add_row()
        after = page.row_count()
        if after != count + 1:
            raise DetailStop("rows", "ROW_INCREMENT_MISMATCH")
        count = after
    if page.row_count() != total:
        raise DetailStop("rows", "ROW_COUNT_MISMATCH")
    for index, values in enumerate(expected_rows):
        for field, value in values.items():
            page.write(index, field, value)
            if not same_value(field, page.read(index, field), value):
                raise DetailStop(field, "READBACK_MISMATCH", index)
        for field, value in values.items():
            if not same_value(field, page.read(index, field), value):
                raise DetailStop(field, "ROW_READBACK_MISMATCH", index)
    if page.row_count() != total:
        raise DetailStop("rows", "ROW_COUNT_MISMATCH")
    for index, values in enumerate(expected_rows):
        for field, value in values.items():
            if not same_value(field, page.read(index, field), value):
                raise DetailStop(field, "FINAL_READBACK_MISMATCH", index)
    page.preserve_for_owner()
    return total


class PlaywrightSalesDetailsPage:
    def __init__(self, header_page):
        self.header = header_page
        self.added = 0

    def _rows(self):
        self.header._assert_owner()
        if self.header.frame is not self.header._bill():
            raise DetailStop("rows", "SALES_FORM_UNCONFIRMED")
        table = self.header.frame.locator("table#_id_dg:visible")
        if table.count() != 1:
            raise DetailStop("rows", "DETAILS_UNCONFIRMED")
        return table.locator("tbody > tr:visible")

    def row_count(self):
        return self._rows().count()

    def add_row(self):
        self._rows()
        button = self.header.frame.locator("#detail_add:visible")
        if button.count() != 1 or button.inner_text().strip() != "新增":
            raise DetailStop("rows", "ADD_ROW_UNCONFIRMED")
        button.click(timeout=5000)
        self.added += 1

    def _cell(self, index, field):
        if field not in DETAIL_FIELDS:
            raise DetailStop(field, "FIELD_NOT_AUTHORIZED", index)
        rows = self._rows()
        if index < 0 or index >= rows.count():
            raise DetailStop(field, "DETAILS_UNCONFIRMED", index)
        cell = rows.nth(index).locator('td[data-field="' + DETAIL_FIELDS[field][0] + '"]')
        if cell.count() != 1 or cell.get_attribute("data-edit") != "text":
            raise DetailStop(field, "CONTROL_UNCONFIRMED", index)
        return cell

    def write(self, index, field, value):
        try:
            cell = self._cell(index, field)
            if cell.locator("input.layui-table-edit:visible,select:visible").count() == 0:
                cell.dblclick(timeout=5000)  # Native grid editor, never JS value assignment.
            select = cell.locator("select:visible")
            if select.count() == 1:
                select.select_option(label=value, timeout=5000)
                return
            editor = cell.locator("input.layui-table-edit:visible")
            if editor.count() != 1 or editor.get_attribute("readonly") is not None:
                raise DetailStop(field, "CONTROL_UNCONFIRMED", index)
            # Confirmed current grid exposes ordinary text inputs for all11 fields.
            if editor.get_attribute("type") not in {None, "text", "number"}:
                raise DetailStop(field, "CONTROL_UNCONFIRMED", index)
            editor.fill(value, timeout=5000)
            editor.press("Tab", timeout=5000)  # Let native blur/change recalculate amounts.
        except DetailStop:
            raise
        except Exception:  # noqa: BLE001 - safe field attribution, no raw Playwright values
            raise DetailStop(field, "CONTROL_UNCONFIRMED", index) from None

    def read(self, index, field):
        try:
            cell = self._cell(index, field)
            editor = cell.locator("input.layui-table-edit:visible")
            if editor.count() == 1:
                return editor.input_value()
            select = cell.locator("select:visible")
            if select.count() == 1:
                return select.locator("option:checked").inner_text().strip()
            return cell.locator("div.layui-table-cell").inner_text().strip()
        except DetailStop:
            raise
        except Exception:  # noqa: BLE001 - no page values in errors
            raise DetailStop(field, "CONTROL_UNCONFIRMED", index) from None

    def preserve_for_owner(self):
        self.header.preserve_for_owner()
