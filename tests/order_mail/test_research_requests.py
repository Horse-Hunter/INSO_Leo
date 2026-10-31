"""Fake TLS/UID/header protocol, no mailbox/Vault/network."""
import imaplib
from types import SimpleNamespace

import pytest

from src.order_mail.research_requests import (
    ACCOUNT,
    ImapAuthenticationRequired,
    ResearchInbox,
)
from tests.workflow.test_mail_research import header


class IMAP:
    is_readonly = True
    def __init__(self):
        self.calls, self.closed = [], False
    def login(self, username, password):
        assert username == ACCOUNT and password == "synthetic"
        return "OK", [b"authenticated"]
    def select(self, folder, *, readonly):
        assert folder == "INBOX" and readonly is True
        return "OK", [b"3"]
    def response(self, field):
        return field, [b"1" if field == "UIDVALIDITY" else b"102"]
    def uid(self, *args):
        self.calls.append(args)
        return "OK", [(b"101 (UID 101)", header())]
    def logout(self):
        self.closed = True


def test_fake_tls_uses_vault_identity_peek_and_uid_range_only():
    client = IMAP()
    def factory(host, port, *, ssl_context, timeout):
        assert host == "imap.qq.com" and port == 993 and timeout == 20
        assert ssl_context.check_hostname
        return client
    with ResearchInbox(credentials=lambda site: SimpleNamespace(username=ACCOUNT, password="synthetic"), factory=factory, verify_origin=lambda _: True) as inbox:
        assert inbox.validity == 1 and inbox.latest == 101
        upper, mails = inbox.read(100)
        assert upper == 101 and mails[0][0] == 101
    assert client.closed
    assert client.calls[0][0:2] == ("fetch", "101:101")
    assert "BODY.PEEK[HEADER.FIELDS" in client.calls[0][2]
    assert "STORE" not in repr(client.calls)


def test_native_auth_rejection_disconnects_and_exposes_only_closed_code():
    client = IMAP()
    def reject(*_):
        raise imaplib.IMAP4.error("[AUTHENTICATIONFAILED] synthetic provider text")
    client.login = reject
    with pytest.raises(ImapAuthenticationRequired, match="IMAP_AUTH_REQUIRED"), ResearchInbox(credentials=lambda _: SimpleNamespace(username=ACCOUNT, password="synthetic"), factory=lambda *a, **k: client):
        pytest.fail("must not enter")
    assert client.closed


@pytest.mark.parametrize("response", ["[UNAVAILABLE] temporary server maintenance", "rate limited; try later", "LOGIN failed; reason unknown"])
def test_transient_or_unclassified_login_response_is_not_an_auth_incident(response):
    client = IMAP()
    def reject(*_):
        raise imaplib.IMAP4.error(response)
    client.login = reject
    with pytest.raises(ValueError, match="IMAP_LOGIN_UNCONFIRMED"), ResearchInbox(
            credentials=lambda _: SimpleNamespace(username=ACCOUNT, password="synthetic"), factory=lambda *a, **k: client):
        pytest.fail("must not enter")
    assert client.closed
