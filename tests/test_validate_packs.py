import json, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate-packs"
FIX = Path(__file__).parent / "fixtures"

def run(*args):
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True)

def test_real_tree_valid():
    r = run("--root", str(ROOT)); assert r.returncode == 0, r.stdout + r.stderr
def test_missing_p1_fails():
    r = run("--root", str(FIX / "bad-missing-p1")); assert r.returncode == 1 and "priority 1" in r.stdout
def test_duplicate_priority_fails():
    r = run("--root", str(FIX / "bad-dup-priority")); assert r.returncode == 1 and "duplicate priority" in r.stdout
def test_shell_string_manifest_fails():
    r = run("--root", str(FIX / "bad-shell-detect")); assert r.returncode == 1 and "argv" in r.stdout
def test_id_dirname_mismatch_fails():
    r = run("--root", str(FIX / "bad-id-mismatch")); assert r.returncode == 1 and "id" in r.stdout
def test_resolve_exact_lane_beats_any():
    r = run("--root", str(FIX / "good-lanes"), "--resolve", "per-task reviewer", "alpha"); assert r.returncode == 0 and "review-model-exact" in r.stdout
def test_resolve_any_fallback():
    r = run("--root", str(FIX / "good-lanes"), "--resolve", "transcription implementer", "alpha"); assert r.returncode == 0 and "cheap-any-model" in r.stdout
def test_resolve_rejected_never():
    r = run("--root", str(FIX / "bad-rejected-only"), "--resolve", "per-task reviewer", "alpha"); assert r.returncode == 1 and "no eligible" in r.stdout
def test_config_malformed_fails_closed():
    r = run("--check-config", str(FIX / "config-malformed.json")); assert r.returncode == 1
def test_config_disabled_default_fails():
    r = run("--check-config", str(FIX / "config-disabled-default.json")); assert r.returncode == 1 and "default_provider" in r.stdout
def test_argv0_mismatch_fails():
    r = run("--root", str(FIX / "bad-argv0")); assert r.returncode == 1 and "argv[0]" in r.stdout
def test_shell_metachar_argv_fails():
    r = run("--root", str(FIX / "bad-metachar")); assert r.returncode == 1 and "metacharacter" in r.stdout
def test_exclusion_advances_fallback():
    r = run("--root", str(FIX / "good-lanes"), "--resolve", "per-task reviewer", "alpha", "--exclude", "alpha:review-model-exact"); assert r.returncode == 0 and "review-model-any" in r.stdout
def test_step0_detection_and_routing():
    r = run("--step0", "--root", str(FIX / "good-lanes"), "--path-dir", str(FIX / "bins-alpha")); assert r.returncode == 0 and "active: alpha" in r.stdout
def test_step0_no_providers_installed():
    r = run("--step0", "--root", str(FIX / "good-lanes"), "--path-dir", str(FIX / "bins-empty")); assert r.returncode == 1 and "no active providers" in r.stdout
def test_step0_native_subagents_bypasses():
    r = run("--step0", "--root", str(FIX / "good-lanes"), "--path-dir", str(FIX / "bins-alpha"), "--lever", "native-subagents"); assert r.returncode == 0 and "native-subagents: bypass" in r.stdout
def test_config_disabled_lane_target_fails():
    r = run("--check-config", str(FIX / "config-disabled-lane.json")); assert r.returncode == 1 and "providers_by_lane" in r.stdout
def test_config_unknown_provider_ids_fail_closed():
    r = run("--root", str(FIX / "good-lanes"), "--check-config", str(FIX / "config-unknown-provider.json"))
    assert r.returncode == 1
    assert "disable names unknown provider ghost-disable" in r.stdout
    assert "default_provider names unknown provider ghost-default" in r.stdout
    assert "providers_by_lane[review] names unknown provider ghost-lane" in r.stdout
def test_interpreter_cli_denied():
    r = run("--root", str(FIX / "bad-interpreter-cli")); assert r.returncode == 1 and "interpreter" in r.stdout
def test_empty_argv_fails():
    r = run("--root", str(FIX / "bad-empty-argv")); assert r.returncode == 1 and "empty" in r.stdout
