"""INSO_V1.0 Windows GUI shell and backend abstraction."""

from .contracts import (
    DiagnosticSnapshot,
    GuiBackend,
    HealthItem,
    HealthReport,
    Order,
    OrderStatus,
    RunSession,
    RunState,
    SourceDetail,
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
    "ResourceManager",
    "RingBufferLog",
    "RunSession",
    "RunState",
    "SourceDetail",
    "make_empty_session",
]
