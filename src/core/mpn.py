"""Pure shared Owner-defined matching for Research and procurement history.

This policy must not be used for source-row identity or purchase submission
validation. Query prefixes retrieve candidates; comparisons keep the full target.
"""
import unicodedata


def normalize_lookup_mpn(value: object) -> str:
    """Normalize separators/case without changing any stored/displayed model."""
    if not isinstance(value, str):
        return ""
    return "".join(
        char for char in unicodedata.normalize("NFKC", value)
        if not char.isspace() and char != "_"
        and unicodedata.category(char) != "Pd"
        and char not in "\u2212\u200b\ufeff\u2060"
    ).upper()


def lookup_mpn_prefix(target: object) -> str:
    """Drop two cleaned tail characters; very short targets remain exact."""
    cleaned = normalize_lookup_mpn(target)
    return cleaned[:-2] if len(cleaned) > 2 else cleaned


def lookup_mpn_matches(target: object, observed: object) -> bool:
    """Directional prefix match with zero through ten cleaned tail characters."""
    cleaned = normalize_lookup_mpn(target)
    result = normalize_lookup_mpn(observed)
    if not cleaned or not result:
        return False
    if len(cleaned) <= 2:
        return result == cleaned
    prefix = lookup_mpn_prefix(cleaned)
    return result.startswith(prefix) and len(result) - len(prefix) <= 10


def inso_lookup_query(target: object) -> str:
    """Retrieve candidates from ERP's literal contains search before filtering.

    ERP does not remove embedded separators. Use the initial contiguous token,
    bounded by the Owner's cleaned prefix, rather than a concatenation that
    cannot occur in a separated stored model. Full matching still uses the
    unchanged lookup_mpn_matches rule and the original target.
    """
    prefix = lookup_mpn_prefix(target)
    if not prefix or not isinstance(target, str):
        return ""
    token = ""
    for char in unicodedata.normalize("NFKC", target).upper():
        if not normalize_lookup_mpn(char):
            if token:
                break
            continue
        token += char
        if len(token) >= len(prefix):
            break
    return token
