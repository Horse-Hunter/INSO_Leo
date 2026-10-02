"""Allowlisted INSO actions and narrowly authorized final submission.

Production write gates default closed and are not read from runtime config.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from .session import SecurityViolation


class WriteAction(StrEnum):
    OPEN_BUSINESS_INQUIRY = "OPEN_BUSINESS_INQUIRY"
    NEW_DRAFT = "NEW_DRAFT"
    SET_CUSTOMER = "SET_CUSTOMER"
    SET_QUOTATION_TYPE = "SET_QUOTATION_TYPE"
    SET_PURCHASER = "SET_PURCHASER"
    OPEN_AI_ENTRY = "OPEN_AI_ENTRY"
    SET_AI_INPUT = "SET_AI_INPUT"
    RUN_AI_RECOGNITION = "RUN_AI_RECOGNITION"
    AI_ENTRY_COMMIT = "AI_ENTRY_COMMIT"
    SAVE_DATA = "SAVE_DATA"
    SAVE_AND_SEND = "SAVE_AND_SEND"


WRITE_ACTION_ALLOWLIST = frozenset(WriteAction)

_DENIED_SEMANTICS = (
    "保存并发送",
    "保存並發送",
    "提交并发送",
    "确认发送",
    "发送",
    "send",
    "submit",
    "final submit",
    "publish",
)
_DENIED_SELECTOR_WORDS = (
    "save-and-send",
    "save_send",
    "send",
    "final-submit",
    "submit",
    "publish",
)


@dataclass(frozen=True, slots=True)
class ControlSemantics:
    role: str
    accessible_name: str
    visible_text: str
    stable_attributes: tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class ControlCandidate:
    selector_id: str
    scope_id: str
    semantics: ControlSemantics
    enabled: bool = True
    visible: bool = True


@dataclass(frozen=True, slots=True)
class DeniedSelector:
    selector_id: str
    reason: str = "forbidden semantic control"


@dataclass(frozen=True, slots=True)
class SelectorDefinition:
    selector_id: str
    scope_id: str
    expected_semantics: ControlSemantics


class FeatureGate(Protocol):
    def require_open(self) -> None: ...


class ProductionWriteGate:
    """Unconditionally closed until a future reviewed implementation gate."""

    def require_open(self) -> None:
        raise SecurityViolation("production write gate is closed")

    def require_save_and_send(self) -> None:
        raise SecurityViolation("save-and-send is not authorized")


class OwnerAuthorizedSaveAndSendGate(ProductionWriteGate):
    """Owner 2026-10-02 exception; Save Data and all other writes stay closed.

    Explicit production composition only. Never enabled by runtime configuration.
    This does not authorize this executor to run a submission test.
    """

    def require_save_and_send(self) -> None:
        pass


class FakeWriteGate:
    """Explicit test-only gate; not wired by launcher or runtime configuration."""

    def __init__(self, *, enabled: bool = False) -> None:
        self._enabled = enabled

    def require_open(self) -> None:
        if not self._enabled:
            raise SecurityViolation("fake write gate is closed")


class SelectorRegistry:
    def __init__(self) -> None:
        self._allow: dict[WriteAction, SelectorDefinition] = {}
        self._deny: dict[str, DeniedSelector] = {}

    @property
    def denied(self) -> tuple[DeniedSelector, ...]:
        return tuple(self._deny[key] for key in sorted(self._deny))

    def deny(self, selector_id: str) -> None:
        if not selector_id:
            raise ValueError("selector identity is required")
        self._deny[selector_id] = DeniedSelector(selector_id)
        for action, registered in tuple(self._allow.items()):
            if registered.selector_id == selector_id:
                del self._allow[action]

    def register(
        self,
        action: WriteAction,
        selector_id: str,
        scope_id: str,
        expected_semantics: ControlSemantics,
    ) -> None:
        if not isinstance(action, WriteAction):
            raise SecurityViolation("unknown write action")
        if not selector_id or not scope_id:
            raise SecurityViolation("selector and scope identities are required")
        assert_safe_control_semantics(expected_semantics, action=action)
        if selector_id in self._deny or _contains_denied_selector_term(selector_id):
            self.deny(selector_id)
            raise SecurityViolation("selector identity is denied")
        if action in self._allow:
            raise SecurityViolation("action already has a selector")
        self._allow[action] = SelectorDefinition(
            selector_id, scope_id, expected_semantics
        )

    def resolve(
        self,
        action: WriteAction,
        candidates: tuple[ControlCandidate, ...],
    ) -> ControlCandidate:
        if not isinstance(action, WriteAction) or action not in WRITE_ACTION_ALLOWLIST:
            raise SecurityViolation("unknown write action")
        if action not in self._allow:
            raise SecurityViolation("allowlisted selector is not registered")
        definition = self._allow[action]
        matches = tuple(
            item
            for item in candidates
            if item.selector_id == definition.selector_id
            and item.scope_id == definition.scope_id
        )
        if not matches:
            raise SecurityViolation("allowlisted control was not found")
        if len(matches) != 1:
            raise SecurityViolation("allowlisted control is ambiguous")
        control = matches[0]
        if control.selector_id in self._deny:
            raise SecurityViolation("resolved selector is denied")
        if not control.enabled or not control.visible:
            raise SecurityViolation("resolved control is not actionable")
        assert_safe_control_semantics(control.semantics, action=action)
        if control.semantics != definition.expected_semantics:
            raise SecurityViolation("resolved control semantics changed")
        return control


class _ActionDispatcher(Protocol):
    def dispatch_validated(
        self, action: WriteAction, control: ControlCandidate, value: str | None
    ) -> None: ...


class _CandidateSource(Protocol):
    def candidates(self) -> tuple[ControlCandidate, ...]: ...


class InsoDraftActions:
    """Narrow public business API; generic click/submit APIs do not exist."""

    def __init__(
        self,
        *,
        gate: FeatureGate | None = None,
        registry: SelectorRegistry,
        candidate_source: _CandidateSource,
        dispatcher: _ActionDispatcher,
    ) -> None:
        self._gate = gate or ProductionWriteGate()
        self._registry = registry
        self._candidate_source = candidate_source
        self._dispatcher = dispatcher

    def open_business_inquiry(self) -> None:
        self._run(WriteAction.OPEN_BUSINESS_INQUIRY)

    def new_draft(self) -> None:
        self._run(WriteAction.NEW_DRAFT)

    def set_customer(self, value: str) -> None:
        self._run(WriteAction.SET_CUSTOMER, value)

    def set_quotation_type(self, value: str) -> None:
        self._run(WriteAction.SET_QUOTATION_TYPE, value)

    def set_purchaser(self, value: str) -> None:
        self._run(WriteAction.SET_PURCHASER, value)

    def open_ai_entry(self) -> None:
        self._run(WriteAction.OPEN_AI_ENTRY)

    def set_ai_input(self, value: str) -> None:
        self._run(WriteAction.SET_AI_INPUT, value)

    def run_ai_recognition(self) -> None:
        self._run(WriteAction.RUN_AI_RECOGNITION)

    def commit_ai_entry(self) -> None:
        """Hand the recognized row back through the panel's own commit control.

        Verified live (2026-10-01): the AI录单 dialog's 保存数据 control runs
        ``pasteImport() -> AiImport.doImport()``, which is ``returnSet(buildResult())``
        plus ``windowsClose()`` -- a purely client-side hand-back whose dialog
        close callback then runs ``ai_appendRow()`` to reload the bill grid.
        It is *not* a server Save; that remains the gated ``WriteAction.SAVE_DATA``
        (``button#btnSave`` -> ``bill_save_auto``), and it stays unreachable here.
        """

        self._run(WriteAction.AI_ENTRY_COMMIT)

    def save_data(self) -> None:
        self._run(WriteAction.SAVE_DATA)

    def save_and_send(self) -> None:
        self._run(WriteAction.SAVE_AND_SEND)

    def _run(self, action: WriteAction, value: str | None = None) -> None:
        if not isinstance(action, WriteAction) or action not in WRITE_ACTION_ALLOWLIST:
            raise SecurityViolation("unknown write action")
        # The production gate protects standalone Save; the explicit Owner
        # exception below protects Save-and-Send separately. The
        # V1.2 pre-save workflow is explicitly allowed to prepare an unsaved
        # draft and validate AI read-back while this gate remains closed.
        if action is WriteAction.SAVE_DATA:
            self._gate.require_open()
        if action is WriteAction.SAVE_AND_SEND:
            authorize = getattr(self._gate, "require_save_and_send", None)
            if not callable(authorize):
                raise SecurityViolation("save-and-send is not authorized")
            authorize()
        control = self._registry.resolve(action, self._candidate_source.candidates())
        # The semantic check runs on the freshly resolved control immediately
        # before the private dispatcher is called.
        assert_safe_control_semantics(control.semantics, action=action)
        self._dispatcher.dispatch_validated(action, control, value)


def assert_safe_control_semantics(
    semantics: ControlSemantics, *, action: WriteAction | None = None,
) -> None:
    if action is WriteAction.SAVE_AND_SEND:
        if semantics != ControlSemantics(
            "button", "保存并发送", "保存并发送", (("id", "btnSave2"),)
        ):
            raise SecurityViolation("save-and-send control identity changed")
        return
    values = [semantics.role, semantics.accessible_name, semantics.visible_text]
    values.extend(f"{key}={value}" for key, value in semantics.stable_attributes)
    normalized = tuple(_semantic_normalize(value) for value in values)
    for denied in _DENIED_SEMANTICS:
        needle = _semantic_normalize(denied)
        if any(needle and needle in value for value in normalized):
            raise SecurityViolation("resolved control has forbidden semantics")


def _semantic_normalize(value: str) -> str:
    return unicodedata.normalize("NFKC", value).strip().casefold()


def _contains_denied_selector_term(selector_id: str) -> bool:
    value = unicodedata.normalize("NFKC", selector_id).casefold()
    return any(term in value for term in _DENIED_SELECTOR_WORDS)
