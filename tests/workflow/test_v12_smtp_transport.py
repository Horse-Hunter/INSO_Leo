"""Deterministic tests for the QQ SMTP notification transport.

No real SMTP connection is made: the SMTP client and Credential Provider are
injected fakes. The authorization code is a unique fake canary and is asserted
absent from every DTO, log record and persisted row.
"""

from __future__ import annotations

import logging
import re
import smtplib
import sqlite3
from contextlib import nullcontext
from datetime import UTC, datetime
from pathlib import Path

import pytest

from src.core import CredentialSiteNotFoundError, Login
from src.workflow import WorkflowStateStore
from src.workflow.v12_contracts import (
    DeliveryOutcome,
    NotificationCommand,
    NotificationKind,
    NotificationRecipient,
    ReasonCode,
)
from src.workflow.v12_notifications import V12NotificationWorker
from src.workflow.v12_smtp_transport import (
    QQ_SMTP_HOST,
    QQSMTPConfig,
    QQSMTPTransport,
)
from src.workflow.v12_store import V12Store, migrate_v12

NOW = datetime(2026, 9, 25, 8, tzinfo=UTC)
INQUIRY = "inq_0123456789abcdef01234567"
RECIPIENT = NotificationRecipient("a", "a@example.invalid")
SECRET_CANARY = "SECRET_CANARY_9F8C_smtp_authorization_code"


def config(**overrides: object) -> QQSMTPConfig:
    settings: dict[str, object] = {"sender_address": "sender@example.invalid"}
    settings.update(overrides)
    return QQSMTPConfig(**settings)  # type: ignore[arg-type]


def make_command() -> NotificationCommand:
    return NotificationCommand(
        "cmd-notify-1",
        INQUIRY,
        NotificationKind.IMPORTANT_ORDER,
        (RECIPIENT,),
        "subject",
        "text body",
        "<p>html body</p>",
        NOW,
    )


class ScriptedSMTP:
    """Records calls and raises the scripted exception at the right phase."""

    def __init__(
        self,
        *,
        login_error: BaseException | None = None,
        send_error: BaseException | None = None,
    ) -> None:
        self._login_error = login_error
        self._send_error = send_error
        self.login_args: tuple[str, str] | None = None
        self.message = None
        self.send_attempts = 0
        self.closed = False

    def login(self, user: str, password: str) -> tuple[int, bytes]:
        self.login_args = (user, password)
        if self._login_error is not None:
            raise self._login_error
        return (235, b"authenticated")

    def send_message(self, message) -> dict:
        self.send_attempts += 1
        if self._send_error is not None:
            raise self._send_error
        self.message = message
        return {}

    def close(self) -> None:
        self.closed = True


class FakeCredentials:
    """Stands in for the Core Credential Provider."""

    def __init__(self, outcome: Login | BaseException) -> None:
        self._outcome = outcome
        self.site_ids: list[str] = []

    def get_login(self, site_id: str) -> Login:
        self.site_ids.append(site_id)
        if isinstance(self._outcome, BaseException):
            raise self._outcome
        return self._outcome


class FakeSMTPFactory:
    def __init__(self, client: ScriptedSMTP | None = None, error: BaseException | None = None):
        self._client = client
        self._error = error
        self.calls = 0

    def __call__(self, *args, **kwargs) -> ScriptedSMTP:
        self.calls += 1
        if self._error is not None:
            raise self._error
        assert self._client is not None
        return self._client


def login(password: str = SECRET_CANARY) -> Login:
    return Login(
        site_id=QQ_SMTP_HOST,
        url="",
        username="sender-account",
        password=password,
    )


