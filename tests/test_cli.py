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


def test_ledger_cli_round_trip(tmp_path):
    path = tmp_path / "ledger.md"

    assert run_cli("ledger", "init", "--path", str(path)).returncode == 0
    assert run_cli(
        "ledger", "append", "--path", str(path),
        "001 allocated: role=reader task=a contract=reader",
    ).returncode == 0
    result = run_cli("ledger", "show", "--path", str(path))

    assert result.returncode == 0
    assert json.loads(result.stdout)["events"] == [
        "001 allocated: role=reader task=a contract=reader"
    ]


def test_python_cli_never_runs_provider_binaries(tmp_path):
    marker = tmp_path / "provider-ran"
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for cli in ("agy", "claude", "codex", "cursor-agent", "devin", "grok", "omp", "opencode", "pi"):
        path = bin_dir / cli
        path.write_text(f"#!/bin/sh\ntouch {marker}\n")
        path.chmod(0o755)
    env = dict(os.environ, PATH=f"{bin_dir}:{os.environ['PATH']}")

    config_path = tmp_path / "boundary-config.json"
    ledger_path = tmp_path / "boundary-ledger.md"
    commands = (
        ("config", "init", "--path", str(config_path)),
        ("config", "show", "--config", str(config_path)),
        ("config", "validate", str(config_path), "--root", str(ROOT)),
        (
            "config", "set", "--path", str(config_path),
            "default_provider", '"codex"', "--root", str(ROOT),
        ),
        ("ledger", "init", "--path", str(ledger_path)),
        (
            "ledger", "append", "--path", str(ledger_path),
            "001 complete: status=DONE outcome=ok",
        ),
        ("ledger", "show", "--path", str(ledger_path)),
    )
    for command in commands:
        result = run_cli(*command, env=env)
        assert result.returncode == 0, result.stdout + result.stderr
    assert not marker.exists()


def test_invalid_invocation_returns_json_error(tmp_path):
    result = run_cli("config", "set", "--path", str(tmp_path / "config.json"))

    assert result.returncode == 1
    assert result.stderr == ""
    assert json.loads(result.stdout)["errors"]


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
