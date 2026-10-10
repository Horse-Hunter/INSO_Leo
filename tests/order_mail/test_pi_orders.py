from email.message import EmailMessage
from io import BytesIO
from types import SimpleNamespace

import pytest
from openpyxl import Workbook

from src.order_mail.pi_orders import PiError, PiOrder, extract_pi, read_sample_pi_orders

PI = "SHAWN20260101-01"


def excel(cells=None):
    wb = Workbook()
    for name, value in (cells or {"H1": "PI No.: " + PI + "\nDate: synthetic"}).items():
        wb.active[name] = value
    stream = BytesIO()
    wb.save(stream)
    return stream.getvalue()


def test_pi_inline_and_label_next_cell_preserve_exact_value():
    assert extract_pi(excel()) == PI
    assert extract_pi(excel({"G1": "PI No.", "H1": PI})) == PI
    assert PI not in repr(PiOrder(1, PI))


@pytest.mark.parametrize("cells", [
    {"H1": PI}, {"H1": "PI No.: no value"},
    {"H1": "PI No.: " + PI + " SHAWN20260101-02"},
    {"H1": "PI No.: " + PI, "H2": "PI No.: " + PI},
    {"G1": "PI No.", "H1": '=CONCAT("SHAWN",123)'},
])
def test_missing_multiple_unlabelled_or_formula_pi_stop(cells):
    with pytest.raises(PiError): extract_pi(excel(cells))


def message(date, attachments=1):
    msg = EmailMessage()
    msg["Date"] = date
    msg.set_content("synthetic")
    for i in range(attachments):
        msg.add_attachment(excel(), maintype="application", subtype="octet-stream", filename=f"synthetic{i}.xlsx")
    return msg


def receiver(*, flags=True, attachments=1):
    def inspect(_message_consumer):
        for date in ["Fri, 09 Oct 2026 16:45:52 +0800", "Wed, 07 Oct 2026 12:26:16 +0800", "Sat, 10 Oct 2026 01:00:00 +0800"]:
            _message_consumer(message(date, attachments))
        return SimpleNamespace(status="SUCCESS" if flags else "FLAGS_DIFFER", flags_unchanged=flags)
    return inspect


def test_only_two_confirmed_samples_are_returned():
    assert [o.sample_number for o in read_sample_pi_orders(inspect=receiver())] == [1, 2]


def test_flags_change_or_multiple_excel_stops_before_inso():
    with pytest.raises(PiError, match="MAIL_READ_NOT_CONFIRMED"):
        read_sample_pi_orders(inspect=receiver(flags=False))
    with pytest.raises(PiError, match="EXCEL_ATTACHMENT_AMBIGUOUS"):
        read_sample_pi_orders(inspect=receiver(attachments=2))
