import json
import pytest
from pathlib import Path

from swingle.config import (
    DEFAULT_CONFIG,
    init_config,
    load_config,
    resolve_config_path,
    set_config_value,
)

PROVIDERS = {"codex", "grok"}


def test_whole_file_precedence_env_project_user(tmp_path, monkeypatch):
    user = tmp_path / "xdg" / "swingle" / "config.json"
    project = tmp_path / "project"
    project.mkdir()
    project_file = project / ".swingle.json"
    env_file = tmp_path / "env.json"
    for path, provider in ((user, "codex"), (project_file, "grok"), (env_file, "codex")):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"default_provider": provider}))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    monkeypatch.setenv("SWINGLE_CONFIG", str(env_file))

    layer, path = resolve_config_path(project=project)

    assert layer == "env"
    assert path == env_file


def test_model_preferences_are_ordered_hints(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({
        "model_preferences": {
            "codex": {"standard": ["future-model", "current-model"]}
        }
    }))

    result = load_config(path, PROVIDERS)

    assert result.config["model_preferences"]["codex"]["standard"] == [
        "future-model", "current-model"
    ]
    assert result.errors == ()


def test_bad_optional_preference_warns_and_drops_only_that_row(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({
        "default_provider": "codex",
        "model_preferences": {
            "codex": {
                "standard": "not-a-list",
                "cheapest": ["small-model"]
            }
        }
    }))

    result = load_config(path, PROVIDERS)

    assert result.config["default_provider"] == "codex"
    assert result.config["model_preferences"]["codex"] == {
        "cheapest": ["small-model"]
    }
    assert any("standard" in warning for warning in result.warnings)
    assert result.errors == ()


def test_removed_keys_warn_and_have_no_effect(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({
        "require-verified-version": True,
        "superpowers": {"codex": {"installed": False}}
    }))

    result = load_config(path, PROVIDERS)

    assert result.config == DEFAULT_CONFIG
    assert {warning.split(":", 1)[0] for warning in result.warnings} == {
        "require-verified-version", "superpowers"
    }
    assert result.errors == ()


def test_malformed_json_returns_defaults_and_error(tmp_path):
    path = tmp_path / "config.json"
    path.write_text("{bad json")

    result = load_config(path, PROVIDERS)

    assert result.config == DEFAULT_CONFIG
    assert result.errors


def test_init_and_set_configuration(tmp_path):
    path = tmp_path / "config.json"
    init_config(path)
    set_config_value(
        path,
        "model_preferences.codex.standard",
        '["preferred", "fallback"]',
        PROVIDERS,
    )

    result = load_config(path, PROVIDERS)

    assert result.config["model_preferences"]["codex"]["standard"] == [
        "preferred", "fallback"
    ]


def test_set_config_value_rejects_malformed_preference_without_writing(tmp_path):
    path = tmp_path / "config.json"
    init_config(path)
    before = path.read_text()

    with pytest.raises(ValueError):
        set_config_value(
            path,
            "model_preferences.codex.standard",
            '"not-a-list"',
            PROVIDERS,
        )

    assert path.read_text() == before


def test_set_config_value_accepts_valid_preference(tmp_path):
    path = tmp_path / "config.json"
    init_config(path)

    set_config_value(
        path,
        "model_preferences.codex.standard",
        '["preferred"]',
        PROVIDERS,
    )

    result = load_config(path, PROVIDERS)
    assert result.config["model_preferences"]["codex"]["standard"] == ["preferred"]
