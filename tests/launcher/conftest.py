"""Launcher composition tests never consult the Owner's default credential store.

Tests of authenticated sessions provide explicit fake logins instead. Production
credential behavior remains exercised by its owning core/research fake backends.
"""

from types import SimpleNamespace

import pytest

from src.launcher import backend


@pytest.fixture(autouse=True)
def no_owner_login_lookup(monkeypatch):
    monkeypatch.setattr(
        backend, "CoreLoginBridge", lambda: SimpleNamespace(login=lambda _site: None)
    )
