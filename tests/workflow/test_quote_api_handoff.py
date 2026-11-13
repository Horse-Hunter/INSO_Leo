"""RFQ-016 phase 1: API input write -> owned page reload -> native 更新报价 click.

Only the container-bound script button stays on CDP. The reload is the one new
step: the page's client model must match the API-written row before the script
reads it. No cell readback is added, and the click is still dispatched once.
"""

import pytest

from src.workflow.v12_faults import FaultScope, V12Fault
from src.workflow.v13_quotation import QuotationOutcome
from src.workflow.v13_quote_update import (
    UpdateAttemptUnconfirmed,
    UpdateClickUnconfirmed,
    V13QuotationUpdater,
)
from tests.workflow.test_v13_quote_update import POPUP, Actions, Input, Source, found


class ApiInput(Input):
    """The same input contract, written by the API transport (outside the page)."""

    external_write = True


class RecordedActions(Actions):
    def __init__(self, source_reader):
        super().__init__(source_reader)
        self.order = []
        self.refresh_error = None

    def open_quote_input(self):
        super().open_quote_input()
        self.order.append("open")

    def refresh_after_external_write(self):
        self.order.append("refresh")
        if self.refresh_error is not None:
            raise self.refresh_error

    def click_update_quote(self):
        super().click_update_quote()
        self.order.append("click")


def build(external):
    src, io = Source(), (ApiInput() if external else Input())
    actions, elapsed = RecordedActions(src), [0.0]
    updater = V13QuotationUpdater(
        source=src, quotation_input=io, actions=actions,
        wait=lambda seconds: elapsed.__setitem__(0, elapsed[0] + seconds) or False,
        clock=lambda: elapsed[0])
    return updater, src, io, actions


def test_api_write_reloads_the_page_before_the_single_click():
    updater, src, io, actions = build(external=True)
    actions.popups = [POPUP]

    result = updater.update_one(found())

    assert result.outcome is QuotationOutcome.UPDATED_INSERTED
    assert actions.order == ["open", "refresh", "click"]
    assert len(io.writes) == 1 and io.reads == 0  # Still no 14-cell readback.
    assert src.clicks == 1


def test_cdp_transport_never_adds_a_reload():
    updater, _, _, actions = build(external=False)
    actions.popups = [POPUP]
    assert updater.update_one(found()).outcome is QuotationOutcome.UPDATED_INSERTED
    assert actions.order == ["open", "click"]


def test_failed_reload_retries_the_same_row_without_a_second_click():
    updater, src, io, actions = build(external=True)
    actions.popups = [POPUP]
    actions.refresh_error = UpdateAttemptUnconfirmed("UPDATE_RESULT_UNCONFIRMED")
    calls = {"n": 0}
    original = actions.refresh_after_external_write

    def refresh_once():
        calls["n"] += 1
        if calls["n"] > 1:
            actions.refresh_error = None
        return original()

    actions.refresh_after_external_write = refresh_once

    assert updater.update_one(found()).outcome is QuotationOutcome.UPDATED_INSERTED
    assert len(io.writes) == 2 and src.clicks == 1


def test_unproven_script_settlement_keeps_the_uncertain_hold_and_never_clicks():
    updater, src, _, actions = build(external=True)
    actions.refresh_error = V12Fault(FaultScope.GLOBAL_STOP, "GOOGLE_SCRIPT_SETTLEMENT_UNCONFIRMED")

    result = updater.update_one(found())

    assert result.outcome is QuotationOutcome.ROW_FAILED
    assert result.effect_uncertain is True
    assert src.clicks == 0
    assert actions.order == ["open", "refresh"]


def test_click_timeout_after_reload_is_unknown_and_not_retried():
    updater, _src, _, actions = build(external=True)
    actions.popups = [POPUP]

    def click_then_fail():
        # The real native click timeout is UpdateClickUnconfirmed: dispatched,
        # delivery/result unknown, never retried.
        actions.clicks += 1
        raise UpdateClickUnconfirmed("UPDATE_RESULT_UNCONFIRMED")

    actions.click_update_quote = click_then_fail

    result = updater.update_one(found())

    assert result.outcome is QuotationOutcome.ROW_FAILED
    assert result.effect_uncertain is True
    assert actions.clicks == 1
    assert actions.order == ["open", "refresh"]


@pytest.mark.parametrize("external", [True, False])
def test_payload_is_identical_for_both_transports(external):
    updater, _, io, actions = build(external=external)
    actions.popups = [POPUP]
    updater.update_one(found())
    assert io.writes == [found().quotation.payload]


# --- ambiguous API input write: durable hold, never a retry, never a click ----
from src.sheets.quotation_input import (
    QuotationInputAttemptFailed,
    QuotationInputWriteUncertain,
)


def test_ambiguous_api_write_holds_the_order_and_never_clicks():
    updater, src, io, actions = build(external=True)
    held = []
    updater._persist_uncertain = held.append
    io.write_failures = [QuotationInputWriteUncertain("QUOTE_INPUT_WRITE_UNCERTAIN")]

    result = updater.update_one(found())

    assert result.outcome is QuotationOutcome.ROW_FAILED
    assert result.effect_uncertain is True
    assert len(io.writes) == 1          # No four-attempt blind retry.
    assert src.clicks == 0 and actions.order == ["open"]
    assert held and held[0].effect_uncertain is True


def test_ambiguous_api_write_without_a_hold_is_still_not_clicked():
    updater, src, io, _actions = build(external=True)
    updater._persist_uncertain = None
    io.write_failures = [QuotationInputWriteUncertain("QUOTE_INPUT_WRITE_UNCERTAIN")]

    result = updater.update_one(found())

    assert result.effect_uncertain is True and src.clicks == 0
    assert len(io.writes) == 1


def test_definite_api_write_rejection_still_retries_then_fails_without_click():
    updater, src, io, _actions = build(external=True)
    io.write_failures = [QuotationInputAttemptFailed("QUOTE_INPUT_WRITE_FAILED")] * 4

    result = updater.update_one(found())

    assert result.outcome is QuotationOutcome.ROW_FAILED
    assert result.effect_uncertain is False   # Nothing was written, nothing clicked.
    assert len(io.writes) == 4 and src.clicks == 0
