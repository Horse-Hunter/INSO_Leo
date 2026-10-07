"""Synthetic combined acceptance; no live I/O, credentials or business writes."""

import sqlite3
from dataclasses import replace
from types import SimpleNamespace

import pytest

from src.gui.app import _order_row_style, _v12_status_text
from src.launcher.v13_integration import (
    notify_quotation,
    quotation_gui,
    quotation_location,
)
from src.research import ResearchResult, ResearchStatus
from src.sheets import query_pending_records
from src.workflow.store import WorkflowStateStore
from src.workflow.v12_contracts import DeliveryOutcome
from src.workflow.v12_faults import FaultScope, V12Fault
from src.workflow.v12_notifications import (
    FakeNotificationTransport,
    V12NotificationWorker,
)
from src.workflow.v12_store import V12Store, migrate_v12
from src.workflow.v13_integration import CombinedCycle, V13HoldStore, V13IntegratedCycle
from src.workflow.v13_quotation import (
    QuotationOutcome,
    RowErrorReason,
    V13QuotationCycle,
    V13QuotationResult,
)
from tests.workflow.test_rfq003_resilience import rows
from tests.workflow.test_v12_flow import NOW, _make_flow
from tests.workflow.test_v13_quotation import WS, Operations, Quotes, Sheets, source


@pytest.mark.parametrize("count", [0, 1, 2, 3])
@pytest.mark.parametrize("status", [ResearchStatus.SUCCESS, ResearchStatus.EXCEPTION])
def test_combined_real_v12_cooldown_only_between_rows(tmp_path, count, status):
    flow, *_ = _make_flow(tmp_path)
    events = []
    flow._research.execute = lambda i: (
        events.append("V12") or ResearchResult(i.inquiry_id, status)
    )
    flow._row_wait = lambda s: events.append(s) or False
    first = rows()[0]
    records = tuple(
        replace(
            first,
            row_position=3 + i,
            record_identity=replace(first.record_identity, row_position=3 + i),
        )
        for i in range(count)
    )
    flow.poll_and_process = lambda reader, worksheet, now: flow.process_pending(
        records, now=now
    )
    combined = CombinedCycle(
        flow, lambda _: events.append("V13"), on_pause=lambda _: None
    )
    combined.run(None, [WS], now=NOW)
    assert events == [
        v for i in range(count) for v in ([180, "V12"] if i else ["V12"])
    ] + ["V13"]


@pytest.mark.parametrize("scope", [FaultScope.V12_PAUSE, FaultScope.GLOBAL_STOP])
def test_combined_fault_scope_and_no_repeat_v12(scope):
    events = []

    def purchase(*args, **kwargs):
        events.append("V12")
        raise V12Fault(
            scope,
            "IC_NET_UNAVAILABLE"
            if scope is FaultScope.V12_PAUSE
            else "INSO_AUTHENTICATION_REQUIRED",
        )

    flow = SimpleNamespace(begin_poll_cycle=lambda: None, poll_and_process=purchase)
    combined = CombinedCycle(
        flow, lambda _: events.append("V13"), on_pause=lambda _: events.append("pause")
    )
    if scope is FaultScope.GLOBAL_STOP:
        with pytest.raises(V12Fault):
            combined.run(None, [WS], now=NOW)
        assert events == ["V12"]
    else:
        combined.run(None, [WS], now=NOW)
        combined.run(None, [WS], now=NOW)
        assert events == ["V12", "pause", "V13", "V13"]


def fixture(tmp_path, responses):
    db = tmp_path / "workflow.sqlite3"
    store = WorkflowStateStore(db)
    sheets = Sheets([source(2, "未发")])
    for record in query_pending_records(sheets, WS):
        store.enqueue(record, now=NOW)
    migrate_v12(db, tmp_path / "backups", quiesce=__import__("contextlib").nullcontext)
    holds = V13HoldStore(db)
    holds.migrate()
    ledger = V12Store(db)
    sheets.rows = [source(2)]
    quotes = Quotes(responses)
    cycle = V13QuotationCycle(
        reader=sheets,
        store=store,
        operations=Operations(),
        clock=lambda: (
            __import__("tests.inso.test_v13_quotation_read", fromlist=["NOW"]).NOW
        ),
        wait=lambda _: False,
        quote_reader=quotes,
    )
    observed = []

    def integrated(update=lambda r: r):
        return V13IntegratedCycle(
            reader=sheets,
            store=store,
            holds=holds,
            cycle=cycle,
            updater_factory=lambda: SimpleNamespace(update_one=update),
            notify=lambda r, k, e: notify_quotation(ledger, r, k, e, at=NOW),
            observe=lambda r, k: observed.append((r, k)),
        )

    return db, store, sheets, holds, ledger, quotes, integrated, observed


