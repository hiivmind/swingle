from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
from typing import Any

LANES = ("implement", "review")
TIERS = ("cheapest", "standard", "most-capable")
DEFAULT_CONFIG = {
    "disable": [],
    "providers_by_lane": {},
    "model_preferences": {},
}
KNOWN_KEYS = {
    "disable", "default_provider", "providers_by_lane", "model_preferences"
}
REMOVED_KEYS = {"require-verified-version", "superpowers", "note"}


@dataclass(frozen=True)
class ConfigResult:
    config: dict[str, Any]
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()


def _defaults() -> dict[str, Any]:
    """Return a fresh configuration tree."""
    return {
        "disable": [],
        "providers_by_lane": {},
        "model_preferences": {},
    }


def resolve_config_path(
    explicit: str | Path | None = None,
    project: str | Path | None = None,
) -> tuple[str, Path | None]:
    candidate = Path(explicit) if explicit else None
    if candidate is None and os.environ.get("SWINGLE_CONFIG"):
        candidate = Path(os.environ["SWINGLE_CONFIG"])
    if candidate is not None:
        return "env", candidate
    if project is not None:
        project_path = Path(project) / ".swingle.json"
        if project_path.is_file():
            return "project", project_path
    xdg = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    user_path = xdg / "swingle" / "config.json"
    if user_path.is_file():
        return "user", user_path
    return "none", None


def _provider_is_known(provider: str, provider_ids: set[str]) -> bool:
    return provider in provider_ids


def _normalise_config(
    raw: dict[str, Any], provider_ids: set[str],
) -> tuple[dict[str, Any], list[str], list[str]]:
    config = _defaults()
    warnings: list[str] = []
    errors: list[str] = []

    for key in raw:
        if key in REMOVED_KEYS:
            warnings.append(f"{key}: removed configuration key")
        elif key not in KNOWN_KEYS:
            warnings.append(f"{key}: unknown configuration key")

    disable = raw.get("disable", [])
    if not isinstance(disable, list) or not all(isinstance(item, str) for item in disable):
        errors.append("disable: must be a list of provider names")
    elif not all(_provider_is_known(item, provider_ids) for item in disable):
        errors.append("disable: contains an unknown provider")
    else:
        config["disable"] = list(disable)

    if "default_provider" in raw:
        default_provider = raw["default_provider"]
        if not isinstance(default_provider, str):
            errors.append("default_provider: must be a provider name")
        elif not _provider_is_known(default_provider, provider_ids):
            errors.append("default_provider: unknown provider")
        else:
            config["default_provider"] = default_provider

    providers_by_lane = raw.get("providers_by_lane", {})
    if not isinstance(providers_by_lane, dict):
        errors.append("providers_by_lane: must be an object")
    else:
        valid_lanes = True
        normalized_lanes: dict[str, str] = {}
        for lane, provider in providers_by_lane.items():
            if lane not in LANES:
                errors.append(f"providers_by_lane.{lane}: unknown lane")
                valid_lanes = False
            elif not isinstance(provider, str):
                errors.append(f"providers_by_lane.{lane}: must be a provider name")
                valid_lanes = False
            elif not _provider_is_known(provider, provider_ids):
                errors.append(f"providers_by_lane.{lane}: unknown provider")
                valid_lanes = False
            else:
                normalized_lanes[lane] = provider
        if valid_lanes:
            config["providers_by_lane"] = normalized_lanes

    model_preferences = raw.get("model_preferences", {})
    if not isinstance(model_preferences, dict):
        warnings.append("model_preferences: must be an object")
    else:
        normalized_preferences: dict[str, dict[str, list[str]]] = {}
        for provider, rows in model_preferences.items():
            if not isinstance(provider, str) or not _provider_is_known(provider, provider_ids):
                warnings.append(f"model_preferences.{provider}: unknown provider")
                continue
            if not isinstance(rows, dict):
                warnings.append(f"model_preferences.{provider}: must be an object")
                continue
            normalized_rows: dict[str, list[str]] = {}
            for tier, models in rows.items():
                if tier not in TIERS:
                    warnings.append(f"model_preferences.{provider}.{tier}: unknown tier")
                elif not isinstance(models, list) or not all(isinstance(model, str) for model in models):
                    warnings.append(f"model_preferences.{provider}.{tier}: must be a list of model names")
                else:
                    normalized_rows[tier] = list(models)
            normalized_preferences[provider] = normalized_rows
        config["model_preferences"] = normalized_preferences

    disabled = set(config["disable"])
    default_provider = config.get("default_provider")
    if default_provider in disabled:
        errors.append("default_provider: provider is disabled")
    for lane, provider in config["providers_by_lane"].items():
        if provider in disabled:
            errors.append(f"providers_by_lane.{lane}: provider is disabled")

    return config, warnings, errors


