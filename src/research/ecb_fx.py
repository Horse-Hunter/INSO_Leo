"""ECB-backed daily USD/RMB quote using the official EUR reference-rate bridge."""

from __future__ import annotations

import csv
import io
import ssl
from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .fx import UsdRmbQuote

ECB_DAILY_USD_CNY_URL = (
    "https://data-api.ecb.europa.eu/service/data/EXR/"
    "D.USD+CNY.EUR.SP00.A?lastNObservations=1&format=csvdata"
)
ECB_DAILY_HKD_CNY_URL = (
    "https://data-api.ecb.europa.eu/service/data/EXR/"
    "D.HKD+CNY.EUR.SP00.A?lastNObservations=1&format=csvdata"
)


class EcbFxError(RuntimeError):
    """Raised when an authoritative, internally consistent quote is unavailable."""


class EcbDailyUsdRmbProvider:
    """Fetch ECB daily USD/EUR and CNY/EUR rates and derive CNY per USD."""

    def __init__(
        self,
        fetch_csv: Callable[[], str] | None = None,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._fetch_csv = fetch_csv or self._fetch_official_csv
        self._clock = clock or (lambda: datetime.now(UTC))

    def get_quote(self) -> UsdRmbQuote:
        try:
            body = self._fetch_csv()
        except (OSError, RuntimeError, UnicodeError) as exc:
            raise EcbFxError("ECB_FETCH_FAILED") from exc
        rate, date = self._cross_rate(body, "USD")
        return UsdRmbQuote(
            rate=rate,
            captured_at=self._clock(),
            source_label=f"ECB daily reference rates {date} (EUR bridge)",
        )

    def get_hkd_rmb_rate(self) -> Decimal:
        """Derive RMB per HKD from same-day official ECB EUR rates."""

        rate, _date = self._cross_rate(
            self._fetch_official_csv(ECB_DAILY_HKD_CNY_URL), "HKD"
        )
        return rate

    @staticmethod
    def _cross_rate(body: str, base_currency: str) -> tuple[Decimal, str]:
        try:
            rows = list(csv.DictReader(io.StringIO(body)))
        except (OSError, RuntimeError, UnicodeError) as exc:
            raise EcbFxError("ECB_FETCH_FAILED") from exc
        observations: dict[str, tuple[str, Decimal]] = {}
        for row in rows:
            currency = (row.get("CURRENCY") or "").strip().upper()
            if currency not in {base_currency, "CNY"}:
                continue
            period = (row.get("TIME_PERIOD") or "").strip()
            raw_value = (row.get("OBS_VALUE") or "").strip()
            try:
                value = Decimal(raw_value)
            except InvalidOperation as exc:
                raise EcbFxError("ECB_INVALID_OBSERVATION") from exc
            if not period or not value.is_finite() or value <= 0:
                raise EcbFxError("ECB_INVALID_OBSERVATION")
            if currency in observations:
                raise EcbFxError("ECB_DUPLICATE_OBSERVATION")
            observations[currency] = period, value

        if set(observations) != {base_currency, "CNY"}:
            raise EcbFxError("ECB_MISSING_OBSERVATION")
        base_period, base_per_eur = observations[base_currency]
        cny_period, cny_per_eur = observations["CNY"]
        if base_period != cny_period:
            raise EcbFxError("ECB_OBSERVATION_DATE_MISMATCH")
        return cny_per_eur / base_per_eur, base_period

    @staticmethod
    def _fetch_official_csv(url: str = ECB_DAILY_USD_CNY_URL) -> str:
        request = Request(
            url,
            headers={
                "Accept": "text/csv",
                "User-Agent": "INSO-Leo-Research/1.0",
            },
        )
        try:
            with urlopen(
                request, timeout=15, context=_platform_ssl_context()
            ) as response:
                final_url = response.geturl()
                if not final_url.startswith("https://data-api.ecb.europa.eu/"):
                    raise EcbFxError("ECB_UNTRUSTED_REDIRECT")
                return response.read().decode("utf-8-sig")
        except (HTTPError, URLError, TimeoutError) as exc:
            raise EcbFxError("ECB_FETCH_FAILED") from exc


def _platform_ssl_context() -> ssl.SSLContext:
    """Use OpenSSL defaults plus Windows root and intermediate CA stores."""

    context = ssl.create_default_context()
    enumerate_certificates = getattr(ssl, "enum_certificates", None)
    if enumerate_certificates is None:
        return context
    for store_name in ("ROOT", "CA"):
        for certificate, encoding, _trust in enumerate_certificates(store_name):
            if encoding == "x509_asn":
                context.load_verify_locations(
                    cadata=ssl.DER_cert_to_PEM_cert(certificate)
                )
    return context
