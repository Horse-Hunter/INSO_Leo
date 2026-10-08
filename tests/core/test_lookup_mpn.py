import pytest

from src.core.mpn import lookup_mpn_matches, lookup_mpn_prefix, normalize_lookup_mpn


@pytest.mark.parametrize("observed, expected", [
    ("WGI210", True), ("WGI210IT", True), ("wgi210it s ljxs", True),
    ("W_GI\t210–IT-S_LJXS", True), ("ＷＧＩ２１０ＩＴ", True),
    ("WGI210" + "A" * 10, True), ("WGI210" + "A" * 11, False),
    ("XWGI210IT", False), ("WGI211IT", False), ("WGI21", False),
    ("", False), (None, False), ("WGI210/+()", True),
])
def test_owner_wgi_example_and_exact_tail_boundary(observed, expected):
    assert lookup_mpn_matches(" W_GI–210_IT ", observed) is expected
    assert lookup_mpn_prefix(" W_GI–210_IT ") == "WGI210"


@pytest.mark.parametrize("target, observed, expected", [
    ("", "ABC", False), (" _− ", "ABC", False), (None, "ABC", False),
    ("A", "a", True), ("A", "AB", False), ("AB", "a_b", True),
    ("AB", "ABC", False), ("ABC", "A", True), ("ABC", "BA", False),
    ("ABC/12", "ABC12", False), ("ABC+12", "ABC12", False),
    ("WGI210ITSLJXS", "WGI210IT", False),
])
def test_directional_short_empty_and_preserved_symbols(target, observed, expected):
    assert lookup_mpn_matches(target, observed) is expected


def test_normalization_removes_only_authorized_separators():
    assert normalize_lookup_mpn("w_g\u200b i\ufeff-210−it\u2060") == "WGI210IT"
    assert normalize_lookup_mpn("A/+().B") == "A/+().B"