def test_strict_grammar_rejects_bad_lines():
    r = run("--root", str(FIX / "bad-grammar")); assert r.returncode == 1 and "grammar" in r.stdout
def test_fallback_order_exact_then_any():
    r = run("--root", str(FIX / "good-lanes"), "--resolve", "per-task reviewer", "alpha"); assert "fallback order: review-model-exact, review-model-any" in r.stdout
def test_step0_multi_active_no_policy_asks():
    r = run("--step0", "--root", str(FIX / "good-two-providers"), "--path-dir", str(FIX / "bins-two"), "--role", "per-task reviewer"); assert r.returncode == 1 and "ask user" in r.stdout
def test_step0_lane_routing_and_resolution():
    r = run("--step0", "--root", str(FIX / "good-two-providers"), "--path-dir", str(FIX / "bins-two"), "--config", str(FIX / "config-lane-beta.json"), "--role", "per-task reviewer"); assert r.returncode == 0 and "provider: beta" in r.stdout and "model:" in r.stdout
def test_step0_version_mismatch_blocks_when_required():
    r = run("--step0", "--root", str(FIX / "good-lanes"), "--path-dir", str(FIX / "bins-alpha-oldver"), "--config", str(FIX / "config-require-version.json"), "--role", "per-task reviewer"); assert r.returncode == 1 and "incompatible" in r.stdout
def test_step0_version_mismatch_warns_but_remains_active_without_strict_mode():
    r = run("--step0", "--root", str(FIX / "good-lanes"), "--path-dir", str(FIX / "bins-alpha-oldver"), "--role", "per-task reviewer")
    assert r.returncode == 0
    assert "warning: incompatible: alpha" in r.stdout
    assert "active: alpha" in r.stdout
def test_step0_readiness_failure_reported():
    r = run("--step0", "--root", str(FIX / "good-lanes"), "--path-dir", str(FIX / "bins-alpha-notready"), "--role", "per-task reviewer"); assert r.returncode == 1 and "not ready" in r.stdout
def test_step0_invalid_manifest_never_detects_or_executes_provider_argv(tmp_path):
    root = tmp_path / "bad-pack"; shutil.copytree(FIX / "bad-interpreter-cli", root)
    bin_dir = tmp_path / "bin"; bin_dir.mkdir(); marker = tmp_path / "executed"
    executable = bin_dir / "sh"
    executable.write_text(f"#!/bin/sh\nprintf executed > {marker}\n")
    executable.chmod(0o755)
    r = run("--step0", "--root", str(root), "--path-dir", str(bin_dir))
    assert r.returncode == 1 and "interpreter" in r.stdout
    assert "installed:" not in r.stdout
    assert not marker.exists()
def test_yaml_rejects_bad_tier(tmp_path):
    root = tmp_path / "bad-tier"; shutil.copytree(FIX / "good-lanes", root)
    models = root / "providers" / "alpha" / "models.yaml"
    models.write_text(models.read_text() + "  - tier: premium\n    lane: review\n    priority: 2\n    model: invalid-tier\n    status: verified\n")
    r = run("--root", str(root))
    assert r.returncode == 1 and "bad tier premium" in r.stdout
def test_link_scan_checks_relative_target_beginning_with_p(tmp_path):
    root = tmp_path / "bad-link"; shutil.copytree(FIX / "good-lanes", root)
    models = root / "providers" / "alpha" / "models.md"
    models.write_text(models.read_text() + "[missing](providers/missing.md)\n")
    r = run("--root", str(root))
    assert r.returncode == 1 and "broken link providers/missing.md" in r.stdout
def test_step0_native_bypass_ignores_malformed_config():
    r = run("--step0", "--root", str(FIX / "good-lanes"),
            "--path-dir", str(FIX / "bins-alpha"), "--lever", "native-subagents",
            "--config", str(FIX / "config-malformed.json"))
    assert r.returncode == 0 and "native-subagents: bypass" in r.stdout

