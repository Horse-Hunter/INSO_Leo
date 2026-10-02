from datetime import UTC, datetime

import pytest

from src.workflow.v12_contracts import (
    DuplicateCheckResult,
    DuplicateOutcome,
    ReasonCode,
)
from src.workflow.v12_safety import (
    BrandPolicy,
    MpnPolicy,
    brand_matches,
    mpn_matches,
    normalize_brand,
    normalize_mpn,
)


def test_ai_and_duplicate_mpn_policy_names_are_distinct_with_same_frozen_semantics() -> None:
    assert MpnPolicy.AI_MPN_V1.value == "ai-mpn-v1"
    assert MpnPolicy.DUP_MPN_V1.value == "dup-mpn-v1"
    for policy in (MpnPolicy.AI_MPN_V1, MpnPolicy.DUP_MPN_V1):
        assert mpn_matches(" abc-123 ", "ABC-123", policy=policy)
        assert not mpn_matches("ABC-123", "ABC123", policy=policy)
        assert not mpn_matches("ABC / 1", "ABC/1", policy=policy)
        assert not mpn_matches("ABC-1", "ABC-2", policy=policy)
        assert mpn_matches("Ａｂｃ－１２３", "ABC-123", policy=policy)
        assert normalize_mpn("ab c-1", policy=policy) == "AB C-1"


def test_mpn_canonicalizer_only_trims_outer_whitespace_and_ascii_uppercases() -> None:
    assert normalize_mpn("  μabc / .-x  ", policy=MpnPolicy.AI_MPN_V1) == "μABC / .-X"
    assert normalize_mpn("A\tB", policy=MpnPolicy.DUP_MPN_V1) == "A\tB"


def test_ai_brand_policy_is_partial_but_never_vacuous() -> None:
    """Owner decision (2026-09-29): partial brand match is acceptable.

    The ERP AI canonicalises the brand, so the Research label and the ERP code
    differ in wording. An empty token on either side still fails closed.
    """

    policy = BrandPolicy.AI_BRAND_V1
    assert policy.value == "ai-brand-v1"
    assert normalize_brand("  HRS(hirose) ", policy=policy) == "hrs(hirose)"
    assert brand_matches("HRS(hirose)", "HRS", policy=policy)
    assert brand_matches("HRS(hirose)", "hirose", policy=policy)
    assert brand_matches(" Brand ", "brand", policy=policy)
    assert not brand_matches("HRS(hirose)", "Nexperia", policy=policy)
    assert not brand_matches("", "HRS", policy=policy)
    assert not brand_matches("HRS", "   ", policy=policy)
    with pytest.raises(TypeError):
        brand_matches("HRS", None, policy=policy)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        normalize_brand("HRS", policy="unknown")  # type: ignore[arg-type]


def test_duplicate_contract_never_allows_unconfirmed_false_result() -> None:
    now = datetime(2026, 9, 25, tzinfo=UTC)
    with pytest.raises(ValueError):
        DuplicateCheckResult(
            "inq_0123456789abcdef01234567",
            DuplicateOutcome.UNAVAILABLE,
            "ABC-1",
            now,
            repeated=False,
            reason_code=ReasonCode.DUPLICATE_LOOKUP_UNAVAILABLE,
        )

    confirmed = DuplicateCheckResult(
        "inq_0123456789abcdef01234567",
        DuplicateOutcome.CONFIRMED,
        "ABC-1",
        now,
        repeated=False,
    )
    assert confirmed.repeated is False
