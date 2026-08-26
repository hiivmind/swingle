import pytest
from swingle.config import load_config
from swingle.liveness import resolve_liveness_policy


BUILTINS = {
    "cheapest": (60, 300, 300, None),
    "standard": (60, 300, 300, None),
    "most-capable": (60, 600, 600, None),
}
FIELDS = (
    "check_interval_seconds",
    "startup_grace_seconds",
    "silence_warning_seconds",
    "hard_timeout_seconds",
)


def test_builtin_policy_differs_for_most_capable():
    for tier, expected in BUILTINS.items():
        result = resolve_liveness_policy({}, "codex", tier)
        assert tuple(result.policy[field] for field in FIELDS) == expected
        assert result.warnings == ()
        assert result.errors == ()


def test_policy_resolves_each_field_across_all_six_layers():
    config = {
        "liveness": {
            "default": {
                "check_interval_seconds": 10,
                "startup_grace_seconds": 20,
                "silence_warning_seconds": 30,
                "hard_timeout_seconds": 40,
            },
            "by_tier": {
                "standard": {
                    "check_interval_seconds": 11,
                    "startup_grace_seconds": 21,
                    "silence_warning_seconds": 31,
                    "hard_timeout_seconds": 41,
                },
            },
            "by_provider": {
                "codex": {
                    "default": {
                        "check_interval_seconds": 12,
                        "startup_grace_seconds": 22,
                        "silence_warning_seconds": 32,
                        "hard_timeout_seconds": 42,
                    },
                    "by_tier": {
                        "standard": {
                            "check_interval_seconds": 13,
                            "startup_grace_seconds": 23,
                            "silence_warning_seconds": 33,
                            "hard_timeout_seconds": 43,
                        },
                    },
                },
            },
        },
    }

    result = resolve_liveness_policy(
        config,
        "codex",
        "standard",
        explicit={
            "check_interval_seconds": 14,
            "startup_grace_seconds": 24,
            "silence_warning_seconds": 34,
            "hard_timeout_seconds": 44,
        },
    )

    assert tuple(result.policy[field] for field in FIELDS) == (14, 24, 34, 44)


def test_null_hard_timeout_survives_resolution():
    result = resolve_liveness_policy(
        {"liveness": {"default": {"hard_timeout_seconds": None}}},
        "codex",
        "standard",
    )

    assert result.policy["hard_timeout_seconds"] is None


def test_invalid_optional_branch_warns_and_falls_through():
    config = {
        "liveness": {
            "default": {"check_interval_seconds": 77},
            "by_provider": {
                "codex": {
                    "default": {"check_interval_seconds": 88},
                    "by_tier": {
                        "standard": {"check_interval_seconds": -1},
                    },
                },
            },
        },
    }

    result = resolve_liveness_policy(config, "codex", "standard")

    assert result.policy["check_interval_seconds"] == 88
    assert any("check_interval_seconds" in warning for warning in result.warnings)


def test_invalid_explicit_value_stops_resolution():
    result = resolve_liveness_policy(
        {"liveness": {"default": {"check_interval_seconds": 77}}},
        "codex",
        "standard",
        explicit={"check_interval_seconds": 0},
    )

    assert result.policy["check_interval_seconds"] is None
    assert any("check_interval_seconds" in error for error in result.errors)


def test_unknown_provider_policy_is_retained_with_warning(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(
        '{"liveness": {"by_provider": '
        '{"future-cli": {"default": {"check_interval_seconds": 99}}}}}'
    )

    loaded = load_config(path, {"codex"})
    result = resolve_liveness_policy(loaded.config, "future-cli", "standard")

    assert loaded.config["liveness"]["by_provider"]["future-cli"] == {
        "default": {"check_interval_seconds": 99}
    }
    assert result.policy["check_interval_seconds"] == 99
    assert any("future-cli" in warning for warning in loaded.warnings)


@pytest.mark.parametrize(
    ("config", "explicit", "expected"),
    [
        ({}, {"check_interval_seconds": 11}, 11),
        (
            {"liveness": {"by_provider": {"codex": {"by_tier": {
                "standard": {"check_interval_seconds": 22}
            }}}}},
            None,
            22,
        ),
        (
            {"liveness": {"by_provider": {"codex": {"default": {
                "check_interval_seconds": 33
            }}}}},
            None,
            33,
        ),
        (
            {"liveness": {"by_tier": {"standard": {
                "check_interval_seconds": 44
            }}}},
            None,
            44,
        ),
        (
            {"liveness": {"default": {"check_interval_seconds": 55}}},
            None,
            55,
        ),
        ({}, None, 60),
    ],
)
def test_each_liveness_layer_can_supply_an_omitted_field(config, explicit, expected):
    result = resolve_liveness_policy(config, "codex", "standard", explicit)

    assert result.policy["check_interval_seconds"] == expected
