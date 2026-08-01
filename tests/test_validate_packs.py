import json, os, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate-packs"
FIX = Path(__file__).parent / "fixtures"

def isolated_env(**overrides):
    """Build a subprocess environment with ambient Swingle config removed.

    Starts from the current process environment, redirects XDG_CONFIG_HOME at a
    path that deliberately does not exist, drops any inherited SWINGLE_CONFIG
    and SWINGLE_MODELS, then applies caller overrides. An override whose value
    is None removes that variable rather than putting a non-string in the
    environment.
    """
    e = dict(os.environ, XDG_CONFIG_HOME=str(FIX / "no-such-xdg"))
    e.pop("SWINGLE_CONFIG", None)
    e.pop("SWINGLE_MODELS", None)
    for name, value in overrides.items():
        if value is None:
            e.pop(name, None)
        else:
            e[name] = value
    return e

def test_no_such_xdg_fixture_stays_absent():
    """isolated_env's XDG redirect only isolates while this path does not exist."""
    assert not (FIX / "no-such-xdg").exists()

import importlib.machinery, importlib.util, io, contextlib
loader = importlib.machinery.SourceFileLoader("validate_packs", str(SCRIPT))
vp_spec = importlib.util.spec_from_loader("validate_packs", loader)
vp = importlib.util.module_from_spec(vp_spec)
vp_spec.loader.exec_module(vp)

def run(*args):
    return subprocess.run([sys.executable, str(SCRIPT), *args],
                          capture_output=True, text=True, env=isolated_env())

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

def run_env(*args, **env):
    return subprocess.run([sys.executable, str(SCRIPT), *args],
                          capture_output=True, text=True, env=isolated_env(**env))

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
                "--project", str(FIX / "proj-override"), SWINGLE_MODELS=str(env_dir))
    assert r.returncode == 0
    assert "layer: env path=" in r.stdout and "env-review-model" in r.stdout

def test_env_layer_unreadable_stops(tmp_path):
    r = run_env("--root", str(FIX / "good-yaml"), "--resolve", "per-task reviewer", "alpha",
                SWINGLE_MODELS=str(tmp_path / "missing-dir"))
    assert r.returncode == 1 and "SWINGLE_MODELS" in r.stdout

def test_override_not_covering_slot_asks_with_path(tmp_path):
    proj = tmp_path / "proj"; (proj / ".swingle" / "models").mkdir(parents=True)
    (proj / ".swingle" / "models" / "alpha.yaml").write_text(
        "schema: 1\nprovider: alpha\nmodels: []\n")
    r = run_env("--root", str(FIX / "good-yaml"), "--resolve", "per-task reviewer", "alpha",
                "--project", str(proj))
    assert r.returncode == 1
    assert "no eligible model" in r.stdout and "does not cover" in r.stdout

def test_malformed_override_stops_never_falls_through(tmp_path):
    proj = tmp_path / "proj"; (proj / ".swingle" / "models").mkdir(parents=True)
    (proj / ".swingle" / "models" / "alpha.yaml").write_text("models: {broken\n")
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

SDD_MODELS = ROOT / "scripts" / "swingle-models"

def run_models(*args, **env):
    return subprocess.run([sys.executable, str(SDD_MODELS), *args],
                          capture_output=True, text=True, env=isolated_env(**env))

def test_sdd_models_which_default_layer():
    r = run_models("which", "alpha", "--root", str(FIX / "good-yaml"))
    assert r.returncode == 0 and "alpha: layer=default path=" in r.stdout

def test_sdd_models_init_project_seeds_and_refuses_overwrite(tmp_path):
    proj = tmp_path / "proj"; proj.mkdir()
    r = run_models("init", "alpha", "--root", str(FIX / "good-yaml"), "--project", str(proj))
    assert r.returncode == 0
    seeded = proj / ".swingle" / "models" / "alpha.yaml"
    assert seeded.exists() and "cheap-any-model" in seeded.read_text()
    r2 = run_models("init", "alpha", "--root", str(FIX / "good-yaml"), "--project", str(proj))
    assert r2.returncode == 1 and "exists" in (r2.stdout + r2.stderr)
    r3 = run_models("init", "alpha", "--root", str(FIX / "good-yaml"), "--project", str(proj), "--force")
    assert r3.returncode == 0

