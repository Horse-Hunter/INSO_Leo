"""Projection of existing successful source reads; no reads, writes or holds."""
from dataclasses import replace
from datetime import timedelta

from src.sheets.brand_write import SheetRecordConflict
from src.sheets.quotation_candidates import relocate_quotation_source
from src.workflow.v13_quotation import expected_source_brand


class SourceStatusProjection:
    def __init__(self):
        self.rows = {}
        self.last_success = {}
        self.statuses = {}

    def observe(self, worksheet, rows, items, *, at, failed=False):
        from src.sheets.worksheet_schema import worksheet_schema
        if failed:
            self.rows.pop(worksheet, None)
        else:
            self.rows[worksheet] = (tuple(rows), at)
            self.last_success[worksheet] = self.rows[worksheet]
        affected = [i for i in items if i.record_identity.worksheet == worksheet]
        candidates = {}
        for item in affected:
            self.statuses[item.inquiry_id] = (None, at, False)
            if failed:
                continue
            try:
                row = relocate_quotation_source(item.record_identity, rows, expected_brand=expected_source_brand(item))
            except SheetRecordConflict:
                continue
            candidates.setdefault(row.row_position, []).append(item)
        for position, matches in candidates.items():
            if len(matches) == 1:
                row = next(r for r in rows if r.row_position == position)
                self.statuses[matches[0].inquiry_id] = (row.cells.get(worksheet_schema(worksheet.worksheet).status_column), at, True)

    def project(self, dto, *, now):
        status, at, fresh = self.statuses.get(dto.inquiry_id, (None, None, False))
        fresh = fresh and at is not None and timedelta(0) <= now-at <= timedelta(minutes=15)
        history = dto.waiting_label or dto.business_label.value
        if fresh:
            text = f"{status}；采购/处理历史：{history}"
        else:
            text = f"状态待同步（来源尚未核实/可能过期）；处理历史：{history}"
        return replace(dto, source_status=status, source_verified_at=at, source_fresh=bool(fresh), waiting_label=text)
