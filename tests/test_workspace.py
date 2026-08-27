from __future__ import annotations

import json
from dataclasses import dataclass

import pytest

from swingle.errors import LedgerLifecycleError, WorkspaceError
from swingle.ledger import append_events, finalize_run, record_complete
from swingle.ledger_schema import EventDraft
from swingle.workspace import copy_workspace, discover_repository_root, show_workspace, verify_workspace

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


def _allocate_job(repo: Path, ledger_dir: Path, *, run_id=RUN, job_id=JOB, session=SESSION) -> Path:
    """Allocate an additional job on an already-started run."""
    append_events(
        ledger_dir,
        session,
        [draft("allocated", session=session, run=run_id, job=job_id, data={"role": "reader", "contract": "$PLUGIN_ROOT/contracts/reader-contract.md", "tier": "standard", "task": "read"})],
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


@pytest.fixture
def completed_run(workspace_run) -> WorkspaceRun:
    finalize_run(workspace_run.repo, workspace_run.ledger_dir, workspace_run.controller_session_id, workspace_run.run_id)
    return workspace_run


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
    active_job_dir = _allocate_job(workspace_run.repo, workspace_run.ledger_dir, run_id=workspace_run.run_id, job_id=OTHER_JOB)

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
    active_job_dir = _allocate_job(workspace_run.repo, workspace_run.ledger_dir, run_id=workspace_run.run_id, job_id=OTHER_JOB)

    result = verify_workspace(run_id=workspace_run.run_id, job_id=workspace_run.job_id, cwd=workspace_run.repo)

    assert result["valid"] is True
    assert result["job_ids"] == [workspace_run.job_id]
    assert result["active_job_ids"] == []


def test_verify_job_scope_active_job_inside_active_run_is_invalid(workspace_run):
    active_job_dir = _allocate_job(workspace_run.repo, workspace_run.ledger_dir, run_id=workspace_run.run_id, job_id=OTHER_JOB)

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


# --- copy: selection forms ------------------------------------------------------


def test_copy_run_scope_publishes_ledger_manifest_and_file(completed_run, tmp_path):
    destination = tmp_path / "dest"

    result = copy_workspace(run_id=completed_run.run_id, destination=str(destination), cwd=completed_run.repo)

    assert result["status"] == "copied"
    assert result["job_ids"] == [completed_run.job_id]
    assert (destination / "ledger.ndjson").is_file()
    assert (destination / "artifacts" / completed_run.run_id / completed_run.job_id / "manifest.json").is_file()
    assert (destination / "artifacts" / completed_run.run_id / completed_run.job_id / "result.md").read_bytes() == b"result\n"


def test_copy_job_scope_does_not_require_run_completed(workspace_run, tmp_path):
    destination = tmp_path / "dest"

    result = copy_workspace(
        run_id=workspace_run.run_id, job_id=workspace_run.job_id, destination=str(destination), cwd=workspace_run.repo
    )

    assert result["status"] == "copied"
    assert (destination / "artifacts" / workspace_run.run_id / workspace_run.job_id / "manifest.json").is_file()


def test_copy_job_scope_with_file_filter_uses_source_manifest_name(workspace_run, tmp_path):
    destination = tmp_path / "dest"

    result = copy_workspace(
        run_id=workspace_run.run_id, job_id=workspace_run.job_id, file_paths=("result.md",),
        destination=str(destination), cwd=workspace_run.repo,
    )

    assert result["status"] == "copied"
    job_dest = destination / "artifacts" / workspace_run.run_id / workspace_run.job_id
    assert (job_dest / "source-manifest.json").is_file()
    assert not (job_dest / "manifest.json").exists()
    assert (job_dest / "result.md").read_bytes() == b"result\n"


def test_copy_run_scope_with_multi_job_file_selection(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    ledger_dir = repo / ".swingle" / "delegate" / "ledger"
    _allocate(repo, ledger_dir)
    job2_dir = _allocate_job(repo, ledger_dir, job_id=OTHER_JOB)
    (repo / ".swingle" / "delegate" / "artifacts" / RUN / JOB / "result.md").write_bytes(b"result\n")
    (job2_dir / "report.json").write_bytes(b"{}")
    _finalize(repo, ledger_dir)
    _finalize(repo, ledger_dir, job_id=OTHER_JOB)
    finalize_run(repo, ledger_dir, SESSION, RUN)
    destination = tmp_path / "dest"

    result = copy_workspace(
        run_id=RUN, file_paths=(f"{JOB}/result.md", f"{OTHER_JOB}/report.json"),
        destination=str(destination), cwd=repo,
    )

    assert result["status"] == "copied"
    assert (destination / "artifacts" / RUN / JOB / "source-manifest.json").is_file()
    assert (destination / "artifacts" / RUN / JOB / "result.md").read_bytes() == b"result\n"
    assert (destination / "artifacts" / RUN / OTHER_JOB / "source-manifest.json").is_file()
    assert (destination / "artifacts" / RUN / OTHER_JOB / "report.json").read_bytes() == b"{}"


def test_copy_ledger_ndjson_contains_only_run_level_and_selected_job_lines(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    ledger_dir = repo / ".swingle" / "delegate" / "ledger"
    _allocate(repo, ledger_dir)
    _allocate_job(repo, ledger_dir, job_id=OTHER_JOB)
    (repo / ".swingle" / "delegate" / "artifacts" / RUN / JOB / "result.md").write_bytes(b"result\n")
    _finalize(repo, ledger_dir)
    destination = tmp_path / "dest"

    result = copy_workspace(run_id=RUN, job_id=JOB, destination=str(destination), cwd=repo)

    assert result["status"] == "copied"
    lines = (destination / "ledger.ndjson").read_bytes().splitlines()
    job_ids_seen = {json.loads(line)["job_id"] for line in lines if json.loads(line)["job_id"] is not None}
    assert job_ids_seen == {JOB}


def test_copy_zero_job_complete_run_copies_only_ledger(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    ledger_dir = repo / ".swingle" / "delegate" / "ledger"
    append_events(ledger_dir, SESSION, [draft("run-started", data={"kind": "batch"})])
    finalize_run(repo, ledger_dir, SESSION, RUN)
    destination = tmp_path / "dest"

    result = copy_workspace(run_id=RUN, destination=str(destination), cwd=repo)

    assert result["status"] == "copied"
    assert result["job_ids"] == []
    assert (destination / "ledger.ndjson").is_file()
    assert not (destination / "artifacts").exists()


# --- copy: transaction behavior --------------------------------------------------


def test_copy_missing_destination_publishes_with_one_rename(completed_run, tmp_path):
    destination = tmp_path / "a" / "b" / "dest"

    result = copy_workspace(run_id=completed_run.run_id, destination=str(destination), cwd=completed_run.repo)

    assert result["status"] == "copied"
    assert destination.is_dir()


def test_copy_identical_destination_is_idempotent(completed_run, tmp_path):
    destination = tmp_path / "dest"
    copy_workspace(run_id=completed_run.run_id, destination=str(destination), cwd=completed_run.repo)

    result = copy_workspace(run_id=completed_run.run_id, destination=str(destination), cwd=completed_run.repo)

    assert result["status"] == "idempotent"


def test_copy_different_destination_returns_conflict_and_changes_nothing(completed_run, tmp_path):
    destination = tmp_path / "dest"
    destination.mkdir()
    (destination / "unexpected.txt").write_bytes(b"pre-existing")

    with pytest.raises(WorkspaceError) as error:
        copy_workspace(run_id=completed_run.run_id, destination=str(destination), cwd=completed_run.repo)

    assert error.value.code == "copy_conflict"
    assert (destination / "unexpected.txt").read_bytes() == b"pre-existing"
    assert not (destination / "ledger.ndjson").exists()


def test_copy_staging_failure_leaves_no_destination_tree(completed_run, tmp_path, monkeypatch):
    import swingle.workspace as workspace_module

    def broken_write_stage(stage_fd, selection):
        raise WorkspaceError("workspace_io_error", "simulated staging failure")

    monkeypatch.setattr(workspace_module, "_write_stage", broken_write_stage)
    destination = tmp_path / "dest"

    with pytest.raises(WorkspaceError):
        copy_workspace(run_id=completed_run.run_id, destination=str(destination), cwd=completed_run.repo)

    assert not destination.exists()
    assert list(tmp_path.glob(".swingle-copy-*")) == []


def test_copy_never_deletes_source_file(completed_run, tmp_path):
    destination = tmp_path / "dest"

    copy_workspace(run_id=completed_run.run_id, destination=str(destination), cwd=completed_run.repo)

    assert (completed_run.job_dir / "result.md").read_bytes() == b"result\n"
    assert (completed_run.job_dir / "manifest.json").is_file()


def test_copy_rejects_destination_inside_workspace(completed_run):
    inside = completed_run.repo / ".swingle" / "delegate" / "somewhere"

    with pytest.raises(WorkspaceError) as error:
        copy_workspace(run_id=completed_run.run_id, destination=str(inside), cwd=completed_run.repo)

    assert error.value.code == "destination_inside_workspace"
    assert not inside.exists()


def test_copy_rejects_destination_equal_to_workspace_root(completed_run):
    workspace_root = completed_run.repo / ".swingle" / "delegate"

    with pytest.raises(WorkspaceError) as error:
        copy_workspace(run_id=completed_run.run_id, destination=str(workspace_root), cwd=completed_run.repo)

    assert error.value.code == "destination_inside_workspace"


def test_show_to_reports_absent_for_missing_destination(completed_run, tmp_path):
    destination = tmp_path / "dest"

    result = show_workspace(run_id=completed_run.run_id, destination=str(destination), cwd=completed_run.repo)

    assert result["destination_state"] == "absent"
    assert not destination.exists()


def test_show_to_reports_identical_without_staging(completed_run, tmp_path):
    destination = tmp_path / "dest"
    copy_workspace(run_id=completed_run.run_id, destination=str(destination), cwd=completed_run.repo)
    before = {p: p.stat().st_mtime_ns for p in destination.rglob("*") if p.is_file()}

    result = show_workspace(run_id=completed_run.run_id, destination=str(destination), cwd=completed_run.repo)

    assert result["destination_state"] == "identical"
    after = {p: p.stat().st_mtime_ns for p in destination.rglob("*") if p.is_file()}
    assert before == after


def test_show_to_reports_conflict_without_staging(completed_run, tmp_path):
    destination = tmp_path / "dest"
    destination.mkdir()
    (destination / "unexpected.txt").write_bytes(b"x")

    result = show_workspace(run_id=completed_run.run_id, destination=str(destination), cwd=completed_run.repo)

    assert result["destination_state"] == "conflict"
    assert list(destination.iterdir()) == [destination / "unexpected.txt"]


# --- copy: symlink safety --------------------------------------------------------


def test_copy_rejects_source_symlink(completed_run, tmp_path):
    (completed_run.job_dir / "result.md").unlink()
    outside = tmp_path / "outside.txt"
    outside.write_text("x", encoding="utf-8")
    (completed_run.job_dir / "result.md").symlink_to(outside)
    destination = tmp_path / "dest"

    with pytest.raises(WorkspaceError) as error:
        copy_workspace(run_id=completed_run.run_id, destination=str(destination), cwd=completed_run.repo)

    assert error.value.code == "symlink_rejected"
    assert not destination.exists()


def test_copy_rejects_destination_parent_symlink(completed_run, tmp_path):
    real_parent = tmp_path / "real"
    real_parent.mkdir()
    linked_parent = tmp_path / "linked"
    linked_parent.symlink_to(real_parent)
    destination = linked_parent / "dest"

    with pytest.raises(WorkspaceError) as error:
        copy_workspace(run_id=completed_run.run_id, destination=str(destination), cwd=completed_run.repo)

    assert error.value.code == "symlink_rejected"
    assert not (real_parent / "dest").exists()


def test_copy_rejects_existing_destination_symlink(completed_run, tmp_path):
    somewhere_else = tmp_path / "somewhere_else"
    somewhere_else.mkdir()
    destination = tmp_path / "dest"
    destination.symlink_to(somewhere_else)

    with pytest.raises(WorkspaceError) as error:
        copy_workspace(run_id=completed_run.run_id, destination=str(destination), cwd=completed_run.repo)

    assert error.value.code == "symlink_rejected"
    assert destination.is_symlink()
    assert list(somewhere_else.iterdir()) == []


def test_copy_rejects_existing_destination_file(completed_run, tmp_path):
    destination = tmp_path / "dest"
    destination.write_bytes(b"not a directory")

    with pytest.raises(WorkspaceError) as error:
        copy_workspace(run_id=completed_run.run_id, destination=str(destination), cwd=completed_run.repo)

    assert error.value.code == "copy_conflict"
    assert destination.read_bytes() == b"not a directory"


# --- copy: staged corruption and source races -------------------------------------


def test_copy_staged_corruption_before_verification_raises_hash_mismatch(completed_run, tmp_path, monkeypatch):
    import os as os_module

    import swingle.workspace as workspace_module

    real_copy = workspace_module.workspace_io.copy_regular_file_at

    def corrupting_copy(*, source_root_fd, source_path, destination_root_fd, destination_path, expected_size, expected_sha256):
        fact = real_copy(
            source_root_fd=source_root_fd, source_path=source_path,
            destination_root_fd=destination_root_fd, destination_path=destination_path,
            expected_size=expected_size, expected_sha256=expected_sha256,
        )
        if source_path == "result.md":
            segments = destination_path.split("/")
            fd = destination_root_fd
            opened = []
            for segment in segments[:-1]:
                fd = os_module.open(segment, os_module.O_DIRECTORY | os_module.O_NOFOLLOW, dir_fd=fd)
                opened.append(fd)
            file_fd = os_module.open(segments[-1], os_module.O_WRONLY | os_module.O_TRUNC, dir_fd=fd)
            os_module.write(file_fd, b"corrupted!")
            os_module.close(file_fd)
            for handle in reversed(opened):
                os_module.close(handle)
        return fact

    monkeypatch.setattr(workspace_module.workspace_io, "copy_regular_file_at", corrupting_copy)
    destination = tmp_path / "dest"

    with pytest.raises(WorkspaceError) as error:
        copy_workspace(run_id=completed_run.run_id, destination=str(destination), cwd=completed_run.repo)

    assert error.value.code == "hash_mismatch"
    assert "result.md" in str(error.value)
    assert not destination.exists()


def test_copy_staged_file_removed_before_verification_raises_file_missing(completed_run, tmp_path, monkeypatch):
    import os as os_module

    import swingle.workspace as workspace_module

    real_copy = workspace_module.workspace_io.copy_regular_file_at

    def vanishing_copy(*, source_root_fd, source_path, destination_root_fd, destination_path, expected_size, expected_sha256):
        fact = real_copy(
            source_root_fd=source_root_fd, source_path=source_path,
            destination_root_fd=destination_root_fd, destination_path=destination_path,
            expected_size=expected_size, expected_sha256=expected_sha256,
        )
        if source_path == "result.md":
            segments = destination_path.split("/")
            fd = destination_root_fd
            opened = []
            for segment in segments[:-1]:
                fd = os_module.open(segment, os_module.O_DIRECTORY | os_module.O_NOFOLLOW, dir_fd=fd)
                opened.append(fd)
            os_module.unlink(segments[-1], dir_fd=fd)
            for handle in reversed(opened):
                os_module.close(handle)
        return fact

    monkeypatch.setattr(workspace_module.workspace_io, "copy_regular_file_at", vanishing_copy)
    destination = tmp_path / "dest"

    with pytest.raises(WorkspaceError) as error:
        copy_workspace(run_id=completed_run.run_id, destination=str(destination), cwd=completed_run.repo)

    assert error.value.code == "file_missing"
    assert "result.md" in str(error.value)
    assert not destination.exists()


def test_copy_source_replaced_during_copy_raises_file_identity_changed(completed_run, tmp_path, monkeypatch):
    import swingle.workspace as workspace_module

    real_copy = workspace_module.workspace_io.copy_regular_file_at

    def raising_copy(**kwargs):
        if kwargs["source_path"] == "result.md":
            raise WorkspaceError("file_identity_changed", f"copy: file changed during read: {kwargs['source_path']}")
        return real_copy(**kwargs)

    monkeypatch.setattr(workspace_module.workspace_io, "copy_regular_file_at", raising_copy)
    destination = tmp_path / "dest"

    with pytest.raises(WorkspaceError) as error:
        copy_workspace(run_id=completed_run.run_id, destination=str(destination), cwd=completed_run.repo)

    assert error.value.code == "file_identity_changed"
    assert "result.md" in str(error.value)
    assert not destination.exists()


# --- copy: publication race protocol ----------------------------------------------


def test_copy_concurrently_created_empty_destination_returns_conflict_never_replaced(completed_run, tmp_path):
    destination = tmp_path / "dest"
    destination.mkdir()
    inode_before = destination.stat().st_ino

    with pytest.raises(WorkspaceError) as error:
        copy_workspace(run_id=completed_run.run_id, destination=str(destination), cwd=completed_run.repo)

    assert error.value.code == "copy_conflict"
    assert destination.stat().st_ino == inode_before
    assert list(destination.iterdir()) == []


def test_copy_extra_empty_directory_in_destination_returns_conflict(completed_run, tmp_path):
    destination = tmp_path / "dest"
    copy_workspace(run_id=completed_run.run_id, destination=str(destination), cwd=completed_run.repo)
    (destination / "artifacts" / completed_run.run_id / completed_run.job_id / "extra_dir").mkdir()

    with pytest.raises(WorkspaceError) as error:
        copy_workspace(run_id=completed_run.run_id, destination=str(destination), cwd=completed_run.repo)

    assert error.value.code == "copy_conflict"


def test_copy_unsupported_rename_primitive_returns_workspace_io_error(completed_run, tmp_path, monkeypatch):
    import swingle.workspace_io as workspace_io_module

    monkeypatch.setattr(workspace_io_module, "_renameat_func", lambda: (None, 0))
    destination = tmp_path / "dest"

    with pytest.raises(WorkspaceError) as error:
        copy_workspace(run_id=completed_run.run_id, destination=str(destination), cwd=completed_run.repo)

    assert error.value.code == "workspace_io_error"
    assert not destination.exists()
    assert list(tmp_path.glob(".swingle-copy-*")) == []


def test_copy_publication_instability_exceeds_race_limit_leaves_destination_unchanged(completed_run, tmp_path, monkeypatch):
    import swingle.workspace as workspace_module

    destination = tmp_path / "dest"
    destination.mkdir()

    real_matches = workspace_module.workspace_io.regular_tree_matches_at
    call_count = {"n": 0}

    def flaky_matches(root_fd, expected):
        call_count["n"] += 1
        result = real_matches(root_fd, expected)
        # Replace the destination with a fresh empty directory so the
        # post-comparison identity recheck always observes a different
        # inode, forcing a retry every attempt. Deterministic; no timing.
        destination.rmdir()
        destination.mkdir()
        return result

    monkeypatch.setattr(workspace_module.workspace_io, "regular_tree_matches_at", flaky_matches)

    with pytest.raises(WorkspaceError) as error:
        copy_workspace(run_id=completed_run.run_id, destination=str(destination), cwd=completed_run.repo)

    assert error.value.code == "workspace_io_error"
    assert call_count["n"] == 8
    assert destination.is_dir()
    assert list(destination.iterdir()) == []
    assert list(tmp_path.glob(".swingle-copy-*")) == []


def test_copy_retries_from_stage_when_destination_replaced_during_comparison(completed_run, tmp_path, monkeypatch):
    import swingle.workspace as workspace_module

    destination = tmp_path / "dest"
    destination.mkdir()

    real_matches = workspace_module.workspace_io.regular_tree_matches_at
    state = {"replaced": False}

    def flaky_matches(root_fd, expected):
        result = real_matches(root_fd, expected)
        if not state["replaced"]:
            state["replaced"] = True
            destination.rmdir()
        return result

    monkeypatch.setattr(workspace_module.workspace_io, "regular_tree_matches_at", flaky_matches)

    result = copy_workspace(run_id=completed_run.run_id, destination=str(destination), cwd=completed_run.repo)

    assert result["status"] == "copied"
    assert destination.is_dir()
    assert (destination / "ledger.ndjson").is_file()


# --- copy: narrowed selection verification ----------------------------------------


def test_copy_narrowed_selection_verifies_staged_file_against_manifest(completed_run, tmp_path):
    destination = tmp_path / "dest"

    result = copy_workspace(
        run_id=completed_run.run_id, job_id=completed_run.job_id, file_paths=("result.md",),
        destination=str(destination), cwd=completed_run.repo,
    )

    assert result["status"] == "copied"
    staged = destination / "artifacts" / completed_run.run_id / completed_run.job_id / "result.md"
    assert staged.read_bytes() == b"result\n"


def test_copy_narrowed_selection_rejects_tampered_source_file(completed_run, tmp_path):
    (completed_run.job_dir / "result.md").write_bytes(b"tampered")
    destination = tmp_path / "dest"

    with pytest.raises(WorkspaceError) as error:
        copy_workspace(
            run_id=completed_run.run_id, job_id=completed_run.job_id, file_paths=("result.md",),
            destination=str(destination), cwd=completed_run.repo,
        )

    assert error.value.code == "hash_mismatch"
