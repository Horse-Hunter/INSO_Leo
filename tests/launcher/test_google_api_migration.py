"""RFQ-016 phase 1: the Service-Account API transport must not recreate false stops.

The Owner's rule is unchanged: a bounded, read-only Google API failure is a
retryable read (keep the cadence, no technical mail, no global stop), a rejected
credential/permission on a read is an accurate Google Sheets condition, and
anything else still fails closed through the existing escalation.
"""

import json
from datetime import timedelta
from types import SimpleNamespace

import httplib2
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from googleapiclient.errors import HttpError

from src.launcher.backend import (
    ProductionBackend,
    ProductionConfigurationError,
    _website_failure,
)
from src.sheets.google_api_service import GoogleApiSheetsService
from src.sheets.google_oauth import GoogleSheetsAuthorizationError
from src.sheets.google_reader import GoogleSheetsReadError, GoogleSheetsRowReader
from src.sheets.pending import WorksheetIdentity
from src.workflow.v12_faults import V12Fault
from src.workflow.v13_integration import is_isolated_source_read_error
from tests.launcher.test_runtime_safety_notice import harness

SHEET = "1AbCdEfGhIjKlMnOpQrStUvWxYz0123456789abcd"
INTERVAL = timedelta(seconds=900)


def http_error(status: int) -> HttpError:
    body = f'{{"error": {{"code": {status}, "message": "synthetic", "status": "SYNTHETIC"}}}}'.encode()
    return HttpError(httplib2.Response({"status": status, "reason": "synthetic"}), body)


class _Exec:
    def __init__(self, error):
        self.error = error

    def execute(self):
        raise self.error


class _FailValues:
    def __init__(self, error):
        self.error = error
        self.attempts = 0

    def get(self, **kwargs):
        self.attempts += 1
        return _Exec(self.error)


class _FailingApi:
    def __init__(self, error):
        self.values_resource = _FailValues(error)

    def spreadsheets(self):
        return self

    def values(self):
        return self.values_resource

    def get(self, **kwargs):
        return _Exec(self.error)


def failing_read(error):
    api = _FailingApi(error)
    reader = GoogleSheetsRowReader(api, retry_wait=lambda _seconds: False)
    with pytest.raises(GoogleSheetsReadError) as caught:
        reader.read_rows(WorksheetIdentity(SHEET, "2026"))
    return caught.value, api


@pytest.mark.parametrize("status", [429, 500, 503])
def test_rate_limit_and_server_reads_are_deferred_not_stopped(tmp_path, monkeypatch, status):
    backend, _, smtp = harness(tmp_path, monkeypatch)
    error, api = failing_read(http_error(status))

    assert api.values_resource.attempts == 5  # The existing bounded budget was reused.
    assert is_isolated_source_read_error(error) is True
    assert _website_failure(error) == "Google Sheets"

    assert backend._defer_website_poll(error, INTERVAL) is True
    assert backend._stop.is_set() is False
    assert "Google Sheets" in backend._site_outages
    assert smtp.send_attempts == 0


def test_permission_read_is_an_accurate_google_condition_not_a_global_stop(tmp_path, monkeypatch):
    backend, _, smtp = harness(tmp_path, monkeypatch)
    error, _ = failing_read(http_error(403))

    assert is_isolated_source_read_error(error) is False  # Never a harmless retry.
    assert _website_failure(error) == "Google Sheets"  # Nor a Google-wide outage.

    assert backend._defer_website_poll(error, INTERVAL) is True
    assert backend._stop.is_set() is False
    assert smtp.send_attempts == 0  # No false technical mail from a bare deferral.


def test_authorization_object_failure_is_recognised_for_reads(tmp_path, monkeypatch):
    backend, _, _ = harness(tmp_path, monkeypatch)
    error, _ = failing_read(GoogleSheetsAuthorizationError("Unable to authorize"))
    assert _website_failure(error) == "Google Sheets"
    assert backend._defer_website_poll(error, INTERVAL) is True
    assert backend._stop.is_set() is False


def test_unclassified_api_failure_still_fails_closed(tmp_path, monkeypatch):
    backend, _, _ = harness(tmp_path, monkeypatch)
    error, _ = failing_read(http_error(400))  # A contract/config defect, not a transient.
    assert is_isolated_source_read_error(error) is False
    assert _website_failure(error) is None
    assert backend._defer_website_poll(error, INTERVAL) is False


# --- the single default-off switch -------------------------------------------
def _synthetic_key(directory):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(serialization.Encoding.PEM,
                            serialization.PrivateFormat.PKCS8,
                            serialization.NoEncryption()).decode()
    path = directory / "sa.json"
    path.write_text(json.dumps({
        "type": "service_account", "project_id": "synthetic", "client_email": "sa@example.com",
        'private_key': pem, "token_uri": "https://oauth2.googleapis.com/token",
    }), encoding="utf-8")
    return path


def _backend(root, recovered=()):
    """A real bound switch/factory over the minimum state those methods read."""
    stub = SimpleNamespace(root=root, _site_recovered=lambda site: recovered.append(site))
    stub._google_api_service = ProductionBackend._google_api_service.__get__(stub)
    stub._sheet_service_for = ProductionBackend._sheet_service_for.__get__(stub)
    return stub


def test_the_api_transport_is_off_by_default(tmp_path):
    web = object()
    for cfg in ({}, {"google_api": {}}, {"google_api": {"enabled": False}},
                {"google_api": "not-a-section"}):
        assert _backend(tmp_path)._sheet_service_for(cfg, web) is web


def test_enabling_without_a_key_path_fails_closed_before_business(tmp_path):
    with pytest.raises(ProductionConfigurationError):
        _backend(tmp_path)._sheet_service_for({"google_api": {"enabled": True}}, object())


def test_enabling_with_a_missing_key_file_is_a_shared_authorization_stop(tmp_path):
    with pytest.raises(V12Fault) as caught:
        _backend(tmp_path)._sheet_service_for(
            {"google_api": {"enabled": True, "service_account_file": "absent.json"}}, object())
    assert caught.value.reason == "SHEETS_AUTH_UNAVAILABLE"


def test_enabled_switch_builds_the_same_sa_transport_without_oauth(tmp_path):
    path = _synthetic_key(tmp_path)
    recovered = []
    service = _backend(tmp_path, recovered)._sheet_service_for(
        {"google_api": {"enabled": True, "service_account_file": str(path)}}, object())

    assert isinstance(service, GoogleApiSheetsService)
    assert service.external_write is True
    # The CDP lifecycle ports exist so the existing call sites keep working.
    assert service.operations_idle() is True
    assert recovered == []
