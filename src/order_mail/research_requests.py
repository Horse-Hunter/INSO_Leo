"""Read-only header-only IMAP input. Never fetch bodies, links or attachments."""
import imaplib
import re
import ssl
from dataclasses import dataclass, replace
from email import policy
from email.parser import BytesParser
from email.utils import parsedate_to_datetime

from src.core import get_login

ACCOUNT = "linan229@qq.com"
SENDER = "sal" + "es2@inso-hk.com"


@dataclass(frozen=True)
class ResearchMail:
    mpn: str
    sent_at: str | None
    message_id: str | None
    sender_verified: bool = False


def verify_sender_origin(_raw):
    """QQ IMAP authenticity contract NOT_VERIFIED. Never trust self-added headers.

    A reviewed provider-grounded verifier is required before live enablement.
    No config/address/authserv-id guess can enable this boundary.
    """
    return False


def parse_research_header(raw):
    """Syntax only; a matching From is NOT authentication."""
    if len(raw) > 32768:
        return None
    try:
        mail = BytesParser(policy=policy.default).parsebytes(raw, headersonly=True)
        if mail.defects or len(mail.get_all("From", [])) != 1 or len(mail.get_all("Subject", [])) != 1:
            return None
        sender = mail["From"]
        if sender.defects or len(sender.addresses) != 1 or sender.addresses[0].addr_spec.casefold() != SENDER:
            return None
        subject = str(mail["Subject"])
        match = re.fullmatch(r"调研\s*([A-Za-z0-9][A-Za-z0-9._+/#-]{0,127})", subject)
        if match is None:
            return None
        date = None
        try:
            value = parsedate_to_datetime(str(mail.get("Date", "")))
            if value.tzinfo is not None:
                date = value.isoformat()
        except (TypeError, ValueError, OverflowError):
            pass
        return ResearchMail(match[1], date, str(mail.get("Message-ID", ""))[:512] or None)
    except (ValueError, TypeError, AttributeError):
        return None


def ok(result):
    if result[0] != "OK":
        raise ValueError("IMAP_OPERATION_UNCONFIRMED")
    return result[1]


class ImapAuthenticationRequired(RuntimeError):
    pass


class ResearchInbox:
    """A short TLS connection per poll; durable cursor belongs to Workflow."""
    def __init__(self, *, credentials=get_login, factory=imaplib.IMAP4_SSL, verify_origin=verify_sender_origin):
        self.credentials, self.factory = credentials, factory
        self.verify_origin = verify_origin
        self.client = None

    def __enter__(self):
        login = self.credentials("imap.qq.com")
        if login.username.strip().casefold() != ACCOUNT:
            raise ValueError("IMAP_ACCOUNT_UNCONFIRMED")
        try:
            self.client = self.factory("imap.qq.com", 993, ssl_context=ssl.create_default_context(), timeout=20)
            try:
                ok(self.client.login(login.username, login.password))
            except imaplib.IMAP4.error as error:
                # Login-stage NO can mean maintenance/rate limiting, not a
                # credential fault. Only explicit standardized auth rejection
                # is evidence that an Owner authorization check is required.
                if re.search(r"\[(?:AUTHENTICATIONFAILED|AUTHORIZATIONFAILED)\]", str(error), re.IGNORECASE):
                    raise ImapAuthenticationRequired("IMAP_AUTH_REQUIRED") from None
                raise ValueError("IMAP_LOGIN_UNCONFIRMED") from None
            ok(self.client.select("INBOX", readonly=True))
            if not self.client.is_readonly:
                raise ValueError("IMAP_READONLY_UNCONFIRMED")
            validity = self.client.response("UIDVALIDITY")[1]
            next_uid = self.client.response("UIDNEXT")[1]
            self.validity = int(validity[0])
            self.latest = int(next_uid[0]) - 1
            if self.validity <= 0 or self.latest < 0:
                raise ValueError("IMAP_UID_UNCONFIRMED")
            return self
        except BaseException:
            self.__exit__(None, None, None)
            raise

    def read(self, after, *, limit=32):
        # UID ranges avoid unbounded SEARCH ALL and never inspect pre-baseline mail.
        upper = min(self.latest, after + limit)
        if upper <= after:
            return upper, ()
        data = ok(self.client.uid("fetch", f"{after+1}:{upper}",
            "(UID BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE MESSAGE-ID)])"))
        found = []
        for item in data:
            if not isinstance(item, tuple):
                continue
            metadata, raw = item
            match = re.search(rb"\bUID (\d+)\b", metadata)
            if not match or not after < int(match[1]) <= upper:
                raise ValueError("IMAP_UID_UNCONFIRMED")
            parsed = parse_research_header(raw)
            if parsed is not None:
                if self.verify_origin(raw) is not True:
                    raise ValueError("SENDER_AUTH_UNVERIFIED")  # Keep UID cursor; no work/SMTP.
                found.append((int(match[1]), replace(parsed, sender_verified=True)))
        return upper, tuple(found)

    def __exit__(self, *_):
        if self.client is not None:
            try:
                self.client.logout()
            except Exception:  # noqa: BLE001 - disconnect cannot expose provider text
                import logging
                logging.getLogger("inso.mail_research").debug("IMAP detach unavailable")
            self.client = None
