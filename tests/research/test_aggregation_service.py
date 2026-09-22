from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from openpyxl import load_workbook

from src.research.aggregation import aggregate_price_results
from src.research.contracts import ResearchInput, ResearchReasonCode, ResearchStatus
from src.research.excel_output import (
    INQUIRY_ID_HEADER,
    VISIBLE_HEADERS,
    ExcelWriteError,
    ResearchExcelOutput,
)
from src.research.icnet import IcNetResult
from src.research.service import ResearchService
from src.research.source_contracts import (
    PRICE_SOURCES,
    PriceCandidate,
    ResearchSource,
    SourceEvidence,
    SourceOutcome,
    SourceResult,
)

NOW = datetime(2026, 9, 22, tzinfo=UTC)


def _result(
    source: ResearchSource, outcome: SourceOutcome, price: str | None = None
) -> SourceResult:
    candidate = (
        None
        if price is None
        else PriceCandidate(source, "ABC", Decimal(price), "RMB", Decimal(price), NOW)
    )
    evidence = SourceEvidence(
        source,
        "ABC",
        None if outcome is SourceOutcome.NO_STRICT_MPN_MATCH else "ABC",
        outcome,
        NOW,
    )
    return SourceResult(source, outcome, evidence, candidate)


def test_aggregation_20_percent_and_partial_failure() -> None:
    results = (
        _result(ResearchSource.FINDCHIPS, SourceOutcome.SUCCESS, "8"),
        _result(ResearchSource.HQEW, SourceOutcome.SUCCESS, "11"),
        _result(ResearchSource.LCSC, SourceOutcome.NO_VALID_PRICE),
        _result(ResearchSource.BOM_AI, SourceOutcome.SOURCE_UNAVAILABLE),
    )
    agg = aggregate_price_results(results, 10)
    assert agg.status is ResearchStatus.PARTIAL_SUCCESS
    assert agg.show_second_lowest is True
    assert agg.market_reference == "8\n11-华强电子网"
    assert agg.estimated_total == Decimal(80)


def test_hqew_challenge_is_non_blocking_when_another_price_is_valid() -> None:
    results = (
        _result(ResearchSource.FINDCHIPS, SourceOutcome.SUCCESS, "8"),
        _result(ResearchSource.HQEW, SourceOutcome.SOURCE_UNAVAILABLE),
        _result(ResearchSource.LCSC, SourceOutcome.NO_VALID_PRICE),
        _result(ResearchSource.BOM_AI, SourceOutcome.NO_VALID_PRICE),
    )

    aggregation = aggregate_price_results(results, 10)

    assert aggregation.status is ResearchStatus.PARTIAL_SUCCESS
    assert aggregation.market_reference == "8"
    assert aggregation.estimated_total == Decimal(80)
    assert aggregation.reason_code is ResearchReasonCode.SOURCE_UNAVAILABLE


def test_no_matching_product_requires_four_successful_no_matches() -> None:
    no_matches = tuple(
        _result(source, SourceOutcome.NO_STRICT_MPN_MATCH) for source in PRICE_SOURCES
    )
    agg = aggregate_price_results(no_matches, 1)
    assert agg.status is ResearchStatus.MANUAL_REVIEW_REQUIRED
    assert agg.reason_code is ResearchReasonCode.NO_MATCHING_PRODUCT
    mixed = list(no_matches)
    mixed[-1] = _result(ResearchSource.BOM_AI, SourceOutcome.NO_VALID_PRICE)
    assert (
        aggregate_price_results(tuple(mixed), 1).status
        is ResearchStatus.RETRYABLE_FAILURE
    )


class FakeIcNet:
    def search(
        self, target_mpn: str, input_brand: str | None, customer_quantity: int
    ) -> IcNetResult:
        evidence = SourceEvidence(
            ResearchSource.IC_NET, target_mpn, target_mpn, SourceOutcome.SUCCESS, NOW
        )
        return IcNetResult(
            SourceResult(ResearchSource.IC_NET, SourceOutcome.SUCCESS, evidence),
            input_brand or "Acme",
            "货多",
        )


class FakePrice:
    def __init__(self, result: SourceResult) -> None:
        self.result = result

    def search(self, target_mpn: str, customer_quantity: int) -> SourceResult:
        return self.result


