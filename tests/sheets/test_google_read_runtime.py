import json
from pathlib import Path
from typing import Any

import pytest

from src.sheets import WorksheetIdentity, WorksheetRow
from src.sheets.google_read_runtime import (
    READ_CONFIG_ENV,
    GoogleSheetsRuntimeConfigError,
    build_google_sheets_read_runtime,
    load_google_sheets_read_config,
)


class FakeRequest:
    def __init__(self, response: dict[str, Any]) -> None:
        self._response = response

    def execute(self) -> dict[str, Any]:
        return self._response


class FakeValuesResource:
    def __init__(self) -> None:
        self.get_calls: list[dict[str, Any]] = []

    def get(self, **kwargs: Any) -> FakeRequest:
        self.get_calls.append(kwargs)
        worksheet = kwargs["range"].split("!", maxsplit=1)[0].strip("'")
        return FakeRequest({"values": [[worksheet]]})


class FakeSpreadsheetsResource:
    def __init__(self, values_resource: FakeValuesResource) -> None:
        self._values_resource = values_resource

    def values(self) -> FakeValuesResource:
        return self._values_resource


class FakeSheetsService:
    def __init__(self) -> None:
        self.values_resource = FakeValuesResource()
        self.spreadsheets_resource = FakeSpreadsheetsResource(self.values_resource)

    def spreadsheets(self) -> FakeSpreadsheetsResource:
        return self.spreadsheets_resource


def write_config(
    tmp_path: Path,
    *,
    config: object | None = None,
) -> tuple[Path, Path]:
    secret_file = tmp_path / "oauth-client.json"
    secret_file.write_text("{}", encoding="utf-8")
    config_file = tmp_path / "sheets-read-runtime.local.json"
    selected_config = (
        {
            "oauth_client_secret_file": secret_file.name,
            "spreadsheet_id": "synthetic-spreadsheet-id",
            "worksheets": ["first", "second"],
        }
        if config is None
        else config
    )
    config_file.write_text(json.dumps(selected_config), encoding="utf-8")
    return config_file, secret_file


def test_loads_explicit_local_config_and_resolves_relative_secret_path(
    tmp_path: Path,
) -> None:
    config_file, secret_file = write_config(tmp_path)

    config = load_google_sheets_read_config(
        environ={READ_CONFIG_ENV: str(config_file)}
    )

    assert config.oauth_client_secret_file == secret_file.resolve()
    assert config.worksheets == (
        WorksheetIdentity("synthetic-spreadsheet-id", "first"),
        WorksheetIdentity("synthetic-spreadsheet-id", "second"),
    )


def test_explicit_file_argument_takes_precedence_over_environment(tmp_path: Path) -> None:
    config_file, _ = write_config(tmp_path)

    config = load_google_sheets_read_config(
        config_file,
        environ={READ_CONFIG_ENV: str(tmp_path / "not-selected.json")},
    )

    assert [item.worksheet for item in config.worksheets] == ["first", "second"]


@pytest.mark.parametrize(
    "environment",
    [{}, {READ_CONFIG_ENV: ""}, {READ_CONFIG_ENV: "   "}],
)
def test_missing_explicit_config_input_fails_closed(
    environment: dict[str, str],
) -> None:
    with pytest.raises(GoogleSheetsRuntimeConfigError):
        load_google_sheets_read_config(environ=environment)


def test_unreadable_or_malformed_config_file_fails_closed(tmp_path: Path) -> None:
    missing_file = tmp_path / "missing.local.json"
    malformed_file = tmp_path / "malformed.local.json"
    malformed_file.write_text("not-json", encoding="utf-8")

    for config_file in (missing_file, malformed_file):
        with pytest.raises(GoogleSheetsRuntimeConfigError):
            load_google_sheets_read_config(config_file, environ={})


@pytest.mark.parametrize(
    "invalid_config",
    [
        [],
        {},
        {
            "oauth_client_secret_file": "oauth-client.json",
            "spreadsheet_id": "sheet",
            "worksheets": ["first"],
            "unexpected": True,
        },
        {
            "oauth_client_secret_file": " ",
            "spreadsheet_id": "sheet",
            "worksheets": ["first"],
        },
        {
            "oauth_client_secret_file": "oauth-client.json",
            "spreadsheet_id": " ",
            "worksheets": ["first"],
        },
        {
            "oauth_client_secret_file": "oauth-client.json",
            "spreadsheet_id": "sheet",
            "worksheets": [],
        },
        {
            "oauth_client_secret_file": "oauth-client.json",
            "spreadsheet_id": "sheet",
            "worksheets": ["first", "first"],
        },
        {
            "oauth_client_secret_file": "oauth-client.json",
            "spreadsheet_id": "sheet",
            "worksheets": ["first", 2],
        },
    ],
)
def test_invalid_configuration_fails_closed(
    tmp_path: Path,
    invalid_config: object,
) -> None:
    config_file, _ = write_config(tmp_path, config=invalid_config)

    with pytest.raises(GoogleSheetsRuntimeConfigError):
        load_google_sheets_read_config(config_file, environ={})


def test_missing_oauth_client_file_fails_closed(tmp_path: Path) -> None:
    config_file, secret_file = write_config(tmp_path)
    secret_file.unlink()

    with pytest.raises(GoogleSheetsRuntimeConfigError):
        load_google_sheets_read_config(config_file, environ={})


def test_builds_existing_reader_and_reads_every_configured_worksheet_once(
    tmp_path: Path,
) -> None:
    config_file, secret_file = write_config(tmp_path)
    config = load_google_sheets_read_config(config_file, environ={})
    service = FakeSheetsService()
    builder_calls: list[Path] = []

    def service_builder(client_secret_file: str | Path) -> FakeSheetsService:
        builder_calls.append(Path(client_secret_file))
        return service

    runtime = build_google_sheets_read_runtime(
        config,
        service_builder=service_builder,
    )
    results = runtime.read_all()

    assert builder_calls == [secret_file.resolve()]
    assert runtime.worksheets == config.worksheets
    assert [result.worksheet.worksheet for result in results] == ["first", "second"]
    assert [result.rows for result in results] == [
        (WorksheetRow(row_position=1, cells={"A": "first", **dict.fromkeys("BCDEFG")}),),
        (WorksheetRow(row_position=1, cells={"A": "second", **dict.fromkeys("BCDEFG")}),),
    ]
    assert [call["range"] for call in service.values_resource.get_calls] == [
        "'first'!A1:G",
        "'second'!A1:G",
    ]
