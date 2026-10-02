"""The GUI allowlists are a hand-maintained mirror of the workflow contracts.

The GUI deliberately does not import workflow internals, so ``V12ReasonCode`` /
``V12EventCode`` / ``V12AlertCode`` / ``V12BusinessLabel`` are re-declared in
``src/gui/contracts.py``. Nothing mechanically tied them to the workflow source,
and they drifted: the workflow persisted ``NOTIFICATION_SENT`` and the GUI could
not decode it.

That is not cosmetic. ``src/launcher/v12_gui.py::read_v12_order_state`` builds a
``V12ReasonCode`` from every stored event, so one undecodable row raises
``ValueError`` and the *entire* order detail / event-history panel is lost for
that order. It happened live against the production database.

These tests pin the mirror in both directions (missing member, extra member and
renamed value) so the drift fails in CI instead of in front of the operator.
"""

from __future__ import annotations

import pytest

from src.gui import contracts as gui
from src.workflow import v12_contracts as workflow

MIRRORED_ENUMS = (
    pytest.param(gui.V12BusinessLabel, workflow.BusinessLabel, id="business-label"),
    pytest.param(gui.V12AlertCode, workflow.AlertType, id="alert-type"),
    pytest.param(gui.V12ReasonCode, workflow.ReasonCode, id="reason-code"),
    pytest.param(gui.V12EventCode, workflow.EventType, id="event-type"),
)


def _members(enum_type: type) -> dict[str, str]:
    return {member.name: member.value for member in enum_type}


@pytest.mark.parametrize(("gui_enum", "workflow_enum"), MIRRORED_ENUMS)
def test_gui_allowlist_mirrors_the_workflow_contract(gui_enum: type, workflow_enum: type) -> None:
    """Name-for-name and value-for-value equality between mirror and source."""

    assert _members(gui_enum) == _members(workflow_enum), (
        f"{gui_enum.__name__} has drifted from workflow.{workflow_enum.__name__}; "
        "a code the workflow can persist but the GUI cannot decode breaks the "
        "order detail view at runtime"
    )


def test_every_workflow_reason_code_is_decodable_by_the_gui() -> None:
    """The concrete failure mode: decoding each stored reason code must not raise."""

    for code in workflow.ReasonCode:
        assert gui.V12ReasonCode(code.value) is not None


def test_every_workflow_event_type_is_decodable_by_the_gui() -> None:
    for event in workflow.EventType:
        assert gui.V12EventCode(event.value) is not None


def test_the_allowlist_stays_strict() -> None:
    """Completeness is fixed by mirroring, never by loosening the allowlist."""

    with pytest.raises(ValueError):
        gui.V12ReasonCode("NOT_A_REAL_REASON_CODE")
    with pytest.raises(ValueError):
        gui.V12EventCode("NOT_A_REAL_EVENT_TYPE")
