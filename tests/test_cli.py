import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "swingle"


def run_cli(*args, env=None):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        env=env,
    )


def test_config_show_returns_machine_readable_effective_configuration(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"default_provider": "codex"}))

    result = run_cli("config", "show", "--config", str(path))

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["layer"] == "env"
    assert payload["config"]["default_provider"] == "codex"


def test_config_show_never_touches_the_provider_directory(tmp_path):
    config = tmp_path / "config.json"
    config.write_text(json.dumps({"default_provider": "codex"}))

    result = run_cli("config", "show", "--config", str(config))

    assert result.returncode == 0
    assert json.loads(result.stdout)["config"]["default_provider"] == "codex"


def test_config_validate_reports_malformed_json(tmp_path):
    path = tmp_path / "config.json"
    path.write_text("{bad")

    result = run_cli("config", "validate", str(path), "--root", str(ROOT))

    assert result.returncode == 1
    assert "errors" in json.loads(result.stdout)


def test_ledger_v2_start_and_show_round_trip(tmp_path):
    ledger_dir = tmp_path / "ledger"
    result = run_cli("ledger", "start", "--dir", str(ledger_dir), "--kind", "direct")

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["controller_session_id"]
    assert payload["run_id"]
    assert payload["ledger_file"] == str((ledger_dir / f"{payload['controller_session_id']}.ndjson").resolve())
    assert payload["events"][0]["event"] == "run-started"

    shown = run_cli("ledger", "show", "--dir", str(ledger_dir))
    assert shown.returncode == 0
    assert json.loads(shown.stdout)["events"][0]["event"] == "run-started"


def test_ledger_legacy_reader_is_read_only(tmp_path):
    path = tmp_path / "ledger.md"
    path.write_text("# Swingle delegation ledger\n\n001 complete: status=DONE outcome=ok\n")

    result = run_cli("ledger", "show", "--legacy-path", str(path), "--format", "json")

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["events"] == [{"schema_version": 1, "raw": "001 complete: status=DONE outcome=ok"}]
    assert payload["warnings"]
    assert result.stderr == ""


def test_ledger_v1_write_commands_are_removed(tmp_path):
    result = run_cli("ledger", "init", "--path", str(tmp_path / "ledger.md"))

    assert result.returncode != 0
    assert "code" not in json.loads(result.stdout)


def test_python_cli_never_runs_provider_binaries(tmp_path):
    marker = tmp_path / "provider-ran"
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for cli in (
        "agy", "claude", "codex", "copilot", "cursor-agent", "devin", "grok", "omp",
        "opencode", "pi",
    ):
        path = bin_dir / cli
        path.write_text(f"#!/bin/sh\ntouch {marker}\n")
        path.chmod(0o755)
    env = dict(os.environ, PATH=f"{bin_dir}:{os.environ['PATH']}")

    config_path = tmp_path / "boundary-config.json"
    grounding_payload = tmp_path / "grounding.json"
    grounding_payload.write_text(json.dumps({
        "complete_profile_observed_at": None,
        "ttl_seconds": 604800,
        "executable": str(bin_dir / "codex"),
        "provider_guidance_sha256": "a" * 64,
        "scopes": {
            "headless-command": {
                "state": "observed",
                "observation": {},
                "applicability": "dispatch",
                "evidence_command": "codex --help",
                "observed_at": "2026-08-24T04:15:30.123Z",
            }
        },
        "models": {"discovery_command": "codex debug models", "observed_at": "2026-08-24T04:15:30.123Z", "entries": []},
    }))
    commands = (
        ("config", "init", "--path", str(config_path)),
        ("config", "show", "--config", str(config_path)),
        ("config", "validate", str(config_path), "--root", str(ROOT)),
        (
            "config", "set", "--path", str(config_path),
            "default_provider", '"codex"', "--root", str(ROOT),
        ),
        ("grounding", "record", "--project", str(tmp_path), "--provider", "codex", "--payload-file", str(grounding_payload)),
        ("grounding", "show", "--project", str(tmp_path), "--provider", "codex"),
        ("grounding", "invalidate", "--project", str(tmp_path), "--provider", "codex", "--scope", "headless-command", "--reason", "test"),
        ("grounding", "refresh", "--project", str(tmp_path), "--provider", "codex", "--scope", "headless-command", "--reason", "test"),
    )
    for command in commands:
        result = run_cli(*command, env=env)
        assert result.returncode == 0, result.stdout + result.stderr
    assert not marker.exists()


