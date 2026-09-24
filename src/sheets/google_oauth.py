"""Google Sheets OAuth with CurrentUser-protected refresh-token persistence."""

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from src.core.protected_local_store import (
    local_app_data_dir,
    protect_bytes,
    unprotect_bytes,
)

READ_ONLY_SCOPE = "https://www.googleapis.com/auth/spreadsheets.readonly"
READ_WRITE_SCOPE = "https://www.googleapis.com/auth/spreadsheets"


class GoogleSheetsDependencyError(RuntimeError):
    """Required official Google client libraries are unavailable."""


class GoogleSheetsAuthorizationError(RuntimeError):
    """OAuth authorization or Google Sheets service construction failed."""


def build_read_only_google_sheets_service(
    client_secret_file: str | Path,
) -> Any:
    """Use a cached read scope when possible; request consent only initially."""

    return _build_google_sheets_service(
        client_secret_file,
        scope=READ_ONLY_SCOPE,
        access_description="read-only",
    )


def build_read_write_google_sheets_service(
    client_secret_file: str | Path,
) -> Any:
    """Use a separately protected write-scope grant when possible."""

    return _build_google_sheets_service(
        client_secret_file,
        scope=READ_WRITE_SCOPE,
        access_description="read/write",
    )


def _token_path(client_secret_file: str | Path, scope: str) -> Path:
    # Bind the encrypted cache to the exact OAuth client file and scope.
    client_digest = hashlib.sha256(Path(client_secret_file).read_bytes()).digest()
    cache_key = hashlib.sha256(client_digest + scope.encode("utf-8")).hexdigest()[:24]
    return local_app_data_dir() / f"sheets-oauth-{cache_key}.bin"


def _read_credentials(path: Path, scope: str, credentials_type: Any) -> Any | None:
    if not path.exists():
        return None
    payload = json.loads(unprotect_bytes(path.read_bytes()).decode("utf-8"))
    if payload.get("scope") != scope or not isinstance(payload.get("credentials"), dict):
        raise GoogleSheetsAuthorizationError("Protected OAuth grant is invalid")
    credentials = credentials_type.from_authorized_user_info(
        payload["credentials"], scopes=[scope]
    )
    if not credentials.refresh_token:
        raise GoogleSheetsAuthorizationError("Protected OAuth grant lacks refresh access")
    return credentials


def _save_credentials(path: Path, scope: str, credentials: Any) -> None:
    if not credentials.refresh_token:
        raise GoogleSheetsAuthorizationError("Google did not grant offline refresh access")
    payload = json.dumps(
        {"scope": scope, "credentials": json.loads(credentials.to_json())},
        separators=(",", ":"),
    ).encode("utf-8")
    protected = protect_bytes(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, suffix=".tmp", delete=False) as handle:
            temporary_path = Path(handle.name)
            handle.write(protected)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def _build_google_sheets_service(
    client_secret_file: str | Path, *, scope: str, access_description: str
) -> Any:
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError as exc:
        raise GoogleSheetsDependencyError(
            "Install google-api-python-client and google-auth-oauthlib"
        ) from exc

    try:
        path = _token_path(client_secret_file, scope)
        credentials = _read_credentials(path, scope, Credentials)
        if credentials is None:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(client_secret_file), scopes=[scope]
            )
            credentials = flow.run_local_server(
                port=0,
                access_type="offline",
                prompt="consent",
                authorization_prompt_message="",
            )
            _save_credentials(path, scope, credentials)
        elif not credentials.valid:
            credentials.refresh(Request())
            _save_credentials(path, scope, credentials)
        return build("sheets", "v4", credentials=credentials, cache_discovery=False)
    except GoogleSheetsAuthorizationError:
        raise
    except Exception:  # noqa: BLE001 - sanitize OAuth and token-storage errors
        raise GoogleSheetsAuthorizationError(
            f"Unable to authorize {access_description} Google Sheets access"
        ) from None
