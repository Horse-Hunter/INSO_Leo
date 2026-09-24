"""Fail-closed local configuration and one-shot Google Sheets read runtime."""

from __future__ import annotations

import json
import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .google_oauth import build_read_only_google_sheets_service
from .google_reader import GoogleSheetsRowReader, GoogleSheetsService
from .pending import WorksheetIdentity, WorksheetRow

READ_CONFIG_ENV = "INSO_SHEETS_READ_CONFIG_FILE"
_CONFIG_KEYS = frozenset(
    {"oauth_client_secret_file", "spreadsheet_id", "worksheets"}
)


class GoogleSheetsRuntimeConfigError(RuntimeError):
    """Local Google Sheets read runtime configuration is missing or invalid."""


@dataclass(frozen=True, slots=True)
class GoogleSheetsReadRuntimeConfig:
    """Validated local inputs needed to construct the read-only adapter."""

    oauth_client_secret_file: Path
    worksheets: tuple[WorksheetIdentity, ...]


@dataclass(frozen=True, slots=True)
class ConfiguredWorksheetRead:
    """Rows returned for one configured worksheet identity."""

    worksheet: WorksheetIdentity
    rows: tuple[WorksheetRow, ...]


@dataclass(frozen=True, slots=True)
class GoogleSheetsReadRuntime:
    """One-shot reader plus the complete ordered set of configured worksheets."""

    reader: GoogleSheetsRowReader
    worksheets: tuple[WorksheetIdentity, ...]

    def read_all(self) -> tuple[ConfiguredWorksheetRead, ...]:
        """Read every configured worksheet exactly once, in configured order."""

        return tuple(
            ConfiguredWorksheetRead(
                worksheet=worksheet,
                rows=self.reader.read_rows(worksheet),
            )
            for worksheet in self.worksheets
        )


def load_google_sheets_read_config(
    config_file: str | Path | None = None,
    *,
    environ: Mapping[str, str] | None = None,
) -> GoogleSheetsReadRuntimeConfig:
    """Load required values from one explicitly selected local JSON file."""

    environment = os.environ if environ is None else environ
    selected_file = config_file
    if selected_file is None:
        selected_file = environment.get(READ_CONFIG_ENV)
    if not isinstance(selected_file, (str, Path)) or not str(selected_file).strip():
        raise GoogleSheetsRuntimeConfigError(
            f"Set {READ_CONFIG_ENV} to an explicit local configuration file"
        )

    path = Path(selected_file).expanduser().resolve()
    try:
        raw_config = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise GoogleSheetsRuntimeConfigError(
            "Unable to read the Google Sheets runtime configuration"
        ) from exc

    if not isinstance(raw_config, dict) or set(raw_config) != _CONFIG_KEYS:
        raise GoogleSheetsRuntimeConfigError(
            "Google Sheets runtime configuration has invalid fields"
        )

    secret_value = _required_text(raw_config, "oauth_client_secret_file")
    spreadsheet_id = _required_text(raw_config, "spreadsheet_id")
    worksheet_titles = _worksheet_titles(raw_config.get("worksheets"))

    secret_file = Path(secret_value).expanduser()
    if not secret_file.is_absolute():
        secret_file = path.parent / secret_file
    secret_file = secret_file.resolve()
    if not secret_file.is_file():
        raise GoogleSheetsRuntimeConfigError(
            "Configured OAuth client-secret file is unavailable"
        )

    return GoogleSheetsReadRuntimeConfig(
        oauth_client_secret_file=secret_file,
        worksheets=tuple(
            WorksheetIdentity(
                spreadsheet=spreadsheet_id,
                worksheet=worksheet_title,
            )
            for worksheet_title in worksheet_titles
        ),
    )


def build_google_sheets_read_runtime(
    config: GoogleSheetsReadRuntimeConfig,
    *,
    service_builder: Callable[[str | Path], GoogleSheetsService] = (
        build_read_only_google_sheets_service
    ),
) -> GoogleSheetsReadRuntime:
    """Construct the existing row reader through read-only OAuth composition."""

    service = service_builder(config.oauth_client_secret_file)
    return GoogleSheetsReadRuntime(
        reader=GoogleSheetsRowReader(service),
        worksheets=config.worksheets,
    )


def _required_text(config: Mapping[str, Any], key: str) -> str:
    value = config.get(key)
    if not isinstance(value, str) or not value.strip():
        raise GoogleSheetsRuntimeConfigError(
            "Google Sheets runtime configuration has a missing or blank value"
        )
    return value.strip()


def _worksheet_titles(value: object) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise GoogleSheetsRuntimeConfigError(
            "Google Sheets runtime configuration requires target worksheets"
        )

    titles: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise GoogleSheetsRuntimeConfigError(
                "Google Sheets runtime configuration has an invalid worksheet"
            )
        title = item.strip()
        if title in titles:
            raise GoogleSheetsRuntimeConfigError(
                "Google Sheets runtime configuration has duplicate worksheets"
            )
        titles.append(title)
    return tuple(titles)