def test_invalid_invocation_returns_json_error(tmp_path):
    result = run_cli("config", "set", "--path", str(tmp_path / "config.json"))

    assert result.returncode == 1
    assert result.stderr == ""
    payload = json.loads(result.stdout)
    assert payload["errors"]
    assert "code" not in payload


def test_typed_ledger_error_emits_stable_code(tmp_path):
    result = run_cli(
        "ledger", "record", "run-completed",
        "--dir", str(tmp_path / "ledger"),
        "--controller-session-id", "11111111-1111-4111-8111-111111111111",
        "--run-id", "22222222-2222-4222-8222-222222222222",
        "--job-id", "33333333-3333-4333-8333-333333333333",
    )

    assert result.returncode == 1
    assert result.stderr == ""
    payload = json.loads(result.stdout)
    assert payload["code"] == "ledger_invalid_lifecycle"
    assert payload["errors"]


def test_grounding_cli_reads_stdin_and_returns_next_actions(tmp_path):
    payload = {
        "complete_profile_observed_at": None,
        "ttl_seconds": 604800,
        "executable": "/usr/bin/codex",
        "provider_guidance_sha256": "a" * 64,
        "scopes": {
            "headless-command": {
                "state": "observed",
                "observation": {},
                "applicability": "dispatch",
                "evidence_command": "codex --help",
                "observed_at": "2026-08-24T04:15:30.123Z",
            }
        },
        "models": {"discovery_command": "codex debug models", "observed_at": "2026-08-24T04:15:30.123Z", "entries": []},
    }
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "grounding", "record", "--project", str(tmp_path), "--provider", "codex", "--payload-file", "-"],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert json.loads(result.stdout)["next_action"] == "refresh_context"
    shown = run_cli("grounding", "show", "--project", str(tmp_path), "--provider", "codex")
    assert shown.returncode == 0
    assert json.loads(shown.stdout)["action"] == "ground_and_record"

def test_config_show_expands_user_path(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    path = home / "config.json"
    path.write_text(json.dumps({"default_provider": "codex"}))
    env = dict(os.environ, HOME=str(home))

    result = run_cli(
        "config", "show", "--config", "~/config.json", env=env
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["path"] == str(path.resolve())
    assert payload["config"]["default_provider"] == "codex"
def test_dispatch_context_cli_accepts_liveness_policy_from_stdin(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    (project / ".swingle.json").write_text(json.dumps({"default_provider": "codex"}))
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "dispatch", "context", "--project", str(project), "--role", "reader", "--tier", "standard", "--liveness-policy-file", "-"],
        input=json.dumps({"check_interval_seconds": 9}),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["liveness_policy"]["check_interval_seconds"] == 9
    assert result.stderr == ""


def test_dispatch_context_cli_returns_json_only_and_does_not_run_provider(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    (project / ".swingle.json").write_text(json.dumps({"default_provider": "codex"}))
    marker = tmp_path / "provider-ran"
    executable = tmp_path / "codex"
    executable.write_text(f"#!/bin/sh\ntouch {marker}\n")
    executable.chmod(0o755)
    env = dict(os.environ, PATH=f"{tmp_path}:{os.environ['PATH']}")
    result = run_cli("dispatch", "context", "--project", str(project), "--role", "reader", "--tier", "standard", env=env)
    assert result.returncode == 0
    json.loads(result.stdout)
    assert result.stderr == ""
    assert not marker.exists()
