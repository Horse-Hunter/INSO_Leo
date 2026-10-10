from datetime import UTC, datetime

import pytest

from src.research.icnet import (
    IcNetPage,
    IcNetParseError,
    parse_icnet_packages,
    select_icnet_package,
)


def page(values, broken=False):
    html = '<div id="resultList">' + ''.join(
        '<li class="stair_tr"><div class="product_number">UNRELATED-MODEL</div>' +
        ('' if broken else f'<div class="result_pakaging">{v}</div>') + '</li>' for v in values) + '</div>'
    return IcNetPage(html, "https://www.ic.net.cn/search/synthetic.html", datetime.now(UTC))


def test_first20_order_no_secondary_matching_blanks_and_mode():
    sample = page(['', 'QFN'] * 10 + ['BGA'] * 30)
    assert len(parse_icnet_packages(sample.html)) == 20
    assert select_icnet_package(sample) == 'QFN'


def test_short_results_frequency_tie_first_seen():
    assert select_icnet_package(page(['BGA', 'QFN', 'QFN'])) == 'QFN'
    assert select_icnet_package(page(['BGA', 'QFN'])) == 'BGA'


@pytest.mark.parametrize('sample', [page(['', '']), page(['QFN'], broken=True), page([]), IcNetPage('<html>bad</html>', '', datetime.now(UTC))])
def test_empty_or_unreliable_column_stops(sample):
    with pytest.raises(IcNetParseError): select_icnet_package(sample)


def test_hidden_row_not_counted_and_ambiguous_column_stops():
    p = page(['QFN'])
    hidden = '<li class="stair_tr" style="display:none"><div class="product_number">X</div><div class="result_pakaging">BGA</div></li>'
    assert parse_icnet_packages(p.html.replace('</div>', '</div>', 1).replace('<li', hidden + '<li', 1)) == ('QFN',)
    with pytest.raises(IcNetParseError):
        parse_icnet_packages(p.html.replace('</li>', '<div class="result_pakaging">BGA</div></li>'))
