"""Actual native target lease logic with fake CDP; never attaches a real client."""
import threading
from types import SimpleNamespace

import pytest

from src.research.cdp_pages import (
    PageResourceAdmission,
    ReadOnlyPageClosed,
    close_research_page,
    new_background_page,
)
from src.research.detailed import DetailedOrder, TpFx
from src.research.mail_session import DetailedReadSession
from src.research.source_contracts import ResearchSource
from tests.research.test_cdp_pages import RacingTargets
from tests.research.test_market_read import attach_scope_target
from tests.workflow.test_v12_notifications import NOW


@pytest.mark.parametrize("closures", [1, 3])
def test_closed_own_page_recovers_bounded_without_adopting_identical_human_page(closures):
    protocol = RacingTargets()
    parent = PageResourceAdmission()
    admission = PageResourceAdmission(parent=parent)
    protocol._inso_page_admission = admission
    pages = []
    def read(*_args, **_kwargs):
        page = attach_scope_target(protocol, new_background_page(protocol, protocol, timeout_ms=1234))
        page.url = "https://synthetic.invalid/"
        pages.append(page)
        if len(pages) <= closures:
            page.closed = True  # Owner closes only this task's target mid-read.
        else:
            close_research_page(page)
        return "confirmed", None
    session = object.__new__(DetailedReadSession)
    session._thread, session._admission = threading.get_ident(), admission
    session._service = SimpleNamespace(read_detailed_source=read)
    if closures == 3:
        with pytest.raises(ReadOnlyPageClosed):
            session.read_source("mail-research:synthetic", ResearchSource.HQEW, DetailedOrder("MPN"), NOW, TpFx(None, NOW))
    else:
        assert session.read_source("mail-research:synthetic", ResearchSource.HQEW, DetailedOrder("MPN"), NOW, TpFx(None, NOW)) == ("confirmed", None)
    assert len(pages) == min(closures+1, 3)
    assert all(page.is_closed() for page in pages)
    assert all(not page.is_closed() for page in protocol.pages if page not in pages)
    assert all(page._inso_native_page_owner[1].startswith("mail-") for page in pages)
    parent.require_open(); admission.require_open()


def test_child_cleanup_uncertainty_does_not_poison_main_browser_admission():
    from src.research.cdp_pages import PageTargetCleanupError
    parent = PageResourceAdmission()
    child = PageResourceAdmission(parent=parent)
    child.invalidate(PageTargetCleanupError(()))
    with pytest.raises(PageTargetCleanupError):
        child.require_open()
    parent.require_open()


def test_foreground_priority_defers_background_without_new_thread_or_tab():
    from src.launcher.research_budget import ResearchBudget, ResearchDeferred
    budget = ResearchBudget()
    with budget.foreground(), pytest.raises(ResearchDeferred), budget.background():
        pytest.fail("background cannot enter while a foreground operation is active")
    with budget.background():
        pass
