from types import SimpleNamespace

from src.launcher.sales_header import maximize_order_window


def test_restore_maximize_verify_front_and_detach_without_navigation():
    calls=[]
    class Session:
        def send(self,op,params=None):
            calls.append((op,params))
            return {'Target.getTargetInfo':{'targetInfo':{'targetId':'owned-order'}},
                'Browser.getWindowForTarget':{'windowId':7},
                'Browser.getWindowBounds':{'bounds':{'windowState':'maximized'}}}.get(op,{})
        def detach(self):calls.append(('detach',None))
    browser=SimpleNamespace(new_browser_cdp_session=lambda:Session())
    page=SimpleNamespace(context=SimpleNamespace(new_cdp_session=lambda p:Session()),bring_to_front=lambda:calls.append(('front',None)))
    maximize_order_window(browser,page)
    assert [params['bounds']['windowState'] for op,params in calls if op=='Browser.setWindowBounds']==['normal','maximized']
    assert calls[-3:]==[('front',None),('detach',None),('detach',None)]
