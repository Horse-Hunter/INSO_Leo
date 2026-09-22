"""Public Research V1 contracts and local output helpers."""

from .contracts import (
    ResearchInput,
    ResearchReasonCode,
    ResearchResult,
    ResearchStatus,
)
from .excel_output import (
    ExcelConsistencyError,
    ExcelOutputError,
    ExcelWriteError,
    ResearchExcelOutput,
)
from .finalize import finalize_research_result
from .icnet import (
    BrandResolution,
    IcNetAdapter,
    IcNetLogin,
    IcNetPage,
    IcNetPageUnavailable,
    IcNetParseError,
    IcNetResult,
    IcNetRow,
    PlaywrightIcNetClient,
    classify_stock,
    extract_manufacturer_display,
    parse_icnet_rows,
    select_brand_by_frequency,
    sum_certified_stock,
)

__all__ = [
    "BrandResolution",
    "ExcelConsistencyError",
    "ExcelOutputError",
    "ExcelWriteError",
    "IcNetAdapter",
    "IcNetLogin",
    "IcNetPage",
    "IcNetPageUnavailable",
    "IcNetParseError",
    "IcNetResult",
    "IcNetRow",
    "PlaywrightIcNetClient",
    "ResearchExcelOutput",
    "ResearchInput",
    "ResearchReasonCode",
    "ResearchResult",
    "ResearchStatus",
    "classify_stock",
    "extract_manufacturer_display",
    "finalize_research_result",
    "parse_icnet_rows",
    "select_brand_by_frequency",
    "sum_certified_stock",
]
