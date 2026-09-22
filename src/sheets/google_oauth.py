"""Minimal non-persistent OAuth paths for Google Sheets access."""

from pathlib import Path
from typing import Any

READ_ONLY_SCOPE = "https://www.googleapis.com/auth/spreadsheets.readonly"
READ_WRITE_SCOPE = "https://www.googleapis.com/auth/spreadsheets"


class GoogleSheetsDependencyError(RuntimeError):
    """Required official Google client libraries are unavailable."""


class GoogleSheetsAuthorizationError(RuntimeError):
    """OAuth authorization or Google Sheets service construction failed."""


def build_read_only_google_sheets_service(
    client_secret_file: str | Path,
) -> Any:
    """Authorize interactively without persisting tokens and build Sheets v4."""

    return _build_google_sheets_service(
        client_secret_file,
        scope=READ_ONLY_SCOPE,
        access_description="read-only",
    )


def build_read_write_google_sheets_service(
    client_secret_file: str | Path,
) -> Any:
    """Authorize for Sheets reads/writes without persisting tokens."""

    return _build_google_sheets_service(
        client_secret_file,
        scope=READ_WRITE_SCOPE,
        access_description="read/write",
    )


def _build_google_sheets_service(
    client_secret_file: str | Path,
    *,
    scope: str,
    access_description: str,
) -> Any:
    """Build one Sheets v4 service for the explicitly supplied OAuth scope."""

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
            scopes=[scope],
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
            f"Unable to authorize {access_description} Google Sheets access"
        ) from exc