def test_yaml_pack_valid_and_resolvable():
    r = run("--root", str(FIX / "good-yaml"), "--resolve", "per-task reviewer", "alpha")
    assert r.returncode == 0 and "review-model-exact" in r.stdout

def test_yaml_unknown_row_key_fails():
    r = run("--root", str(FIX / "bad-yaml-unknown-key"))
    assert r.returncode == 1 and "unknown row key" in r.stdout

def test_yaml_bad_schema_or_provider_fails():
    r = run("--root", str(FIX / "bad-yaml-schema"))
    assert r.returncode == 1 and "schema" in r.stdout and "provider" in r.stdout

def test_yaml_pack_clean_tree_passes():
    r = run("--root", str(FIX / "good-yaml"))
    assert r.returncode == 0

def test_yaml_eligible_md_row_guard(tmp_path):
    import shutil as _sh
    root = tmp_path / "drift"; _sh.copytree(FIX / "good-yaml", root)
    md = root / "providers" / "alpha" / "models.md"
    md.write_text(md.read_text() +
        "\n| cheapest | any | 9 | sneaky-model | verified | - | drift |\n")
    r = run("--root", str(root))
    assert r.returncode == 1 and "eligible-row guard" in r.stdout

import os

def run_env(*args, **env):
    e = dict(os.environ, XDG_CONFIG_HOME=str(FIX / "no-such-xdg"))
    e.pop("SDD_DISPATCH_MODELS", None)
    e.update(env)
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, env=e)

def test_resolve_default_layer_line():
    r = run_env("--root", str(FIX / "good-yaml"), "--resolve", "per-task reviewer", "alpha")
    assert r.returncode == 0
    assert "layer: default path=" in r.stdout and "models.yaml" in r.stdout

def test_resolve_project_layer_wins():
    r = run_env("--root", str(FIX / "good-yaml"), "--resolve", "per-task reviewer", "alpha",
                "--project", str(FIX / "proj-override"))
    assert r.returncode == 0
    assert "layer: project path=" in r.stdout and "project-review-model" in r.stdout

def test_resolve_env_layer_beats_project(tmp_path):
    env_dir = tmp_path / "envmodels"; env_dir.mkdir()
    (env_dir / "alpha.yaml").write_text(
        "schema: 1\nprovider: alpha\nmodels:\n"
        "  - tier: standard\n    lane: review\n    priority: 1\n"
        "    model: env-review-model\n    status: experimental\n")
    r = run_env("--root", str(FIX / "good-yaml"), "--resolve", "per-task reviewer", "alpha",
                "--project", str(FIX / "proj-override"), SDD_DISPATCH_MODELS=str(env_dir))
    assert r.returncode == 0
    assert "layer: env path=" in r.stdout and "env-review-model" in r.stdout

def test_env_layer_unreadable_stops(tmp_path):
    r = run_env("--root", str(FIX / "good-yaml"), "--resolve", "per-task reviewer", "alpha",
                SDD_DISPATCH_MODELS=str(tmp_path / "missing-dir"))
    assert r.returncode == 1 and "SDD_DISPATCH_MODELS" in r.stdout

def test_override_not_covering_slot_asks_with_path(tmp_path):
    proj = tmp_path / "proj"; (proj / ".sdd-dispatch" / "models").mkdir(parents=True)
    (proj / ".sdd-dispatch" / "models" / "alpha.yaml").write_text(
        "schema: 1\nprovider: alpha\nmodels: []\n")
    r = run_env("--root", str(FIX / "good-yaml"), "--resolve", "per-task reviewer", "alpha",
                "--project", str(proj))
    assert r.returncode == 1
    assert "no eligible model" in r.stdout and "does not cover" in r.stdout

def test_malformed_override_stops_never_falls_through(tmp_path):
    proj = tmp_path / "proj"; (proj / ".sdd-dispatch" / "models").mkdir(parents=True)
    (proj / ".sdd-dispatch" / "models" / "alpha.yaml").write_text("models: {broken\n")
    r = run_env("--root", str(FIX / "good-yaml"), "--resolve", "per-task reviewer", "alpha",
                "--project", str(proj))
    assert r.returncode == 1 and "layer: default" not in r.stdout

