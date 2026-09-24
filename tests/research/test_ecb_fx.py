from datetime import UTC, datetime
from decimal import Decimal

import pytest

from src.research.ecb_fx import EcbDailyUsdRmbProvider, EcbFxError

NOW = datetime(2026, 9, 22, 10, 30, tzinfo=UTC)
HEADER = "CURRENCY,TIME_PERIOD,OBS_VALUE\n"


def test_ecb_provider_uses_eur_bridge_with_decimal() -> None:
    provider = EcbDailyUsdRmbProvider(
        lambda: HEADER + "USD,2026-09-21,1.2\nCNY,2026-09-21,8.4\n",
        clock=lambda: NOW,
    )

    quote = provider.get_quote()

    assert quote.rate == Decimal(7)
    assert quote.captured_at == NOW
    assert quote.source_label == "ECB daily reference rates 2026-09-21 (EUR bridge)"


def test_hkd_and_usd_cross_rates_must_share_the_same_ecb_date() -> None:
    usd = HEADER + "USD,2026-09-21,1.2\nCNY,2026-09-21,8.4\n"
    hkd = HEADER + "HKD,2026-09-21,9.2\nCNY,2026-09-21,8.4\n"
    provider = EcbDailyUsdRmbProvider(lambda: usd, fetch_hkd_csv=lambda: hkd)
    provider.get_quote()
    assert provider.get_hkd_rmb_rate() == Decimal("8.4") / Decimal("9.2")

    hkd = HEADER + "HKD,2026-09-20,9.2\nCNY,2026-09-20,8.4\n"
    provider = EcbDailyUsdRmbProvider(lambda: usd, fetch_hkd_csv=lambda: hkd)
    provider.get_quote()
    with pytest.raises(EcbFxError, match="ECB_OBSERVATION_DATE_MISMATCH"):
        provider.get_hkd_rmb_rate()


@pytest.mark.parametrize(
    ("body", "code"),
    [
        (HEADER + "USD,2026-09-21,1.2\n", "ECB_MISSING_OBSERVATION"),
        (
            HEADER + "USD,2026-09-21,1.2\nCNY,2026-09-20,8.4\n",
            "ECB_OBSERVATION_DATE_MISMATCH",
        ),
        (
            HEADER + "USD,2026-09-21,0\nCNY,2026-09-21,8.4\n",
            "ECB_INVALID_OBSERVATION",
        ),
        (
            HEADER + "USD,2026-09-21,NaN\nCNY,2026-09-21,8.4\n",
            "ECB_INVALID_OBSERVATION",
        ),
    ],
)
def test_ecb_provider_fails_closed(body: str, code: str) -> None:
    with pytest.raises(EcbFxError, match=code):
        EcbDailyUsdRmbProvider(lambda: body).get_quote()
