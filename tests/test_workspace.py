from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from swingle.errors import LedgerLifecycleError, WorkspaceError
from swingle.ledger import append_events, finalize_run, record_complete
from swingle.ledger_schema import EventDraft
from swingle.workspace import discover_repository_root, show_workspace, verify_workspace

SESSION = "11111111-1111-4111-8111-111111111111"
OTHER_SESSION = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
RUN = "22222222-2222-4222-8222-222222222222"
JOB = "33333333-3333-4333-8333-333333333333"
OTHER_JOB = "55555555-5555-4555-8555-555555555555"
OTHER_RUN = "66666666-6666-4666-8666-666666666666"


def draft(event, *, session=SESSION, run=RUN, job=None, data=None):
    return EventDraft(event, session, run, job, {} if data is None else data)


def _dispatched(*, run=RUN, job=JOB, provider="codex"):
    return draft(
        "dispatched",
        run=run,
        job=job,
        data={
            "provider": provider,
            "model": "provider-default",
            "effort": "none",
            "attempt": 1,
            "liveness_policy": {
                "check_interval_seconds": 60,
                "startup_grace_seconds": 300,
                "silence_warning_seconds": 300,
                "hard_timeout_seconds": None,
            },
            "grounding_receipt_id": "44444444-4444-4444-8444-444444444444",
            "grounding_receipt_revision": None,
            "grounding_source": "reused",
        },
    )


def _provider_outcome(status="DONE", exit_code=0):
    return {
        "status": status, "claim": "WRITE_OK", "exit_code": exit_code,
        "model_requested": "provider-default", "model_used": None, "session_id": None,
        "stop_reason": "end_turn",
        "usage": {"input_tokens": None, "output_tokens": None, "reasoning_tokens": None, "cache_read_tokens": None, "cache_write_tokens": None, "total_tokens": None},
        "cost": None, "result_artifact": "$REPO_ROOT/.swingle/delegate/artifacts/run/job/result.md",
    }


def _repo_outcome(required=False, status="NOT_APPLICABLE", count=None):
    return {
        "required": required, "status": status, "changed_path_count": count,
        "summary": "no repository changes", "verification_artifact": None,
    }


@dataclass
class WorkspaceRun:
    repo: Path
    ledger_dir: Path
    run_id: str
    job_id: str
    controller_session_id: str
    run_dir: Path
    job_dir: Path


def _allocate(repo: Path, ledger_dir: Path, *, run_id=RUN, job_id=JOB, session=SESSION) -> Path:
    append_events(
        ledger_dir,
        session,
        [
            draft("run-started", session=session, run=run_id, data={"kind": "batch"}),
            draft("allocated", session=session, run=run_id, job=job_id, data={"role": "reader", "contract": "$PLUGIN_ROOT/contracts/reader-contract.md", "tier": "standard", "task": "read"}),
        ],
    )
    job_dir = repo / ".swingle" / "delegate" / "artifacts" / run_id / job_id
    job_dir.mkdir(parents=True)
    return job_dir


def _finalize(repo: Path, ledger_dir: Path, *, run_id=RUN, job_id=JOB, session=SESSION, status="DONE", provider="codex"):
    append_events(ledger_dir, session, [_dispatched(run=run_id, job=job_id, provider=provider)])
    return record_complete(
        project=repo, ledger_dir=ledger_dir, controller_session_id=session, run_id=run_id, job_id=job_id,
        provider_outcome=_provider_outcome(status), repository_verification=_repo_outcome(),
        outcome="result", evidence=[{"kind": "report", "value": "result.md"}],
    )


@pytest.fixture
def workspace_run(tmp_path) -> WorkspaceRun:
    repo = tmp_path / "repo"
    repo.mkdir()
    ledger_dir = repo / ".swingle" / "delegate" / "ledger"
    job_dir = _allocate(repo, ledger_dir)
    (job_dir / "result.md").write_bytes(b"result\n")
    _finalize(repo, ledger_dir)
    return WorkspaceRun(
        repo=repo,
        ledger_dir=ledger_dir,
        run_id=RUN,
        job_id=JOB,
        controller_session_id=SESSION,
        run_dir=repo / ".swingle" / "delegate" / "artifacts" / RUN,
        job_dir=job_dir,
    )


# --- repository discovery -----------------------------------------------------


