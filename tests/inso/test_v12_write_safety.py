from __future__ import annotations

from pathlib import Path

import pytest

from src.inso.session import SecurityViolation
from src.inso.write_safety import (
    ControlCandidate,
    ControlSemantics,
    FakeWriteGate,
    InsoDraftActions,
    ProductionWriteGate,
    SelectorRegistry,
    WriteAction,
)


class FakeCandidateSource:
    def __init__(self, candidates: tuple[ControlCandidate, ...]) -> None:
        self.items = candidates

    def candidates(self) -> tuple[ControlCandidate, ...]:
        return self.items


class FakeDispatcher:
    def __init__(self) -> None:
        self.dispatched: list[tuple[WriteAction, str, str | None]] = []

    def dispatch_validated(self, action, control, value) -> None:
        self.dispatched.append((action, control.selector_id, value))


def candidate(
    *,
    selector: str = "save-data-control",
    name: str = "保存数据",
    text: str = "保存数据",
    attributes: tuple[tuple[str, str], ...] = (("data-action", "save-data"),),
) -> ControlCandidate:
    return ControlCandidate(
        selector,
        "verified-inquiry-form",
        ControlSemantics("button", name, text, attributes),
    )


def make_actions(candidates: tuple[ControlCandidate, ...], *, enabled: bool = True):
    registry = SelectorRegistry()
    registry.register(
        WriteAction.SAVE_DATA,
        "save-data-control",
        "verified-inquiry-form",
        candidate().semantics,
    )
    dispatcher = FakeDispatcher()
    api = InsoDraftActions(
        gate=FakeWriteGate(enabled=enabled),
        registry=registry,
        candidate_source=FakeCandidateSource(candidates),
        dispatcher=dispatcher,
    )
    return api, registry, dispatcher


def test_closed_enum_and_public_api_have_no_send_or_generic_click_methods() -> None:
    names = {action.name for action in WriteAction}
    assert names == {
        "OPEN_BUSINESS_INQUIRY",
        "NEW_DRAFT",
        "SET_CUSTOMER",
        "SET_QUOTATION_TYPE",
        "SET_PURCHASER",
        "OPEN_AI_ENTRY",
        "SET_AI_INPUT",
        "RUN_AI_RECOGNITION",
        "SAVE_DATA",
    }
    methods = set(dir(InsoDraftActions))
    assert not {"send", "submit", "final_submit", "click", "dispatch"} & methods


@pytest.mark.parametrize(
    "field,value",
    [
        ("accessible_name", "保存并发送"),
        ("visible_text", "发送"),
        ("accessible_name", "Send now"),
        ("visible_text", "Final Submit"),
        ("stable_attributes", (("formaction", "/publish"),)),
    ],
)
def test_semantic_guard_blocks_forbidden_control_even_when_save_data_requested(
    field: str, value: object
) -> None:
    values = {
        "role": "button",
        "accessible_name": "保存数据",
        "visible_text": "保存数据",
        "stable_attributes": (("data-action", "save-data"),),
    }
    values[field] = value
    control = candidate(
        name=values["accessible_name"],
        text=values["visible_text"],
        attributes=values["stable_attributes"],
    )
    api, _, dispatcher = make_actions((control,))

    with pytest.raises(SecurityViolation):
        api.save_data()
    assert dispatcher.dispatched == []


def test_selector_drift_zero_and_multiple_controls_fail_closed() -> None:
    drifted, _, dispatch = make_actions((candidate(name="保存并发送"),))
    with pytest.raises(SecurityViolation):
        drifted.save_data()
    assert dispatch.dispatched == []

    renamed, _, renamed_dispatch = make_actions(
        (candidate(name="删除记录", text="删除记录"),)
    )
    with pytest.raises(SecurityViolation):
        renamed.save_data()
    assert renamed_dispatch.dispatched == []

    missing, _, _ = make_actions(())
    with pytest.raises(SecurityViolation):
        missing.save_data()

    ambiguous, _, ambiguous_dispatch = make_actions((candidate(), candidate()))
    with pytest.raises(SecurityViolation):
        ambiguous.save_data()
    assert ambiguous_dispatch.dispatched == []


def test_selector_deny_identity_can_never_become_actionable() -> None:
    registry = SelectorRegistry()
    registry.deny("save-and-send-button")
    with pytest.raises(SecurityViolation):
        registry.register(
            WriteAction.SAVE_DATA,
            "save-and-send-button",
            "form",
            candidate().semantics,
        )
    with pytest.raises(SecurityViolation):
        registry.register(
            WriteAction.SAVE_DATA,
            "save-and-send-alias",
            "form",
            candidate().semantics,
        )
    assert registry.denied


def test_unknown_action_direct_helper_bypass_and_default_gate_do_not_dispatch() -> None:
    api, _, dispatcher = make_actions((candidate(),))
    with pytest.raises(SecurityViolation):
        api._run("SAVE_AND_SEND")  # type: ignore[arg-type]
    assert dispatcher.dispatched == []

    forbidden = candidate(name="保存并发送", text="保存并发送")
    fake_enabled, _, direct_dispatcher = make_actions((forbidden,), enabled=True)
    with pytest.raises(SecurityViolation):
        fake_enabled._run(WriteAction.SAVE_DATA)
    assert direct_dispatcher.dispatched == []

    default_closed = InsoDraftActions(
        registry=SelectorRegistry(),
        candidate_source=FakeCandidateSource((candidate(),)),
        dispatcher=dispatcher,
    )
    with pytest.raises(SecurityViolation):
        default_closed.save_data()
    with pytest.raises(SecurityViolation):
        default_closed._run(WriteAction.SAVE_DATA)
    assert dispatcher.dispatched == []
    assert isinstance(ProductionWriteGate(), ProductionWriteGate)


def test_fake_gate_allows_only_verified_save_data_action_and_no_coordinate_fallback() -> None:
    api, _, dispatcher = make_actions((candidate(),))
    api.save_data()
    assert dispatcher.dispatched == [(WriteAction.SAVE_DATA, "save-data-control", None)]

    source = Path("src/inso/write_safety.py").read_text(encoding="utf-8").casefold()
    assert "mouse.click" not in source
    assert "coordinates" not in source
    assert "def click(" not in source
