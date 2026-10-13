from copy import deepcopy

import pytest

from src.sheets import WorksheetIdentity, WorksheetRow
from src.sheets.intent_status import (
    INTENT_STATUS,
    QUOTED_STATUS,
    IntentLine,
    update_intent_statuses,
)
from src.sheets.worksheet_schema import worksheet_schema

SHEETS = (WorksheetIdentity('test', '2026'), WorksheetIdentity('test', 'SHAHAB'))


def row(worksheet, model='TEST-A', quantity=2, status=QUOTED_STATUS, position=12):
    schema = worksheet_schema(worksheet.worksheet)
    return WorksheetRow(position, {schema.status_column: status, schema.model_column: model,
        schema.quantity_column: quantity, schema.brand_column: 'TEST', 'G' if worksheet.worksheet == 'SHAHAB' else 'B': 'keep'})


class Source:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []
        self.reads = 0
        self.mutate = lambda: None
        self.fail_write = False
        self.bad_readback = False

    def read_rows(self, worksheet):
        self.reads += 1
        if self.reads == 3:
            self.mutate()
        return deepcopy(self.rows.get(worksheet, ()))

    def write_intent_status(self, worksheet, position):
        self.calls.append((worksheet, position))
        if self.fail_write:
            raise RuntimeError('PRIVATE_PROVIDER_BODY')
        column = worksheet_schema(worksheet.worksheet).status_column
        if not self.bad_readback:
            for current in self.rows[worksheet]:
                if current.row_position == position:
                    current.cells[column] = INTENT_STATUS


def run(source, lines=None):
    lines = (IntentLine('TEST-A', 2),) if lines is None else lines
    return update_intent_statuses(source, source, SHEETS, lines)


@pytest.mark.parametrize('target', SHEETS)
def test_unique_match_writes_only_schema_status_and_verifies_both_sheets(target):
    source = Source({target: [row(target)], SHEETS[1-SHEETS.index(target)]: []})
    before = deepcopy(source.rows[target][0].cells)
    result, = run(source)
    assert result.success and result.reason == 'UPDATED'
    assert source.calls == [(target, 12)] and source.reads == 6
    assert source.rows[target][0].cells == {**before, worksheet_schema(target.worksheet).status_column: INTENT_STATUS}


def test_already_intent_is_success_without_write():
    source = Source({SHEETS[0]: [row(SHEETS[0], status=INTENT_STATUS)]})
    result, = run(source)
    assert result.success and result.reason == 'ALREADY_INTENT' and not source.calls


@pytest.mark.parametrize('status', ['未发', '发给采购', '采购已报价', '成交'])
def test_other_status_is_never_modified(status):
    source = Source({SHEETS[0]: [row(SHEETS[0], status=status)]})
    result, = run(source)
    assert not result.success and not source.calls


@pytest.mark.parametrize('second_status', [QUOTED_STATUS, INTENT_STATUS])
def test_duplicate_across_sheets_never_selects_first(second_status):
    source = Source({SHEETS[0]: [row(SHEETS[0])], SHEETS[1]: [row(SHEETS[1], status=second_status)]})
    result, = run(source)
    assert result.reason == 'MATCH_NOT_UNIQUE' and not source.calls


@pytest.mark.parametrize('model,quantity', [('TEST-B', 2), ('TEST-A', 3), ('TEST-A', True), ('TEST-A', 'NaN')])
def test_model_and_quantity_must_both_match(model, quantity):
    source = Source({SHEETS[0]: [row(SHEETS[0], model=model, quantity=quantity)]})
    assert not run(source)[0].success and not source.calls


def test_numeric_quantity_and_duplicate_contract_lines_write_once():
    source = Source({SHEETS[0]: [row(SHEETS[0], quantity='2.0')]})
    assert len(run(source, (IntentLine('TEST-A', 2),) * 2)) == 1
    assert len(source.calls) == 1


def test_source_change_between_reads_stops_before_write():
    source = Source({SHEETS[0]: [row(SHEETS[0])]})
    source.mutate = lambda: source.rows[SHEETS[0]][0].cells.update(F='HUMAN_BRAND')
    assert run(source)[0].reason == 'SOURCE_CHANGED' and not source.calls


@pytest.mark.parametrize('failure', ['fail_write', 'bad_readback'])
def test_uncertain_write_is_not_retried_and_other_model_can_complete(failure):
    source = Source({SHEETS[0]: [row(SHEETS[0])]})
    setattr(source, failure, True)
    result, = run(source)
    assert not result.success and len(source.calls) == 1 and 'PRIVATE' not in result.reason


def test_multiline_partial_result_does_not_hide_failed_model():
    source = Source({SHEETS[0]: [row(SHEETS[0])]})
    results = run(source, (IntentLine('TEST-A', 2), IntentLine('TEST-B', 3)))
    assert [r.success for r in results] == [True, False] and len(source.calls) == 1


def test_unconfirmed_sheet_count_causes_no_read_or_write():
    source = Source({})
    result, = update_intent_statuses(source, source, SHEETS[:1], [IntentLine('TEST-A', 2)])
    assert result.reason == 'CONFIGURATION_UNCONFIRMED' and not source.calls and source.reads == 0
