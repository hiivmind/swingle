from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess


import swingle.grounding as grounding_module
from swingle.dispatch import NEXT_ACTIONS, build_dispatch_context, required_grounding_scopes
from swingle.grounding import GROUNDING_SCOPES, dispatch_guidance_sha256, record_grounding

STAMP = "2026-08-24T04:15:30.123Z"


def _scope(name: str, *, observed_at: str = STAMP):
    return {
        "state": "observed", "observation": {}, "applicability": "dispatch",
        "evidence_command": "provider --help", "observed_at": observed_at,
    }


def _pack(root: Path, provider: str) -> Path:
    path = root / "providers" / provider / "pack.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"# {provider}\n\n## Dispatch guidance\nGuidance.\n", encoding="utf-8")
    return path


def _record(project: Path, plugin_root: Path, provider: str = "codex", *, ttl: int = 604800, scopes=None, models=None):
    selected = {scope: _scope(scope) for scope in (scopes or GROUNDING_SCOPES)}
    return record_grounding(project, provider, {
        "complete_profile_observed_at": STAMP if set(selected) == set(GROUNDING_SCOPES) else None,
        "ttl_seconds": ttl, "executable": f"/usr/bin/{provider}",
        "provider_guidance_sha256": dispatch_guidance_sha256(plugin_root / "providers" / provider / "pack.md"),
        "scopes": selected,
        "models": {"discovery_command": f"{provider} models", "observed_at": STAMP, "entries": models or []},
    })


def _base(tmp_path: Path, config=None):
    plugin_root, project = tmp_path / "plugin", tmp_path / "project"
    plugin_root.mkdir(); project.mkdir()
    for provider in ("codex", "omp", "claude"):
        _pack(plugin_root, provider)
    if config is not None:
        (project / ".swingle.json").write_text(json.dumps(config), encoding="utf-8")
    return plugin_root, project


def test_explicit_provider_precedes_contract_and_default(tmp_path):
    plugin_root, project = _base(tmp_path, {"default_provider": "omp", "providers_by_contract": {"reader": "claude"}})
    result = build_dispatch_context(plugin_root=plugin_root, project=project, role="reader", tier="standard", provider="codex")
    assert result["selection"]["provider"] == {"value": "codex", "source": "explicit"}


def test_tier_contract_precedes_plain_contract_and_default(tmp_path):
    plugin_root, project = _base(tmp_path, {"default_provider": "omp", "providers_by_contract": {"reader": {"standard": "codex", "cheapest": "claude"}}})
    result = build_dispatch_context(plugin_root=plugin_root, project=project, role="reader", tier="standard")
    assert result["selection"]["provider"] == {"value": "codex", "source": "contract-tier"}


def test_no_provider_returns_choose_provider(tmp_path):
    plugin_root, project = _base(tmp_path)
    result = build_dispatch_context(plugin_root=plugin_root, project=project, role="reader", tier="standard")
    assert result["next_action"] == "choose_provider"
    assert result["selection"]["provider"]["value"] is None
    assert result["grounding"]["status"] == "not-evaluated"


def test_config_error_without_provider_returns_setup_repair(tmp_path):
    plugin_root, project = _base(tmp_path, {"disable": "codex"})
    result = build_dispatch_context(plugin_root=plugin_root, project=project, role="reader", tier="standard")
    assert result["next_action"] == "setup_repair"
    assert result["setup_repair"]["target"] == "config-error"


def test_config_error_returns_setup_repair_config_error(tmp_path):
    plugin_root, project = _base(tmp_path, {"disable": "codex"})
    result = build_dispatch_context(plugin_root=plugin_root, project=project, role="reader", tier="standard", provider="codex")
    assert result["next_action"] == "setup_repair"
    assert result["setup_repair"]["target"] == "config-error"
    assert result["errors"]


def test_viable_partial_config_proceeds_with_warnings(tmp_path):
    plugin_root, project = _base(tmp_path, {"model_preferences": {"codex": {"standard": "bad"}}, "default_provider": "codex"})
    result = build_dispatch_context(plugin_root=plugin_root, project=project, role="reader", tier="standard")
    assert result["next_action"] in NEXT_ACTIONS
    assert result["warnings"] and not result["errors"]


def test_explicit_disabled_provider_returns_provider_routing_repair(tmp_path):
    plugin_root, project = _base(tmp_path, {"disable": ["codex"]})
    result = build_dispatch_context(plugin_root=plugin_root, project=project, role="reader", tier="standard", provider="codex")
    assert result["next_action"] == "setup_repair"
    assert result["setup_repair"]["target"] == "provider-routing"


def test_missing_cache_returns_ground_and_record(tmp_path):
    plugin_root, project = _base(tmp_path, {"default_provider": "codex"})
    result = build_dispatch_context(plugin_root=plugin_root, project=project, role="reader", tier="standard")
    assert result["next_action"] == "ground_and_record"
    assert result["grounding"]["status"] == "missing"


def test_zero_ttl_returns_ground_without_cache_without_cache_io(tmp_path, monkeypatch):
    plugin_root, project = _base(tmp_path, {"default_provider": "codex", "grounding_cache": {"ttl_seconds": 0}})
    monkeypatch.setattr(grounding_module, "_read_record", lambda *a, **kw: (_ for _ in ()).throw(AssertionError("cache I/O")))
    result = build_dispatch_context(plugin_root=plugin_root, project=project, role="reader", tier="standard")
    assert result["next_action"] == "ground_without_cache"
    assert result["grounding"]["status"] == "bypass"
    assert not (project / ".swingle").exists()


