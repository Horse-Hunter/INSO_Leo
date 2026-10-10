from dataclasses import replace
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from src.launcher import sales_header as service
from src.order_mail.contracts import ContractLine, ContractOrder, OrderError
from src.research.icnet import IcNetPage, IcNetPageUnavailable
from tests.inso.test_sales_details import Grid
from tests.inso.test_sales_header import HeaderPage


def order():
    line = ContractLine('TEST-A','1-3 DAYS','TEST','24+',2,Decimal('3.25'),'2026-10-17')
    return ContractOrder('SHAWN20260101-01', (line, line, replace(line, part_number='TEST-B')), date(2026,10,10))


def test_serial_package_preflight_cache_exact_duplicates_no_model_filter():
    calls = []
    class Client:
        def fetch_first_page(self, mpn):
            calls.append(mpn)
            return IcNetPage('<div id="resultList"><li class="stair_tr"><div class="product_number">OTHER</div><div class="result_pakaging">QFN</div></li></div>', '', None)
    rows = service.prepare_sales_rows(order(), Client())
    assert calls == ['TEST-A','TEST-B'] and len(rows) == 3
    assert all(r['package']=='QFN' for r in rows)


def test_package_failure_stops_whole_preflight():
    class Client:
        def fetch_first_page(self, mpn): raise IcNetPageUnavailable('INTERNAL_PROVIDER_URL')
    with pytest.raises(OrderError) as exc: service.prepare_sales_rows(order(), Client())
    assert exc.value.code == 'ICNET' and exc.value.part_number == 'TEST-A'
    assert 'INTERNAL' not in str(exc.value)


def setup(monkeypatch):
    from src.inso import sales_details, sales_header
    from src.order_mail import contracts
    from src.research import icnet
    phases, notifications = [], []
    def read(*args,**kwargs):
        phases.append('parse'); return order()
    monkeypatch.setattr(contracts,'parse_contract',read)
    config=SimpleNamespace(cdp=SimpleNamespace(cdp_url='http://127.0.0.1:9222'),browser=SimpleNamespace(timeout_ms=5000))
    monkeypatch.setattr(service,'sales_config',lambda *a:(config,{}))
    handle=SimpleNamespace(owned=False, browser=SimpleNamespace(contexts=[SimpleNamespace(pages=[])]),playwright=object(),disconnect=lambda:phases.append('detach'))
    monkeypatch.setattr(service,'acquire_cdp_browser',lambda *a:handle)
    page=SimpleNamespace(bring_to_front=lambda:None, close=lambda:phases.append('close-blank'))
    monkeypatch.setattr(service,'new_background_page',lambda *a,**k:page)
    monkeypatch.setattr(service,'maximize_order_window',lambda *a:phases.append('maximize'))
    from src.order_mail import filled, inspection
    monkeypatch.setattr(filled,'FilledOrders',lambda root:SimpleNamespace(contains=lambda keys:False,mark=lambda keys:phases.append('mark')))
    def mail(**kw):
        phases.append('mail')
        return SimpleNamespace(excel=b'test',identities=('opaque',))
    monkeypatch.setattr(inspection,'read_oldest_order_mail',mail)

    monkeypatch.setattr(icnet,'CdpIcNetClient',lambda **kw:object())
    def acquire(**kwargs):
        phases.append('sales');return handle,page,False
    monkeypatch.setattr(service,'acquire_sales_tab',acquire)
    header=HeaderPage()
    monkeypatch.setattr(sales_header,'PlaywrightSalesHeaderPage',lambda *a,**kw:header)
    grid=Grid()
    monkeypatch.setattr(sales_details,'PlaywrightSalesDetailsPage',lambda *a:grid)
    return phases,notifications,grid


def run(notifications):
    return service.run_sales_header_check(config_path='unused',production_path='unused',root='unused',notify=lambda **kw:notifications.append(kw))


def test_all_packages_complete_before_sales_and_success_no_notify(monkeypatch):
    phases,notes,grid=setup(monkeypatch)
    def packages(o,c):
        phases.append('packages')
        from tests.inso.test_sales_details import expected
        return expected(3)
    monkeypatch.setattr(service,'prepare_sales_rows',packages)
    assert run(notes)[0]=='WAITING_OWNER'
    assert phases==['maximize','mail','parse','packages','sales','mark','detach'] and not notes and grid.adds==2


def test_icnet_failure_no_sales_and_notification_once(monkeypatch):
    phases,notes,_=setup(monkeypatch)
    def fail(*a): raise OrderError('ICNET',pi_no=order().pi_no,part_number='TEST-A')
    monkeypatch.setattr(service,'prepare_sales_rows',fail)
    assert run(notes)[0]=='STOPPED' and 'sales' not in phases and phases[-1]=='detach'
    assert len(notes)==1 and notes[0]['part_number']=='TEST-A'


