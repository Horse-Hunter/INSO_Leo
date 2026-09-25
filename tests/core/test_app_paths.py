from pathlib import Path

from src.core.app_paths import app_root, resolve_app_path, runtime_config_path
from src.research.runtime import default_runtime_config_path


def test_repo_and_frozen_app_root_and_default_config_paths(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    module = repo / "src" / "core" / "app_paths.py"
    module.parent.mkdir(parents=True)
    module.touch()
    assert app_root(module_file=module, frozen=False) == repo

    exe = tmp_path / "release" / "INSO_V1.1.exe"
    assert app_root(module_file=module, frozen=True, executable=exe) == exe.parent
    assert runtime_config_path("research.json", root=exe.parent) == exe.parent / "runtime/research.json"
    assert runtime_config_path("production.json", root=repo) == repo / "runtime/production.json"

    monkeypatch.setattr("src.core.app_paths.app_root", lambda: exe.parent)
    assert default_runtime_config_path() == exe.parent / "runtime/research.json"


def test_config_relative_paths_resolve_against_app_root(tmp_path):
    assert resolve_app_path("runtime/production/workflow.sqlite3", root=tmp_path) == (
        tmp_path / "runtime/production/workflow.sqlite3"
    )
    absolute = tmp_path / "external.xlsx"
    assert resolve_app_path(absolute, root=Path("ignored")) == absolute
