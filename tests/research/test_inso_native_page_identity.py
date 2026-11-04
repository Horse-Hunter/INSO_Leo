"""Regression: direct HTTP rejected, original native settled read succeeds."""
from contextlib import contextmanager
from types import SimpleNamespace

from src.inso.duplicate_history import PlaywrightProcurementHistoryPage
from src.research.inso_history import (
    InsoBrowserConfig,
    InsoLogin,
    PlaywrightInsoReadOnlyBrowser,
)


def test_page_identity_rejection_is_avoided_by_original_native_query(monkeypatch):
    calls=[]
    frame=object()
    class Request:
        def post(self,*args,**kwargs):
            calls.append("unsafe-direct-http")
            return SimpleNamespace(status=409,text=lambda:'{"Code":"PAGE_IDENTITY_REQUIRED"}')
    page=SimpleNamespace(request=Request())
    @contextmanager
    def borrow():
        yield SimpleNamespace(page=page,shell_frame=frame)
    def native(self,target_mpn,**kwargs):
        assert self._page is frame and target_mpn=="SYNTH-NEW-1"
        calls.append("native")
        return {"rows":[{"CreateTime":"2026-11-04 12:00:00","InPrice":"1.25","CurrencyID":"USD","PartNo":"SYNTH-NEW-1"}]}
    monkeypatch.setattr(PlaywrightProcurementHistoryPage,"query_exact_response",native)
    browser=PlaywrightInsoReadOnlyBrowser(InsoBrowserConfig(login_url="https://inso.example/"),operation_access=SimpleNamespace(operation_page=borrow))
    capture=browser.fetch_procurement_temporary_inquiry_history("SYNTH-NEW-1",InsoLogin("synthetic","synthetic"))
    assert len(capture.records)==1 and calls==["native"]


import pytest

from src.inso.duplicate_history import (
    DuplicateHistoryFailure,
    InsoDuplicateHistoryError,
)
from src.inso.session import SecurityViolation
from src.research.inso_history import InsoReadError


@pytest.mark.parametrize("failure,expected",[
    (SecurityViolation("synthetic invalid lease"),"AUTHENTICATED_SESSION_REQUIRED"),
    (InsoDuplicateHistoryError(DuplicateHistoryFailure.QUERY_SETTLEMENT_UNCONFIRMED),"QUERY_SETTLEMENT_UNCONFIRMED"),
    (InsoDuplicateHistoryError(DuplicateHistoryFailure.RESULT_IDENTIFIER_AMBIGUOUS),"RESULT_IDENTIFIER_AMBIGUOUS"),
])
def test_native_failure_stays_unknown_and_never_falls_back_to_direct_http(monkeypatch,failure,expected):
    calls=[]
    page=SimpleNamespace(request=SimpleNamespace(post=lambda *a,**k:calls.append("forbidden-http")))
    @contextmanager
    def borrow():yield SimpleNamespace(page=page,shell_frame=object())
    def native(self,*args,**kwargs):raise failure
    monkeypatch.setattr(PlaywrightProcurementHistoryPage,"query_exact_response",native)
    browser=PlaywrightInsoReadOnlyBrowser(InsoBrowserConfig(login_url="https://inso.example/"),operation_access=SimpleNamespace(operation_page=borrow))
    with pytest.raises(InsoReadError) as caught:
        browser.fetch_procurement_temporary_inquiry_history("SYNTH-NEW-1",InsoLogin("synthetic","synthetic"))
    assert caught.value.code==expected and calls==[]


@pytest.mark.parametrize("payload,expected",[
    ({"rows":[]},None),
    ({"Code":"PAGE_IDENTITY_REQUIRED"},"RESPONSE_ROWS_MISSING"),
    ({"rows":"unverified"},"HISTORY_ROWS_UNPARSEABLE"),
])
def test_native_empty_is_distinct_from_unverified_or_page_identity_failure(monkeypatch,payload,expected):
    @contextmanager
    def borrow():yield SimpleNamespace(shell_frame=object())
    monkeypatch.setattr(PlaywrightProcurementHistoryPage,"query_exact_response",lambda *a,**k:payload)
    browser=PlaywrightInsoReadOnlyBrowser(InsoBrowserConfig(login_url="https://inso.example/"),operation_access=SimpleNamespace(operation_page=borrow))
    if expected is None:
        assert browser.fetch_procurement_temporary_inquiry_history("SYNTH-NEW-1",InsoLogin("synthetic","synthetic")).records==()
    else:
        with pytest.raises(InsoReadError) as caught:
            browser.fetch_procurement_temporary_inquiry_history("SYNTH-NEW-1",InsoLogin("synthetic","synthetic"))
        assert caught.value.code==expected
