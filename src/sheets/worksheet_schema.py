"""Internal physical-column mappings for supported worksheet schemas."""

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
    default_importance="A",
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