def test_readback_failure_specific_business_mail_no_internal_code(monkeypatch):
    from tests.inso.test_sales_details import expected
    _,notes,grid=setup(monkeypatch)
    grid.wrong='quantity'
    monkeypatch.setattr(service,'prepare_sales_rows',lambda *a:expected(3))
    assert run(notes)[0]=='STOPPED'
    assert len(notes)==1 and '订单量' in notes[0]['situation']
    assert 'MISMATCH' not in notes[0]['situation'] and notes[0]['part_number']=='TEST-A'


@pytest.mark.parametrize('failure', ['LOGIN_REQUIRED','RESULT_NAVIGATION_FAILED','PACKAGE_COLUMN_UNCONFIRMED','PACKAGE_EMPTY'])
def test_icnet_login_search_parse_and_empty_each_stop_before_sales(monkeypatch, failure):
    from src.research.icnet import IcNetParseError
    phases,notes,_=setup(monkeypatch)
    class Client:
        def fetch_first_page(self, mpn):
            if failure == 'PACKAGE_EMPTY':
                return IcNetPage('<div id="resultList"><li class="stair_tr"><div class="product_number">OTHER</div><div class="result_pakaging"></div></li></div>', '', None)
            if failure == 'PACKAGE_COLUMN_UNCONFIRMED': raise IcNetParseError(failure)
            raise IcNetPageUnavailable(failure)
    from src.research import icnet
    monkeypatch.setattr(icnet,'CdpIcNetClient',lambda **kw:Client())
    assert run(notes)[0]=='STOPPED' and 'sales' not in phases
    assert len(notes)==1 and failure not in notes[0]['situation']



@pytest.mark.parametrize('code,field', [('REQUIRED','DC'),('LEAD_TIME','L/T'),('MAIL',None),('STRUCTURE',None)])
def test_contract_failure_zero_sales_mutation_and_safe_notify(monkeypatch, code, field):
    from src.order_mail import contracts
    phases,notes,_=setup(monkeypatch)
    def fail(*args, **kwargs): raise OrderError(code,field=field,pi_no='SHAWN20260101-01')
    monkeypatch.setattr(contracts, 'parse_contract', fail)
    assert run(notes)[0]=='STOPPED' and 'sales' not in phases and 'mark' not in phases
    assert len(notes)==1 and code not in notes[0]['situation']


def test_new_sales_owner_every_click_old_review_page_not_borrowed(monkeypatch):
    from tests.inso.test_sales_details import expected
    _phases,notes,_=setup(monkeypatch)
    owners=[]
    def acquire(**kwargs):
        assert kwargs['reuse'] is False
        owners.append(kwargs['owner'])
        return SimpleNamespace(disconnect=lambda:None),kwargs['page'],False
    monkeypatch.setattr(service,'acquire_sales_tab',acquire)
    monkeypatch.setattr(service,'prepare_sales_rows',lambda *a:expected(3))
    assert run(notes)[0]=='WAITING_OWNER'
    assert run(notes)[0]=='WAITING_OWNER'
    assert len(owners)==2 and owners[0]!=owners[1] and all(o.startswith('v14-sales-') for o in owners)


def test_no_orders_end_without_sales_or_exception_notification(monkeypatch):
    from src.order_mail import inspection
    phases,notes,_=setup(monkeypatch)
    monkeypatch.setattr(inspection,'read_oldest_order_mail',lambda **kw:None)
    assert run(notes)[0]=='NO_ORDER' and phases==['maximize','close-blank','detach'] and not notes


def test_failed_fill_has_no_completion_receipt(monkeypatch):
    from tests.inso.test_sales_details import expected
    phases,notes,grid=setup(monkeypatch)
    grid.wrong='quantity'
    monkeypatch.setattr(service,'prepare_sales_rows',lambda *a:expected(3))
    assert run(notes)[0]=='STOPPED' and 'mark' not in phases and len(notes)==1


def test_mail_failure_has_correct_human_notification(monkeypatch):
    from src.order_mail import inspection
    phases,notes,_=setup(monkeypatch)
    def fail(**kwargs): raise ValueError('SECRET_METADATA_UID_INTERNAL')
    monkeypatch.setattr(inspection,'read_oldest_order_mail',fail)
    assert run(notes)[0]=='STOPPED' and 'sales' not in phases
    assert len(notes)==1 and '229' in notes[0]['situation']
    assert 'SECRET' not in notes[0]['situation']
