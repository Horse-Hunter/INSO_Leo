import pytest

from src.inso.sales_details import (
    DETAIL_FIELDS,
    DetailStop,
    PlaywrightSalesDetailsPage,
    fill_sales_details,
)


def expected(n=1):
    return tuple({'model':'SYNTHETIC', 'quantity':'2', 'price':'3.25', 'brand':'TEST', 'dc':'24+',
        'package':'QFN', 'due':'2026-10-17', 'packing':'全新拆封', 'developer':'无', 'moisture':'1', 'unpack':'是'} for _ in range(n))


class Grid:
    def __init__(self, count=1, increment=1, wrong=None, wrong_read=1):
        self.count, self.increment, self.wrong, self.wrong_read = count, increment, wrong, wrong_read
        self.adds, self.calls, self.reads, self.values = 0, [], {}, {}
        self.preserved = False
    def row_count(self): return self.count
    def add_row(self):
        self.adds += 1
        self.count += self.increment
    def write(self, index, field, value):
        self.calls.append((index, field))
        self.values[index, field] = value
    def read(self, index, field):
        key = (index, field)
        self.reads[key] = self.reads.get(key, 0) + 1
        return 'mismatch' if field == self.wrong and self.reads[key] >= self.wrong_read else self.values[key]
    def preserve_for_owner(self): self.preserved = True


@pytest.mark.parametrize('n', [1,4])
def test_exact_additions_all_immediate_row_final_readbacks(n):
    grid = Grid()
    assert fill_sales_details(grid, expected(n)) == n and grid.adds == n - 1
    assert grid.preserved and len(grid.calls) == 11*n
    assert all(count == 3 for count in grid.reads.values())


@pytest.mark.parametrize('increment', [0,2])
def test_each_add_must_be_plus_one(increment):
    grid = Grid(increment=increment)
    with pytest.raises(DetailStop): fill_sales_details(grid, expected(4))
    assert grid.adds == 1 and not grid.calls


def test_existing_excess_stops_without_deletion_or_writes():
    grid = Grid(count=4)
    with pytest.raises(DetailStop): fill_sales_details(grid, expected())
    assert not grid.adds and not grid.calls


@pytest.mark.parametrize('field', DETAIL_FIELDS)
@pytest.mark.parametrize('when', [1,2,3])
def test_every_field_each_validation_stage_stops_without_retry(field, when):
    grid = Grid(wrong=field, wrong_read=when)
    with pytest.raises(DetailStop) as exc: fill_sales_details(grid, expected())
    assert exc.value.field == field and exc.value.row == 0
    assert len(set(grid.calls)) == len(grid.calls) and not grid.preserved


def test_forbidden_action_surface_and_fields():
    page = PlaywrightSalesDetailsPage(None)
    for field in ['Amount', 'save', 'submit', 'pdf', 'condition', 'delete']:
        with pytest.raises(DetailStop): page.write(0, field, 'blocked')
    assert all(not hasattr(page, action) for action in ['save', 'submit', 'upload', 'delete', 'fill_amount'])
