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
    # A failed assertion must not leave a live worker outlasting monkeypatches.
    # Such a worker can hold the process-wide research lock and later use real
    # collaborators after this test's fakes have been restored.
    instances = []
    original_init = backend.ProductionBackend.__init__

    def tracked_init(instance, *args, **kwargs):
        original_init(instance, *args, **kwargs)
        instances.append(instance)

    monkeypatch.setattr(backend.ProductionBackend, "__init__", tracked_init)
    yield
    for instance in reversed(instances):
        instance.shutdown()
