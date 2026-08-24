from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from .config import load_config, resolve_config_path
from .grounding import GROUNDING_SCOPES, GroundingPackError, dispatch_guidance_sha256, evaluate_grounding
from .liveness import resolve_grounding_ttl, resolve_liveness_policy
from .providers import discover_provider_ids

NEXT_ACTIONS = (
    "dispatch",
    "choose_provider",
    "setup_repair",
    "ground_and_record",
    "ground_without_cache",
    "refresh_context",
)
_BASE_SCOPES = (
    "headless-command",
    "stdin-closure",
    "permission-trust",
    "model-effort-encoding",
    "output-report-mode",
    "liveness-signal",
)


def required_grounding_scopes(
    *,
    explicit_model: bool,
    has_model_preferences: bool,
    report_mode: str | None,
    resume: bool,
) -> tuple[str, ...]:
    """Return the grounding scopes needed to compose one dispatch.

    This function computes requirements only.  It never reads a provider or cache.
    """
    del report_mode  # output-report-mode is required for every dispatch.
    selected = set(_BASE_SCOPES)
    if not explicit_model and has_model_preferences:
        selected.update(("model-discovery", "model-inventory"))
    if resume:
        selected.add("session-resume-fork")
    return tuple(scope for scope in GROUNDING_SCOPES if scope in selected)


def _config_details(plugin_root: Path, project: Path) -> tuple[dict[str, Any], dict[str, Any], list[str], list[str]]:
    config_layer, config_path = resolve_config_path(project=project)
    provider_ids = discover_provider_ids(plugin_root) if (plugin_root / "providers").is_dir() else set()
    loaded = load_config(config_path, provider_ids)
    details = {
        "layer": config_layer,
        "path": str(config_path.expanduser().resolve()) if config_path is not None else None,
        "warnings": list(loaded.warnings),
        "errors": list(loaded.errors),
    }
    return loaded.config, details, list(loaded.warnings), list(loaded.errors)


def _provider_candidate(config: dict[str, Any], role: str, tier: str, explicit: str | None) -> tuple[str | None, str]:
    if explicit is not None:
        return explicit, "explicit"
    contracts = config.get("providers_by_contract", {})
    configured = contracts.get(role) if isinstance(contracts, dict) else None
    if isinstance(configured, dict):
        selected = configured.get(tier)
        if isinstance(selected, str):
            return selected, "contract-tier"
    elif isinstance(configured, str):
        return configured, "contract"
    default = config.get("default_provider")
    if isinstance(default, str):
        return default, "default"
    return None, "none"


def _inventory_match(entries: list[Any], model: str) -> dict[str, Any] | None:
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        if entry.get("id") == model or model in entry.get("aliases", []):
            return deepcopy(entry)
    return None


def _model_candidates(
    config: dict[str, Any],
    provider: str,
    tier: str,
    explicit_model: str | None,
    explicit_effort: str | None,
    grounding: dict[str, Any],
) -> list[dict[str, Any]]:
    entries = grounding.get("models", {}).get("entries", []) if grounding.get("status") == "usable" else []
    if not isinstance(entries, list):
        entries = []
    candidates: list[dict[str, Any]] = []

    if explicit_model is not None:
        candidates.append({
            "model": explicit_model,
            "effort": explicit_effort or "provider-default",
            "source": "explicit",
            "observed": _inventory_match(entries, explicit_model),
        })
    else:
        prefs_root = config.get("model_preferences", {})
        rows = prefs_root.get(provider, {}) if isinstance(prefs_root, dict) else {}
        preferences = rows.get(tier, []) if isinstance(rows, dict) else []
        if isinstance(preferences, list):
            for preference in preferences:
                if isinstance(preference, str):
                    model_name, joined_effort = preference, None
                elif isinstance(preference, dict):
                    model_name, joined_effort = preference.get("model"), preference.get("effort")
                else:
                    continue
                if not isinstance(model_name, str):
                    continue
                candidates.append({
                    "model": model_name,
                    "effort": explicit_effort or joined_effort or "provider-default",
                    "source": "preference",
                    "observed": _inventory_match(entries, model_name),
                })
    candidates.append({
        "model": "provider-default",
        "effort": explicit_effort or "provider-default",
        "source": "provider-default",
        "observed": _inventory_match(entries, "provider-default"),
    })
    return candidates


def _ledger_event(provider: str, grounding: dict[str, Any], required: tuple[str, ...]) -> dict[str, Any] | None:
    if grounding.get("status") != "usable":
        return None
    receipt = grounding.get("receipt")
    if not isinstance(receipt, dict):
        return None
    mechanics = grounding.get("mechanics", {})
    selected = [scope for scope in required if scope in mechanics]
    return {
        "event": "grounding-reused",
        "data": {
            "receipt_id": receipt.get("receipt_id"),
            "receipt_revision": receipt.get("revision"),
            "storage": "cache",
            "provider": provider,
            "cache_path": grounding.get("cache_path"),
            "grounded_at": receipt.get("grounded_at"),
            "expires_at": receipt.get("expires_at"),
            "executable": receipt.get("executable"),
            "provider_guidance_sha256": receipt.get("provider_guidance_sha256"),
            "scopes": selected,
            "model_count": len(grounding.get("models", {}).get("entries", [])),
            "evidence_commands": sorted({
                mechanics[scope].get("evidence_command", "")
                for scope in selected
                if isinstance(mechanics.get(scope), dict) and mechanics[scope].get("evidence_command", "")
            }),
        },
    }


