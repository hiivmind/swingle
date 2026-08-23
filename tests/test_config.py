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


def test_contracts_tuple_matches_contracts_directory():
    from swingle.config import CONTRACTS

    stems = sorted(
        path.stem.removesuffix("-contract")
        for path in (Path(__file__).resolve().parents[1] / "contracts").glob("*-contract.md")
    )
    assert sorted(CONTRACTS) == stems


def test_providers_by_contract_accepts_string_and_tier_map(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({
        "providers_by_contract": {
            "implementer": "codex",
            "fact-checker": {"cheapest": "grok", "most-capable": "codex"},
        }
    }))

    result = load_config(path, PROVIDERS)

    assert result.config["providers_by_contract"] == {
        "implementer": "codex",
        "fact-checker": {"cheapest": "grok", "most-capable": "codex"},
    }
    assert result.errors == ()
    assert result.warnings == ()


def test_providers_by_contract_rejects_unknown_contract(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"providers_by_contract": {"deployer": "codex"}}))

    result = load_config(path, PROVIDERS)

    assert result.config["providers_by_contract"] == {}
    assert any("unknown contract" in error for error in result.errors)


def test_providers_by_contract_rejects_empty_tier_map(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"providers_by_contract": {"reader": {}}}))

    result = load_config(path, PROVIDERS)

    assert result.config["providers_by_contract"] == {}
    assert any("at least one tier" in error for error in result.errors)


def test_providers_by_contract_rejects_disabled_provider_in_both_forms(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({
        "disable": ["grok"],
        "providers_by_contract": {
            "implementer": "grok",
            "fact-checker": {"cheapest": "grok"},
        },
    }))

    result = load_config(path, PROVIDERS)

    assert any("provider is disabled" in error for error in result.errors)
    assert len(result.errors) == 2


def test_legacy_providers_by_lane_expands_with_warning_and_excludes_new_contracts(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({
        "providers_by_lane": {
            "implement": "codex",
            "review": "grok",
        }
    }))

    result = load_config(path, PROVIDERS)

    assert result.config["providers_by_contract"] == {
        "reader": "codex",
        "implementer": "codex",
        "task-reviewer": "grok",
        "design-reviewer": "grok",
    }
    assert any(
        "expanded to providers_by_contract" in warning for warning in result.warnings
    )
    assert not any(
        role in result.config["providers_by_contract"]
        for role in ("independent-review", "fact-checker", "general-task")
    )
    assert result.errors == ()


def test_authored_provider_beats_lane_expansion(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({
        "providers_by_contract": {"implementer": "grok"},
        "providers_by_lane": {"implement": "codex"},
    }))

    result = load_config(path, PROVIDERS)

    assert result.config["providers_by_contract"]["implementer"] == "grok"
    assert result.config["providers_by_contract"]["reader"] == "codex"


def test_set_providers_by_contract_string_and_tier_entry(tmp_path):
    path = tmp_path / "config.json"
    init_config(path)

    set_config_value(path, "providers_by_contract.implementer", '"codex"', PROVIDERS)
    set_config_value(
        path, "providers_by_contract.fact-checker.most-capable", '"grok"', PROVIDERS
    )

    result = load_config(path, PROVIDERS)
    assert result.config["providers_by_contract"]["implementer"] == "codex"
    assert result.config["providers_by_contract"]["fact-checker"] == {
        "most-capable": "grok"
    }


def test_set_providers_by_contract_rejects_unknown_contract_or_tier(tmp_path):
    path = tmp_path / "config.json"
    init_config(path)
    before = path.read_text()

    with pytest.raises(ValueError):
        set_config_value(path, "providers_by_contract.deployer", '"codex"', PROVIDERS)
    with pytest.raises(ValueError):
        set_config_value(
            path, "providers_by_contract.reader.fastest", '"codex"', PROVIDERS
        )

    assert path.read_text() == before


def test_legacy_providers_by_lane_non_dict_and_empty_forms(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"providers_by_lane": "codex"}))
    result = load_config(path, PROVIDERS)
    assert any("must be an object" in error for error in result.errors)
    assert any("providers_by_lane" in warning for warning in result.warnings)

    path.write_text(json.dumps({"providers_by_lane": {}}))
    result = load_config(path, PROVIDERS)
    assert result.config["providers_by_contract"] == {}
    assert any("providers_by_lane" in warning for warning in result.warnings)