def test_no_quote_requeries_next_cycle_without_hold_or_mail(tmp_path):
    db, _store, _sheets, holds, _ledger, quotes, make, _ = fixture(tmp_path, [(), ()])
    make().run(WS)
    make().run(WS)
    assert len(quotes.calls) == 2 and holds.active() == ()
    with sqlite3.connect(db) as c:
        assert (
            c.execute(
                "SELECT count(*) FROM workflow_v12_notification_commands"
            ).fetchone()[0]
            == 0
        )


@pytest.mark.parametrize("reason", list(RowErrorReason))
def test_explicit_failure_hold_restart_skip_mail_and_owner_completion(tmp_path, reason):
    from tests.inso.test_v13_quotation_read import quote

    db, _store, sheets, holds, _ledger, quotes, make, observed = fixture(
        tmp_path, [(quote(),)]
    )
    fail = lambda r: replace(
        r, outcome=QuotationOutcome.ROW_FAILED, row_error_reason=reason
    )
    make(fail).run(WS)
    V13HoldStore(
        db
    ).migrate()  # repeated migration preserves pending notifications/history
    make().run(WS)
    assert len(quotes.calls) == 1 and len(holds.active()) == 1
    with sqlite3.connect(db) as c:
        assert (
            c.execute(
                "SELECT count(*) FROM workflow_v12_notification_commands"
            ).fetchone()[0]
            == 1
        )
        assert c.execute("PRAGMA foreign_key_check").fetchall() == []
    sheets.rows = [source(2, "采购已报价")]
    make().run(WS)
    assert (
        holds.active() == ()
        and observed[-1][0].outcome is QuotationOutcome.UPDATED_ALREADY_EXISTS
    )
    assert len(quotes.calls) == 1
    migrate_v12(
        db, tmp_path / "backups", quiesce=__import__("contextlib").nullcontext
    )  # backward v1.2 schema accepted


def test_crash_before_final_result_does_not_hold(tmp_path):
    from tests.inso.test_v13_quotation_read import quote

    _db, _store, _sheets, holds, _ledger, quotes, make, _ = fixture(
        tmp_path, [(quote(),), ()]
    )

    def crash(_):
        raise SystemExit("simulated process crash")

    with pytest.raises(SystemExit):
        make(crash).run(WS)
    assert holds.active() == ()
    make().run(WS)
    assert len(quotes.calls) == 2


def test_unresolved_no_fake_inquiry_and_notification_pending(tmp_path):
    db, store, sheets, holds, ledger, quotes, make, _ = fixture(tmp_path, [])
    sheets.rows = [source(9, model="OTHER")]
    make().run(WS)
    make().run(WS)
    assert len(store.all_items()) == 1 and len(holds.active()) == 1 and not quotes.calls
    transport = FakeNotificationTransport(
        {"owner": (DeliveryOutcome.RETRYABLE_FAILURE,)}
    )
    V12NotificationWorker(ledger, transport).run_due(now=NOW)
    with sqlite3.connect(db) as c:
        assert (
            c.execute(
                "SELECT inquiry_id FROM workflow_v12_notification_commands"
            ).fetchone()[0]
            is None
        )
        assert (
            c.execute(
                "SELECT outcome FROM workflow_v12_notification_recipients"
            ).fetchone()[0]
            == "OPERATIONAL_RETRYABLE_FAILURE"
        )
        assert c.execute("PRAGMA foreign_key_check").fetchall() == []


def test_reason_change_new_notification_episode(tmp_path):
    db, store, _sheets, holds, ledger, _quotes, _make, _observed = fixture(tmp_path, [])
    i = store.all_items()[0]
    result = V13QuotationResult(
        i.inquiry_id,
        i.record_identity,
        "MPN",
        QuotationOutcome.ROW_FAILED,
        None,
        RowErrorReason.UPDATE_RESULT_UNCONFIRMED,
        WS,
        2,
    )
    for reason in [
        RowErrorReason.UPDATE_RESULT_UNCONFIRMED,
        RowErrorReason.UPDATE_RESULT_UNCONFIRMED,
        RowErrorReason.SOURCE_STATUS_NOT_UPDATED,
    ]:
        result = replace(result, row_error_reason=reason)
        key, episode = holds.hold(result, i.record_identity)
        notify_quotation(ledger, result, key, episode, at=NOW)
    with sqlite3.connect(db) as c:
        assert (
            c.execute(
                "SELECT count(*) FROM workflow_v12_notification_commands"
            ).fetchone()[0]
            == 2
        )


