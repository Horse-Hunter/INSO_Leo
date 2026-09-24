"""INSO_V1.0 Windows GUI shell and backend abstraction."""

from .contracts import (
    DiagnosticSnapshot,
    GuiBackend,
    HealthItem,
    HealthReport,
    Order,
    OrderStatus,
    PriceEvidence,
    RunSession,
    RunState,
)
from .mock_backend import MockBackend
from .resources import ResourceManager, RingBufferLog
from .state import make_empty_session

__all__ = [
    "DiagnosticSnapshot",
    "GuiBackend",
    "HealthItem",
    "HealthReport",
    "MockBackend",
    "Order",
    "OrderStatus",
    "PriceEvidence",
    "ResourceManager",
    "RingBufferLog",
    "RunSession",
    "RunState",
    "make_empty_session",
]
