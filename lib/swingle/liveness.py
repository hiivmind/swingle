from __future__ import annotations

from dataclasses import dataclass
from typing import Any

DEFAULT_GROUNDING_TTL_SECONDS = 604800
LIVENESS_FIELDS = (
    "check_interval_seconds",
    "startup_grace_seconds",
    "silence_warning_seconds",
    "hard_timeout_seconds",
)
BUILTIN_LIVENESS_POLICY = {
    "cheapest": (60, 300, 300, None),
    "standard": (60, 300, 300, None),
    "most-capable": (60, 600, 600, None),
}
_MISSING = object()


@dataclass(frozen=True)
class PolicyResult:
    policy: dict[str, int | None]
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()


def _valid_grounding_ttl(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def resolve_grounding_ttl(
    config: dict[str, Any],
    provider: str,
    override: int | None = None,
) -> int:
    if override is not None and not _valid_grounding_ttl(override):
        raise ValueError("grounding TTL override must be a non-negative integer")
    if override is not None:
        return override

    grounding = config.get("grounding_cache")
    if not isinstance(grounding, dict):
        return DEFAULT_GROUNDING_TTL_SECONDS
    by_provider = grounding.get("by_provider")
    if isinstance(by_provider, dict):
        provider_branch = by_provider.get(provider)
        if isinstance(provider_branch, dict):
            provider_ttl = provider_branch.get("ttl_seconds", _MISSING)
            if _valid_grounding_ttl(provider_ttl):
                return provider_ttl
    config_ttl = grounding.get("ttl_seconds", _MISSING)
    if _valid_grounding_ttl(config_ttl):
        return config_ttl
    return DEFAULT_GROUNDING_TTL_SECONDS


def _valid_liveness_value(field: str, value: Any) -> bool:
    if field == "hard_timeout_seconds" and value is None:
        return True
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _field_value(
    branch: Any,
    field: str,
    path: str,
    warnings: list[str],
) -> Any:
    if branch is _MISSING:
        return _MISSING
    if not isinstance(branch, dict):
        warnings.append(f"{path}: must be an object")
        return _MISSING
    value = branch.get(field, _MISSING)
    if value is _MISSING:
        return _MISSING
    if not _valid_liveness_value(field, value):
        warnings.append(f"{path}.{field}: invalid value")
        return _MISSING
    return value


def _lookup_branch(root: Any, keys: tuple[str, ...], path: str, warnings: list[str]) -> Any:
    current = root
    for key in keys:
        if not isinstance(current, dict):
            warnings.append(f"{path}: must be an object")
            return _MISSING
        if key not in current:
            return _MISSING
        current = current[key]
    return current


def resolve_liveness_policy(
    config: dict[str, Any],
    provider: str,
    tier: str,
    explicit: dict[str, Any] | None = None,
) -> PolicyResult:
    warnings: list[str] = []
    errors: list[str] = []
    if not isinstance(config, dict):
        config = {}

    if explicit is None:
        explicit = {}
    elif not isinstance(explicit, dict):
        errors.append("explicit liveness policy must be an object")
        explicit = {}

    for field in explicit:
        if field not in LIVENESS_FIELDS:
            warnings.append(f"explicit.{field}: unknown field")

    liveness = config.get("liveness", _MISSING)
    if liveness is _MISSING:
        liveness = {}
    elif not isinstance(liveness, dict):
        warnings.append("liveness: must be an object")
        liveness = {}

    if tier not in BUILTIN_LIVENESS_POLICY:
        warnings.append(f"liveness tier {tier}: unknown tier")
        builtin_tier = "standard"
    else:
        builtin_tier = tier

    builtin = dict(zip(LIVENESS_FIELDS, BUILTIN_LIVENESS_POLICY[builtin_tier]))
    policy: dict[str, int | None] = {}
    for field in LIVENESS_FIELDS:
        if field in explicit:
            value = explicit[field]
            if _valid_liveness_value(field, value):
                policy[field] = value
            else:
                errors.append(f"explicit.{field}: invalid value")
                policy[field] = None
            continue

        candidates = (
            (("by_provider", provider, "by_tier", tier),
             f"liveness.by_provider.{provider}.by_tier.{tier}"),
            (("by_provider", provider, "default"),
             f"liveness.by_provider.{provider}.default"),
            (("by_tier", tier), f"liveness.by_tier.{tier}"),
            (("default",), "liveness.default"),
        )
        value = _MISSING
        for keys, path in candidates:
            branch = _lookup_branch(liveness, keys, path, warnings)
            candidate = _field_value(branch, field, path, warnings)
            if candidate is not _MISSING:
                value = candidate
                break
        policy[field] = builtin[field] if value is _MISSING else value

    return PolicyResult(policy, tuple(warnings), tuple(errors))
