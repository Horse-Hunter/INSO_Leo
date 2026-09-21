from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from src.research.source_contracts import (
    PRICE_SOURCES,
    EvidenceField,
    PriceCandidate,
    ResearchSource,
    SourceEvidence,
    SourceOutcome,
    SourceResult,
    is_strict_mpn_match,
)


CAPTURED_AT = datetime(2026, 9, 21, 8, 0, tzinfo=UTC)


def _evidence(
    source: ResearchSource,
    outcome: SourceOutcome = SourceOutcome.SUCCESS,
) -> SourceEvidence:
    return SourceEvidence(
        source=source,
        query_mpn="ABC123",
        matched_mpn=(
            "ABC123" if outcome is not SourceOutcome.NO_STRICT_MPN_MATCH else None
        ),
        outcome=outcome,
        captured_at=CAPTURED_AT,
        source_url="https://example.invalid/item",
        fields=(EvidenceField("stock_present", True),),
    )


def _candidate(source: ResearchSource = ResearchSource.FINDCHIPS) -> PriceCandidate:
    return PriceCandidate(
        source=source,
        matched_mpn="ABC123",
        raw_price=Decimal("1.25"),
        raw_currency="USD",
        normalized_rmb_price=Decimal("8.90"),
        captured_at=CAPTURED_AT,
        source_url="https://example.invalid/item",
    )


def test_source_catalog_and_price_sources_are_exact() -> None:
    assert {source.value for source in ResearchSource} == {
        "ic.net",
        "findchips",
        "hqew",
        "lcsc",
        "bom.ai",
    }
    assert PRICE_SOURCES == (
        ResearchSource.FINDCHIPS,
        ResearchSource.HQEW,
        ResearchSource.LCSC,
        ResearchSource.BOM_AI,
    )
    assert ResearchSource.IC_NET not in PRICE_SOURCES


def test_source_outcome_catalog_is_exact() -> None:
    assert {outcome.value for outcome in SourceOutcome} == {
        "SUCCESS",
        "NO_STRICT_MPN_MATCH",
        "NO_VALID_PRICE",
        "SOURCE_UNAVAILABLE",
    }


@pytest.mark.parametrize(
    ("target", "observed"),
    [
        ("ABC123", "abc123"),
        (" ABC123 ", "ABC123"),
    ],
)
def test_strict_mpn_match_accepts_only_edge_whitespace_and_case_differences(
    target: str,
    observed: str,
) -> None:
    assert is_strict_mpn_match(target, observed)


@pytest.mark.parametrize(
    ("target", "observed"),
    [
        ("ABC123", "ABC123TR"),
        ("ABC123-7", "ABC123-13"),
        ("ABC 123", "ABC123"),
        ("ABC/123", "ABC-123"),
        ("ABC.123", "ABC123"),
    ],
)
def test_strict_mpn_match_does_not_normalize_variants(
    target: str,
    observed: str,
) -> None:
    assert not is_strict_mpn_match(target, observed)


def test_contracts_are_immutable_and_price_is_decimal_safe() -> None:
    candidate = _candidate()
    evidence = _evidence(ResearchSource.FINDCHIPS)
    result = SourceResult(
        source=ResearchSource.FINDCHIPS,
        outcome=SourceOutcome.SUCCESS,
        evidence=evidence,
        price_candidate=candidate,
    )

    assert isinstance(candidate.raw_price, Decimal)
    assert isinstance(candidate.normalized_rmb_price, Decimal)
    with pytest.raises(FrozenInstanceError):
        candidate.raw_price = Decimal("2.00")  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        evidence.query_mpn = "changed"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        result.outcome = SourceOutcome.NO_VALID_PRICE  # type: ignore[misc]


@pytest.mark.parametrize("field", ["raw_price", "normalized_rmb_price"])
def test_price_candidate_rejects_binary_float(field: str) -> None:
    values = {
        "source": ResearchSource.FINDCHIPS,
        "matched_mpn": "ABC123",
        "raw_price": Decimal("1.25"),
        "raw_currency": "USD",
        "normalized_rmb_price": Decimal("8.90"),
        "captured_at": CAPTURED_AT,
    }
    values[field] = 1.25

    with pytest.raises(TypeError, match="must be Decimal"):
        PriceCandidate(**values)  # type: ignore[arg-type]


def test_ic_net_cannot_produce_price_candidate() -> None:
    with pytest.raises(ValueError, match="price sources"):
        _candidate(ResearchSource.IC_NET)


@pytest.mark.parametrize(
    "outcome",
    [
        SourceOutcome.NO_STRICT_MPN_MATCH,
        SourceOutcome.NO_VALID_PRICE,
        SourceOutcome.SOURCE_UNAVAILABLE,
    ],
)
def test_non_success_outcome_rejects_price_candidate(outcome: SourceOutcome) -> None:
    source = ResearchSource.FINDCHIPS

    with pytest.raises(ValueError, match="successful"):
        SourceResult(
            source=source,
            outcome=outcome,
            evidence=_evidence(source, outcome),
            price_candidate=_candidate(source),
        )


@pytest.mark.parametrize("source", PRICE_SOURCES)
def test_successful_price_source_can_carry_matching_candidate(
    source: ResearchSource,
) -> None:
    result = SourceResult(
        source=source,
        outcome=SourceOutcome.SUCCESS,
        evidence=_evidence(source),
        price_candidate=_candidate(source),
    )

    assert result.price_candidate is not None


def test_ic_net_success_can_omit_price_candidate() -> None:
    result = SourceResult(
        source=ResearchSource.IC_NET,
        outcome=SourceOutcome.SUCCESS,
        evidence=_evidence(ResearchSource.IC_NET),
    )

    assert result.price_candidate is None


def test_result_rejects_mismatched_evidence_or_candidate_source() -> None:
    with pytest.raises(ValueError, match="evidence source"):
        SourceResult(
            source=ResearchSource.HQEW,
            outcome=SourceOutcome.SUCCESS,
            evidence=_evidence(ResearchSource.LCSC),
        )

    with pytest.raises(ValueError, match="candidate source"):
        SourceResult(
            source=ResearchSource.HQEW,
            outcome=SourceOutcome.SUCCESS,
            evidence=_evidence(ResearchSource.HQEW),
            price_candidate=_candidate(ResearchSource.LCSC),
        )


def test_result_rejects_mismatched_evidence_outcome() -> None:
    with pytest.raises(ValueError, match="evidence outcome"):
        SourceResult(
            source=ResearchSource.HQEW,
            outcome=SourceOutcome.NO_VALID_PRICE,
            evidence=_evidence(ResearchSource.HQEW, SourceOutcome.SUCCESS),
        )
