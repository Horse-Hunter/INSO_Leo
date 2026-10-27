"""V1 typed immutable ports for existing WorkflowRuntime/Launcher composition.

No queue, worker, browser or durable business permission is implemented here.
Messages stay private in memory; default repr excludes source/customer fields.
"""
import re
from dataclasses import dataclass, field
from enum import Enum
from math import isfinite

from src.research.market_contracts import (
    MarketReadMode,
    MarketReadQuery,
    MarketReadResult,
)
from src.sheets.pending import (
    IdentifyingSnapshot,
    SheetRecordIdentity,
    WorksheetIdentity,
)

_TOKEN = re.compile(r"[A-Za-z0-9_.:-]{1,160}")
_CODE = re.compile(r"[A-Z][A-Z_]{0,63}")
_CLASS = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,63}")
_RESOURCE = {"CDP_PAGE_CREATION_UNCONFIRMED", "CDP_PAGE_OWNERSHIP_UNCONFIRMED",
             "CDP_PAGE_CLEANUP_UNCONFIRMED", "ORDER_RESOURCE_OWNERSHIP_LOST",
             "MODULE_RESOURCE_OWNERSHIP_LOST"}


class MarketModule(str, Enum):
    INQUIRY = "inquiry"
    QUOTATION = "quotation"
    TP = "tp"


class MarketTerminal(str, Enum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MarketFaultScope(str, Enum):
    GLOBAL_STOP = "global_stop"
    SITE_DEFER = "site_defer"
    FAILED = "failed"


def _seconds(value):
    return type(value) in {int, float} and isfinite(value) and value >= 0


@dataclass(frozen=True, slots=True)
class MarketTaskIdentity:
    module: MarketModule
    cycle_id: str
    request_id: str
    domain_task_id: str = field(repr=False)
    source_record: SheetRecordIdentity = field(repr=False)
    version: int = 1

    def __post_init__(self):
        if (type(self.version) is not int or self.version != 1 or not isinstance(self.module, MarketModule)
                or any(not isinstance(v, str) or not _TOKEN.fullmatch(v)
                       for v in (self.cycle_id, self.request_id, self.domain_task_id))):
            raise ValueError("MARKET_TASK_IDENTITY_INVALID")
        record = self.source_record
        if (type(record) is not SheetRecordIdentity or type(record.worksheet) is not WorksheetIdentity
                or type(record.identifying_snapshot) is not IdentifyingSnapshot
                or type(record.row_position) is not int or record.row_position < 1
                or any(not isinstance(v, str) or not v.strip() or len(v) > 256
                       for v in (record.worksheet.spreadsheet, record.worksheet.worksheet))):
            raise ValueError("MARKET_TASK_SOURCE_INVALID")
        snapshot = record.identifying_snapshot
        for value in (snapshot.status, snapshot.importance_raw, snapshot.model, snapshot.brand, snapshot.quantity):
            if (value is not None and type(value) not in {str, int, bool, float}
                    or isinstance(value, str) and len(value) > 8192
                    or isinstance(value, float) and not isfinite(value)):
                raise ValueError("MARKET_TASK_SNAPSHOT_INVALID")


@dataclass(frozen=True, slots=True)
class MarketReadRequest:
    identity: MarketTaskIdentity
    query: MarketReadQuery = field(repr=False)
    due_at: float
    admitted_at: float

    def __post_init__(self):
        if (type(self.identity) is not MarketTaskIdentity or type(self.query) is not MarketReadQuery
                or not _seconds(self.due_at) or not _seconds(self.admitted_at)):
            raise ValueError("MARKET_REQUEST_INVALID")
        expected = MarketReadMode.TP_OFFERS if self.identity.module is MarketModule.TP else MarketReadMode.ORDINARY
        if self.query.mode is not expected:
            raise ValueError("MARKET_MODULE_QUERY_MODE_MISMATCH")


@dataclass(frozen=True, slots=True)
class MarketFault:
    scope: MarketFaultScope
    reason: str
    exception_classes: tuple[str, ...] = ()

    def __post_init__(self):
        if (not isinstance(self.scope, MarketFaultScope) or not isinstance(self.reason, str)
                or not _CODE.fullmatch(self.reason)
                or self.reason not in _RESOURCE | {"MARKET_SOURCE_FAILED", "MARKET_ACTOR_INITIALIZATION_FAILED",
                    "MARKET_SOURCE_TIMEOUT", "MARKET_AUTH_REQUIRED", "MARKET_PROTOCOL_INVALID",
                    "MARKET_RESULT_INVALID", "MARKET_OWNER_REQUIRED"}
                or type(self.exception_classes) is not tuple
                or len(self.exception_classes) > 8
                or any(not isinstance(v, str) or not _CLASS.fullmatch(v) for v in self.exception_classes)):
            raise ValueError("MARKET_FAULT_INVALID")
        if self.reason in _RESOURCE and self.scope is not MarketFaultScope.GLOBAL_STOP:
            raise ValueError("MARKET_RESOURCE_FAULT_MUST_STOP")


@dataclass(frozen=True, slots=True)
class MarketCompletion:
    identity: MarketTaskIdentity
    terminal: MarketTerminal
    started_at: float
    finished_at: float
    result: MarketReadResult | None = field(default=None, repr=False)
    fault: MarketFault | None = None

    def __post_init__(self):
        if (type(self.identity) is not MarketTaskIdentity or not isinstance(self.terminal, MarketTerminal)
                or not _seconds(self.started_at) or not _seconds(self.finished_at)
                or self.finished_at < self.started_at):
            raise ValueError("MARKET_COMPLETION_INVALID")
        if self.terminal is MarketTerminal.SUCCEEDED:
            valid = type(self.result) is MarketReadResult and self.fault is None
        elif self.terminal is MarketTerminal.FAILED:
            valid = self.result is None and type(self.fault) is MarketFault
        else:
            valid = self.result is None and self.fault is None
        if not valid:
            raise ValueError("MARKET_COMPLETION_SHAPE_INVALID")


class MarketStage(str, Enum):
    QUEUED = "queued"
    STARTED = "started"
    READING = "reading"
    FINISHED = "finished"


@dataclass(frozen=True, slots=True)
class MarketProgress:
    identity: MarketTaskIdentity
    stage: MarketStage
    at: float

    def __post_init__(self):
        if (type(self.identity) is not MarketTaskIdentity or not isinstance(self.stage, MarketStage)
                or not _seconds(self.at)):
            raise ValueError("MARKET_PROGRESS_INVALID")
