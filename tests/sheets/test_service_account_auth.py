"""Service-account authorization facts, verified OFFLINE with synthetic keys.

Scope (RFQ-016 phase 2, Owner/CEO constrained): no real Google credential, no
network call, no production spreadsheet, no CDP. Every key here is generated at
runtime and discarded with the test. Passing this module proves the *mechanism*;
it deliberately does NOT prove a live Google grant — that stays
`BLOCKED_OWNER_SETUP` until the Owner supplies an approved test sheet and an
independently created service account.

The point of the exercise is the difference between a user refresh token (the
historical 7-day problem) and a service account, which signs a JWT with a local
private key and exchanges it for a short-lived access token. That exchange has no
refresh token and no consent screen, so it cannot expire on the Testing-app
schedule; what can still fail is the key itself (deleted, disabled, revoked,
rotated) or the target document's sharing.
"""
import base64
import json
import os
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httplib2
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from google.auth.exceptions import RefreshError
from google.oauth2 import service_account
from googleapiclient.errors import HttpError

from src.launcher.backend import _website_failure
from src.sheets.google_oauth import GoogleSheetsAuthorizationError
from src.sheets.google_reader import (
    GoogleSheetsReadError,
    GoogleSheetsReadUnavailable,
    _temporary_read_failure,
)
from src.sheets.quotation_input import QuotationInputUnavailable, _shared_error
from src.workflow.v13_integration import is_isolated_source_read_error

SHEETS_SCOPE = "https://www.googleapis.com/auth/spreadsheets"
TOKEN_URI = "https://oauth2.googleapis.com/token"
CLIENT_EMAIL = "inso-rfq016-probe@example-project.iam.gserviceaccount.com"


def _private_key_pem() -> bytes:
    """A throwaway 2048-bit key; never a real Google credential."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )


def _info(key_pem: bytes) -> dict:
    return {
        "type": "service_account",
        "project_id": "example-project",
        "private_key_id": "0000000000000000000000000000000000000000",
        "private_key": key_pem.decode("utf-8"),
        "client_email": CLIENT_EMAIL,
        "client_id": "100000000000000000000",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": TOKEN_URI,
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{CLIENT_EMAIL}",
    }


class _Response:
    """Minimal `google.auth.transport.Response` shape for a fake endpoint."""

    def __init__(self, status, payload):
        self.status = status
        self.data = json.dumps(payload).encode("utf-8") if isinstance(payload, dict) else payload
        self.headers = {"content-type": "application/json"}


class _TokenEndpoint:
    """Records the token exchange instead of contacting Google."""

    def __init__(self, *, status=200, payload=None):
        self.calls = []
        self.status, self.payload = status, payload

    def __call__(self, url=None, method=None, body=None, headers=None, **kwargs):
        self.calls.append({"url": url, "method": method, "body": body, "headers": headers})
        if self.status != 200:
            return _Response(self.status, self.payload or {"error": "invalid_grant"})
        index = len(self.calls)
        return _Response(200, {
            "access_token": f"ya29.synthetic-{index}",
            "expires_in": 3599,
            "token_type": "Bearer",
        })

    def last_assertion(self):
        from urllib.parse import parse_qsl
        body = self.calls[-1]["body"]
        if isinstance(body, bytes):
            body = body.decode("utf-8")
        return dict(parse_qsl(body))["assertion"]


def _claims(assertion: str) -> dict:
    payload = assertion.split(".")[1]
    payload += "=" * (-len(payload) % 4)
    return json.loads(base64.urlsafe_b64decode(payload))


def _credentials(key_pem=None, *, scopes=(SHEETS_SCOPE,)):
    return service_account.Credentials.from_service_account_info(
        _info(key_pem or _private_key_pem()), scopes=list(scopes))


def test_service_account_credentials_carry_no_user_grant_and_no_consent_step():
    credentials = _credentials()
    assert credentials.service_account_email == CLIENT_EMAIL
    assert credentials.token is None and credentials.expiry is None
    assert credentials.valid is False  # No access token yet; nothing to expire.
    assert credentials.scopes == [SHEETS_SCOPE]
    # The 7-day Testing rule applies to OAuth user refresh tokens. A service
    # account has no refresh token at all, so that mechanism cannot apply.
    assert not hasattr(credentials, "refresh_token") or not credentials.refresh_token


def test_access_token_comes_from_a_signed_jwt_not_a_refresh_token():
    endpoint = _TokenEndpoint()
    credentials = _credentials()
    credentials.refresh(endpoint)

    assert endpoint.calls[0]["url"] == TOKEN_URI
    assert endpoint.calls[0]["method"] == "POST"
    body = endpoint.calls[0]["body"].decode("utf-8") if isinstance(endpoint.calls[0]["body"], bytes) \
        else endpoint.calls[0]["body"]
    assert "refresh_token" not in body
    assert "grant_type=urn%3Aietf%3Aparams%3Aoauth%3Agrant-type%3Ajwt-bearer" in body

    claims = _claims(endpoint.last_assertion())
    assert claims["iss"] == CLIENT_EMAIL
    assert claims["aud"] == TOKEN_URI
    assert claims["scope"] == SHEETS_SCOPE
    assert claims["exp"] - claims["iat"] == 3600

    assert credentials.token == "ya29.synthetic-1"
    assert credentials.valid is True
    assert timedelta(minutes=50) < credentials.expiry - datetime.now(UTC).replace(tzinfo=None) \
        <= timedelta(minutes=61)


def test_expired_access_token_is_re_exchanged_automatically():
    endpoint = _TokenEndpoint()
    credentials = _credentials()
    credentials.refresh(endpoint)
    first = credentials.token

    credentials.expiry = datetime.now(UTC).replace(tzinfo=None) - timedelta(seconds=5)
    assert credentials.valid is False and credentials.expired is True

    credentials.refresh(endpoint)
    assert credentials.token != first
    assert len(endpoint.calls) == 2
    # Both exchanges are JWT-bearer assertions; no long-lived grant is involved.
    assert "refresh_token" not in str(endpoint.calls[-1]["body"])


def test_new_process_authenticates_from_the_key_file_without_any_stored_token(tmp_path):
    """A restart needs the key file and nothing else: no token cache, no prompt."""
    key_file = tmp_path / "synthetic-sa-key.json"
    key_file.write_text(json.dumps(_info(_private_key_pem())), encoding="utf-8")

    script = r"""
