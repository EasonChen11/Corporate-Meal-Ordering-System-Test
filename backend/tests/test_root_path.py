import importlib
import os

import backend.main as backend_main


def _reload_with_env(monkeypatch, value: str | None):
    if value is None:
        monkeypatch.delenv("ROOT_PATH", raising=False)
    else:
        monkeypatch.setenv("ROOT_PATH", value)
    return importlib.reload(backend_main)


def test_root_path_defaults_to_empty_when_env_unset(monkeypatch):
    module = _reload_with_env(monkeypatch, None)
    assert module.app.root_path == ""


def test_root_path_uses_env_when_set(monkeypatch):
    module = _reload_with_env(monkeypatch, "/preview/feat-a")
    assert module.app.root_path == "/preview/feat-a"


def test_create_app_picks_up_root_path(monkeypatch):
    monkeypatch.setenv("ROOT_PATH", "/preview/x")
    module = importlib.reload(backend_main)
    app = module.create_app()
    assert app.root_path == "/preview/x"