@pytest.mark.parametrize(
    "outcome,label,style",
    [
        (QuotationOutcome.NO_RECENT_QUOTE, "等待采购报价", "legacy"),
        (QuotationOutcome.ROW_FAILED, "报价处理异常，需人工处理", "error"),
        (QuotationOutcome.UPDATED_INSERTED, "采购已报价", "completed"),
        (QuotationOutcome.UPDATED_ALREADY_EXISTS, "采购已报价", "completed"),
    ],
)
def test_gui_projection(outcome, label, style):
    result = V13QuotationResult("id", None, None, outcome, None)
    dto = quotation_gui(result, "id")
    assert _v12_status_text(dto, "") == label
    assert _order_row_style(SimpleNamespace(), v12_state=dto) == style


@pytest.mark.parametrize(
    "config",
    [
        {},
        {"quotation_input": {}},
        {
            "quotation_input": {
                "gid": "0",
                "input_row": None,
                "first_column": 1,
            }
        },
    ],
)
def test_missing_geometry_fail_closed(config):
    with pytest.raises(V12Fault) as exc:
        quotation_location({"spreadsheet_id": "fake", **config})
    assert exc.value.scope is FaultScope.GLOBAL_STOP


@pytest.mark.parametrize(
    "reason",
    [
        "INSO_AUTHENTICATION_REQUIRED",
        "SHEETS_READ_UNAVAILABLE",
        "WORKFLOW_LEDGER_UNAVAILABLE",
        "CDP_RECONNECT_EXHAUSTED",
    ],
)
def test_shared_fault_stops_both_before_quotation(reason):
    events = []

    def fail(*args, **kwargs):
        raise V12Fault(FaultScope.GLOBAL_STOP, reason)

    combined = CombinedCycle(
        SimpleNamespace(begin_poll_cycle=lambda: None, poll_and_process=fail),
        lambda _: events.append("V13"),
        on_pause=lambda _: events.append("pause"),
    )
    with pytest.raises(V12Fault):
        combined.run(None, [WS], now=NOW)
    assert not events


def test_row_failure_continues_next_quote_in_same_cycle_without_cooldown(tmp_path):
    from tests.inso.test_v13_quotation_read import NOW as QUOTE_NOW
    from tests.inso.test_v13_quotation_read import quote

    _db, store, sheets, holds, ledger, quotes, _make, observed = fixture(
        tmp_path, [(quote(),), (quote(model="MPN2"),)]
    )
    records = query_pending_records(Sheets([source(3, "未发", model="MPN2")]), WS)
    store.enqueue(records[0], now=NOW)
    sheets.rows = [source(2), source(3, model="MPN2")]
    waits = []
    cycle = V13QuotationCycle(
        reader=sheets,
        store=store,
        operations=Operations(),
        clock=lambda: QUOTE_NOW,
        wait=lambda s: waits.append(s) or False,
        quote_reader=quotes,
    )

    def update(result):
        return replace(
            result,
            outcome=QuotationOutcome.ROW_FAILED
            if result.queried_mpn == "MPN"
            else QuotationOutcome.UPDATED_INSERTED,
            row_error_reason=RowErrorReason.UPDATE_RESULT_UNCONFIRMED
            if result.queried_mpn == "MPN"
            else None,
        )

    service = V13IntegratedCycle(
        reader=sheets,
        store=store,
        holds=holds,
        cycle=cycle,
        updater_factory=lambda: SimpleNamespace(update_one=update),
        notify=lambda r, k, e: notify_quotation(ledger, r, k, e, at=NOW),
        observe=lambda r, k: observed.append(r),
    )
    results = service.run(WS)
    assert [r.outcome for r in results] == [
        QuotationOutcome.ROW_FAILED,
        QuotationOutcome.UPDATED_INSERTED,
    ]
    assert waits == [] and len(holds.active()) == 1