def test_workspace_discovery_starts_at_controller_cwd(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    nested = repo / "a" / "b"
    nested.mkdir(parents=True)
    monkeypatch.chdir(nested)

    assert discover_repository_root() == repo


def test_workspace_discovery_prefers_existing_workspace_over_git(tmp_path):
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    nested_repo = repo / "vendor" / "nested"
    (nested_repo / ".swingle" / "delegate").mkdir(parents=True)
    (nested_repo / "sub").mkdir()

    assert discover_repository_root(nested_repo / "sub") == nested_repo


def test_workspace_discovery_rejects_when_neither_marker_exists(tmp_path):
    isolated = tmp_path / "isolated"
    isolated.mkdir()

    with pytest.raises(WorkspaceError) as error:
        discover_repository_root(isolated)

    assert error.value.code == "workspace_not_found"


# --- run/job selection ---------------------------------------------------------


def test_run_selection_comes_from_ledger_not_directory_listing(workspace_run):
    orphan = workspace_run.run_dir / OTHER_JOB
    orphan.mkdir()

    result = show_workspace(run_id=workspace_run.run_id, cwd=workspace_run.repo)

    assert result["job_ids"] == [workspace_run.job_id]
    assert result["orphan_artifact_directories"] == [str(orphan)]


def test_show_reports_missing_workspace(tmp_path):
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)

    with pytest.raises(WorkspaceError) as error:
        show_workspace(run_id=RUN, cwd=repo)

    assert error.value.code == "workspace_not_found"


def test_show_reports_unknown_run(workspace_run):
    with pytest.raises(WorkspaceError) as error:
        show_workspace(run_id=OTHER_RUN, cwd=workspace_run.repo)

    assert error.value.code == "run_not_found"


def test_show_reports_job_outside_the_run(workspace_run):
    with pytest.raises(WorkspaceError) as error:
        show_workspace(run_id=workspace_run.run_id, job_id=OTHER_JOB, cwd=workspace_run.repo)

    assert error.value.code == "job_not_found"


def test_show_rejects_duplicate_run_identity_across_session_ledgers(workspace_run):
    _allocate(workspace_run.repo, workspace_run.ledger_dir, run_id=workspace_run.run_id, job_id=OTHER_JOB, session=OTHER_SESSION)

    with pytest.raises(LedgerLifecycleError):
        show_workspace(run_id=workspace_run.run_id, cwd=workspace_run.repo)


