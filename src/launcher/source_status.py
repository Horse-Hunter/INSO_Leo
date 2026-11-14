"""Projection of existing successful source reads; no reads, writes or holds."""
from dataclasses import replace
from datetime import timedelta
from threading import Lock
from types import MappingProxyType

from src.sheets.brand_write import SheetRecordConflict
from src.sheets.quotation_candidates import relocate_quotation_source
from src.workflow.v13_quotation import expected_source_brand


class SourceStatusProjection:
    def __init__(self):
        self._revision_lock, self.revision = Lock(), 0
        self.rows = {}
        self.guardable = {}
        self._updating = {}
        self._sheet_revisions = {}
        self._observation_sequence = {}
        self.last_success = {}
        self.statuses = {}
        self._status_sources = {}

    def begin_update(self, worksheet):
        with self._revision_lock:
            self.revision += 1
            self._sheet_revisions[worksheet] = self._sheet_revisions.get(worksheet, 0)+1
            ticket = self._observation_sequence.get(worksheet, 0)+1
            self._observation_sequence[worksheet] = ticket
            self._updating.setdefault(worksheet, set()).add(ticket)
            return ticket

    def end_update(self, worksheet, *, failed=False, ticket=None):
        with self._revision_lock:
            if failed and (ticket is None or self._observation_sequence.get(worksheet) == ticket):
                self.rows.pop(worksheet, None)
                self.guardable.pop(worksheet, None)
                for inquiry, source in self._status_sources.items():
                    if source == worksheet:
                        self.statuses[inquiry] = (None, None, False)
            self.revision += 1
            self._sheet_revisions[worksheet] += 1
            self._updating[worksheet].discard(ticket)
            if not self._updating[worksheet]:
                del self._updating[worksheet]

    def observe(self, worksheet, rows, items, *, at, failed=False, ticket=None):
        from src.sheets.worksheet_schema import worksheet_schema
        owns_update = ticket is None
        if owns_update:
            ticket = self.begin_update(worksheet)
        accepted = False
        try:
            if not failed:
                immutable, guardable = [], True
                for row in rows:
                    cells = dict(row.cells)
                    guardable &= all(type(k) is str and type(v) in {str, int, float, bool, type(None)}
                                     for k, v in cells.items())
                    guardable &= type(row.source_order_date) in {str, int, float, bool, type(None)}
                    immutable.append(replace(row, cells=MappingProxyType(cells)))
                rows = tuple(immutable)
            with self._revision_lock:
                existing = self.rows.get(worksheet)
                older = (not failed and existing is not None and at is not None and existing[1] is not None
                         and at < existing[1])
                if self._observation_sequence.get(worksheet) == ticket and not older:
                    if failed:
                        self.rows.pop(worksheet, None)
                        self.guardable.pop(worksheet, None)
                    else:
                        self.rows[worksheet] = (rows, at)
                        self.guardable[worksheet] = guardable
                        self.last_success[worksheet] = self.rows[worksheet]
                    accepted = True
            if not accepted:
                return False
            affected = [i for i in items if i.record_identity.worksheet == worksheet]
            statuses = {item.inquiry_id: (None, at, False) for item in affected}
            candidates = {}
            if not failed:
                for item in affected:
                    try:
                        row = relocate_quotation_source(item.record_identity, rows, expected_brand=expected_source_brand(item))
                    except SheetRecordConflict:
                        continue
                    candidates.setdefault(row.row_position, []).append(item)
                for position, matches in candidates.items():
                    if len(matches) == 1:
                        row = next(r for r in rows if r.row_position == position)
                        statuses[matches[0].inquiry_id] = (row.cells.get(worksheet_schema(worksheet.worksheet).status_column), at, True)
                # Orders whose sheet status moved on (the Owner finished the line, or
                # an earlier run wrote a later status) no longer relocate by the stored
                # snapshot, so their status stayed unknown and the list could not show
                # the sheet. For display only, fall back to the row this order still
                # occupies: one physical position, one order.
                column = worksheet_schema(worksheet.worksheet).status_column
                for item in affected:
                    if statuses.get(item.inquiry_id, (None, None, False))[0] is not None:
                        continue
                    anchors = [r for r in rows if r.row_position == item.record_identity.row_position]
                    if len(anchors) == 1:
                        statuses[item.inquiry_id] = (anchors[0].cells.get(column), at, True)
            with self._revision_lock:
                if self._observation_sequence.get(worksheet) == ticket:
                    self.statuses.update(statuses)
                    self._status_sources.update({inquiry: worksheet for inquiry in statuses})
                else:
                    return False
            return True
        except Exception:
            with self._revision_lock:
                if self._observation_sequence.get(worksheet) == ticket:
                    self.rows.pop(worksheet, None)
                    self.guardable.pop(worksheet, None)
                    for inquiry, source in self._status_sources.items():
                        if source == worksheet:
                            self.statuses[inquiry] = (None, None, False)
            raise
        finally:
            if owns_update:
                self.end_update(worksheet, ticket=ticket)

    def snapshot(self, worksheet, *, blocking=True):
        """Never expose an older source while a newer read is publishing."""
        if not self._revision_lock.acquire(blocking=blocking):
            return None
        try:
            return None if self._observation_sequence.get(worksheet) in self._updating.get(worksheet, ()) else self.rows.get(worksheet)
        finally:
            self._revision_lock.release()

    def project(self, dto, *, now):
        with self._revision_lock:
            status, at, fresh = self.statuses.get(dto.inquiry_id, (None, None, False))
            source = self._status_sources.get(dto.inquiry_id)
            if source is not None and self._observation_sequence.get(source) in self._updating.get(source, ()):
                status, fresh = None, False
        # A successful row read does not verify a missing or non-text status.
        if not isinstance(status, str) or not status.strip():
            status, fresh = None, False
        else:
            status = status.strip()
        fresh = fresh and at is not None and timedelta(0) <= now-at <= timedelta(minutes=15)
        history = dto.processing_history or dto.waiting_label or dto.business_label.value
        if fresh:
            text = f"{status}；采购/处理历史：{history}"
        else:
            text = f"状态待同步（来源尚未核实/可能过期）；处理历史：{history}"
        return replace(dto, source_status=status, source_verified_at=at, source_fresh=bool(fresh),
                       waiting_label=text, processing_history=history)
