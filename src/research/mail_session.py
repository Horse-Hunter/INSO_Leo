"""Thread-owned read-only client on existing9222; canonical adapters/pages only."""
from contextlib import contextmanager
from hashlib import sha256
from types import SimpleNamespace
from uuid import uuid4

from .bom_ai import CdpBomAiAuthenticatedBrowser
from .cdp_pages import (
    ReadOnlyPageClosed,
    close_research_page,
    market_read_pages,
    native_page_owner,
    new_background_page,
    shared_playwright_factory,
)
from .runtime import ResearchMarketSession, build_research_service


class _ReadOnlyBom(CdpBomAiAuthenticatedBrowser):
    def _login_once_if_required(self, page, login, target_url):
        # Independent service never submits a login or takes over a human page.
        return


class DetailedReadSession(ResearchMarketSession):
    def __enter__(self):
        super().__enter__()
        try:
            factory = shared_playwright_factory(lambda: (self._playwright, self._browser), admission=self._admission)
            self._service = build_research_service(self._config,
                icnet_client=self._service._icnet._client,
                findchips_client=self._service._price_sources[0]._client,
                hqew_client=self._service._price_sources[1]._client,
                lcsc_client=self._service._price_sources[2]._client,
                bom_ai_browser=_ReadOnlyBom(self._config.bom_ai, cdp_url=self._config.cdp.cdp_url,
                    timeout_ms=self._config.browser.timeout_ms, playwright_factory=factory),
                inso_operation_access=self, playwright_provider=lambda: (self._playwright, self._browser),
                page_admission=self._admission)
        except BaseException:
            self.__exit__(None, None, None)
            raise
        return self

    @contextmanager
    def operation_page(self):
        """Native INSO history adapter reads only a newly owned dedicated target."""
        page = new_background_page(self._browser, self._browser.contexts[0],
                                   timeout_ms=self._config.browser.timeout_ms)
        owner = native_page_owner(page)
        try:
            if not owner:
                raise ValueError("MAIL_READ_OWNER_UNCONFIRMED")
            yield SimpleNamespace(page=page)
            if page.is_closed():
                raise ReadOnlyPageClosed("OWNED_READ_TAB_CLOSED")
            if native_page_owner(page) != owner:
                raise ValueError("MAIL_READ_OWNER_CHANGED")
        finally:
            close_research_page(page)

    def read_source(self, task_id, source, order, reference, fx):
        self._check_thread()
        for attempt in range(3):
            try:
                with market_read_pages("mail-" + sha256(task_id.encode()).hexdigest()[:12] + "-" + uuid4().hex[:16], self._admission, recover_closed=True):
                    result = self._service.read_detailed_source(source, order, now=reference, fx=fx)
                return result
            except ReadOnlyPageClosed:
                import logging
                logging.getLogger("inso.mail_research").warning("Owned read tab closed; bounded recovery=%s", attempt+1)
                if attempt == 2:
                    raise
        raise AssertionError("bounded recovery exhausted")