def test_corrupt_hold_is_shared_fault(tmp_path):
    db, _store, _sheets, _holds, _ledger, _quotes, make, _ = fixture(tmp_path, [])
    with sqlite3.connect(db) as c:
        c.execute(
            "INSERT INTO workflow_v13_holds VALUES ('bad','{}','{}','SOURCE_CHANGED',1,1)"
        )
    with pytest.raises(V12Fault) as exc:
        make().run(WS)
    assert exc.value.scope is FaultScope.GLOBAL_STOP


def test_upgrade_preserves_existing_v12_notification_recipients_and_events(tmp_path):
    from contextlib import nullcontext

    from src.workflow.v12_contracts import (
        NotificationCommand,
        NotificationKind,
        NotificationRecipient,
    )

    db = tmp_path / "workflow.sqlite3"
    workflow = WorkflowStateStore(db)
    workflow.enqueue(query_pending_records(Sheets([source(2, "未发")]), WS)[0], now=NOW)
    inquiry = workflow.all_items()[0].inquiry_id
    migrate_v12(db, tmp_path / "backups", quiesce=nullcontext)
    ledger = V12Store(db)
    ledger.enqueue_notification(
        NotificationCommand(
            "legacy-mail",
            inquiry,
            NotificationKind.PURCHASE_EXCEPTION,
            (NotificationRecipient("owner", "linan229@qq.com"),),
            "synthetic",
            "synthetic",
            None,
            NOW,
        )
    )
    with sqlite3.connect(db) as c:
        before = {
            name: c.execute("SELECT * FROM " + name).fetchall()
            for name in (
                "workflow_items",
                "workflow_v12_notification_commands",
                "workflow_v12_notification_recipients",
                "workflow_v12_events",
            )
        }
    V13HoldStore(db).migrate()
    with sqlite3.connect(db) as c:
        assert all(
            c.execute("SELECT * FROM " + name).fetchall() == records
            for name, records in before.items()
        )
        assert c.execute("PRAGMA foreign_key_check").fetchall() == []
        assert c.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    commands = ledger.claim_due_notifications(now=NOW)
    assert len(commands) == 1 and commands[0].inquiry_id == inquiry


def test_restart_repairs_crash_between_hold_commit_and_notification_enqueue(tmp_path):
    from tests.inso.test_v13_quotation_read import quote

    db, _store, _sheets, holds, _ledger, quotes, make, _ = fixture(
        tmp_path, [(quote(),)]
    )
    service = make(
        lambda r: replace(
            r,
            outcome=QuotationOutcome.ROW_FAILED,
            row_error_reason=RowErrorReason.UPDATE_RESULT_UNCONFIRMED,
        )
    )

    def failed_enqueue(*args):
        raise V12Fault(FaultScope.GLOBAL_STOP, "WORKFLOW_LEDGER_UNAVAILABLE")

    service.notify = failed_enqueue
    with pytest.raises(V12Fault):
        service.run(WS)
    assert len(holds.active()) == 1
    make().run(WS)
    assert len(quotes.calls) == 1
    with sqlite3.connect(db) as c:
        assert (
            c.execute(
                "SELECT count(*) FROM workflow_v12_notification_commands"
            ).fetchone()[0]
            == 1
        )
        # Previous executable's exact eligible status list never claims operational mail.
        assert (
            c.execute(
                "SELECT count(*) FROM workflow_v12_notification_recipients r JOIN workflow_v12_notification_commands c USING(command_id) WHERE c.inquiry_id IS NULL AND r.outcome IN ('PENDING','RETRYABLE_FAILURE','SENDING')"
            ).fetchone()[0]
            == 0
        )


@pytest.mark.parametrize(
    "name",
    ["InsoAuthenticationError", "BrowserBootstrapError", "GoogleSheetsReadError"],
)
@pytest.mark.parametrize("wrapped", [False, True])
def test_shared_preparation_cause_is_not_downgraded_to_purchase_pause(name, wrapped):
    failure = type(name, (RuntimeError,), {})("synthetic")
    if wrapped:
        outer = RuntimeError("synthetic wrapper")
        outer.__cause__ = failure
        failure = outer

    def fail(*args, **kwargs):
        raise failure

    events = []
    combined = CombinedCycle(
        SimpleNamespace(begin_poll_cycle=lambda: None, poll_and_process=fail),
        lambda _: events.append("V13"),
        on_pause=lambda _: events.append("pause"),
    )
    with pytest.raises(V12Fault) as exc:
        combined.run(None, [WS], now=NOW)
    assert exc.value.scope is FaultScope.GLOBAL_STOP and not events


