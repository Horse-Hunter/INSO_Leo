"""Internal physical-column mappings for supported worksheet schemas."""

from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class WorksheetSchema:
    status_column: str
    importance_column: str | None
    model_column: str
    brand_column: str
    quantity_column: str
    default_importance: str | None = None
    customer_name_column: str | None = None
    fixed_customer_name: str | None = None

    @property
    def relocation_columns(self) -> tuple[str, ...]:
        columns = [self.status_column]
        if self.importance_column is not None:
            columns.append(self.importance_column)
        columns.extend((self.model_column, self.quantity_column))
        return tuple(columns)


STANDARD_SCHEMA = WorksheetSchema(
    status_column="A",
    importance_column="C",
    model_column="E",
    brand_column="F",
    quantity_column="G",
)

SHAHAB_SCHEMA = WorksheetSchema(
    status_column="B",
    importance_column=None,
    model_column="D",
    brand_column="E",
    quantity_column="F",
    default_importance="SHAHAB",
    fixed_customer_name="SHAHAB",
)

YEAR_2026_SCHEMA = WorksheetSchema(
    status_column="A",
    importance_column="C",
    model_column="E",
    brand_column="F",
    quantity_column="G",
    customer_name_column="D",
)


def worksheet_schema(worksheet_title: str) -> WorksheetSchema:
    """Return the confirmed V1 mapping for a worksheet title."""

    # Google Sheets worksheet titles are passed through unchanged for every
    # API operation and identity.  Schema selection alone is case-insensitive
    # so the confirmed production title ``SHAHAB`` receives its B/D/E/F
    # mapping just like the historical lower-case spelling.
    if worksheet_title.casefold() == "shahab":
        return SHAHAB_SCHEMA
    if worksheet_title == "2026":
        return YEAR_2026_SCHEMA
    return STANDARD_SCHEMA


# The exact header block each source worksheet opens its RFQ table with.  The
# keys are physical column indexes (A=0), the values the literal label the Owner
# keeps there.  A source read is only accepted when one such block is present:
# this is the worksheet-identity proof both transports share.
SOURCE_HEADER_LABELS: dict[str, dict[int, str]] = {
    "2026": {0: "STATUS", 2: "CLASS", 4: "MPN", 5: "MFR", 6: "Qty"},
    "SHAHAB": {1: "STATUS", 3: "Part Number", 4: "Brand", 5: "QTY"},
}

# The earliest row (0-based) the block may start on.  SHAHAB always keeps one
# line above its block; 2026 starts at the very top.
SOURCE_HEADER_ANCHOR_ROW = {"2026": 0, "SHAHAB": 1}

# 2026 is a stack of small RFQ blocks, each opened by its own copy of the header
# row, so the block header is a repeated structure rather than a single top row.
# The Owner's own rows from before this program existed still sit above the
# first well-formed block, and those rows are ordinary business noise: their
# status cell is blank, which every status query already ignores.  Only the
# header proof was anchored to row 1 and therefore refused the whole sheet.
# Scanning a bounded window keeps the labels an exact match while tolerating
# that pre-program preamble; nothing outside the window is considered.
SOURCE_HEADER_WINDOW = 10


def locate_source_header(rows: Sequence[Sequence[object]], title: str) -> int | None:
    """Return the 0-based row of the exact source header block, else ``None``."""

    expected = SOURCE_HEADER_LABELS.get(title)
    if expected is None:
        return None
    start = SOURCE_HEADER_ANCHOR_ROW[title]
    for index in range(start, min(len(rows), start + SOURCE_HEADER_WINDOW)):
        row = rows[index]
        if all(
            column < len(row) and row[column] == label
            for column, label in expected.items()
        ):
            return index
    return None
