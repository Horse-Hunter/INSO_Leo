"""Read-only header-only IMAP input. Never fetch bodies, links or attachments."""
import imaplib
import re
import ssl
from dataclasses import dataclass
from email import policy
from email.parser import BytesParser
from email.utils import parsedate_to_datetime

from src.core import get_login

ACCOUNT = "linan229@qq.com"
TRIGGER_POLICY = "subject-only-v1"


@dataclass(frozen=True)
class ResearchMail:
    mpn: str
    sent_at: str | None
    message_id: str | None
    trigger_policy: str | None = None


def parse_research_subject(subject):
    match = re.fullmatch(r"调研\s*([A-Za-z0-9][A-Za-z0-9._+/#-]{0,127})", subject)
    return match[1] if match else None


def parse_research_header(raw):
    """Owner accepts any sender; only one decoded legal subject is authoritative."""
    if len(raw) > 32768:
        return None
    try:
        mail = BytesParser(policy=policy.default).parsebytes(raw, headersonly=True)
        if len(mail.get_all("Subject", [])) != 1 or mail["Subject"].defects:
            return None
        subject = str(mail["Subject"])
        mpn = parse_research_subject(subject)
        if mpn is None:
            return None
        date = None
        try:
            value = parsedate_to_datetime(str(mail.get("Date", "")))
            if value.tzinfo is not None:
                date = value.isoformat()
        except (TypeError, ValueError, OverflowError):
            pass
        return ResearchMail(mpn, date, str(mail.get("Message-ID", ""))[:512] or None, TRIGGER_POLICY)
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
    def __init__(self, *, credentials=get_login, factory=imaplib.IMAP4_SSL):
        self.credentials, self.factory = credentials, factory
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
            "(UID BODY.PEEK[HEADER.FIELDS (SUBJECT DATE MESSAGE-ID)])"))
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
                found.append((int(match[1]), parsed))
        return upper, tuple(found)

    def __exit__(self, *_):
        if self.client is not None:
            try:
                self.client.logout()
            except Exception:  # noqa: BLE001 - disconnect cannot expose provider text
                import logging
                logging.getLogger("inso.mail_research").debug("IMAP detach unavailable")
            self.client = None