def test_show_accepts_active_job_with_absent_manifest(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    ledger_dir = repo / ".swingle" / "delegate" / "ledger"
    _allocate(repo, ledger_dir)

    result = show_workspace(run_id=RUN, cwd=repo)

    assert result["jobs"] == [
        {
            "job_id": JOB,
            "terminal_status": None,
            "manifest_state": "absent",
            "manifest_path": str(repo / ".swingle" / "delegate" / "artifacts" / RUN / JOB / "manifest.json"),
            "selected_files": [],
            "selected_bytes": 0,
        }
    ]


def test_show_reports_alternate_caller_subdirectory(workspace_run):
    nested = workspace_run.repo / "packages" / "app"
    nested.mkdir(parents=True)

    result = show_workspace(run_id=workspace_run.run_id, cwd=nested)

    assert result["repository_root"] == str(workspace_run.repo)


# --- manifest states -----------------------------------------------------------


def test_show_reports_prepared_manifest_for_active_job(tmp_path):
    from swingle.workspace_manifest import finalize_job_manifest

    repo = tmp_path / "repo"
    repo.mkdir()
    ledger_dir = repo / ".swingle" / "delegate" / "ledger"
    job_dir = _allocate(repo, ledger_dir)
    (job_dir / "result.md").write_bytes(b"result\n")
    append_events(ledger_dir, SESSION, [_dispatched()])
    # Simulate a crash after the pre-terminal manifest write, before the
    # ledger append that would make the job terminal.
    finalize_job_manifest(
        project=repo, controller_session_id=SESSION, run_id=RUN, job_id=JOB,
        provider="codex", terminal_status="DONE", finished_at="2026-08-26T10:34:00.000Z",
    )

    result = show_workspace(run_id=RUN, cwd=repo)

    assert result["jobs"][0]["manifest_state"] == "prepared"
    assert result["jobs"][0]["terminal_status"] is None


def test_show_reports_terminal_corruption_on_missing_manifest_file(workspace_run):
    (workspace_run.job_dir / "manifest.json").unlink()

    result = show_workspace(run_id=workspace_run.run_id, cwd=workspace_run.repo)

    assert result["jobs"][0]["manifest_state"] == "corrupt"


def test_show_reports_terminal_corruption_on_tampered_file(workspace_run):
    (workspace_run.job_dir / "result.md").write_bytes(b"tampered")

    result = show_workspace(run_id=workspace_run.run_id, cwd=workspace_run.repo)

    assert result["jobs"][0]["manifest_state"] == "corrupt"


# --- file selection and path escapes --------------------------------------------


@pytest.mark.parametrize(
    "bad_file",
    ["../result.md", "/etc/passwd"],
)
def test_show_job_scope_rejects_escaping_file_path(workspace_run, bad_file):
    with pytest.raises(WorkspaceError) as error:
        show_workspace(run_id=workspace_run.run_id, job_id=workspace_run.job_id, file_paths=(bad_file,), cwd=workspace_run.repo)

    assert error.value.code == "path_escape"


def test_show_run_scope_rejects_escaping_file_path(workspace_run):
    with pytest.raises(WorkspaceError) as error:
        show_workspace(run_id=workspace_run.run_id, file_paths=(f"{workspace_run.job_id}/../result.md",), cwd=workspace_run.repo)

    assert error.value.code == "path_escape"


def test_show_selects_named_file(workspace_run):
    result = show_workspace(run_id=workspace_run.run_id, job_id=workspace_run.job_id, file_paths=("result.md",), cwd=workspace_run.repo)

    assert result["jobs"][0]["selected_files"] == ["result.md"]
    assert result["jobs"][0]["selected_bytes"] == len(b"result\n")


def test_show_run_scope_selects_file_with_job_prefix(workspace_run):
    result = show_workspace(run_id=workspace_run.run_id, file_paths=(f"{workspace_run.job_id}/result.md",), cwd=workspace_run.repo)

    assert result["jobs"][0]["selected_files"] == ["result.md"]


def test_show_duplicate_file_values_collapse_to_one(workspace_run):
    result = show_workspace(
        run_id=workspace_run.run_id, job_id=workspace_run.job_id,
        file_paths=("result.md", "result.md"), cwd=workspace_run.repo,
    )

    assert result["jobs"][0]["selected_files"] == ["result.md"]


def test_show_rejects_file_not_in_manifest(workspace_run):
    with pytest.raises(WorkspaceError) as error:
        show_workspace(run_id=workspace_run.run_id, job_id=workspace_run.job_id, file_paths=("nope.txt",), cwd=workspace_run.repo)

    assert error.value.code == "file_missing"


def test_show_rejects_file_filter_on_manifest_json(workspace_run):
    with pytest.raises(WorkspaceError) as error:
        show_workspace(run_id=workspace_run.run_id, job_id=workspace_run.job_id, file_paths=("manifest.json",), cwd=workspace_run.repo)

    assert error.value.code == "file_missing"


def test_show_reports_source_manifest_name_when_file_filter_active(workspace_run):
    result = show_workspace(run_id=workspace_run.run_id, job_id=workspace_run.job_id, file_paths=("result.md",), cwd=workspace_run.repo)

    assert f"artifacts/{workspace_run.run_id}/{workspace_run.job_id}/source-manifest.json" in result["selected_paths"]


def test_show_reports_manifest_name_without_file_filter(workspace_run):
    result = show_workspace(run_id=workspace_run.run_id, cwd=workspace_run.repo)

    assert f"artifacts/{workspace_run.run_id}/{workspace_run.job_id}/manifest.json" in result["selected_paths"]


def test_show_byte_count_includes_manifest_and_ledger(workspace_run):
    result = show_workspace(run_id=workspace_run.run_id, cwd=workspace_run.repo)

    ledger_file = next(workspace_run.ledger_dir.glob("*.ndjson"))
    ledger_bytes = ledger_file.stat().st_size
    manifest_bytes = (workspace_run.job_dir / "manifest.json").stat().st_size
    assert result["byte_count"] == len(b"result\n") + manifest_bytes + ledger_bytes


# --- verify: run and job scope state matrix -------------------------------------


def test_verify_complete_run_is_valid(workspace_run):
    finalize_run(workspace_run.repo, workspace_run.ledger_dir, workspace_run.controller_session_id, workspace_run.run_id)

    result = verify_workspace(run_id=workspace_run.run_id, cwd=workspace_run.repo)

    assert result["valid"] is True
    assert result["run_complete"] is True
    assert result["active_job_ids"] == []
    assert result["manifest_states"] == {workspace_run.job_id: "terminal"}
    assert result["verified_files"] == 1
    assert result["verified_bytes"] == len(b"result\n")


def test_verify_active_run_is_invalid(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    ledger_dir = repo / ".swingle" / "delegate" / "ledger"
    _allocate(repo, ledger_dir)

    result = verify_workspace(run_id=RUN, cwd=repo)

    assert result["valid"] is False
    assert result["active_job_ids"] == [JOB]
    assert result["manifest_states"] == {JOB: "absent"}


def test_verify_mixed_run_reports_active_and_terminal(workspace_run):
    active_job_dir = _allocate(workspace_run.repo, workspace_run.ledger_dir, run_id=workspace_run.run_id, job_id=OTHER_JOB)

    result = verify_workspace(run_id=workspace_run.run_id, cwd=workspace_run.repo)

    assert result["valid"] is False
    assert result["active_job_ids"] == [OTHER_JOB]
    assert result["manifest_states"] == {workspace_run.job_id: "terminal", OTHER_JOB: "absent"}
    assert result["verified_files"] == 1
    assert result["verified_bytes"] == len(b"result\n")


def test_verify_zero_job_complete_run_is_valid(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    ledger_dir = repo / ".swingle" / "delegate" / "ledger"
    append_events(ledger_dir, SESSION, [draft("run-started", data={"kind": "batch"})])
    finalize_run(repo, ledger_dir, SESSION, RUN)

    result = verify_workspace(run_id=RUN, cwd=repo)

    assert result["valid"] is True
    assert result["job_ids"] == []
    assert result["active_job_ids"] == []
    assert result["verified_files"] == 0
    assert result["verified_bytes"] == 0


def test_verify_prepared_manifest_counts_toward_verified_bytes_but_stays_invalid(tmp_path):
    from swingle.workspace_manifest import finalize_job_manifest

    repo = tmp_path / "repo"
    repo.mkdir()
    ledger_dir = repo / ".swingle" / "delegate" / "ledger"
    job_dir = _allocate(repo, ledger_dir)
    (job_dir / "result.md").write_bytes(b"result\n")
    append_events(ledger_dir, SESSION, [_dispatched()])
    finalize_job_manifest(
        project=repo, controller_session_id=SESSION, run_id=RUN, job_id=JOB,
        provider="codex", terminal_status="DONE", finished_at="2026-08-26T10:34:00.000Z",
    )

    result = verify_workspace(run_id=RUN, cwd=repo)

    assert result["valid"] is False
    assert result["manifest_states"] == {JOB: "prepared"}
    assert result["verified_files"] == 1
    assert result["verified_bytes"] == len(b"result\n")


def test_verify_corrupt_terminal_manifest_raises(workspace_run):
    (workspace_run.job_dir / "result.md").write_bytes(b"tampered")

    with pytest.raises(WorkspaceError) as error:
        verify_workspace(run_id=workspace_run.run_id, cwd=workspace_run.repo)

    assert error.value.code == "hash_mismatch"


def test_verify_corrupt_terminal_manifest_missing_file_raises_manifest_missing(workspace_run):
    (workspace_run.job_dir / "manifest.json").unlink()

    with pytest.raises(WorkspaceError) as error:
        verify_workspace(run_id=workspace_run.run_id, cwd=workspace_run.repo)

    assert error.value.code == "manifest_missing"


def test_verify_job_scope_terminal_job_inside_active_run_is_valid(workspace_run):
    active_job_dir = _allocate(workspace_run.repo, workspace_run.ledger_dir, run_id=workspace_run.run_id, job_id=OTHER_JOB)

    result = verify_workspace(run_id=workspace_run.run_id, job_id=workspace_run.job_id, cwd=workspace_run.repo)

    assert result["valid"] is True
    assert result["job_ids"] == [workspace_run.job_id]
    assert result["active_job_ids"] == []


def test_verify_job_scope_active_job_inside_active_run_is_invalid(workspace_run):
    active_job_dir = _allocate(workspace_run.repo, workspace_run.ledger_dir, run_id=workspace_run.run_id, job_id=OTHER_JOB)

    result = verify_workspace(run_id=workspace_run.run_id, job_id=OTHER_JOB, cwd=workspace_run.repo)

    assert result["valid"] is False
    assert result["active_job_ids"] == [OTHER_JOB]


def test_show_zero_job_complete_run_reports_only_ledger(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    ledger_dir = repo / ".swingle" / "delegate" / "ledger"
    append_events(ledger_dir, SESSION, [draft("run-started", data={"kind": "batch"})])
    finalize_run(repo, ledger_dir, SESSION, RUN)

    result = show_workspace(run_id=RUN, cwd=repo)

    assert result["job_ids"] == []
    assert result["jobs"] == []
    assert result["selected_paths"] == ["ledger.ndjson"]
    ledger_bytes = next(ledger_dir.glob("*.ndjson")).stat().st_size
    assert result["byte_count"] == ledger_bytes
