"""Native write selection settles before typing; fake Sheets only."""
import pytest

from src.sheets.quotation_input import QuotationInputUnavailable
from src.workflow.v12_faults import V12Fault
from tests.launcher.test_google_web import GridLocator, GridPage
from tests.launcher.test_google_web import web as web  # noqa: PLC0414


def payload(service, first="A", last="N"):
    return service.update(spreadsheetId="test",range=f"'报价输入'!{first}2:{last}2",
        valueInputOption="RAW",body={"values":[[f"synthetic-{n}" for n in range(14)]]}).execute()


@pytest.mark.parametrize("mode",["value","focus"])
@pytest.mark.parametrize("cell",["A2","D2"])
def test_delayed_native_namebox_value_or_focus_settles_before_each_write(web,monkeypatch,mode,cell):
    service,browser,_,human=web
    value=GridLocator.input_value;evaluate=GridLocator.evaluate;wait=GridPage.wait_for_function
    observed=[]
    def input_value(control):
        if control.kind=="box" and control.page.selection==cell and mode=="value" and not observed:return "Z999"
        return value(control)
    def focus(control,script):
        if control.page.selection==cell and mode=="focus" and not observed:return True
        return evaluate(control,script)
    def settle(page,script,**kwargs):
        if "#t-name-box" in script and "document.activeElement" in script:
            assert kwargs['timeout']<=10000 and kwargs['arg']==page.selection
            if page.selection==cell:observed.append(True)
            return
        return wait(page,script,**kwargs)
    monkeypatch.setattr(GridLocator,"input_value",input_value)
    monkeypatch.setattr(GridLocator,"evaluate",focus)
    monkeypatch.setattr(GridPage,"wait_for_function",settle)
    with service.poll_scope():assert payload(service)=={"updatedCells":14}
    assert observed and len(browser.contexts[0].pages[-1].typed)==14 and not human.closed


@pytest.mark.parametrize("partial",[False,True])
def test_persistent_selection_failure_never_types_wrong_cell_or_loses_partial_write_protection(web,monkeypatch,partial):
    from playwright.sync_api import TimeoutError as PageTimeout
    service,browser,_,human=web
    wait=GridPage.wait_for_function
    def blocked(page,script,**kwargs):
        if "#t-name-box" in script and "document.activeElement" in script:
            if page.selection=="D2":raise PageTimeout("synthetic native selection never settled")
            return
        return wait(page,script,**kwargs)
    monkeypatch.setattr(GridPage,"wait_for_function",blocked)
    with service.poll_scope(),pytest.raises(Exception) as caught:
        payload(service,"A" if partial else "D","N" if partial else "Q")
    page=browser.contexts[0].pages[-1]
    assert len(page.typed)==(3 if partial else 0) and not human.closed
    if partial:
        assert isinstance(caught.value,QuotationInputUnavailable)
        assert caught.value.reason=="GOOGLE_WRITE_SETTLEMENT_UNCONFIRMED" and not page.closed


@pytest.mark.parametrize("failure",["auth","document"])
def test_selection_settlement_cannot_hide_auth_or_document_change_before_typing(web,monkeypatch,failure):
    service,browser,_,human=web
    wait=GridPage.wait_for_function
    def changed(page,script,**kwargs):
        if "#t-name-box" in script and "document.activeElement" in script:
            if failure=="auth":page.login_markers.add("登录")
            else:page.url="https://docs.google.com/spreadsheets/d/other/edit#gid=29"
            return
        return wait(page,script,**kwargs)
    monkeypatch.setattr(GridPage,"wait_for_function",changed)
    with service.poll_scope(),pytest.raises(V12Fault):payload(service)
    assert not browser.contexts[0].pages[-1].typed and not human.closed


def test_native_owner_loss_after_selection_retains_page_and_never_types(web,monkeypatch):
    service,browser,_,human=web
    wait=GridPage.wait_for_function
    def changed(page,script,**kwargs):
        if '#t-name-box' in script and 'document.activeElement' in script:
            monkeypatch.setattr('src.launcher.google_web.page_owner',lambda _:None)
            return
        return wait(page,script,**kwargs)
    monkeypatch.setattr(GridPage,'wait_for_function',changed)
    with service.poll_scope(),pytest.raises(V12Fault):payload(service)
    page=browser.contexts[0].pages[-1]
    assert not page.typed and not page.closed and not human.closed


def test_keyboard_timeout_preserves_unknown_input_and_does_not_retype(web,monkeypatch):
    service,browser,_,human=web
    def failed(page,text,**kwargs):
        page.typed.append(text)
        raise TimeoutError('synthetic reply lost after possible input')
    monkeypatch.setattr(GridPage,'type_text',failed)
    with service.poll_scope(),pytest.raises(QuotationInputUnavailable) as caught:payload(service)
    page=browser.contexts[0].pages[-1]
    assert caught.value.reason=='GOOGLE_WRITE_SETTLEMENT_UNCONFIRMED'
    assert len(page.typed)==1 and not page.closed and not human.closed

@pytest.mark.parametrize('fault',['auth','document','keyboard'])
def test_real_adapter_and_updater_preserve_native_safety_and_partial_input(web,monkeypatch,fault):
    from src.inso.quotation_read import QUOTATION_COLUMNS
    from src.sheets import WorksheetIdentity
    from src.sheets.quotation_input import GoogleQuotationInput, QuotationInputLocation
    from src.workflow.v13_quotation import QuotationOutcome
    from tests.workflow.test_v13_quote_update import found
    from tests.workflow.test_v13_quote_update import service as updater_service
    service,browser,_,human=web
    updater,_,_,actions,_=updater_service()
    updater._input=GoogleQuotationInput(service,QuotationInputLocation(
        WorksheetIdentity('fake-sheet','报价输入'),2,1,'29'),expected_columns=QUOTATION_COLUMNS)
    wait=GridPage.wait_for_function
    def settle(page,script,**kwargs):
        if '#t-name-box' in script and 'document.activeElement' in script:
            if fault=='auth':page.login_markers.add('登录')
            elif fault=='document':page.url='https://docs.google.com/spreadsheets/d/other/edit#gid=29'
            return
        return wait(page,script,**kwargs)
    monkeypatch.setattr(GridPage,'wait_for_function',settle)
    if fault=='keyboard':
        def timeout(page,text,**kwargs):
            page.typed.append(text)
            raise TimeoutError('synthetic possible partial input')
        monkeypatch.setattr(GridPage,'type_text',timeout)
    with service.poll_scope():
        if fault=='keyboard':
            result=updater.update_one(found())
            assert result.outcome is QuotationOutcome.ROW_FAILED
        else:
            with pytest.raises(V12Fault) as caught:updater.update_one(found())
            assert caught.value.reason==('GOOGLE_AUTHENTICATION_REQUIRED' if fault=='auth' else 'GOOGLE_SPREADSHEET_UNAVAILABLE')
    assert actions.clicks==0 and not human.closed
    page=browser.contexts[0].pages[-1]
    assert len(page.typed)==(1 if fault=='keyboard' else 0)
    if fault in {'keyboard','document'}:assert not page.closed