def transport(
    *,
    client: ScriptedSMTP | None = None,
    connect_error: BaseException | None = None,
    credential: Login | BaseException | None = None,
    **config_overrides: object,
) -> tuple[QQSMTPTransport, ScriptedSMTP | None, FakeSMTPFactory, FakeCredentials]:
    smtp_client = client if client is not None else ScriptedSMTP()
    factory = FakeSMTPFactory(smtp_client, connect_error)
    credentials = FakeCredentials(credential if credential is not None else login())
    adapter = QQSMTPTransport(
        config=config(**config_overrides),
        credentials=credentials,
        smtp_factory=factory,
    )
    return adapter, smtp_client, factory, credentials


# --- 1. SENT ---------------------------------------------------------------


def test_accepted_send_returns_sent_with_one_recipient() -> None:
    adapter, client, factory, credentials = transport()

    result = adapter.send_one(make_command(), RECIPIENT)

    assert result.outcome is DeliveryOutcome.SENT
    assert result.reason_code is ReasonCode.NOTIFICATION_SENT
    assert factory.calls == 1
    assert client.send_attempts == 1
    assert client.closed is True
    assert client.login_args == ("sender-account", SECRET_CANARY)
    # The credential is read from the Core Provider under the QQ SMTP site id.
    assert credentials.site_ids == [QQ_SMTP_HOST]
    assert client.message["To"] == RECIPIENT.address
    assert client.message["From"] == "sender@example.invalid"


def test_text_only_command_has_no_html_alternative() -> None:
    adapter, client, _, _ = transport()
    command = NotificationCommand(
        "cmd-notify-1", INQUIRY, NotificationKind.DUPLICATE_ORDER, (RECIPIENT,),
        "subject", "text body", None, NOW,
    )

    assert adapter.send_one(command, RECIPIENT).outcome is DeliveryOutcome.SENT
    assert client.message.get_content_type() == "text/plain"


# --- 2. timeout / network -> RETRYABLE_FAILURE -----------------------------


@pytest.mark.parametrize(
    "error",
    [
        TimeoutError("timed out"),
        ConnectionError("connection reset"),
        OSError("network unreachable"),
        smtplib.SMTPServerDisconnected("closed during connect"),
        smtplib.SMTPConnectError(421, b"service not available"),
    ],
)
def test_pre_send_network_failure_is_retryable(error: BaseException) -> None:
    adapter, _, _, _ = transport(connect_error=error)

    result = adapter.send_one(make_command(), RECIPIENT)

    assert result.outcome is DeliveryOutcome.RETRYABLE_FAILURE
    assert result.reason_code is ReasonCode.NOTIFICATION_TRANSIENT


def test_login_phase_network_failure_is_retryable() -> None:
    adapter, _, _, _ = transport(client=ScriptedSMTP(login_error=TimeoutError("login timeout")))

    result = adapter.send_one(make_command(), RECIPIENT)

    assert result.outcome is DeliveryOutcome.RETRYABLE_FAILURE
    assert result.reason_code is ReasonCode.NOTIFICATION_TRANSIENT


# --- 3. auth failure -> PERMANENT_FAILURE ----------------------------------


def test_authentication_failure_is_permanent() -> None:
    adapter, _, _, _ = transport(
        client=ScriptedSMTP(login_error=smtplib.SMTPAuthenticationError(535, b"authentication failed"))
    )

    result = adapter.send_one(make_command(), RECIPIENT)

    assert result.outcome is DeliveryOutcome.PERMANENT_FAILURE
    assert result.reason_code is ReasonCode.NOTIFICATION_PERMANENT


def test_missing_credential_is_permanent_and_sends_nothing() -> None:
    adapter, client, factory, credentials = transport(
        credential=CredentialSiteNotFoundError(QQ_SMTP_HOST, "not in vault")
    )

    result = adapter.send_one(make_command(), RECIPIENT)

    assert result.outcome is DeliveryOutcome.PERMANENT_FAILURE
    assert result.reason_code is ReasonCode.NOTIFICATION_PERMANENT
    assert credentials.site_ids == [QQ_SMTP_HOST]
    assert client.send_attempts == 0
    assert factory.calls == 1


