import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "swingle"


def run_cli(*args, env=None, cwd=None):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        env=env,
        cwd=cwd,
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


def test_ledger_session_filter_rejects_non_uuid_before_path_access(tmp_path):
    outside = tmp_path / "outside"
    started = run_cli(
        "ledger", "start",
        "--dir", str(outside),
        "--kind", "direct",
        "--controller-session-id", "11111111-1111-4111-8111-111111111111",
    )
    assert started.returncode == 0
    escaped_session = str(outside / "11111111-1111-4111-8111-111111111111")
    selected = tmp_path / "selected"
    selected.mkdir()
    for command in ("show", "validate"):
        result = run_cli(
            "ledger", command,
            "--dir", str(selected),
            "--controller-session-id", escaped_session,
        )
        assert result.returncode == 1
        assert "canonical lowercase UUID" in json.loads(result.stdout)["errors"][0]


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


def test_complete_record_rejects_provider_session_flag(tmp_path):
    result = run_cli(
        "ledger", "record", "complete",
        "--dir", str(tmp_path / "ledger"),
        "--project", str(tmp_path / "project"),
        "--controller-session-id", "11111111-1111-4111-8111-111111111111",
        "--run-id", "22222222-2222-4222-8222-222222222222",
        "--job-id", "33333333-3333-4333-8333-333333333333",
        "--status", "BLOCKED",
        "--outcome", "blocked",
        "--evidence-file", str(tmp_path / "evidence.json"),
        "--completion-file", str(tmp_path / "completion.json"),
        "--provider-session-id", "provider-session",
    )

    assert result.returncode == 1
    assert "unrecognized arguments: --provider-session-id" in json.loads(result.stdout)["errors"][0]


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
def test_record_subparser_rejects_irrelevant_event_flags(tmp_path):
    result = run_cli(
        "ledger", "record", "provider-session",
        "--dir", str(tmp_path / "ledger"),
        "--controller-session-id", "11111111-1111-4111-8111-111111111111",
        "--run-id", "22222222-2222-4222-8222-222222222222",
        "--job-id", "33333333-3333-4333-8333-333333333333",
        "--attempt", "1",
        "--provider-session-id", "session-1",
        "--provider", "codex",
    )
    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert any("unrecognized arguments" in error for error in payload["errors"])