def test_sdd_models_init_user_layer(tmp_path):
    r = run_models("init", "alpha", "--root", str(FIX / "good-yaml"), "--user",
                   XDG_CONFIG_HOME=str(tmp_path / "xdg"))
    assert r.returncode == 0
    assert (tmp_path / "xdg" / "swingle" / "models" / "alpha.yaml").exists()

def test_codex_manifest_version_mismatch_fails(tmp_path):
    root = tmp_path / "ver-drift"; shutil.copytree(FIX / "good-lanes", root)
    (root / ".claude-plugin").mkdir(); (root / ".codex-plugin").mkdir()
    (root / ".claude-plugin" / "plugin.json").write_text(json.dumps({"version": "2.0.0"}))
    (root / ".codex-plugin" / "plugin.json").write_text(json.dumps({"version": "1.9.9"}))
    (root / "README.md").write_text("**Version:** 2.0.0\n")
    r = run("--root", str(root))
    assert r.returncode == 1 and ".claude-plugin 2.0.0 != .codex-plugin 1.9.9" in r.stdout

def make_health_test_root(tmp_path, providers=("alpha", "beta")):
    root = tmp_path / "root"
    for p in providers:
        pdir = root / "providers" / p
        pdir.mkdir(parents=True)
        (pdir / "pack.md").write_text(
            "---\n"
            f"schema-version: 1\n"
            f"id: {p}\n"
            f"cli: {p}-cli\n"
            "verified-version: 1.0.0\n"
            f'version-argv: ["{p}-cli", "--version"]\n'
            f'resume-argv: ["{p}-cli", "--resume", "{{session_id}}"]\n'
            f'readiness-argv: ["{p}-cli", "--ready"]\n'
            "session-source: conversation-id\n"
            "stall-signal: log-age\n"
            "sandbox: enforced\n"
            "---\n"
        )
        (pdir / "models.yaml").write_text(
            f"schema: 1\nprovider: {p}\nmodels:\n"
            "  - tier: standard\n    lane: implement\n    priority: 1\n"
            f"    model: {p}-model\n    status: verified\n"
        )
        (pdir / "models.md").write_text(f"# {p} models\n")
        (pdir / "verification-log.md").write_text(f"# {p} log\n")
    return root

def test_health_installed_and_uninstalled(tmp_path):
    root = make_health_test_root(tmp_path, ("alpha", "beta"))
    bin_dir = tmp_path / "bin"; bin_dir.mkdir()
    cli = bin_dir / "alpha-cli"
    cli.write_text("#!/bin/sh\nif [ \"$1\" = \"--version\" ]; then echo \"1.0.0\"; else echo \"ready\"; fi\n")
    cli.chmod(0o755)

    r = run("--health", "--root", str(root), "--path-dir", str(bin_dir))
    assert r.returncode == 0
    assert "alpha: installed=yes version=1.0.0 verified=1.0.0 drift=no readiness=ok registry-layer=default" in r.stdout
    assert "beta: installed=no version=- verified=1.0.0 drift=no readiness=skipped registry-layer=default" in r.stdout
    assert "config-layer=none" in r.stdout

def test_health_version_drift(tmp_path):
    root = make_health_test_root(tmp_path, ("alpha",))
    bin_dir = tmp_path / "bin"; bin_dir.mkdir()
    cli = bin_dir / "alpha-cli"
    cli.write_text("#!/bin/sh\nif [ \"$1\" = \"--version\" ]; then echo \"2.0.0\"; else echo \"ready\"; fi\n")
    cli.chmod(0o755)

    r = run("--health", "--root", str(root), "--path-dir", str(bin_dir))
    assert r.returncode == 0
    assert "alpha: installed=yes version=2.0.0 verified=1.0.0 drift=yes readiness=ok registry-layer=default" in r.stdout

def test_health_readiness_fail(tmp_path):
    root = make_health_test_root(tmp_path, ("alpha",))
    bin_dir = tmp_path / "bin"; bin_dir.mkdir()
    cli = bin_dir / "alpha-cli"
    cli.write_text("#!/bin/sh\nif [ \"$1\" = \"--version\" ]; then echo \"1.0.0\"; else exit 1; fi\n")
    cli.chmod(0o755)

    r = run("--health", "--root", str(root), "--path-dir", str(bin_dir))
    assert r.returncode == 0
    assert "alpha: installed=yes version=1.0.0 verified=1.0.0 drift=no readiness=fail registry-layer=default" in r.stdout