def test_legacy_lane_rejects_non_string_value(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"providers_by_lane": {"implement": ["codex"]}}))

    result = load_config(path, PROVIDERS)

    assert any(
        "must be a provider name" in error for error in result.errors
    )
    assert not any("unknown provider" in error for error in result.errors)


def test_fully_shadowed_legacy_key_warns_and_expands_nothing(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({
        "providers_by_contract": {
            "reader": "grok", "implementer": "grok",
            "task-reviewer": "grok", "design-reviewer": "grok",
        },
        "providers_by_lane": {"implement": "codex", "review": "codex"},
    }))

    result = load_config(path, PROVIDERS)

    assert all(result.config["providers_by_contract"][role] == "grok" for role in (
        "reader", "implementer", "task-reviewer", "design-reviewer",
    ))
    assert any("ignored" in warning for warning in result.warnings)


def test_disabled_provider_via_legacy_lane_names_its_origin(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({
        "disable": ["codex"],
        "providers_by_lane": {"review": "codex"},
    }))

    result = load_config(path, PROVIDERS)

    assert any(
        "expanded from providers_by_lane" in error for error in result.errors
    )


def test_authored_tier_map_beats_lane_expansion(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({
        "providers_by_contract": {"implementer": {"most-capable": "grok"}},
        "providers_by_lane": {"implement": "codex"},
    }))

    result = load_config(path, PROVIDERS)

    assert result.config["providers_by_contract"]["implementer"] == {
        "most-capable": "grok"
    }
    assert result.config["providers_by_contract"]["reader"] == "codex"


def test_set_tier_over_string_converts_to_map(tmp_path):
    path = tmp_path / "config.json"
    init_config(path)
    set_config_value(path, "providers_by_contract.reader", '"codex"', PROVIDERS)
    set_config_value(path, "providers_by_contract.reader.most-capable", '"grok"', PROVIDERS)

    result = load_config(path, PROVIDERS)
    assert result.config["providers_by_contract"]["reader"] == {"most-capable": "grok"}


def test_set_full_tier_map_object_as_value(tmp_path):
    path = tmp_path / "config.json"
    init_config(path)

    set_config_value(
        path,
        "providers_by_contract.fact-checker",
        '{"cheapest": "grok", "most-capable": "codex"}',
        PROVIDERS,
    )

    result = load_config(path, PROVIDERS)
    assert result.config["providers_by_contract"]["fact-checker"] == {
        "cheapest": "grok", "most-capable": "codex",
    }


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


def test_model_preferences_accept_model_effort_objects(tmp_path):
    path = tmp_path / "config.json"
    entries = ["current-model", {"model": "frontier-model", "effort": "high"}]
    path.write_text(json.dumps({
        "model_preferences": {"codex": {"most-capable": entries}}
    }))

    result = load_config(path, PROVIDERS)

    assert result.config["model_preferences"]["codex"]["most-capable"] == entries
    assert result.errors == ()
    assert result.warnings == ()


def test_malformed_preference_entry_warns_and_drops_row(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({
        "model_preferences": {
            "codex": {
                "standard": [{"model": "m1"}],
                "cheapest": [{"model": "m2", "effort": 3}],
                "most-capable": ["ok-model"]
            }
        }
    }))

    result = load_config(path, PROVIDERS)

    assert result.config["model_preferences"]["codex"] == {
        "most-capable": ["ok-model"]
    }
    assert any("standard" in w for w in result.warnings)
    assert any("cheapest" in w for w in result.warnings)
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


def test_set_config_value_accepts_model_effort_object(tmp_path):
    path = tmp_path / "config.json"
    init_config(path)

    set_config_value(
        path,
        "model_preferences.codex.most-capable",
        '[{"model": "frontier-model", "effort": "high"}]',
        PROVIDERS,
    )

    result = load_config(path, PROVIDERS)
    assert result.config["model_preferences"]["codex"]["most-capable"] == [
        {"model": "frontier-model", "effort": "high"}
    ]
    assert result.errors == ()