def test_finish_direct_cli_writes_manifest_and_finalizes_run(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    ledger_dir = tmp_path / "ledger"
    dispatch_context = tmp_path / "dispatch-context.json"
    dispatch_context.write_text(json.dumps({
        "grounding_source": "observed",
        "grounding_event": {
            "event": "grounding-observed",
            "data": {
                "receipt_id": None,
                "receipt_revision": None,
                "storage": "none",
                "provider": "codex",
                "cache_path": None,
                "grounded_at": "2026-08-24T04:15:30.123Z",
                "expires_at": None,
                "executable": "/usr/bin/codex",
                "provider_guidance_sha256": "0" * 64,
                "scopes": ["headless-command"],
                "model_count": 0,
                "evidence_commands": ["codex --help"],
            },
        },
        "liveness_policy": {
            "check_interval_seconds": 60,
            "startup_grace_seconds": 300,
            "silence_warning_seconds": 300,
            "hard_timeout_seconds": None,
        },
    }))

    begun = run_cli(
        "ledger", "begin-direct",
        "--project", str(project),
        "--dir", str(ledger_dir),
        "--controller-session-id", "11111111-1111-4111-8111-111111111111",
        "--role", "reader",
        "--contract", "$PLUGIN_ROOT/contracts/reader-contract.md",
        "--tier", "standard",
        "--task", "read",
        "--dispatch-context-file", str(dispatch_context),
        "--provider", "codex",
        "--model", "provider-default",
        "--effort", "none",
    )
    assert begun.returncode == 0, begun.stdout + begun.stderr
    started = json.loads(begun.stdout)
    run_id = started["run_id"]
    job_id = started["job_id"]

    result_file = Path(started["artifact_dir"]) / "result.md"
    result_file.write_text("result\n", encoding="utf-8")

    completion_file = tmp_path / "completion.json"
    completion_file.write_text(json.dumps({
        "provider_outcome": {
            "status": "DONE", "claim": "WRITE_OK", "exit_code": 0,
            "model_requested": "provider-default", "model_used": None, "session_id": None,
            "stop_reason": "end_turn",
            "usage": {"input_tokens": None, "output_tokens": None, "reasoning_tokens": None, "cache_read_tokens": None, "cache_write_tokens": None, "total_tokens": None},
            "cost": None, "result_artifact": str(result_file),
        },
        "repository_verification": {
            "required": False, "status": "NOT_APPLICABLE", "changed_path_count": None,
            "summary": "no repository changes", "verification_artifact": None,
        },
    }))
    evidence_file = tmp_path / "evidence.json"
    evidence_file.write_text(json.dumps([{"kind": "report", "value": "result.md"}]))

    finished = run_cli(
        "ledger", "finish-direct",
        "--project", str(project),
        "--dir", str(ledger_dir),
        "--controller-session-id", "11111111-1111-4111-8111-111111111111",
        "--run-id", run_id,
        "--job-id", job_id,
        "--status", "DONE",
        "--outcome", "result",
        "--evidence-file", str(evidence_file),
        "--completion-file", str(completion_file),
    )
    assert finished.returncode == 0, finished.stdout + finished.stderr
    payload = json.loads(finished.stdout)
    assert [event["event"] for event in payload["events"]] == ["complete", "run-completed"]

    manifest_path = Path(started["artifact_dir"]) / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    assert manifest["files"] == [{
        "path": "result.md",
        "size_bytes": len(b"result\n"),
        "sha256": hashlib.sha256(b"result\n").hexdigest(),
    }]
    assert manifest["provider"] == "codex"
    assert manifest["terminal_status"] == "DONE"


def test_record_complete_cli_missing_project_reports_stable_error(tmp_path):
    result = run_cli(
        "ledger", "record", "complete",
        "--dir", str(tmp_path / "ledger"),
        "--controller-session-id", "11111111-1111-4111-8111-111111111111",
        "--run-id", "22222222-2222-4222-8222-222222222222",
        "--job-id", "33333333-3333-4333-8333-333333333333",
        "--status", "DONE",
        "--outcome", "result",
        "--evidence-file", str(tmp_path / "evidence.json"),
        "--completion-file", str(tmp_path / "completion.json"),
    )
    assert result.returncode == 1
    assert "--project" in json.loads(result.stdout)["errors"][0]


def _begin_and_finish_via_cli(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    ledger_dir = project / ".swingle" / "delegate" / "ledger"
    dispatch_context = tmp_path / "dispatch-context.json"
    dispatch_context.write_text(json.dumps({
        "grounding_source": "observed",
        "grounding_event": {
            "event": "grounding-observed",
            "data": {
                "receipt_id": None, "receipt_revision": None, "storage": "none", "provider": "codex",
                "cache_path": None, "grounded_at": "2026-08-24T04:15:30.123Z", "expires_at": None,
                "executable": "/usr/bin/codex", "provider_guidance_sha256": "0" * 64,
                "scopes": ["headless-command"], "model_count": 0, "evidence_commands": ["codex --help"],
            },
        },
        "liveness_policy": {"check_interval_seconds": 60, "startup_grace_seconds": 300, "silence_warning_seconds": 300, "hard_timeout_seconds": None},
    }))
    begun = run_cli(
        "ledger", "begin-direct",
        "--project", str(project), "--dir", str(ledger_dir),
        "--controller-session-id", "11111111-1111-4111-8111-111111111111",
        "--role", "reader", "--contract", "$PLUGIN_ROOT/contracts/reader-contract.md",
        "--tier", "standard", "--task", "read",
        "--dispatch-context-file", str(dispatch_context),
        "--provider", "codex", "--model", "provider-default", "--effort", "none",
    )
    assert begun.returncode == 0, begun.stdout + begun.stderr
    started = json.loads(begun.stdout)
    (Path(started["artifact_dir"]) / "result.md").write_text("result\n", encoding="utf-8")

    completion_file = tmp_path / "completion.json"
    completion_file.write_text(json.dumps({
        "provider_outcome": {
            "status": "DONE", "claim": "WRITE_OK", "exit_code": 0,
            "model_requested": "provider-default", "model_used": None, "session_id": None,
            "stop_reason": "end_turn",
            "usage": {"input_tokens": None, "output_tokens": None, "reasoning_tokens": None, "cache_read_tokens": None, "cache_write_tokens": None, "total_tokens": None},
            "cost": None, "result_artifact": str(Path(started["artifact_dir"]) / "result.md"),
        },
        "repository_verification": {
            "required": False, "status": "NOT_APPLICABLE", "changed_path_count": None,
            "summary": "no repository changes", "verification_artifact": None,
        },
    }))
    evidence_file = tmp_path / "evidence.json"
    evidence_file.write_text(json.dumps([{"kind": "report", "value": "result.md"}]))
    finished = run_cli(
        "ledger", "finish-direct",
        "--project", str(project), "--dir", str(ledger_dir),
        "--controller-session-id", "11111111-1111-4111-8111-111111111111",
        "--run-id", started["run_id"], "--job-id", started["job_id"],
        "--status", "DONE", "--outcome", "result",
        "--evidence-file", str(evidence_file), "--completion-file", str(completion_file),
    )
    assert finished.returncode == 0, finished.stdout + finished.stderr
    return project, started["run_id"], started["job_id"]


def test_workspace_show_cli_json_reports_manifest_state(tmp_path):
    project, run_id, job_id = _begin_and_finish_via_cli(tmp_path)

    result = run_cli("workspace", "show", "--run", run_id, "--json", cwd=str(project))

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["job_ids"] == [job_id]
    assert payload["jobs"][0]["manifest_state"] == "terminal"
    assert payload["errors"] == []


def test_workspace_show_cli_text_output_by_default(tmp_path):
    project, run_id, job_id = _begin_and_finish_via_cli(tmp_path)

    result = run_cli("workspace", "show", "--run", run_id, cwd=str(project))

    assert result.returncode == 0, result.stdout + result.stderr
    assert job_id in result.stdout
    with pytest.raises(json.JSONDecodeError):
        json.loads(result.stdout)


def test_workspace_verify_cli_json_reports_valid_job_scope(tmp_path):
    project, run_id, job_id = _begin_and_finish_via_cli(tmp_path)

    result = run_cli("workspace", "verify", "--run", run_id, "--job", job_id, "--json", cwd=str(project))

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["valid"] is True
    assert payload["verified_files"] == 1


def test_workspace_cli_reports_stable_error_code_for_unknown_run(tmp_path):
    project, _run_id, _job_id = _begin_and_finish_via_cli(tmp_path)

    result = run_cli("workspace", "show", "--run", "99999999-9999-4999-8999-999999999999", "--json", cwd=str(project))

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["code"] == "run_not_found"


def test_workspace_show_cli_rejects_escaping_file_path(tmp_path):
    project, run_id, job_id = _begin_and_finish_via_cli(tmp_path)

    result = run_cli("workspace", "show", "--run", run_id, "--job", job_id, "--file", "../result.md", "--json", cwd=str(project))

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["code"] == "path_escape"


def test_workspace_copy_cli_publishes_destination(tmp_path):
    project, run_id, job_id = _begin_and_finish_via_cli(tmp_path)
    destination = tmp_path / "dest"

    result = run_cli("workspace", "copy", "--run", run_id, "--to", str(destination), "--json", cwd=str(project))

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "copied"
    assert payload["job_ids"] == [job_id]
    assert (destination / "ledger.ndjson").is_file()
    assert (destination / "artifacts" / run_id / job_id / "manifest.json").is_file()
    assert (destination / "artifacts" / run_id / job_id / "result.md").read_bytes() == b"result\n"
    assert payload["errors"] == []


def test_workspace_copy_cli_text_output_by_default(tmp_path):
    project, run_id, job_id = _begin_and_finish_via_cli(tmp_path)
    destination = tmp_path / "dest"

    result = run_cli("workspace", "copy", "--run", run_id, "--to", str(destination), cwd=str(project))

    assert result.returncode == 0, result.stdout + result.stderr
    assert "copied" in result.stdout
    with pytest.raises(json.JSONDecodeError):
        json.loads(result.stdout)


def test_workspace_copy_cli_conflict_reports_stable_code_and_changes_nothing(tmp_path):
    project, run_id, job_id = _begin_and_finish_via_cli(tmp_path)
    destination = tmp_path / "dest"
    destination.mkdir()
    (destination / "unexpected.txt").write_bytes(b"pre-existing")

    result = run_cli("workspace", "copy", "--run", run_id, "--to", str(destination), "--json", cwd=str(project))

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["code"] == "copy_conflict"
    assert (destination / "unexpected.txt").read_bytes() == b"pre-existing"


def test_workspace_show_to_cli_reports_absent_identical_and_conflict(tmp_path):
    project, run_id, job_id = _begin_and_finish_via_cli(tmp_path)
    destination = tmp_path / "dest"

    absent = run_cli("workspace", "show", "--run", run_id, "--to", str(destination), "--json", cwd=str(project))
    assert absent.returncode == 0, absent.stdout + absent.stderr
    assert json.loads(absent.stdout)["destination_state"] == "absent"

    copied = run_cli("workspace", "copy", "--run", run_id, "--job", job_id, "--to", str(destination), "--json", cwd=str(project))
    assert copied.returncode == 0, copied.stdout + copied.stderr

    identical = run_cli("workspace", "show", "--run", run_id, "--to", str(destination), "--json", cwd=str(project))
    assert identical.returncode == 0, identical.stdout + identical.stderr
    assert json.loads(identical.stdout)["destination_state"] == "identical"

    (destination / "extra.txt").write_bytes(b"x")
    conflict = run_cli("workspace", "show", "--run", run_id, "--to", str(destination), "--json", cwd=str(project))
    assert conflict.returncode == 0, conflict.stdout + conflict.stderr
    assert json.loads(conflict.stdout)["destination_state"] == "conflict"


def test_workspace_copy_cli_rejects_destination_inside_workspace(tmp_path):
    project, run_id, job_id = _begin_and_finish_via_cli(tmp_path)
    inside = project / ".swingle" / "delegate" / "somewhere"

    result = run_cli("workspace", "copy", "--run", run_id, "--job", job_id, "--to", str(inside), "--json", cwd=str(project))

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["code"] == "destination_inside_workspace"
    assert not inside.exists()


def test_workspace_delete_cli_preview_reports_selection_and_digest(tmp_path):
    project, run_id, job_id = _begin_and_finish_via_cli(tmp_path)

    result = run_cli("workspace", "delete", "--run", run_id, "--json", cwd=str(project))

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["applied"] is False
    assert payload["selection_sha256"]
    paths = {item["path"] for item in payload["files"]}
    assert paths == {f"{job_id}/manifest.json", f"{job_id}/result.md"}
    job_dir = Path(project) / ".swingle" / "delegate" / "artifacts" / run_id / job_id
    assert (job_dir / "result.md").exists()


def test_workspace_delete_cli_apply_deletes_selection(tmp_path):
    project, run_id, job_id = _begin_and_finish_via_cli(tmp_path)
    preview = run_cli("workspace", "delete", "--run", run_id, "--json", cwd=str(project))
    digest = json.loads(preview.stdout)["selection_sha256"]

    result = run_cli(
        "workspace", "delete", "--run", run_id,
        "--expect-selection-sha256", digest, "--apply", "--json", cwd=str(project),
    )

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["applied"] is True
    assert payload["deleted_files"] == 2
    run_dir = Path(project) / ".swingle" / "delegate" / "artifacts" / run_id
    assert not run_dir.exists()
    ledger_file = next((Path(project) / ".swingle" / "delegate" / "ledger").glob("*.ndjson"))
    assert ledger_file.exists()


def test_workspace_delete_cli_apply_requires_expect_selection_sha256(tmp_path):
    project, run_id, job_id = _begin_and_finish_via_cli(tmp_path)

    result = run_cli("workspace", "delete", "--run", run_id, "--apply", "--json", cwd=str(project))

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert "code" not in payload
    assert payload["errors"]
    job_dir = Path(project) / ".swingle" / "delegate" / "artifacts" / run_id / job_id
    assert (job_dir / "result.md").exists()


def test_workspace_delete_cli_expect_selection_sha256_requires_apply(tmp_path):
    project, run_id, job_id = _begin_and_finish_via_cli(tmp_path)

    result = run_cli(
        "workspace", "delete", "--run", run_id,
        "--expect-selection-sha256", "0" * 64, "--json", cwd=str(project),
    )

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert "code" not in payload
    assert payload["errors"]


def test_workspace_delete_cli_text_output_by_default(tmp_path):
    project, run_id, job_id = _begin_and_finish_via_cli(tmp_path)

    result = run_cli("workspace", "delete", "--run", run_id, cwd=str(project))

    assert result.returncode == 0, result.stdout + result.stderr
    assert "applied=false" in result.stdout
    with pytest.raises(json.JSONDecodeError):
        json.loads(result.stdout)