import json, sys
from datetime import datetime, timezone
from google.oauth2 import service_account

key_file = sys.argv[1]
creds = service_account.Credentials.from_service_account_file(
    key_file, scopes=["https://www.googleapis.com/auth/spreadsheets"])

class Response:
    status = 200
    headers = {"content-type": "application/json"}
    def __init__(self):
        self.data = json.dumps({"access_token": "ya29.child", "expires_in": 3599,
                                "token_type": "Bearer"}).encode()

calls = []
def transport(**kwargs):
    calls.append(kwargs)
    return Response()

creds.refresh(transport)
print(json.dumps({
    "token": bool(creds.token),
    "valid": creds.valid,
    "has_refresh_token": bool(getattr(creds, "refresh_token", None)),
    "grant_type": "grant_type=urn%3Aietf%3Aparams%3Aoauth%3Agrant-type%3Ajwt-bearer"
                  in calls[0]["body"].decode(),
}))
"""
    completed = subprocess.run(
        [sys.executable, "-c", script, str(key_file)],
        capture_output=True, text=True, timeout=120, check=False,
    )
    assert completed.returncode == 0, completed.stderr[-800:]
    result = json.loads(completed.stdout.strip().splitlines()[-1])
    assert result == {"token": True, "valid": True, "has_refresh_token": False, "grant_type": True}
    # The child process wrote nothing: authorization is stateless apart from the key.
    assert sorted(p.name for p in tmp_path.iterdir()) == [key_file.name]


@pytest.mark.skipif(os.name != "nt", reason="Windows CurrentUser DPAPI is the production boundary")
def test_dpapi_protection_hides_the_private_key_without_losing_it():
    from src.core.protected_local_store import protect_bytes, unprotect_bytes

    raw = json.dumps(_info(_private_key_pem())).encode("utf-8")
    protected = protect_bytes(raw)

    assert protected != raw
    assert b"PRIVATE KEY" not in protected
    assert b"private_key" not in protected
    assert unprotect_bytes(protected) == raw  # Same-user round trip only.


def _http_error(status: int) -> HttpError:
    body = json.dumps({"error": {"code": status, "message": "synthetic", "status": "SYNTHETIC"}}).encode()
    return HttpError(httplib2.Response({"status": status, "reason": "synthetic"}), body)


def _read_failure(cause: BaseException) -> GoogleSheetsReadError:
    """The exact shape GoogleSheetsRowReader._read_rows produces."""
    wrapped = GoogleSheetsReadError("Unable to read worksheet '2026'")
    wrapped.__cause__ = cause
    return wrapped


@pytest.mark.parametrize("status,retryable", [(429, True), (500, True), (503, True),
                                              (401, False), (403, False)])
def test_bounded_read_retry_accepts_only_quota_and_server_faults(status, retryable):
    """The inner 5-attempt budget must never retry a credential/permission failure."""
    assert _temporary_read_failure(_http_error(status)) is retryable


@pytest.mark.parametrize("status", [429, 500, 503])
def test_api_transport_transients_are_a_deferred_read_not_a_stop(status):
    """The API form of the batch-1 rule: bounded read, next poll, no mail.

    `HttpError` 429/5xx is now part of the canonical read vocabulary, so an
    exhausted retry defers the module instead of reaching `_runtime_error`.
    """
    # The real reader shape after `execute_google_read` exhausts its budget:
    # `_read_rows` re-raises the existing GoogleSheetsReadUnavailable unchanged.
    failure = GoogleSheetsReadUnavailable("Google read retry exhausted")
    failure.__cause__ = _http_error(status)
    assert is_isolated_source_read_error(failure) is True
    assert _website_failure(failure) == "Google Sheets"


@pytest.mark.parametrize("status", [401, 403])
def test_missing_or_insufficient_credentials_are_shared_failures_not_retries(status):
    error = _http_error(status)
    assert _shared_error(error) is True          # quotation adapter: infrastructure
    assert _temporary_read_failure(error) is False
    # Never retried, and never reported as a Google-wide outage; the read is
    # named as an accurate Google Sheets credential/permission condition so the
    # existing deferral (one notice, bounded three-hour escalation) owns it.
    assert is_isolated_source_read_error(_read_failure(error)) is False
    assert _website_failure(_read_failure(error)) == "Google Sheets"


def test_authorization_object_failure_is_labelled_and_never_claims_google_is_down():
    error = GoogleSheetsAuthorizationError("Unable to authorize read-only Google Sheets access")
    assert _shared_error(error) is True
    assert _temporary_read_failure(error) is False
    # Reads: no retry, no "Google is down" claim, and an accurate named condition.
    assert is_isolated_source_read_error(_read_failure(error)) is False
    assert _website_failure(_read_failure(error)) == "Google Sheets"
    # The metadata path is the one place that still names Google Sheets.
    assert _website_failure(QuotationInputUnavailable("QUOTE_INPUT_METADATA_UNAVAILABLE")) == "Google Sheets"
    assert _website_failure(QuotationInputUnavailable("QUOTE_INPUT_INFRASTRUCTURE_UNAVAILABLE")) is None


def test_rejected_signing_key_surfaces_as_refresh_error_without_a_consent_screen():
    """A deleted/disabled key is a token-endpoint rejection, not a user prompt."""
    endpoint = _TokenEndpoint(status=400, payload={"error": "invalid_grant",
                                                   "error_description": "Invalid JWT Signature."})
    credentials = _credentials()
    with pytest.raises(RefreshError):
        credentials.refresh(endpoint)
    assert credentials.token is None
    # Nothing in this path can open a browser or ask the Owner for consent.
    assert _shared_error(RefreshError("invalid_grant")) is True


@pytest.mark.parametrize("error", [TimeoutError("read timed out"), ConnectionError("reset")])
def test_transport_interruptions_stay_retryable(error):
    assert _temporary_read_failure(error) is True


def test_no_private_key_material_is_committed_anywhere():
    """Hygiene guard for the rule that keys never enter Git, logs or reports."""
    markers = ("BEGIN " + "PRIVATE KEY", '"private_key"', "private_key_id")
    roots = [Path("src"), Path("docs"), Path("control-room"), Path("tests")]
    offenders = []
    for root in roots:
        for path in root.rglob("*"):
            if path.suffix not in {".py", ".md", ".json", ".txt", ".csv"} or not path.is_file():
                continue
            if path.name == Path(__file__).name:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            if any(marker in text for marker in markers):
                offenders.append(str(path))
    assert offenders == []