def test_yaml_accepts_apostrophe_in_double_quoted_scalar(tmp_path):
    root = tmp_path / "apos"; shutil.copytree(FIX / "good-yaml", root)
    yaml = root / "providers" / "alpha" / "models.yaml"
    text = yaml.read_text()
    yaml.write_text(text.replace('"test row"', '"it\'s fine"'))
    r = run("--root", str(root))
    assert r.returncode == 0

def test_yaml_rejects_single_quoted_scalar(tmp_path):
    root = tmp_path / "sq"; shutil.copytree(FIX / "good-yaml", root)
    yaml = root / "providers" / "alpha" / "models.yaml"
    text = yaml.read_text()
    yaml.write_text(text.replace('review-model-exact', "'single-quoted-value'"))
    r = run("--root", str(root))
    assert r.returncode == 1 and "single-quoted" in r.stdout

def test_list_models_argv_accepted_and_validated(tmp_path):
    import shutil as _sh
    root = tmp_path / "lm"; _sh.copytree(FIX / "good-yaml", root)
    pack = root / "providers" / "alpha" / "pack.md"
    pack.write_text(pack.read_text().replace(
        "sandbox: enforced\n---",
        'sandbox: enforced\nlist-models-argv: ["alpha", "--list-models"]\n---', 1))
    assert run("--root", str(root)).returncode == 0
    pack.write_text(pack.read_text().replace(
        '["alpha", "--list-models"]', '["wrong-cli", "--list-models"]'))
    r = run("--root", str(root))
    assert r.returncode == 1 and "argv[0]" in r.stdout

SDD_MODELS = ROOT / "scripts" / "sdd-models"

def run_models(*args, **env):
    e = dict(os.environ, XDG_CONFIG_HOME=str(FIX / "no-such-xdg"))
    e.pop("SDD_DISPATCH_MODELS", None)
    e.update(env)
    return subprocess.run([sys.executable, str(SDD_MODELS), *args], capture_output=True, text=True, env=e)

def test_sdd_models_which_default_layer():
    r = run_models("which", "alpha", "--root", str(FIX / "good-yaml"))
    assert r.returncode == 0 and "alpha: layer=default path=" in r.stdout

def test_sdd_models_init_project_seeds_and_refuses_overwrite(tmp_path):
    proj = tmp_path / "proj"; proj.mkdir()
    r = run_models("init", "alpha", "--root", str(FIX / "good-yaml"), "--project", str(proj))
    assert r.returncode == 0
    seeded = proj / ".sdd-dispatch" / "models" / "alpha.yaml"
    assert seeded.exists() and "cheap-any-model" in seeded.read_text()
    r2 = run_models("init", "alpha", "--root", str(FIX / "good-yaml"), "--project", str(proj))
    assert r2.returncode == 1 and "exists" in (r2.stdout + r2.stderr)
    r3 = run_models("init", "alpha", "--root", str(FIX / "good-yaml"), "--project", str(proj), "--force")
    assert r3.returncode == 0

def test_sdd_models_init_user_layer(tmp_path):
    r = run_models("init", "alpha", "--root", str(FIX / "good-yaml"), "--user",
                   XDG_CONFIG_HOME=str(tmp_path / "xdg"))
    assert r.returncode == 0
    assert (tmp_path / "xdg" / "sdd-dispatch" / "models" / "alpha.yaml").exists()

def test_codex_manifest_version_mismatch_fails(tmp_path):
    root = tmp_path / "ver-drift"; shutil.copytree(FIX / "good-lanes", root)
    (root / ".claude-plugin").mkdir(); (root / ".codex-plugin").mkdir()
    (root / ".claude-plugin" / "plugin.json").write_text(json.dumps({"version": "2.0.0"}))
    (root / ".codex-plugin" / "plugin.json").write_text(json.dumps({"version": "1.9.9"}))
    (root / "README.md").write_text("**Version:** 2.0.0\n")
    r = run("--root", str(root))
    assert r.returncode == 1 and ".claude-plugin 2.0.0 != .codex-plugin 1.9.9" in r.stdout

