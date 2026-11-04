"""Compatibility facade over the shared automatic order admission policy."""
from .automatic_admission import SHANGHAI, age_reason, source_date

__all__ = ("SHANGHAI", "age_reason", "quotation_age_date")


def quotation_age_date(candidate, current_row, brief_lines, intake_at, *, recorded_source_date=None, as_of=None):
    return source_date(candidate.record_identity, current_row, brief_lines, intake_at, recorded_source_date=recorded_source_date, as_of=as_of)
