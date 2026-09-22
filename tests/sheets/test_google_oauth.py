import sys
from types import ModuleType
from typing import Any

import pytest

from src.sheets.google_oauth import (
    READ_ONLY_SCOPE,
    READ_WRITE_SCOPE,
    build_read_only_google_sheets_service,
    build_read_write_google_sheets_service,
)


def test_read_and_write_oauth_helpers_use_separate_exact_scopes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    flow_calls: list[tuple[str, list[str]]] = []
    build_calls: list[dict[str, Any]] = []
    credentials = object()

    class FakeFlow:
        @classmethod
        def from_client_secrets_file(
            cls,
            client_secret_file: str,
            *,
            scopes: list[str],
        ) -> "FakeFlow":
            flow_calls.append((client_secret_file, scopes))
            return cls()

        def run_local_server(self, *, port: int) -> object:
            assert port == 0
            return credentials

    def fake_build(*args: str, **kwargs: Any) -> object:
        build_calls.append({"args": args, **kwargs})
        return object()

    auth_package = ModuleType("google_auth_oauthlib")
    auth_flow_module = ModuleType("google_auth_oauthlib.flow")
    auth_flow_module.__dict__["InstalledAppFlow"] = FakeFlow
    api_package = ModuleType("googleapiclient")
    api_discovery_module = ModuleType("googleapiclient.discovery")
    api_discovery_module.__dict__["build"] = fake_build
    monkeypatch.setitem(sys.modules, "google_auth_oauthlib", auth_package)
    monkeypatch.setitem(sys.modules, "google_auth_oauthlib.flow", auth_flow_module)
    monkeypatch.setitem(sys.modules, "googleapiclient", api_package)
    monkeypatch.setitem(sys.modules, "googleapiclient.discovery", api_discovery_module)

    build_read_only_google_sheets_service("client.json")
    build_read_write_google_sheets_service("client.json")

    assert READ_ONLY_SCOPE == "https://www.googleapis.com/auth/spreadsheets.readonly"
    assert READ_WRITE_SCOPE == "https://www.googleapis.com/auth/spreadsheets"
    assert flow_calls == [
        ("client.json", [READ_ONLY_SCOPE]),
        ("client.json", [READ_WRITE_SCOPE]),
    ]
    assert build_calls == [
        {
            "args": ("sheets", "v4"),
            "credentials": credentials,
            "cache_discovery": False,
        },
        {
            "args": ("sheets", "v4"),
            "credentials": credentials,
            "cache_discovery": False,
        },
    ]
