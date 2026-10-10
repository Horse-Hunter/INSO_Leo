from dataclasses import replace
from io import BytesIO

import pytest
from pypdf import PdfWriter

from src.order_mail.inspection import MailPdf, OrderMail, verified_order_pdf


def pdf(encrypted=False):
    writer=PdfWriter()
    writer.add_blank_page(width=100,height=100)
    if encrypted: writer.encrypt('synthetic')
    stream=BytesIO();writer.write(stream)
    return MailPdf('synthetic.pdf',stream.getvalue(),'application/pdf')


def test_unique_pdf_memory_original_bytes():
    attachment=pdf()
    mail=OrderMail(('hash',),b'xlsx',(attachment,))
    assert verified_order_pdf(mail) is attachment
    assert 'synthetic.pdf' not in repr(mail) and 'synthetic.pdf' not in repr(attachment)


@pytest.mark.parametrize('count',[0,2])
def test_missing_or_multiple_pdf_stop(count):
    with pytest.raises(ValueError,match='AMBIGUOUS'):
        verified_order_pdf(OrderMail((),b'',(pdf(),)*count))


@pytest.mark.parametrize('change',[{'name':'../private.pdf'},{'mime':'image/png'},{'data':b'%PDF-broken'},{'data':b'not pdf'}])
def test_invalid_pdf_closed_errors(change):
    with pytest.raises(ValueError,match='ORDER_PDF_INVALID'):
        verified_order_pdf(OrderMail((),b'',(replace(pdf(),**change),)))


def test_encrypted_pdf_stop():
    with pytest.raises(ValueError,match='ORDER_PDF_INVALID'):
        verified_order_pdf(OrderMail((),b'',(pdf(True),)))
