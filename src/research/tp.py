"""Compatibility exports; detailed.py is the single acquisition/ranking authority."""
from .detailed import (
    TpFx,
    TpOffer,
    TpQuote,
    TpResearchResult,
    TpSourceResult,
    collect_tp,
    collect_tp_offers,
    distinct_two,
    execute_tp,
    finish_tp,
    select_tp_offers,
)

__all__ = ["TpFx", "TpOffer", "TpQuote", "TpResearchResult", "TpSourceResult", "collect_tp",
           "collect_tp_offers", "distinct_two", "execute_tp", "finish_tp", "select_tp_offers"]
