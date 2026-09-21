"""Minimal non-persistent OAuth path for read-only Google Sheets access."""

from pathlib import Path
from typing import Any

READ_ONLY_SCOPE = "https://www.googleapis.com/auth/spreadsheets.readonly"


class GoogleSheetsDependencyError(RuntimeError):
    """Required official Google client libraries are unavailable."""


class GoogleSheetsAuthorizationError(RuntimeError):
    """OAuth authorization or Google Sheets service construction failed."""


def build_read_only_google_sheets_service(
    client_secret_file: str | Path,
) -> Any:
    """Authorize interactively without persisting tokens and build Sheets v4."""

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError as exc:
        raise GoogleSheetsDependencyError(
            "Install google-api-python-client and google-auth-oauthlib"
        ) from exc

    try:
        flow = InstalledAppFlow.from_client_secrets_file(
            str(client_secret_file),
            scopes=[READ_ONLY_SCOPE],
        )
        credentials = flow.run_local_server(port=0)
        return build(
            "sheets",
            "v4",
            credentials=credentials,
            cache_discovery=False,
        )
    except Exception as exc:
        raise GoogleSheetsAuthorizationError(
            "Unable to authorize read-only Google Sheets access"
        ) from exc
