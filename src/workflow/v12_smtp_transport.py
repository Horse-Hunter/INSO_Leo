"""Minimal QQ SMTP notification transport for the V1.2 notification worker.

This adapter performs exactly one delivery attempt for one recipient and maps
the provider outcome onto the frozen ``NotificationTransportResult`` contract.
It owns provider-specific error classification only: the Workflow notification
worker keeps the recipient ledger, retry timing and alerts, so no retry
scheduler lives here.

The SMTP authorization code is read from the Core Credential Provider at send
time (``site_id=smtp.qq.com``) and is never logged, persisted or returned. Raw
provider responses and exception text are never copied into any result.
"""

from __future__ import annotations

import contextlib
import smtplib
import ssl
from collections.abc import Callable
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Protocol

from src.core import CredentialError, CredentialProvider, Login, get_login

from .v12_contracts import (
    DeliveryOutcome,
    NotificationCommand,
    NotificationRecipient,
    NotificationTransportResult,
    ReasonCode,
)

QQ_SMTP_HOST = "smtp.qq.com"
QQ_SMTP_SSL_PORT = 465


@dataclass(frozen=True, slots=True)
class QQSMTPConfig:
    """Non-secret runtime settings for the QQ SMTP transport.

    ``sender_address`` is the Owner-configured sender mailbox and is runtime
    configuration, not a credential. The authorization code lives only in the
    Core Credential Vault under ``site_id``.
    """

    sender_address: str
    host: str = QQ_SMTP_HOST
    port: int = QQ_SMTP_SSL_PORT
    site_id: str = QQ_SMTP_HOST
    timeout_seconds: float = 30.0


class _SMTPClient(Protocol):
    """The narrow part of ``smtplib.SMTP`` this transport depends on."""

    def login(self, user: str, password: str) -> tuple[int, bytes]: ...

    def send_message(self, message: EmailMessage) -> dict: ...

    def close(self) -> None: ...


_SMTPFactory = Callable[..., _SMTPClient]

# Outcomes are frozen in v12_contracts; the reason code is the allowlisted
# counterpart of each transport outcome.
_SENT = NotificationTransportResult(DeliveryOutcome.SENT, ReasonCode.NOTIFICATION_SENT)
_RETRYABLE = NotificationTransportResult(
    DeliveryOutcome.RETRYABLE_FAILURE, ReasonCode.NOTIFICATION_TRANSIENT
)
_PERMANENT = NotificationTransportResult(
    DeliveryOutcome.PERMANENT_FAILURE, ReasonCode.NOTIFICATION_PERMANENT
)
_UNKNOWN = NotificationTransportResult(
    DeliveryOutcome.UNKNOWN, ReasonCode.NOTIFICATION_UNKNOWN
)

# Failures that happen before the message envelope is transmitted are safe to
# retry; nothing was attempted at the provider.
_PRE_SEND_NETWORK_ERRORS = (
    TimeoutError,
    ConnectionError,
    OSError,
    smtplib.SMTPServerDisconnected,
    smtplib.SMTPConnectError,
)


class QQSMTPTransport:
    """One-recipient QQ SMTP adapter; performs no scheduling or persistence.

    Satisfies the Workflow ``NotificationTransport`` protocol.
    """

    def __init__(
        self,
        *,
        config: QQSMTPConfig,
        credentials: CredentialProvider | None = None,
        smtp_factory: _SMTPFactory | None = None,
    ) -> None:
        self._config = config
        self._credentials = credentials
        self._smtp_factory = smtp_factory or smtplib.SMTP_SSL

    def send_one(
        self,
        command: NotificationCommand,
        recipient: NotificationRecipient,
    ) -> NotificationTransportResult:
        if not self._config.sender_address:
            # Configuration error: no retry can fix a missing sender.
            return _PERMANENT

        try:
            message = _build_message(self._config.sender_address, command, recipient)
        except Exception:  # noqa: BLE001 - malformed command is a configuration error
            return _PERMANENT

        try:
            client = self._connect()
        except ssl.SSLCertVerificationError:
            # Certificate verification failure is a configuration/security error.
            return _PERMANENT
        except _PRE_SEND_NETWORK_ERRORS:
            return _RETRYABLE
        except Exception:  # noqa: BLE001 - unknown pre-send failure is not guessed transient
            return _UNKNOWN

        try:
            return self._deliver(client, message)
        finally:
            _close(client)

    # -- internals ---------------------------------------------------------

    def _connect(self) -> _SMTPClient:
        return self._smtp_factory(
            self._config.host,
            self._config.port,
            timeout=self._config.timeout_seconds,
            context=ssl.create_default_context(),
        )

    def _get_login(self) -> Login:
        if self._credentials is None:
            return get_login(self._config.site_id)
        return self._credentials.get_login(self._config.site_id)

    def _deliver(
        self,
        client: _SMTPClient,
        message: EmailMessage,
    ) -> NotificationTransportResult:
        try:
            login = self._get_login()
        except CredentialError:
            # Missing/unconfigured vault entry is a configuration error.
            return _PERMANENT

        try:
            client.login(login.username, login.password)
        except smtplib.SMTPAuthenticationError:
            return _PERMANENT
        except smtplib.SMTPNotSupportedError:
            return _PERMANENT
        except _PRE_SEND_NETWORK_ERRORS:
            # Login precedes the envelope; no message was attempted.
            return _RETRYABLE
        except Exception:  # noqa: BLE001 - unknown login failure is not guessed transient
            return _UNKNOWN
        finally:
            del login

        try:
            client.send_message(message)
        except smtplib.SMTPRecipientsRefused as exc:
            return _classify_recipients_refused(exc)
        except smtplib.SMTPSenderRefused as exc:
            return _classify_response_code(exc)
        except smtplib.SMTPDataError as exc:
            return _classify_response_code(exc)
        except Exception:  # noqa: BLE001 - the message may already be transmitted
            # The send attempt was made but the outcome cannot be confirmed, so
            # it is recorded as UNKNOWN and never guessed as transient.
            return _UNKNOWN
        return _SENT


def _build_message(
    sender_address: str,
    command: NotificationCommand,
    recipient: NotificationRecipient,
) -> EmailMessage:
    message = EmailMessage()
    message["From"] = sender_address
    message["To"] = recipient.address
    message["Subject"] = command.subject
    message.set_content(command.text_body)
    if command.html_body:
        message.add_alternative(command.html_body, subtype="html")
    return message


def _classify_response_code(
    exc: smtplib.SMTPResponseException,
) -> NotificationTransportResult:
    """4xx is transient, anything else is a permanent provider rejection."""
    code = getattr(exc, "smtp_code", None)
    if isinstance(code, int) and 400 <= code < 500:
        return _RETRYABLE
    return _PERMANENT


def _classify_recipients_refused(
    exc: smtplib.SMTPRecipientsRefused,
) -> NotificationTransportResult:
    codes = [code for code, _response in exc.recipients.values()]
    if codes and all(isinstance(code, int) and 400 <= code < 500 for code in codes):
        return _RETRYABLE
    return _PERMANENT


def _close(client: _SMTPClient) -> None:
    # Closing must never mask the real delivery outcome.
    with contextlib.suppress(Exception):
        client.close()