def _empty_grounding() -> dict[str, Any]:
    return {"cache_path": None, "ttl_seconds": None, "required_scopes": [], "status": "not-evaluated", "receipt": None, "mechanics": {}, "models": {}, "ledger_event": None}


def _setup(target: str, reason: str, **extra: Any) -> dict[str, Any]:
    return {"target": target, "reason": reason, **extra}


def build_dispatch_context(
    *,
    plugin_root: Path,
    project: Path,
    role: str,
    tier: str,
    provider: str | None = None,
    model: str | None = None,
    effort: str | None = None,
    report_mode: str | None = None,
    resume: bool = False,
    explicit_liveness: dict[str, Any] | None = None,
) -> dict[str, Any]:
    plugin_root = Path(plugin_root).expanduser().resolve()
    project = Path(project).expanduser().resolve()
    config, config_info, warnings, errors = _config_details(plugin_root, project)
    provider_ids = discover_provider_ids(plugin_root) if (plugin_root / "providers").is_dir() else set()
    mode = report_mode or "captured-output"
    selection_provider, provider_source = _provider_candidate(config, role, tier, provider)
    result: dict[str, Any] = {
        "project_root": str(project),
        "config": config_info,
        "selection": {"provider": {"value": selection_provider, "source": provider_source}, "models": [], "report_mode": mode},
        "provider_pack": None,
        "grounding": _empty_grounding(),
        "liveness_policy": None,
        "setup_repair": None,
        "next_action": "choose_provider" if selection_provider is None else "dispatch",
        "reason": "no provider could be resolved" if selection_provider is None else "",
        "warnings": warnings,
        "errors": errors,
    }
    if selection_provider is not None and selection_provider in config.get("disable", []):
        result["next_action"] = "setup_repair"
        result["reason"] = "selected provider is disabled"
        result["setup_repair"] = _setup("provider-routing", result["reason"], provider=selection_provider)
        result["errors"] = [result["reason"]]
        return result
    if selection_provider is None and errors:
        result["next_action"] = "setup_repair"
        result["reason"] = "selected configuration is malformed"
        result["setup_repair"] = _setup("config-error", result["reason"], config_path=config_info["path"])
        return result
    if selection_provider is None:
        return result
    if provider is not None and selection_provider not in provider_ids:
        result["next_action"] = "setup_repair"
        result["reason"] = "explicit provider is not available"
        result["setup_repair"] = _setup("provider-routing", result["reason"], provider=selection_provider)
        result["errors"] = [result["reason"]]
        return result
    if errors:
        result["next_action"] = "setup_repair"
        result["reason"] = "selected configuration is malformed"
        result["setup_repair"] = _setup("config-error", result["reason"], config_path=config_info["path"])
        return result
    pack_path = plugin_root / "providers" / selection_provider / "pack.md"
    try:
        fingerprint = dispatch_guidance_sha256(pack_path)
    except (GroundingPackError, OSError, UnicodeError, ValueError) as exc:
        result["next_action"] = "setup_repair"
        result["reason"] = str(exc)
        result["setup_repair"] = _setup("provider-grounding", result["reason"], provider=selection_provider, path=str(pack_path.resolve()))
        result["errors"] = [result["reason"]]
        return result
    result["provider_pack"] = {"path": str(pack_path.resolve()), "dispatch_guidance_sha256": fingerprint}

    has_preferences = bool(config.get("model_preferences", {}).get(selection_provider, {}).get(tier, [])) if isinstance(config.get("model_preferences"), dict) else False
    required = required_grounding_scopes(explicit_model=model is not None, has_model_preferences=has_preferences, report_mode=mode, resume=resume)
    ttl = resolve_grounding_ttl(config, selection_provider)
    policy = resolve_liveness_policy(config, selection_provider, tier, explicit_liveness)
    warnings.extend(policy.warnings)
    result["warnings"] = warnings
    if policy.errors:
        result["errors"] = list(policy.errors)
        result["next_action"] = "setup_repair"
        result["reason"] = "explicit liveness policy is invalid"
        result["setup_repair"] = _setup("liveness-policy", result["reason"], provider=selection_provider)
        return result
    result["liveness_policy"] = policy.policy

    grounding = evaluate_grounding(project, selection_provider, provider_guidance_sha256=fingerprint, required_scopes=required, ttl_seconds=ttl)
    if grounding.get("status") == "missing" and ttl > 0:
        required = tuple(GROUNDING_SCOPES)
        grounding = evaluate_grounding(project, selection_provider, provider_guidance_sha256=fingerprint, required_scopes=required, ttl_seconds=ttl)
    grounding["ledger_event"] = _ledger_event(selection_provider, grounding, required)
    result["grounding"] = grounding
    result["selection"]["models"] = _model_candidates(config, selection_provider, tier, model, effort, grounding)

    status = grounding.get("status")
    if status == "usable":
        result["next_action"] = "dispatch"
        result["reason"] = "all required grounding scopes are usable"
    elif status == "bypass":
        result["next_action"] = "ground_without_cache"
        result["reason"] = "grounding cache TTL is zero"
    else:
        result["next_action"] = "ground_and_record"
        result["reason"] = f"grounding cache is {status}"
    return result
