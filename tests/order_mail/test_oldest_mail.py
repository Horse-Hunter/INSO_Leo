from email.message import EmailMessage
from io import BytesIO
from zipfile import ZipFile

import pytest

from src.core import Login
from src.order_mail.filled import FilledOrders
from src.order_mail.inspection import read_oldest_order_mail


class Client:
    is_readonly = True
    def __init__(self, changed=False, validity=b'1'):
        self.calls=[];self.changed=changed;self.validity=validity
        self.dates={b'9':b'09-Oct-2026 16:00:00 +0800',b'20':b'07-Oct-2026 12:00:00 +0800',b'3':b'10-Oct-2026 10:00:00 +0800'}
    def login(self,*a):return 'OK',[b'ok']
    def select(self,mailbox,readonly):
        assert mailbox=='INBOX' and readonly
        return 'OK',[b'3']
    def response(self, key):return key,[self.validity]
    def logout(self):self.calls.append(('logout',))
    def uid(self,command,*args):
        self.calls.append((command,*args))
        if command=='search':return 'OK',[b'3 9 20']
        uid,fields=args
        msg=EmailMessage();msg['Subject']='订单录单 SYNTHETIC';msg['Message-ID']='<test-'+uid.decode()+'>'
        msg.set_content('PRIVATE MAIL TEXT')
        stream=BytesIO()
        with ZipFile(stream,'w') as z:z.writestr('synthetic','PRIVATE CUSTOMER')
        msg.add_attachment(stream.getvalue(),maintype='application',subtype='octet-stream',filename='private.xlsx')
        flags=b'\\Seen' if self.changed and fields=='(UID FLAGS)' else b''
        meta=b'1 (UID '+uid+b' FLAGS ('+flags+b') INTERNALDATE "'+self.dates[uid]+b'" RFC822.SIZE 1000)'
        return 'OK',[(meta,msg.as_bytes())] if 'PEEK' in fields else [meta]


def read(client, ledger):
    return read_oldest_order_mail(is_processed=ledger.contains,
        credential_getter=lambda _:Login('imap.qq.com','','linan229@qq.com','synthetic-secret'),
        client_factory=lambda *a,**kw:client)


def test_oldest_receipt_not_uid_order_then_success_skipped_and_restart(tmp_path):
    ledger=FilledOrders(tmp_path)
    client=Client();mail=read(client,ledger)
    assert [call[1] for call in client.calls if len(call)>2 and call[2]=='(UID FLAGS BODY.PEEK[])']==[b'20']
    assert 'PRIVATE' not in repr(mail)
    ledger.mark(mail.identities)
    next_client=Client();read(next_client,FilledOrders(tmp_path))
    assert [call[1] for call in next_client.calls if len(call)>2 and call[2]=='(UID FLAGS BODY.PEEK[])']==[b'9']
    assert 'PRIVATE' not in ledger.path.read_bytes().decode('latin1')


def test_failure_unmarked_retryable_no_flag_write(tmp_path):
    ledger=FilledOrders(tmp_path)
    for _ in range(2):
        client=Client();read(client,ledger)
        assert [call[1] for call in client.calls if len(call)>2 and call[2]=='(UID FLAGS BODY.PEEK[])']==[b'20']
        assert all(call[0] in {'search','fetch','logout'} for call in client.calls)


def test_empty_after_all_filled_and_uidvalidity_change_safe_alias(tmp_path):
    ledger=FilledOrders(tmp_path)
    for _ in range(3):ledger.mark(read(Client(),ledger).identities)
    client=Client();assert read(client,ledger) is None
    assert not any(len(call)>2 and call[2]=='(UID FLAGS BODY.PEEK[])' for call in client.calls)
    assert read(Client(validity=b'2'),ledger) is None


def test_flags_changed_and_identity_missing_stop(tmp_path):
    with pytest.raises(ValueError,match='MAIL_FLAGS_CHANGED'):read(Client(changed=True),FilledOrders(tmp_path))
    with pytest.raises(ValueError,match='MAIL_IDENTITY_UNCONFIRMED'):read(Client(validity=None),FilledOrders(tmp_path))
