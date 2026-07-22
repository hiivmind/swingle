import json, subprocess, sys
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
def test_step0_readiness_failure_reported():
    r = run("--step0", "--root", str(FIX / "good-lanes"), "--path-dir", str(FIX / "bins-alpha-notready"), "--role", "per-task reviewer"); assert r.returncode == 1 and "not ready" in r.stdout
