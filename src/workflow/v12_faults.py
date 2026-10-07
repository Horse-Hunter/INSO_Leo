"""Explicit V1.2 pause versus shared-infrastructure stop boundary."""
from enum import StrEnum

from .service import ResearchPreparationError


class FaultScope(StrEnum):
    V12_PAUSE = "V12_PAUSE"
    GLOBAL_STOP = "GLOBAL_STOP"


class V12Fault(ResearchPreparationError):
    def __init__(self, scope: FaultScope, reason: str):
        super().__init__(reason)
        self.scope = scope
        self.reason = reason