@pytest.mark.parametrize("bound,changes", [
    (False, {"model": "NEW-MPN"}),
    (True, {"model": "NEW-MPN"}),
    (True, {"brand": "NEW-BRAND"}),
    (True, {"quantity": "999"}),
])
@pytest.mark.parametrize("status", ["发给采购", "采购已报价", "UNKNOWN"])
def test_hold_mutation_uses_original_position_only_as_human_status_anchor(tmp_path, bound, changes, status):
    from tests.inso.test_v13_quotation_read import quote
    db, store, sheets, holds, _ledger, quotes, make, observed = fixture(tmp_path, [(quote(),)])
    if not bound:
        sheets.rows = [source(9, model="")]
    fail = lambda r: replace(r, outcome=QuotationOutcome.ROW_FAILED, row_error_reason=RowErrorReason.UPDATE_RESULT_UNCONFIRMED)
    make(fail).run(WS)
    before = len(quotes.calls)
    position = 2 if bound else 9
    sheets.rows = [source(position, status, **changes)]
    make().run(WS)
    make().run(WS)
    assert len(quotes.calls) == before
    assert len(store.all_items()) == 1
    assert bool(holds.active()) == (status != "采购已报价")
    if status == "采购已报价":
        assert observed[-1][0].outcome is QuotationOutcome.UPDATED_ALREADY_EXISTS
    with sqlite3.connect(db) as c:
        assert c.execute("SELECT count(*) FROM workflow_v12_notification_commands").fetchone()[0] == 1


def test_deleted_held_row_retains_hold_and_unrelated_bound_row_continues(tmp_path):
    _db, store, sheets, holds, _ledger, quotes, make, _observed = fixture(tmp_path, [()])
    sheets.rows = [source(9, model="")]
    make().run(WS)
    sheets.rows = [source(2)]
    output = make().run(WS)
    assert len(holds.active()) == 1 and len(quotes.calls) == 1
    assert output[0].outcome is QuotationOutcome.NO_RECENT_QUOTE
    assert len(store.all_items()) == 1


@pytest.mark.parametrize("stage", ["reader", "operation", "factory", "update", "contract", "close"])
@pytest.mark.parametrize("error_type", [RuntimeError, ValueError])
def test_unknown_v13_exception_globally_stops_without_hold_or_later_query(tmp_path, stage, error_type):
    from tests.inso.test_v13_quotation_read import quote
    db, store, sheets, holds, _ledger, quotes, make, observed = fixture(tmp_path, [(quote(),), ()])
    sheets.rows = [source(3, "未发", model="SECOND")]
    for record in query_pending_records(sheets, WS):
        store.enqueue(record, now=NOW)
    sheets.rows = [source(2), source(3, model="SECOND")]
    def fail(*_):
        raise error_type("private provider details")
    integrated = make(fail if stage == "update" else lambda r: r)
    if stage == "reader":
        quotes.read = fail
    elif stage == "operation":
        integrated.cycle._operations.open = fail
    elif stage == "factory":
        integrated.updater_factory = fail
    elif stage == "contract":
        integrated.updater_factory = lambda: SimpleNamespace(update_one=lambda _: None)
    elif stage == "close":
        integrated.cycle._operations.close = fail
    with pytest.raises(V12Fault) as raised:
        integrated.run(WS)
    assert raised.value.scope is FaultScope.GLOBAL_STOP
    assert raised.value.reason == "V13_INTERNAL_FAILURE"
    assert holds.active() == () and observed == []
    assert len(quotes.calls) <= 1 and len(store.all_items()) == 2
    with sqlite3.connect(db) as c:
        assert c.execute("SELECT count(*) FROM workflow_v12_notification_commands").fetchone()[0] == 0


def test_typed_row_local_updater_source_error_still_holds_only_that_row(tmp_path):
    from src.workflow.v13_quotation import V13SourceRowError
    from tests.inso.test_v13_quotation_read import quote
    _db, _store, _sheets, holds, _ledger, _quotes, make, _observed = fixture(tmp_path, [(quote(),)])
    def local_error(_):
        raise V13SourceRowError(RowErrorReason.SOURCE_CHANGED)
    assert make(local_error).run(WS)[0].outcome is QuotationOutcome.ROW_FAILED
    assert len(holds.active()) == 1