def test_health_readiness_timeout(tmp_path, monkeypatch):
    root = make_health_test_root(tmp_path, ("alpha",))
    bin_dir = tmp_path / "bin"; bin_dir.mkdir()
    cli = bin_dir / "alpha-cli"
    cli.write_text(f"#!/bin/sh\nif [ \"$1\" = \"--version\" ]; then echo \"1.0.0\"; else {sys.executable} -c \"import time; time.sleep(2)\"; fi\n")
    cli.chmod(0o755)
    # Warm-up exec: macOS scans a freshly created executable on first exec
    # (~400ms observed), which would push the fast --version probe past the
    # shortened timeout below. Pay that cost outside the timed probes.
    subprocess.run([str(cli), "--version"], capture_output=True)

    monkeypatch.setattr(vp, "HEALTH_PROBE_TIMEOUT_SECONDS", 0.5)

    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        monkeypatch.setattr(sys, "argv", ["validate-packs", "--health", "--root", str(root), "--path-dir", str(bin_dir)])
        exit_code = vp.main()

    output = out.getvalue()
    assert exit_code == 0
    assert "alpha: installed=yes version=1.0.0 verified=1.0.0 drift=no readiness=timeout registry-layer=default" in output

def test_health_version_probe_timeout_reports_no_version(tmp_path, monkeypatch):
    # Regression: a timed-out version probe must report version=-, never a number
    # scraped from the TimeoutExpired message ("timed out after 0.1 seconds"
    # used to yield version=0.1).
    root = make_health_test_root(tmp_path, ("alpha",))
    bin_dir = tmp_path / "bin"; bin_dir.mkdir()
    cli = bin_dir / "alpha-cli"
    cli.write_text(f"#!/bin/sh\n{sys.executable} -c \"import time; time.sleep(2)\"\n")
    cli.chmod(0o755)

    monkeypatch.setattr(vp, "HEALTH_PROBE_TIMEOUT_SECONDS", 0.1)

    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        monkeypatch.setattr(sys, "argv", ["validate-packs", "--health", "--root", str(root), "--path-dir", str(bin_dir)])
        exit_code = vp.main()

    assert exit_code == 0
    assert "alpha: installed=yes version=- verified=1.0.0 drift=yes readiness=timeout registry-layer=default" in out.getvalue()

def test_health_registry_layers(tmp_path):
    root = make_health_test_root(tmp_path, ("alpha",))
    proj = tmp_path / "proj"
    (proj / ".swingle" / "models").mkdir(parents=True)
    (proj / ".swingle" / "models" / "alpha.yaml").write_text(
        "schema: 1\nprovider: alpha\nmodels:\n  - tier: standard\n    lane: implement\n    priority: 1\n    model: proj-model\n    status: verified\n"
    )

    r = run("--health", "--root", str(root), "--project", str(proj))
    assert r.returncode == 0
    assert "alpha: installed=no version=- verified=1.0.0 drift=no readiness=skipped registry-layer=project" in r.stdout

def test_health_config_layers(tmp_path):
    root = make_health_test_root(tmp_path, ("alpha",))

    # none
    r = run_env("--health", "--root", str(root))
    assert r.returncode == 0 and "config-layer=none" in r.stdout

    # project
    proj = tmp_path / "proj"; proj.mkdir()
    (proj / ".swingle.json").write_text("{}")
    r = run_env("--health", "--root", str(root), "--project", str(proj))
    assert r.returncode == 0 and "config-layer=project" in r.stdout

    # user
    xdg = tmp_path / "xdg"
    (xdg / "swingle").mkdir(parents=True)
    (xdg / "swingle" / "config.json").write_text("{}")
    r = run_env("--health", "--root", str(root), XDG_CONFIG_HOME=str(xdg))
    assert r.returncode == 0 and "config-layer=user" in r.stdout

    # env
    cfg = tmp_path / "custom.json"; cfg.write_text("{}")
    r = run_env("--health", "--root", str(root), SWINGLE_CONFIG=str(cfg))
    assert r.returncode == 0 and "config-layer=env" in r.stdout

    # env-unreadable
    r = run_env("--health", "--root", str(root), SWINGLE_CONFIG=str(tmp_path / "missing.json"))
    assert r.returncode == 0 and "config-layer=env-unreadable" in r.stdout