def test_service_writes_complete_idempotent_business_row(tmp_path: Path) -> None:
    path = tmp_path / "调研价格.xlsx"
    sources = [
        _result(ResearchSource.FINDCHIPS, SourceOutcome.SUCCESS, "8"),
        _result(ResearchSource.HQEW, SourceOutcome.SUCCESS, "11"),
        _result(ResearchSource.LCSC, SourceOutcome.NO_VALID_PRICE),
        _result(ResearchSource.BOM_AI, SourceOutcome.NO_VALID_PRICE),
    ]
    service = ResearchService(
        icnet=FakeIcNet(),
        findchips=FakePrice(sources[0]),
        hqew=FakePrice(sources[1]),
        lcsc=FakePrice(sources[2]),
        bom_ai=FakePrice(sources[3]),
        output=ResearchExcelOutput(path),
    )
    value = ResearchInput("inq_1", "ABC", None, 10, "A")
    assert service.execute(value).status is ResearchStatus.SUCCESS
    assert service.execute(value).status is ResearchStatus.SUCCESS
    ws = load_workbook(path).active
    headers = [ws.cell(1, i).value for i in range(1, ws.max_column + 1)]
    assert headers[: len(VISIBLE_HEADERS)] == list(VISIBLE_HEADERS)
    assert headers[-1] == INQUIRY_ID_HEADER
    assert ws.column_dimensions[ws.cell(1, ws.max_column).column_letter].hidden is True
    assert ws.max_row == 2
    row = {headers[i - 1]: ws.cell(2, i).value for i in range(1, ws.max_column + 1)}
    assert row["型号"] == "ABC" and row["品牌"] == "Acme" and row["数量"] == 10
    assert row["货量标识"] == "货多"
    assert row["预计订单总价"] == "80"
    assert row["市场最低参考价"] == "8\n11-华强电子网"


def test_single_price_is_valid_without_second_line() -> None:
    results = (
        _result(ResearchSource.FINDCHIPS, SourceOutcome.SUCCESS, "8"),
        _result(ResearchSource.HQEW, SourceOutcome.NO_VALID_PRICE),
        _result(ResearchSource.LCSC, SourceOutcome.NO_VALID_PRICE),
        _result(ResearchSource.BOM_AI, SourceOutcome.NO_VALID_PRICE),
    )

    aggregation = aggregate_price_results(results, 3)

    assert aggregation.status is ResearchStatus.SUCCESS
    assert aggregation.market_reference == "8"
    assert aggregation.estimated_total == Decimal(24)


def test_service_excel_failure_is_retryable_and_preserves_evidence() -> None:
    class FailingOutput:
        def upsert(self, inquiry_id: str, **values: object) -> None:
            raise ExcelWriteError("synthetic failure")

    sources = [
        _result(ResearchSource.FINDCHIPS, SourceOutcome.SUCCESS, "8"),
        _result(ResearchSource.HQEW, SourceOutcome.NO_VALID_PRICE),
        _result(ResearchSource.LCSC, SourceOutcome.NO_VALID_PRICE),
        _result(ResearchSource.BOM_AI, SourceOutcome.NO_VALID_PRICE),
    ]
    service = ResearchService(
        icnet=FakeIcNet(),
        findchips=FakePrice(sources[0]),
        hqew=FakePrice(sources[1]),
        lcsc=FakePrice(sources[2]),
        bom_ai=FakePrice(sources[3]),
        output=FailingOutput(),  # type: ignore[arg-type]
    )

    execution = service.execute_detailed(
        ResearchInput("inq_excel_failure", "ABC", None, 10, "A")
    )

    assert execution.result.status is ResearchStatus.RETRYABLE_FAILURE
    assert execution.price_sources == tuple(sources)
    assert execution.aggregation.lowest is not None


def test_partial_then_success_clears_stale_remarks_without_duplicate(
    tmp_path: Path,
) -> None:
    path = tmp_path / "调研价格.xlsx"
    partial_sources = [
        _result(ResearchSource.FINDCHIPS, SourceOutcome.SUCCESS, "8"),
        _result(ResearchSource.HQEW, SourceOutcome.SOURCE_UNAVAILABLE),
        _result(ResearchSource.LCSC, SourceOutcome.NO_VALID_PRICE),
        _result(ResearchSource.BOM_AI, SourceOutcome.NO_VALID_PRICE),
    ]
    success_sources = [
        partial_sources[0],
        _result(ResearchSource.HQEW, SourceOutcome.NO_VALID_PRICE),
        partial_sources[2],
        partial_sources[3],
    ]
    value = ResearchInput("inq_refresh", "ABC", None, 10, "A")

    first = ResearchService(
        icnet=FakeIcNet(),
        findchips=FakePrice(partial_sources[0]),
        hqew=FakePrice(partial_sources[1]),
        lcsc=FakePrice(partial_sources[2]),
        bom_ai=FakePrice(partial_sources[3]),
        output=ResearchExcelOutput(path),
    ).execute(value)
    second = ResearchService(
        icnet=FakeIcNet(),
        findchips=FakePrice(success_sources[0]),
        hqew=FakePrice(success_sources[1]),
        lcsc=FakePrice(success_sources[2]),
        bom_ai=FakePrice(success_sources[3]),
        output=ResearchExcelOutput(path),
    ).execute(value)

    worksheet = load_workbook(path).active
    headers = {
        worksheet.cell(1, column).value: column
        for column in range(1, worksheet.max_column + 1)
    }
    assert first.status is ResearchStatus.PARTIAL_SUCCESS
    assert second.status is ResearchStatus.SUCCESS
    assert worksheet.max_row == 2
    assert worksheet.cell(2, headers["备注"]).value is None