def load_config(path: str | Path | None, provider_ids: set[str]) -> ConfigResult:
    if path is None:
        return ConfigResult(_defaults())
    config_path = Path(path)
    if not config_path.exists():
        return ConfigResult(_defaults())
    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        return ConfigResult(_defaults(), errors=(f"{config_path}: unreadable or malformed JSON ({error})",))
    if not isinstance(raw, dict):
        return ConfigResult(_defaults(), errors=(f"{config_path}: config root must be an object",))

    config, warnings, errors = _normalise_config(raw, provider_ids)
    return ConfigResult(config, tuple(warnings), tuple(errors))


def init_config(path: str | Path, force: bool = False) -> Path:
    config_path = Path(path)
    if config_path.exists() and not force:
        return config_path
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(DEFAULT_CONFIG, indent=2) + "\n", encoding="utf-8")
    return config_path


def set_config_value(
    path: str | Path,
    dotted_key: str,
    json_value: str,
    provider_ids: set[str],
) -> Path:
    config_path = Path(path)
    current = load_config(config_path, provider_ids)
    if current.errors:
        raise ValueError("cannot update invalid configuration: " + "; ".join(current.errors))
    try:
        value = json.loads(json_value)
    except json.JSONDecodeError as error:
        raise ValueError(f"invalid JSON value: {error}") from error

    parts = dotted_key.split(".")
    if not dotted_key or any(not part for part in parts):
        raise ValueError("configuration key must be non-empty dotted path")
    if parts[0] not in KNOWN_KEYS:
        raise ValueError(f"unknown configuration key: {parts[0]}")
    if parts[0] in {"disable", "default_provider"} and len(parts) != 1:
        raise ValueError(f"{parts[0]} does not support nested values")
    if parts[0] == "providers_by_lane":
        if len(parts) != 2 or parts[1] not in LANES:
            raise ValueError("providers_by_lane key must name a known lane")
    if parts[0] == "model_preferences":
        if len(parts) != 3:
            raise ValueError("model_preferences key must be provider.tier")
        if not _provider_is_known(parts[1], provider_ids):
            raise ValueError(f"unknown provider: {parts[1]}")
        if parts[2] not in TIERS:
            raise ValueError(f"unknown tier: {parts[2]}")

    updated = json.loads(json.dumps(current.config))
    target: dict[str, Any] = updated
    for part in parts[:-1]:
        child = target.get(part)
        if not isinstance(child, dict):
            child = {}
            target[part] = child
        target = child
    target[parts[-1]] = value

    normalized, warnings, errors = _normalise_config(updated, provider_ids)
    if errors:
        raise ValueError("invalid configuration value: " + "; ".join(errors))
    kept_value: Any = normalized
    for part in parts:
        if not isinstance(kept_value, dict) or part not in kept_value:
            kept_value = None
            break
        kept_value = kept_value[part]
    if kept_value is None or kept_value != value:
        raise ValueError(f"invalid configuration value for {dotted_key}")
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(normalized, indent=2) + "\n", encoding="utf-8")
    return config_path
