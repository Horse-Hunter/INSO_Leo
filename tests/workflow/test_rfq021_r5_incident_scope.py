"""RFQ-021-R5: a scoped run settles only the incidents it has standing for.

`V12Store.resolve_incidents` closes incident records; an incident's evidence can
name a specific order. A one-order trial must settle the program-level records
and its own order's record, and leave an out-of-scope order's record exactly as
it was -- otherwise the next real outage looks "already recovered" (or the next
notification is suppressed) because a trial touched it.

The unscoped behaviour is the historical one and is pinned here too.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import nullcontext
from datetime import UTC, datetime
from pathlib import Path

from src.workflow.store import WorkflowStateStore
from src.workflow.v12_store import V12Store, migrate_v12

NOW = datetime(2026, 11, 15, 9, tzinfo=UTC)
INQUIRY = "inq_" + "a" * 24
OTHER = "inq_" + "b" * 24


def _database(path: Path) -> Path:
    for inquiry_id in (INQUIRY, OTHER):
        WorkflowStateStore(path)
        with sqlite3.connect(path) as connection:
            connection.execute(
                "INSERT OR IGNORE INTO workflow_items (spreadsheet, worksheet, row_number, "
                "inquiry_id, record_identity_json, mpn_json, brand_json, quantity_json, "
                "importance_raw_json, status, attempt_count, next_attempt_at, research_status, "
                "resolved_brand, brand_update_status, last_error, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'QUEUED', 0, ?, NULL, NULL, NULL, NULL, ?, ?)",
                (
                    "sheet-id", "2026", 4, inquiry_id, "{}", '"MPN-1"', '"Brand"', "10", '"A"',
                    NOW.isoformat(), NOW.isoformat(), NOW.isoformat(),
                ),
            )
    migrate_v12(path, path.parent / "backups", quiesce=lambda: nullcontext(), clock=lambda: NOW)
    return path


def _incident(store: V12Store, *, command_id: str, inquiry_id: str, module: str, proof: dict) -> None:
    with sqlite3.connect(store.database_path) as connection:
        connection.execute(
            "INSERT INTO workflow_v12_notification_commands (command_id, inquiry_id, kind, "
            "subject, text_body, html_body, created_at, payload_version, review_json, "
            "suppression_reason) VALUES (?, ?, 'PURCHASE_EXCEPTION', 's', 'b', NULL, ?, 2, ?, NULL)",
            (command_id, inquiry_id, NOW.isoformat(), json.dumps({"module": module, "active": True, **proof})),
        )


def _active(store: V12Store, command_id: str) -> bool:
    return json.loads(store.notification_review(command_id))["active"]


def _fixture(tmp_path: Path) -> tuple[V12Store, dict[str, str]]:
    store = V12Store(_database(tmp_path / "workflow.sqlite3"))
    ids = {
        "in_scope": "incident:inscope:0",
        "out_of_scope": "incident:outofscope:0",
        "program_level": "incident:program:0",
        "other_module": "incident:othermodule:0",
    }
    _incident(store, command_id=ids["in_scope"], inquiry_id=INQUIRY, module="INSO",
              proof={"inquiry_id": INQUIRY})
    _incident(store, command_id=ids["out_of_scope"], inquiry_id=OTHER, module="INSO",
              proof={"inquiry_id": OTHER})
    _incident(store, command_id=ids["program_level"], inquiry_id=INQUIRY, module="INSO", proof={})
    _incident(store, command_id=ids["other_module"], inquiry_id=INQUIRY, module="IC.net",
              proof={"inquiry_id": INQUIRY})
    return store, ids


def test_a_scoped_resolution_settles_its_own_order_and_program_level_records(tmp_path):
    store, ids = _fixture(tmp_path)

    store.resolve_incidents("INSO", at=NOW, within=frozenset({INQUIRY}))

    assert _active(store, ids["in_scope"]) is False
    assert _active(store, ids["program_level"]) is False
    assert _active(store, ids["out_of_scope"]) is True
    assert _active(store, ids["other_module"]) is True


def test_an_empty_scope_settles_only_the_program_level_record(tmp_path):
    store, ids = _fixture(tmp_path)

    store.resolve_incidents("INSO", at=NOW, within=frozenset())

    assert _active(store, ids["program_level"]) is False
    assert _active(store, ids["in_scope"]) is True
    assert _active(store, ids["out_of_scope"]) is True


def test_the_unscoped_call_keeps_its_historical_behaviour(tmp_path):
    store, ids = _fixture(tmp_path)

    store.resolve_incidents("INSO", at=NOW)

    assert _active(store, ids["in_scope"]) is False
    assert _active(store, ids["out_of_scope"]) is False
    assert _active(store, ids["program_level"]) is False
    assert _active(store, ids["other_module"]) is True
