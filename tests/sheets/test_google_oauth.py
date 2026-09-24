import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from src.sheets import google_oauth


def test_scopes_cache_and_refresh_without_reopening_consent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    flow_calls: list[tuple[str, list[str]]] = []
    refresh_calls: list[object] = []
    build_calls: list[Any] = []

    class FakeCredentials:
        def __init__(self, *, valid: bool = True) -> None:
            self.valid = valid
            self.refresh_token = "synthetic-refresh"

        @classmethod
        def from_authorized_user_info(
            cls, data: dict[str, str], *, scopes: list[str]
        ) -> "FakeCredentials":
            assert scopes == [data["scope"]]
            return cls(valid=False)  # exercise refresh on second call

        def to_json(self) -> str:
            return json.dumps({"refresh_token": self.refresh_token,
                               "scope": build_scope[0]})

        def refresh(self, request: object) -> None:
            refresh_calls.append(request)
            self.valid = True

    build_scope = [google_oauth.READ_ONLY_SCOPE]

    class FakeFlow:
        @classmethod
        def from_client_secrets_file(
            cls, client_secret_file: str, *, scopes: list[str]
        ) -> "FakeFlow":
            flow_calls.append((client_secret_file, scopes))
            build_scope[0] = scopes[0]
            return cls()

        def run_local_server(
            self, *, port: int, access_type: str, prompt: str,
            authorization_prompt_message: str,
        ) -> FakeCredentials:
            assert (port, access_type, prompt, authorization_prompt_message) == (
                0, "offline", "consent", ""
            )
            return FakeCredentials()

    def fake_build(*args: str, **kwargs: Any) -> object:
        assert args == ("sheets", "v4")
        build_calls.append(kwargs["credentials"])
        return object()

    modules = {
        "google": ModuleType("google"),
        "google.auth": ModuleType("google.auth"),
        "google.auth.transport": ModuleType("google.auth.transport"),
        "google.auth.transport.requests": ModuleType("google.auth.transport.requests"),
        "google.oauth2": ModuleType("google.oauth2"),
        "google.oauth2.credentials": ModuleType("google.oauth2.credentials"),
        "google_auth_oauthlib": ModuleType("google_auth_oauthlib"),
        "google_auth_oauthlib.flow": ModuleType("google_auth_oauthlib.flow"),
        "googleapiclient": ModuleType("googleapiclient"),
        "googleapiclient.discovery": ModuleType("googleapiclient.discovery"),
    }
    modules["google.auth.transport.requests"].Request = object  # type: ignore[attr-defined]
    modules["google.oauth2.credentials"].Credentials = FakeCredentials  # type: ignore[attr-defined]
    modules["google_auth_oauthlib.flow"].InstalledAppFlow = FakeFlow  # type: ignore[attr-defined]
    modules["googleapiclient.discovery"].build = fake_build  # type: ignore[attr-defined]
    for name, module in modules.items():
        monkeypatch.setitem(sys.modules, name, module)
    monkeypatch.setattr(google_oauth, "local_app_data_dir", lambda: tmp_path)
    monkeypatch.setattr(google_oauth, "protect_bytes", lambda data: b"protected:" + data)
    monkeypatch.setattr(google_oauth, "unprotect_bytes", lambda data: data.removeprefix(b"protected:"))
    client_file = tmp_path / "synthetic-client.json"
    client_file.write_text("synthetic", encoding="utf-8")

    google_oauth.build_read_only_google_sheets_service(client_file)
    google_oauth.build_read_only_google_sheets_service(client_file)
    google_oauth.build_read_write_google_sheets_service(client_file)

    assert google_oauth.READ_ONLY_SCOPE != google_oauth.READ_WRITE_SCOPE
    assert flow_calls == [
        (str(client_file), [google_oauth.READ_ONLY_SCOPE]),
        (str(client_file), [google_oauth.READ_WRITE_SCOPE]),
    ]
    assert len(refresh_calls) == 1
    assert len(build_calls) == 3
    assert len(list(tmp_path.glob("sheets-oauth-*.bin"))) == 2


def test_corrupt_protected_cache_fails_closed_without_consent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    path = tmp_path / "cache.bin"
    path.write_bytes(b"invalid")
    monkeypatch.setattr(google_oauth, "_token_path", lambda *_: path)
    monkeypatch.setattr(google_oauth, "unprotect_bytes", lambda *_: (_ for _ in ()).throw(ValueError()))
    with pytest.raises(google_oauth.GoogleSheetsAuthorizationError):
        google_oauth.build_read_only_google_sheets_service("unused")