def test_run_ignores_ambient_swingle_config(tmp_path, monkeypatch):
    """A developer's real Swingle config must not reach subprocess tests.

    Sets valid-looking ambient config at all three inputs the production layer
    walk reads, then invokes plain `run`. The subprocess must still report the
    built-in model layer and config-layer=none.
    """
    root = make_health_test_root(tmp_path, ("alpha",))

    ambient_xdg = tmp_path / "ambient-xdg"
    (ambient_xdg / "swingle").mkdir(parents=True)
    (ambient_xdg / "swingle" / "config.json").write_text("{}")

    ambient_cfg = tmp_path / "ambient-config.json"
    ambient_cfg.write_text("{}")

    ambient_models = tmp_path / "ambient-models"; ambient_models.mkdir()
    (ambient_models / "alpha.yaml").write_text(
        "schema: 1\nprovider: alpha\nmodels:\n"
        "  - tier: standard\n    lane: review\n    priority: 1\n"
        "    model: ambient-review-model\n    status: experimental\n")

    monkeypatch.setenv("XDG_CONFIG_HOME", str(ambient_xdg))
    monkeypatch.setenv("SWINGLE_CONFIG", str(ambient_cfg))
    monkeypatch.setenv("SWINGLE_MODELS", str(ambient_models))

    r = run("--health", "--root", str(root))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "config-layer=none" in r.stdout

    r2 = run("--root", str(FIX / "good-yaml"), "--resolve", "per-task reviewer", "alpha")
    assert r2.returncode == 0, r2.stdout + r2.stderr
    assert "layer: default path=" in r2.stdout
    assert "ambient-review-model" not in r2.stdout


def test_health_composes_with_check_config(tmp_path):
    root = make_health_test_root(tmp_path, ("alpha",))
    cfg = tmp_path / "bad.json"; cfg.write_text('{"disable": ["unknown-provider"]}')

    r = run("--health", "--root", str(root), "--check-config", str(cfg))
    assert r.returncode == 1
    assert "disable names unknown provider unknown-provider" in r.stdout
    assert "alpha: installed=no" in r.stdout
    assert "config-layer=none" in r.stdout

def test_health_never_exits_nonzero_for_env_states(tmp_path):
    root = make_health_test_root(tmp_path, ("alpha",))
    bin_dir = tmp_path / "bin"; bin_dir.mkdir()
    cli = bin_dir / "alpha-cli"
    cli.write_text("#!/bin/sh\nif [ \"$1\" = \"--version\" ]; then echo \"9.9.9\"; else exit 1; fi\n")
    cli.chmod(0o755)

    r = run_env("--health", "--root", str(root), "--path-dir", str(bin_dir), SWINGLE_CONFIG=str(tmp_path / "missing.json"))
    assert r.returncode == 0
    assert "alpha: installed=yes version=9.9.9 verified=1.0.0 drift=yes readiness=fail registry-layer=default" in r.stdout
    assert "config-layer=env-unreadable" in r.stdout

def test_health_provider_scoping(tmp_path):
    root = make_health_test_root(tmp_path, ("alpha", "beta"))
    r = run("--health", "--root", str(root), "--provider", "alpha")
    assert r.returncode == 0
    assert "alpha: installed=no" in r.stdout
    assert "beta: installed=no" not in r.stdout
    assert "config-layer=none" in r.stdout

def test_health_detects_cli_on_inherited_path(tmp_path):
    root = make_health_test_root(tmp_path, ("alpha",))
    bin_dir = tmp_path / "bin"; bin_dir.mkdir()
    cli = bin_dir / "alpha-cli"
    cli.write_text("#!/bin/sh\nif [ \"$1\" = \"--version\" ]; then echo \"1.0.0\"; else echo \"ready\"; fi\n")
    cli.chmod(0o755)

    new_path = str(bin_dir) + os.pathsep + os.environ.get("PATH", "")
    r = run_env("--health", "--root", str(root), PATH=new_path)
    assert r.returncode == 0
    assert "alpha: installed=yes version=1.0.0 verified=1.0.0 drift=no readiness=ok registry-layer=default" in r.stdout

def test_config_superpowers_block_accepted():
    r = run("--check-config", str(FIX / "config-superpowers-good.json")); assert r.returncode == 0, r.stdout
def test_config_superpowers_malformed_stops():
    r = run("--check-config", str(FIX / "config-superpowers-malformed.json"))
    assert r.returncode == 1 and "superpowers" in r.stdout
def test_config_superpowers_unknown_provider_fails():
    r = run("--root", str(FIX / "good-lanes"), "--check-config", str(FIX / "config-superpowers-ghost.json"))
    assert r.returncode == 1 and "superpowers names unknown provider ghost" in r.stdout
