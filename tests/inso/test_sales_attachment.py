from types import SimpleNamespace

import pytest

from src.inso.sales_attachment import PlaywrightSalesPdfUpload, UploadStop


class Node:
    def __init__(self, frame, key): self.f,self.key=frame,key
    @property
    def first(self): return self
    def nth(self,i): return self
    def locator(self,key): return Node(self.f,key)
    def count(self):
        if self.key=='#billdata_image a': return int(self.f.existing or (self.f.started and self.f.proof))
        if self.key=='.filelist > li': return int(self.f.queued)
        if self.key=='.success': return int(self.f.started and self.f.proof)
        return 1
    def wait_for(self,**kw): pass
    def is_visible(self): return True
    def inner_text(self):
        if self.key=='p.title': return 'wrong.pdf' if self.f.wrong else 'synthetic.pdf'
        if self.key=='.uploadBtn:visible': return '开始上传'
        if self.key=='.statusBar .info': return '共1张，已上传1张' if self.f.proof else '上传错误'
        if self.key=='#billdata_image a': return 'synthetic.pdf'
        raise AssertionError(self.key)
    def click(self,**kw):
        if self.key=='a#li_img': return
        assert self.key=='.uploadBtn:visible'
        self.f.clicks+=1;self.f.started=True
        if self.f.throw: raise RuntimeError('PRIVATE')
    def set_input_files(self,value,**kw):
        self.f.files=value;self.f.queued=True


class Frame:
    def __init__(self):
        self.queued=False;self.started=False;self.existing=False;self.proof=True;self.wrong=False;self.throw=False;self.clicks=0
    def locator(self,key): return Node(self,key)


def adapter():
    frame=Frame()
    header=SimpleNamespace(frame=frame,_bill=lambda:frame,_assert_owner=lambda:None,page=SimpleNamespace(wait_for_timeout=lambda ms:None))
    return PlaywrightSalesPdfUpload(header),frame


PDF=SimpleNamespace(name='synthetic.pdf',data=b'%PDF-test')


def test_native_memory_upload_single_click_double_proof():
    uploader,frame=adapter();uploader.upload(PDF)
    assert frame.files=={'name':PDF.name,'mimeType':'application/pdf','buffer':PDF.data}
    assert frame.clicks==1 and uploader.dispatched
    with pytest.raises(UploadStop,match='ALREADY_DISPATCHED'): uploader.upload(PDF)
    assert frame.clicks==1


@pytest.mark.parametrize('issue',['existing','queued','wrong'])
def test_existing_or_mismatched_queue_no_dispatch(issue):
    uploader,frame=adapter();setattr(frame,issue,True)
    with pytest.raises(UploadStop): uploader.upload(PDF)
    assert frame.clicks==0


@pytest.mark.parametrize('issue',['throw','proof'])
def test_uncertain_upload_never_replayed(issue):
    uploader,frame=adapter();setattr(frame,issue,issue=='throw')
    with pytest.raises(UploadStop,match='UPLOAD_UNCONFIRMED'): uploader.upload(PDF)
    with pytest.raises(UploadStop,match='ALREADY_DISPATCHED'): uploader.upload(PDF)
    assert frame.clicks==1


def test_ownership_lost_stops_before_click():
    uploader,frame=adapter()
    uploader.header._assert_owner=lambda:(_ for _ in ()).throw(ValueError('PRIVATE'))
    with pytest.raises(UploadStop,match='UPLOAD_UNCONFIRMED'): uploader.upload(PDF)
    assert frame.clicks==0
