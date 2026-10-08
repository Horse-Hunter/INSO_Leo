"""Narrow Owner command inputs; business execution stays in canonical workflows."""
from dataclasses import replace
from decimal import Decimal, InvalidOperation

from src.sheets import query_pending_records
from src.sheets.worksheet_schema import worksheet_schema


class SingleRowReader:
    def __init__(self, reader, worksheet, row):
        self.reader, self.worksheet, self.row = reader, worksheet, row
    def read_rows(self, worksheet):
        if worksheet != self.worksheet:
            return ()
        return tuple(r for r in self.reader.read_rows(worksheet) if r.row_position == self.row)


def current_record(reader, worksheet, row_position):
    rows = SingleRowReader(reader, worksheet, row_position).read_rows(worksheet)
    if len(rows) != 1:
        raise ValueError("原工作表行已删除或无法唯一确认，未执行操作。")
    row = rows[0]
    schema = worksheet_schema(worksheet.worksheet)
    status = row.cells.get(schema.status_column)
    if status not in {"未发", "发给采购", "采购已报价", "成交"}:
        raise ValueError("原行状态无法确认，未执行操作。")
    normalized = replace(row, cells={**row.cells, schema.status_column: "未发"})
    parser = type("CurrentRow", (), {"read_rows": lambda self, ws: (normalized,)})()
    record, = query_pending_records(parser, worksheet)
    return record, status


def editable_value(field, value):
    text = str(value).strip()
    if field == "quantity":
        try:
            number = Decimal(text)
        except InvalidOperation:
            raise ValueError("数量必须为正整数。") from None
        if not number.is_finite() or number <= 0 or number != number.to_integral_value():
            raise ValueError("数量必须为正整数。")
        return int(number)
    if field == "importance":
        if text.upper() not in {"S", "A", "B", "C"}:
            raise ValueError("重要程度只能为S、A、B或C。")
        return text.upper()
    if field not in {"model", "brand"} or not text:
        raise ValueError("型号和品牌不能为空。")
    return text


class CurrentQuotationStore:
    """Read-only current-source projection; original purchase audit stays untouched."""
    def __init__(self, item, record):
        self.item = replace(item, record_identity=record.record_identity,
            mpn=record.model, brand=record.brand, quantity=record.quantity,
            importance_raw=record.importance_raw, resolved_brand=None, brand_update_status=None)
    def all_items(self):
        return (self.item,)
    def get_by_inquiry_id(self, inquiry_id):
        if inquiry_id != self.item.inquiry_id:
            raise KeyError(inquiry_id)
        return self.item


class InquiryHolds:
    """Scope the existing durable hold store to the selected inquiry."""
    def __init__(self, holds, inquiry):
        self.holds, self.inquiry = holds, inquiry
    def active(self):
        return tuple(row for row in self.holds.active() if row[0] == self.inquiry)
    def hold(self, result, observed):
        return self.holds.hold(result, observed)
    def close(self, key):
        return self.holds.close(key)
