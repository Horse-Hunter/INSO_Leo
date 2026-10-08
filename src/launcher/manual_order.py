"""Narrow Owner command inputs; business execution stays in canonical workflows."""
import json
from dataclasses import replace
from decimal import Decimal, InvalidOperation

from src.sheets import query_pending_records
from src.sheets.worksheet_schema import worksheet_schema
from src.workflow.v12_faults import FaultScope, V12Fault
from src.workflow.v13_quotation import QuotationOutcome


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


class ManualRetryHolds:
    """One invocation bypass; matching barriers stay durable until settlement."""
    def __init__(self, holds, inquiry, identity):
        self.holds, self.inquiry, self.identity = holds, inquiry, identity
        self.matched_old = []
        self.new_hold_keys = set()
        for row in holds.active():
            key = row[0]
            matched = key == inquiry
            if key.startswith("unresolved:"):
                try:
                    observed = json.loads(row[2])
                    matched = (observed["worksheet"] == {
                        "spreadsheet": identity.worksheet.spreadsheet,
                        "worksheet": identity.worksheet.worksheet}
                        and observed["row_position"] == identity.row_position)
                except (ValueError, TypeError, KeyError):
                    raise V12Fault(FaultScope.GLOBAL_STOP, "WORKFLOW_LEDGER_UNAVAILABLE") from None
            if matched:
                self.matched_old.append(row)
        self.matched_old_keys = {row[0] for row in self.matched_old}

    def active(self):
        # Other inquiries/locations are outside the selected-row invocation.
        return tuple(row for row in self.holds.active()
            if row[0] in self.new_hold_keys and row[0] not in self.matched_old_keys)

    def hold(self, result, observed):
        key, episode = self.holds.hold(result, observed)
        self.new_hold_keys.add(key)
        return key, episode

    def close(self, key):
        if key in self.new_hold_keys and key not in self.matched_old_keys:
            return self.holds.close(key)

    def finalize(self, results):
        # A selected-row runner must return exactly one terminal row result.
        if not isinstance(results, tuple) or len(results) != 1:
            raise V12Fault(FaultScope.GLOBAL_STOP, "V13_MANUAL_RETRY_UNSETTLED")
        result, = results
        location = result.record_identity
        worksheet = result.source_worksheet or (location.worksheet if location else None)
        row = result.source_row_position or (location.row_position if location else None)
        if (worksheet != self.identity.worksheet or row != self.identity.row_position
                or result.inquiry_id not in {None, self.inquiry}):
            raise V12Fault(FaultScope.GLOBAL_STOP, "V13_MANUAL_RETRY_UNSETTLED")
        if result.outcome is QuotationOutcome.ROW_FAILED:
            active = {row[0]: row for row in self.holds.active()}
            current = self.new_hold_keys & active.keys()
            if not current or not any(active[key][3] == result.row_error_reason.value for key in current):
                raise V12Fault(FaultScope.GLOBAL_STOP, "V13_MANUAL_RETRY_UNSETTLED")
            # Never deactivate a newly updated bound key that equals the old key.
            to_close = self.matched_old_keys - current
        elif result.outcome in {QuotationOutcome.NO_RECENT_QUOTE,
                QuotationOutcome.UPDATED_INSERTED, QuotationOutcome.UPDATED_ALREADY_EXISTS}:
            to_close = self.matched_old_keys
        else:
            raise V12Fault(FaultScope.GLOBAL_STOP, "V13_MANUAL_RETRY_UNSETTLED")
        if to_close:
            self.holds.close_many(sorted(to_close))
