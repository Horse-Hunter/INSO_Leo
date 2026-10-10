"""One native PDF upload, confirmed by status and persisted attachment link."""
import re
from time import monotonic


class UploadStop(ValueError):
    pass


class PlaywrightSalesPdfUpload:
    def __init__(self, header_page):
        self.header = header_page
        self.dispatched = False

    def _frame(self):
        self.header._assert_owner()
        frame = self.header._bill()
        if frame is not self.header.frame:
            raise UploadStop("UPLOAD_PAGE_UNCONFIRMED")
        return frame

    def upload(self, pdf):
        """No Save/submit/HTTP bypass/reset/replay. Bytes go to native input."""
        if self.dispatched:
            raise UploadStop("UPLOAD_ALREADY_DISPATCHED")
        try:
            frame = self._frame()
            tab = frame.locator("a#li_img")
            if tab.count() != 1:
                raise UploadStop("ATTACHMENT_TAB_UNCONFIRMED")
            tab.click(timeout=5000)
            uploader = frame.locator("#uploader:visible")
            uploader.wait_for(state="visible", timeout=10000)
            if uploader.count() != 1 or frame.locator("#billdata_image").count() != 1:
                raise UploadStop("UPLOAD_PANEL_UNCONFIRMED")
            if frame.locator("#billdata_image a").count() or uploader.locator(".filelist > li").count():
                raise UploadStop("ATTACHMENT_NOT_EMPTY")
            picker = uploader.locator("#filePicker input[type=file]")
            if picker.count() != 1:
                raise UploadStop("UPLOAD_INPUT_UNCONFIRMED")
            picker.set_input_files({"name": pdf.name, "mimeType": "application/pdf", "buffer": pdf.data}, timeout=10000)
            rows = uploader.locator(".filelist > li")
            rows.first.wait_for(state="attached", timeout=10000)
            if rows.count() != 1:
                raise UploadStop("UPLOAD_QUEUE_AMBIGUOUS")
            title = rows.first.locator("p.title")
            if title.count() != 1 or title.inner_text().strip() != pdf.name:
                raise UploadStop("UPLOAD_QUEUE_MISMATCH")
            start = uploader.locator(".uploadBtn:visible")
            if start.count() != 1 or start.inner_text().strip() != "开始上传":
                raise UploadStop("UPLOAD_START_UNCONFIRMED")
            self.dispatched = True  # Before dispatch; an exception never triggers another click.
            start.click(timeout=10000)
            deadline = monotonic() + 45
            while monotonic() < deadline:
                self._frame()
                info = uploader.locator(".statusBar .info")
                text = info.inner_text() if info.count() == 1 else ""
                links = frame.locator("#billdata_image a")
                exact = [links.nth(i) for i in range(links.count())
                         if links.nth(i).inner_text().strip() == pdf.name]
                if (re.search(r"已上传\s*1\s*张", text) and re.search(r"共\s*1\s*张", text)
                        and len(exact) == 1 and exact[0].is_visible()
                        and rows.count() == 1 and rows.first.locator(".success").count() == 1):
                    return
                if re.search(r"(?:失败|错误)", text):
                    raise UploadStop("UPLOAD_UNCONFIRMED")
                self.header.page.wait_for_timeout(150)  # Bounded settlement only, no replay.
            raise UploadStop("UPLOAD_UNCONFIRMED")
        except UploadStop:
            raise
        except Exception:  # noqa: BLE001 - filename/page/credential values never in error output
            raise UploadStop("UPLOAD_UNCONFIRMED") from None
