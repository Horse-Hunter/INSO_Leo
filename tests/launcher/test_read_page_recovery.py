"""A lost read-only page is not evidence of an unknown Google write."""
import pytest
from playwright.sync_api import Error as PageError
from playwright.sync_api import TimeoutError as PageTimeout

from src.sheets import WorksheetIdentity
from src.sheets.google_reader import GoogleSheetsRowReader
from tests.launcher.test_google_web import GridPage
from tests.launcher.test_google_web import web as web  # noqa: PLC0414


@pytest.mark.parametrize("sheet",["2026","SHAHAB"])
def test_retained_read_closed_during_download_reopens_only_its_read_without_false_write_hold(web,monkeypatch,sheet):
    service,browser,_rows,human=web;service._retained_pages={}
    reader=GoogleSheetsRowReader(service,retry_wait=lambda _:False)
    ws=WorksheetIdentity("test",sheet)
    with service.poll_scope():expected=reader.read_rows(ws)
    old=browser.contexts[0].pages[-1]
    original_evaluate=GridPage.evaluate
    def strict_evaluate(page,*args,**kwargs):
        if page.closed:raise PageError("Target page, context or browser has been closed")
        return original_evaluate(page,*args,**kwargs)
    monkeypatch.setattr(GridPage,"evaluate",strict_evaluate)
    original_download=service._download;failures=[]
    def interrupted(page,actions):
        if not failures:
            assert actions._poll_entry is not None
            failures.append(page);page.closed=True
            raise PageTimeout("synthetic owned READ disappeared during download")
        return original_download(page,actions)
    monkeypatch.setattr(service,"_download",interrupted)
    with service.poll_scope():assert reader.read_rows(ws)==expected
    assert old.closed and not human.closed
    assert sum(not p.closed for p in browser.contexts[0].pages[1:])==1
    assert all(not protected for _target,protected,_reopen in service._retained_pages.values())