def test_missing_sender_configuration_is_permanent_and_never_connects() -> None:
    adapter, _, factory, _ = transport(sender_address="")

    result = adapter.send_one(make_command(), RECIPIENT)

    assert result.outcome is DeliveryOutcome.PERMANENT_FAILURE
    assert result.reason_code is ReasonCode.NOTIFICATION_PERMANENT
    assert factory.calls == 0


# --- 4. permanent recipient rejection -> PERMANENT_FAILURE -----------------


def test_permanent_recipient_rejection_is_permanent() -> None:
    adapter, _, _, _ = transport(
        client=ScriptedSMTP(
            send_error=smtplib.SMTPRecipientsRefused(
                {RECIPIENT.address: (550, b"mailbox unavailable")}
            )
        )
    )

    result = adapter.send_one(make_command(), RECIPIENT)

    assert result.outcome is DeliveryOutcome.PERMANENT_FAILURE
    assert result.reason_code is ReasonCode.NOTIFICATION_PERMANENT


def test_transient_recipient_rejection_is_retryable() -> None:
    adapter, _, _, _ = transport(
        client=ScriptedSMTP(
            send_error=smtplib.SMTPRecipientsRefused(
                {RECIPIENT.address: (450, b"mailbox busy")}
            )
        )
    )

    result = adapter.send_one(make_command(), RECIPIENT)

    assert result.outcome is DeliveryOutcome.RETRYABLE_FAILURE
    assert result.reason_code is ReasonCode.NOTIFICATION_TRANSIENT


def test_permanent_sender_refusal_is_permanent() -> None:
    adapter, _, _, _ = transport(
        client=ScriptedSMTP(send_error=smtplib.SMTPSenderRefused(553, b"bad sender", "sender@example.invalid"))
    )

    assert adapter.send_one(make_command(), RECIPIENT).outcome is DeliveryOutcome.PERMANENT_FAILURE


def test_permanent_data_error_is_permanent() -> None:
    adapter, _, _, _ = transport(
        client=ScriptedSMTP(send_error=smtplib.SMTPDataError(554, b"message rejected"))
    )

    assert adapter.send_one(make_command(), RECIPIENT).outcome is DeliveryOutcome.PERMANENT_FAILURE


# --- 5. uncertain result -> UNKNOWN ---------------------------------------


@pytest.mark.parametrize(
    "error",
    [
        smtplib.SMTPServerDisconnected("connection lost during DATA"),
        TimeoutError("no acknowledgement received"),
        ConnectionError("reset after transmission started"),
        smtplib.SMTPException("unclassified provider failure"),
    ],
)
def test_unconfirmed_send_outcome_is_unknown(error: BaseException) -> None:
    adapter, _, _, _ = transport(client=ScriptedSMTP(send_error=error))

    result = adapter.send_one(make_command(), RECIPIENT)

    assert result.outcome is DeliveryOutcome.UNKNOWN
    assert result.reason_code is ReasonCode.NOTIFICATION_UNKNOWN


def test_unknown_send_is_never_guessed_retryable() -> None:
    adapter, _, _, _ = transport(
        client=ScriptedSMTP(send_error=smtplib.SMTPServerDisconnected("dropped"))
    )

    assert (
        adapter.send_one(make_command(), RECIPIENT).outcome
        is not DeliveryOutcome.RETRYABLE_FAILURE
    )


# --- 6. unexpected exception never leaks the raw message -------------------


def test_unexpected_exception_is_unknown_and_leaks_no_raw_text() -> None:
    raw = f"raw provider response containing {SECRET_CANARY}"
    adapter, _, _, _ = transport(client=ScriptedSMTP(send_error=RuntimeError(raw)))

    result = adapter.send_one(make_command(), RECIPIENT)

    assert result.outcome is DeliveryOutcome.UNKNOWN
    assert result.reason_code is ReasonCode.NOTIFICATION_UNKNOWN
    assert SECRET_CANARY not in repr(result)
    assert "raw provider response" not in repr(result)