def test_usable_cache_returns_dispatch_and_reused_ledger_event(tmp_path):
    plugin_root, project = _base(tmp_path, {"default_provider": "codex"})
    _record(project, plugin_root)
    result = build_dispatch_context(plugin_root=plugin_root, project=project, role="reader", tier="standard")
    assert result["next_action"] == "dispatch"
    event = result["grounding"]["ledger_event"]
    assert event["event"] == "grounding-reused" and "age_seconds" not in event["data"]
    assert event["data"]["grounded_at"] == STAMP


def test_usable_cache_returns_output_and_permission_observations(tmp_path):
    plugin_root, project = _base(tmp_path, {"default_provider": "codex"})
    scopes = {scope: _scope(scope) for scope in GROUNDING_SCOPES}
    scopes["output-report-mode"]["observation"] = {"format": "jsonl"}
    scopes["permission-trust"]["observation"] = {"tool_class_notes": "edit"}
    record_grounding(project, "codex", {"complete_profile_observed_at": STAMP, "ttl_seconds": 604800, "executable": "/usr/bin/codex", "provider_guidance_sha256": dispatch_guidance_sha256(plugin_root / "providers/codex/pack.md"), "scopes": scopes, "models": {"discovery_command": "codex models", "observed_at": STAMP, "entries": []}})
    result = build_dispatch_context(plugin_root=plugin_root, project=project, role="reader", tier="standard")
    assert result["grounding"]["mechanics"]["output-report-mode"]["observation"] == {"format": "jsonl"}
    assert result["grounding"]["mechanics"]["permission-trust"]["observation"] == {"tool_class_notes": "edit"}


def test_context_returns_selected_pack_path_and_matching_fingerprint(tmp_path):
    plugin_root, project = _base(tmp_path, {"default_provider": "codex"})
    result = build_dispatch_context(plugin_root=plugin_root, project=project, role="reader", tier="standard")
    assert result["provider_pack"]["path"] == str((plugin_root / "providers/codex/pack.md").resolve())
    assert result["provider_pack"]["dispatch_guidance_sha256"] == dispatch_guidance_sha256(plugin_root / "providers/codex/pack.md")


def test_provider_default_and_auto_candidates_survive_context(tmp_path):
    plugin_root, project = _base(tmp_path, {"default_provider": "codex", "model_preferences": {"codex": {"standard": ["preferred"]}}})
    _record(project, plugin_root, models=[{"id": "provider-default"}, {"id": "auto"}])
    result = build_dispatch_context(plugin_root=plugin_root, project=project, role="reader", tier="standard")
    assert [item["model"] for item in result["selection"]["models"]] == ["preferred", "provider-default"]
    assert result["grounding"]["models"]["entries"][-1]["id"] == "auto"


def test_context_returns_no_runnable_command_or_result_parser(tmp_path):
    plugin_root, project = _base(tmp_path, {"default_provider": "codex"})
    result = build_dispatch_context(plugin_root=plugin_root, project=project, role="reader", tier="standard")

    def keys(value):
        if isinstance(value, dict):
            return set(value) | set().union(*(keys(child) for child in value.values()))
        if isinstance(value, list):
            return set().union(*(keys(child) for child in value))
        return set()

    assert not keys(result) & {"argv", "command", "parser", "selector", "result_parser"}


def test_required_scopes_explicit_model_bypasses_inventory():
    scopes = required_grounding_scopes(explicit_model=True, has_model_preferences=True, report_mode="captured-output", resume=False)
    assert "model-inventory" not in scopes
    assert scopes == ("headless-command", "stdin-closure", "permission-trust", "model-effort-encoding", "output-report-mode", "liveness-signal")


def test_required_scopes_preferences_need_inventory():
    scopes = required_grounding_scopes(explicit_model=False, has_model_preferences=True, report_mode="report-file", resume=True)
    assert "model-discovery" in scopes and "model-inventory" in scopes and "session-resume-fork" in scopes


def test_required_scopes_have_stable_base():
    scopes = required_grounding_scopes(explicit_model=True, has_model_preferences=False, report_mode=None, resume=False)
    assert scopes == ("headless-command", "stdin-closure", "permission-trust", "model-effort-encoding", "output-report-mode", "liveness-signal")
def test_explicit_model_survives_inventory_miss_without_inventory_scope(tmp_path):
    plugin_root, project = _base(tmp_path, {"default_provider": "codex"})
    _record(project, plugin_root, models=[{"id": "provider-default"}])
    result = build_dispatch_context(plugin_root=plugin_root, project=project, role="reader", tier="standard", model="future-model")
    assert result["selection"]["models"][0]["model"] == "future-model"
    assert result["selection"]["models"][0]["source"] == "explicit"
    assert "model-inventory" not in result["grounding"]["required_scopes"]


def test_dispatch_context_is_read_only_and_never_resolves_or_runs_provider(tmp_path, monkeypatch):
    plugin_root, project = _base(tmp_path, {"default_provider": "codex"})
    before = {path: path.read_bytes() for path in project.rglob("*") if path.is_file()}

    def fail(*args, **kwargs):
        raise AssertionError("provider process access")

    monkeypatch.setattr(shutil, "which", fail)
    monkeypatch.setattr(subprocess, "run", fail)
    monkeypatch.setattr(subprocess, "Popen", fail)
    result = build_dispatch_context(plugin_root=plugin_root, project=project, role="reader", tier="standard")
    assert result["next_action"] == "ground_and_record"
    assert {path: path.read_bytes() for path in project.rglob("*") if path.is_file()} == before
    assert not (project / ".swingle").exists()
