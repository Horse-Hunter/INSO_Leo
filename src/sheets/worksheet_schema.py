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
)


def worksheet_schema(worksheet_title: str) -> WorksheetSchema:
    """Return the confirmed V1 mapping for a worksheet title."""

    return SHAHAB_SCHEMA if worksheet_title == "shahab" else STANDARD_SCHEMA