def test_unexpected_connect_exception_is_unknown_and_does_not_raise() -> None:
    adapter, _, _, _ = transport(connect_error=RuntimeError(f"boom {SECRET_CANARY}"))

    result = adapter.send_one(make_command(), RECIPIENT)

    assert result.outcome is DeliveryOutcome.UNKNOWN
    assert SECRET_CANARY not in repr(result)


# --- 7. secret canary never reaches logs, DTOs or persistence -------------


def prepared_store(tmp_path: Path) -> V12Store:
    database = tmp_path / "workflow.sqlite3"
    WorkflowStateStore(database)
    with sqlite3.connect(database) as connection:
        connection.execute(
            "INSERT INTO workflow_items (spreadsheet, worksheet, row_number, inquiry_id, "
            "record_identity_json, mpn_json, brand_json, quantity_json, importance_raw_json, "
            "status, attempt_count, next_attempt_at, created_at, updated_at) "
            "VALUES ('sheet-id','2026',4,?,'{}','\"MPN-1\"','\"Brand\"','10','\"A\"',"
            "'QUEUED',0,?,?,?)",
            (INQUIRY, NOW.isoformat(), NOW.isoformat(), NOW.isoformat()),
        )
    migrate_v12(
        database,
        tmp_path / "backups",
        quiesce=lambda: nullcontext(),
        clock=lambda: NOW,
    )
    return V12Store(database)


def test_secret_canary_absent_from_logs_dto_and_database(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    store = prepared_store(tmp_path)
    store.enqueue_notification(make_command())
    adapter, _, _, _ = transport()
    worker = V12NotificationWorker(store, adapter)

    with caplog.at_level(logging.DEBUG):
        assert worker.run_due(now=NOW) == 1

    result = store.recipient_results("cmd-notify-1")[0]
    assert result.outcome is DeliveryOutcome.SENT
    assert SECRET_CANARY not in repr(result)
    assert SECRET_CANARY not in caplog.text

    with sqlite3.connect(store.database_path) as connection:
        tables = [
            name
            for (name,) in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'workflow_v12_%'"
            )
        ]
        for table in tables:
            rows = tuple(tuple(row) for row in connection.execute(f"SELECT * FROM {table}"))
            assert SECRET_CANARY not in repr(rows), table


def test_credential_failure_also_leaks_no_secret(tmp_path: Path, caplog) -> None:
    store = prepared_store(tmp_path)
    store.enqueue_notification(make_command())
    adapter, _, _, _ = transport(
        credential=CredentialSiteNotFoundError(QQ_SMTP_HOST, f"missing {SECRET_CANARY}")
    )
    worker = V12NotificationWorker(store, adapter)

    with caplog.at_level(logging.DEBUG):
        worker.run_due(now=NOW)

    assert store.recipient_results("cmd-notify-1")[0].outcome is DeliveryOutcome.PERMANENT_FAILURE
    assert SECRET_CANARY not in caplog.text
    with sqlite3.connect(store.database_path) as connection:
        blob = repr(tuple(connection.iterdump()))
    assert SECRET_CANARY not in blob


# --- 8. the transport implements no retry scheduler -----------------------


def test_transport_makes_exactly_one_provider_attempt_and_owns_no_scheduler() -> None:
    adapter, client, factory, _ = transport(
        client=ScriptedSMTP(send_error=smtplib.SMTPServerDisconnected("dropped"))
    )

    adapter.send_one(make_command(), RECIPIENT)

    assert factory.calls == 1
    assert client.send_attempts == 1
    assert not hasattr(adapter, "run_due")
    assert not hasattr(adapter, "claim_due_notifications")
    assert not hasattr(adapter, "reschedule")
    assert not hasattr(adapter, "next_attempt_at")


def test_transport_module_ships_no_sleep_or_scheduler() -> None:
    import src.workflow.v12_smtp_transport as module

    source = Path(module.__file__).read_text(encoding="utf-8")

    assert not re.search(r"\bsleep\b", source)
    assert "time.monotonic" not in source
