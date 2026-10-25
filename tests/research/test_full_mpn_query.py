"""Search the full source model; fuzzy normalization belongs to comparison only."""
from decimal import Decimal
from urllib.parse import quote

import pytest

from src.core.mpn import lookup_mpn_matches, lookup_mpn_query
from src.research.bom_ai import BomAiBrowserConfig
from src.research.findchips import build_findchips_search_url
from src.research.hqew import build_hqew_result_url
from src.research.icnet import IcNetAdapter
from tests.research.test_icnet import FakeCdpPage, _cdp_client, _page_html, _row_html


@pytest.mark.parametrize("target", ["TEST1234AB", "ABC-123", "Ab+C&12", " W_GI–210_IT "])
def test_full_source_query_and_fuzzy_results_are_separate(target):
    encoded = quote(target, safe="")
    assert lookup_mpn_query(target) == target
    assert build_findchips_search_url(target).endswith("/" + encoded)
    assert build_hqew_result_url(target).endswith("/" + encoded + ".html?y4=1")
    config = BomAiBrowserConfig("https://www.bom.ai/", "https://www.bom.ai/search/{mpn}",
                                "#user", "#password", "#login")
    assert config.result_url(target).endswith("/" + encoded)
    html = _page_html(_row_html(target, "TEST", "10", "SSCP"))
    html = html.replace('<body>', '<body><div class="navigation"><div class="cankaoPrice">'
        '<a><span>￥12.345</span></a></div></div>')
    page = FakeCdpPage("https://www.ic.net.cn/search/" + encoded + ".html", html)
    client, _ = _cdp_client([page], navigate=False)
    result = IcNetAdapter(client).search(target, None, 1)
    assert result.source_result.price_candidate.raw_price == Decimal("12.345")
    assert not page.closed and not page.goto_calls
    assert lookup_mpn_matches("TEST1234AB", "TEST1234CD")
    assert not lookup_mpn_matches("TEST1234AB", "OTHER1234AB")