def test_new_no_price_snapshot_clears_old_market_reference(tmp_path: Path) -> None:
    path = tmp_path / "调研价格.xlsx"
    value = ResearchInput("inq_manual", "ABC", None, 10, "A")
    priced = [
        _result(ResearchSource.FINDCHIPS, SourceOutcome.SUCCESS, "8"),
        _result(ResearchSource.HQEW, SourceOutcome.NO_VALID_PRICE),
        _result(ResearchSource.LCSC, SourceOutcome.NO_VALID_PRICE),
        _result(ResearchSource.BOM_AI, SourceOutcome.NO_VALID_PRICE),
    ]
    no_matches = [
        _result(source, SourceOutcome.NO_STRICT_MPN_MATCH) for source in PRICE_SOURCES
    ]

    ResearchService(
        icnet=FakeIcNet(),
        findchips=FakePrice(priced[0]),
        hqew=FakePrice(priced[1]),
        lcsc=FakePrice(priced[2]),
        bom_ai=FakePrice(priced[3]),
        output=ResearchExcelOutput(path),
    ).execute(value)
    result = ResearchService(
        icnet=FakeIcNet(),
        findchips=FakePrice(no_matches[0]),
        hqew=FakePrice(no_matches[1]),
        lcsc=FakePrice(no_matches[2]),
        bom_ai=FakePrice(no_matches[3]),
        output=ResearchExcelOutput(path),
    ).execute(value)

    worksheet = load_workbook(path).active
    headers = {
        worksheet.cell(1, column).value: column
        for column in range(1, worksheet.max_column + 1)
    }
    assert result.status is ResearchStatus.MANUAL_REVIEW_REQUIRED
    assert worksheet.max_row == 2
    assert worksheet.cell(2, headers["预计订单总价"]).value is None
    assert worksheet.cell(2, headers["市场最低参考价"]).value is None


def test_corrupted_workbook_load_becomes_retryable_failure(tmp_path: Path) -> None:
    path = tmp_path / "调研价格.xlsx"
    path.write_bytes(b"not an xlsx archive")
    source = _result(ResearchSource.FINDCHIPS, SourceOutcome.SUCCESS, "8")
    service = ResearchService(
        icnet=FakeIcNet(),
        findchips=FakePrice(source),
        hqew=FakePrice(_result(ResearchSource.HQEW, SourceOutcome.NO_VALID_PRICE)),
        lcsc=FakePrice(_result(ResearchSource.LCSC, SourceOutcome.NO_VALID_PRICE)),
        bom_ai=FakePrice(_result(ResearchSource.BOM_AI, SourceOutcome.NO_VALID_PRICE)),
        output=ResearchExcelOutput(path),
    )

    result = service.execute(ResearchInput("inq_corrupt", "ABC", None, 10, "A"))

    assert result.status is ResearchStatus.RETRYABLE_FAILURE


def test_synthetic_save_failure_becomes_retryable_failure(
    tmp_path: Path, monkeypatch
) -> None:
    def fail_save(*args: object, **kwargs: object) -> None:
        raise RuntimeError("synthetic openpyxl save failure")

    monkeypatch.setattr("openpyxl.workbook.workbook.Workbook.save", fail_save)
    source = _result(ResearchSource.FINDCHIPS, SourceOutcome.SUCCESS, "8")
    service = ResearchService(
        icnet=FakeIcNet(),
        findchips=FakePrice(source),
        hqew=FakePrice(_result(ResearchSource.HQEW, SourceOutcome.NO_VALID_PRICE)),
        lcsc=FakePrice(_result(ResearchSource.LCSC, SourceOutcome.NO_VALID_PRICE)),
        bom_ai=FakePrice(_result(ResearchSource.BOM_AI, SourceOutcome.NO_VALID_PRICE)),
        output=ResearchExcelOutput(tmp_path / "调研价格.xlsx"),
    )

    result = service.execute(ResearchInput("inq_save", "ABC", None, 10, "A"))

    assert result.status is ResearchStatus.RETRYABLE_FAILURE
