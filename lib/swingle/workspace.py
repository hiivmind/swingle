from __future__ import annotations

import errno
import hashlib
import json
import os
import stat
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from . import ledger
from . import ledger_schema
from . import workspace_io
from . import workspace_manifest
from .errors import LedgerLifecycleError, WorkspaceError
from .ledger import LedgerRecord
from .workspace_io import FileFact, TreeFact
from .workspace_manifest import JobManifest

ManifestState = Literal["absent", "prepared", "terminal", "corrupt"]

_LEDGER_FILE_NAME = "ledger.ndjson"


@dataclass(frozen=True)
class SelectedJob:
    controller_session_id: str
    job_id: str
    provider: str | None
    terminal_status: str | None
    manifest_state: ManifestState
    manifest_path: Path
    manifest: JobManifest | None
    selected_files: tuple[FileFact, ...]
    manifest_destination_name: Literal["manifest.json", "source-manifest.json"]
    selected_bytes: int


@dataclass(frozen=True)
class WorkspaceSelection:
    repository_root: Path
    workspace_root: Path
    ledger_dir: Path
    artifact_root: Path
    controller_session_id: str
    run_id: str
    run_status: str | None
    run_complete: bool
    jobs: tuple[SelectedJob, ...]
    ledger_records: tuple[LedgerRecord, ...]
    selected_paths: tuple[str, ...]
    byte_count: int
    file_filter_active: bool


def discover_repository_root(cwd: Path | None = None) -> Path:
    """Find the repository root from `cwd`, without running Git.

    Prefers the nearest ancestor that already contains `.swingle/delegate`.
    Falls back to the nearest ancestor with a `.git` file or directory, so
    a repository without a workspace yet can still be located.
    """
    start = Path(cwd) if cwd is not None else Path.cwd()
    if not start.is_absolute():
        start = Path.cwd() / start
    candidates = (start, *start.parents)
    for candidate in candidates:
        if (candidate / ".swingle" / "delegate").is_dir():
            return candidate
    for candidate in candidates:
        git_path = candidate / ".git"
        if git_path.is_dir() or git_path.is_file():
            return candidate
    raise WorkspaceError("workspace_not_found", f"no .swingle/delegate or .git ancestor found from {start}")


def _orphan_artifact_directories(artifact_root: Path, run_id: str, allocated_job_ids: set[str]) -> tuple[str, ...]:
    run_dir = artifact_root / run_id
    if not run_dir.is_dir():
        return ()
    orphans = [
        str(entry)
        for entry in sorted(run_dir.iterdir())
        if entry.is_dir() and entry.name not in allocated_job_ids
    ]
    return tuple(orphans)


def _dedupe_preserve_order(values: Sequence[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(values))


def _job_relative_paths(
    raw_paths: tuple[str, ...],
    *,
    job_id: str | None,
    allocated_job_ids: set[str],
) -> dict[str, list[str]]:
    """Validate and group raw `--file` values by the job they belong to.

    Every raw path is validated for containment before any job-prefix
    stripping, so `<job-id>/../result.md` fails identically to `../result.md`.
    """
    by_job: dict[str, list[str]] = {}
    for raw in raw_paths:
        workspace_io._validate_declared_path(raw)
        if job_id is not None:
            by_job.setdefault(job_id, []).append(raw)
            continue
        matched = None
        for candidate in allocated_job_ids:
            prefix = f"{candidate}/"
            if raw.startswith(prefix):
                matched = candidate
                relative = raw[len(prefix):]
                workspace_io._validate_declared_path(relative)
                by_job.setdefault(candidate, []).append(relative)
                break
        if matched is None:
            raise WorkspaceError("file_missing", f"selection: file does not match an allocated job: {raw}")
    return by_job


def _select_workspace(
    *,
    run_id: str,
    job_id: str | None,
    file_paths: Sequence[str],
    require_terminal_job: bool,
    require_complete_run: bool,
    cwd: Path,
) -> WorkspaceSelection:
    ledger_schema.validate_uuid(run_id, "run_id")
    if job_id is not None:
        ledger_schema.validate_uuid(job_id, "job_id")

    repository_root = discover_repository_root(cwd)
    workspace_root = repository_root / ".swingle" / "delegate"
    if not workspace_root.is_dir():
        raise WorkspaceError("workspace_not_found", f"no workspace at {workspace_root}")
    ledger_dir = workspace_root / "ledger"
    artifact_root = workspace_root / "artifacts"

    all_records = tuple(ledger.iter_event_records(ledger_dir))
    matching_records = tuple(record for record in all_records if record.event["run_id"] == run_id)
    if not matching_records:
        raise WorkspaceError("run_not_found", f"run not found: {run_id}")

    sessions = {record.event["controller_session_id"] for record in matching_records}
    if len(sessions) > 1:
        raise LedgerLifecycleError(f"run_id is duplicated across session ledgers: {run_id}")
    controller_session_id = next(iter(sessions))

    events = [record.event for record in matching_records]
    run_status: str | None = None
    run_complete = False
    for event in events:
        if event["event"] == "run-completed":
            run_complete = True
            run_status = event["data"]["status"]
    if require_complete_run and not run_complete:
        raise WorkspaceError("run_not_complete", f"run is not complete: {run_id}")

    allocation_events: dict[str, dict[str, Any]] = {}
    for event in events:
        if event["event"] == "allocated":
            allocation_events[event["job_id"]] = event

    if job_id is not None:
        if job_id not in allocation_events:
            raise WorkspaceError("job_not_found", f"job is not allocated in run: {job_id}")
        selected_job_ids: tuple[str, ...] = (job_id,)
    else:
        selected_job_ids = tuple(allocation_events)

    raw_file_paths = _dedupe_preserve_order(tuple(file_paths))
    file_filter_active = bool(raw_file_paths)
    files_by_job = _job_relative_paths(raw_file_paths, job_id=job_id, allocated_job_ids=set(allocation_events))
    for filtered_job_id in files_by_job:
        if filtered_job_id not in selected_job_ids:
            raise WorkspaceError("job_not_found", f"file selection targets an unselected job: {filtered_job_id}")

    selected_jobs: list[SelectedJob] = []
    for selected_job_id in selected_job_ids:
        job_events = [event for event in events if event["job_id"] == selected_job_id]
        complete_events = [event for event in job_events if event["event"] == "complete"]
        dispatched_events = [event for event in job_events if event["event"] == "dispatched"]
        is_terminal = bool(complete_events)
        if require_terminal_job and not is_terminal:
            raise WorkspaceError("job_not_terminal", f"job is not terminal: {selected_job_id}")

        terminal_status = complete_events[-1]["data"]["status"] if complete_events else None
        provider = dispatched_events[-1]["data"]["provider"] if dispatched_events else None
        manifest_path = artifact_root / run_id / selected_job_id / "manifest.json"

        requested_relative_paths = files_by_job.get(selected_job_id)
        require_valid_manifest = require_terminal_job or requested_relative_paths is not None

        manifest: JobManifest | None = None
        manifest_state: ManifestState
        if is_terminal:
            finished_at = complete_events[-1]["timestamp"]
            if require_valid_manifest:
                manifest = workspace_manifest.verify_job_manifest(
                    project=repository_root,
                    controller_session_id=controller_session_id,
                    run_id=run_id,
                    job_id=selected_job_id,
                    provider=provider or "",
                    terminal_status=terminal_status,
                    finished_at=finished_at,
                )
                manifest_state = "terminal"
            else:
                try:
                    manifest = workspace_manifest.verify_job_manifest(
                        project=repository_root,
                        controller_session_id=controller_session_id,
                        run_id=run_id,
                        job_id=selected_job_id,
                        provider=provider or "",
                        terminal_status=terminal_status,
                        finished_at=finished_at,
                    )
                    manifest_state = "terminal"
                except WorkspaceError:
                    manifest_state = "corrupt"
        elif workspace_manifest.manifest_json_exists(repository_root, run_id, selected_job_id):
            if require_valid_manifest:
                manifest, _verified = workspace_manifest.verify_manifest_files_only(
                    project=repository_root, run_id=run_id, job_id=selected_job_id
                )
                manifest_state = "prepared"
            else:
                try:
                    manifest, _verified = workspace_manifest.verify_manifest_files_only(
                        project=repository_root, run_id=run_id, job_id=selected_job_id
                    )
                    manifest_state = "prepared"
                except WorkspaceError:
                    manifest_state = "corrupt"
        else:
            if require_valid_manifest:
                raise WorkspaceError("manifest_missing", f"selection: no manifest for job: {selected_job_id}")
            manifest_state = "absent"

        if requested_relative_paths is not None:
            manifest_paths = {item.path for item in manifest.files}
            for relative_path in requested_relative_paths:
                if relative_path not in manifest_paths:
                    raise WorkspaceError("file_missing", f"selection: file not in manifest: {relative_path}")
            selected_relative_paths = tuple(requested_relative_paths)
        elif manifest is not None:
            selected_relative_paths = tuple(item.path for item in manifest.files)
        else:
            selected_relative_paths = ()

        job_dir = artifact_root / run_id / selected_job_id
        selected_files = tuple(
            workspace_io.read_file_fact(job_dir, relative_path) for relative_path in selected_relative_paths
        )
        selected_bytes = sum(fact.size_bytes for fact in selected_files)
        manifest_destination_name: Literal["manifest.json", "source-manifest.json"] = (
            "source-manifest.json" if file_filter_active else "manifest.json"
        )

        selected_jobs.append(
            SelectedJob(
                controller_session_id=controller_session_id,
                job_id=selected_job_id,
                provider=provider,
                terminal_status=terminal_status,
                manifest_state=manifest_state,
                manifest_path=manifest_path,
                manifest=manifest,
                selected_files=selected_files,
                manifest_destination_name=manifest_destination_name,
                selected_bytes=selected_bytes,
            )
        )

    selected_job_id_set = set(selected_job_ids)
    ledger_records = tuple(
        record
        for record in matching_records
        if record.event["job_id"] is None or record.event["job_id"] in selected_job_id_set
    )

    selected_paths: list[str] = [_LEDGER_FILE_NAME]
    byte_count = sum(len(record.line) for record in ledger_records)
    for job in selected_jobs:
        selected_paths.append(f"artifacts/{run_id}/{job.job_id}/{job.manifest_destination_name}")
        if job.manifest is not None:
            byte_count += len(workspace_manifest._serialize_manifest(job.manifest))
        for fact in job.selected_files:
            selected_paths.append(f"artifacts/{run_id}/{job.job_id}/{fact.path}")
        byte_count += job.selected_bytes

    return WorkspaceSelection(
        repository_root=repository_root,
        workspace_root=workspace_root,
        ledger_dir=ledger_dir,
        artifact_root=artifact_root,
        controller_session_id=controller_session_id,
        run_id=run_id,
        run_status=run_status,
        run_complete=run_complete,
        jobs=tuple(selected_jobs),
        ledger_records=ledger_records,
        selected_paths=tuple(sorted(selected_paths)),
        byte_count=byte_count,
        file_filter_active=file_filter_active,
    )


def _allocated_job_ids(ledger_dir: Path, run_id: str) -> set[str]:
    return {
        record.event["job_id"]
        for record in ledger.iter_event_records(ledger_dir)
        if record.event["run_id"] == run_id and record.event["event"] == "allocated"
    }


def _selection_tree_facts(selection: WorkspaceSelection) -> tuple[TreeFact, ...]:
    """Build the complete expected tree a copy of `selection` would stage."""
    file_facts: list[TreeFact] = []
    ledger_bytes = b"".join(record.line for record in selection.ledger_records)
    file_facts.append(
        TreeFact(
            path=_LEDGER_FILE_NAME,
            entry_type="file",
            size_bytes=len(ledger_bytes),
            sha256=hashlib.sha256(ledger_bytes).hexdigest(),
        )
    )
    for job in selection.jobs:
        if job.manifest is None:
            continue
        manifest_bytes = workspace_manifest._serialize_manifest(job.manifest)
        manifest_path = f"artifacts/{selection.run_id}/{job.job_id}/{job.manifest_destination_name}"
        file_facts.append(
            TreeFact(
                path=manifest_path,
                entry_type="file",
                size_bytes=len(manifest_bytes),
                sha256=hashlib.sha256(manifest_bytes).hexdigest(),
            )
        )
        for fact in job.selected_files:
            file_facts.append(
                TreeFact(
                    path=f"artifacts/{selection.run_id}/{job.job_id}/{fact.path}",
                    entry_type="file",
                    size_bytes=fact.size_bytes,
                    sha256=fact.sha256,
                )
            )

    directory_paths: set[str] = set()
    for fact in file_facts:
        parts = fact.path.split("/")
        for depth in range(1, len(parts)):
            directory_paths.add("/".join(parts[:depth]))
    directory_facts = [
        TreeFact(path=path, entry_type="directory", size_bytes=0, sha256=None) for path in sorted(directory_paths)
    ]
    return tuple(file_facts) + tuple(directory_facts)


def _tree_sha256(facts: Sequence[TreeFact]) -> str:
    ordered = sorted(facts, key=lambda fact: fact.path.encode("utf-8"))
    payload = {"entries": [asdict(fact) for fact in ordered]}
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _reject_destination_inside_workspace(destination_abs: str, workspace_root: Path) -> None:
    workspace_abs = os.path.normpath(str(workspace_root))
    dest_norm = os.path.normpath(destination_abs)
    if dest_norm == workspace_abs or dest_norm.startswith(workspace_abs + os.sep):
        raise WorkspaceError(
            "destination_inside_workspace", f"copy: destination is inside the live workspace: {destination_abs}"
        )


def _inspect_destination_state(destination_abs: str, expected: tuple[TreeFact, ...]) -> str:
    """Read-only destination inspection for `workspace show --to`.

    Returns `"absent"`, `"identical"`, or `"conflict"`. Never creates a
    directory or a staging tree. Raises `symlink_rejected` for a
    symbolic link anywhere in the destination path, matching copy's own
    safety rule.
    """
    parent_path, name = os.path.split(destination_abs)
    components = [component for component in parent_path.split(os.sep) if component]
    fd = os.open("/", workspace_io._DIR_NOFOLLOW)
    try:
        for component in components:
            try:
                entry_stat = os.stat(component, dir_fd=fd, follow_symlinks=False)
            except FileNotFoundError:
                return "absent"
            if stat.S_ISLNK(entry_stat.st_mode):
                raise WorkspaceError("symlink_rejected", f"show: symbolic link in destination path: {component}")
            if not stat.S_ISDIR(entry_stat.st_mode):
                return "conflict"
            next_fd = workspace_io._open_dir_no_follow(fd, component, operation="show", path=component)
            os.close(fd)
            fd = next_fd
        try:
            entry_stat = os.stat(name, dir_fd=fd, follow_symlinks=False)
        except FileNotFoundError:
            return "absent"
        if stat.S_ISLNK(entry_stat.st_mode):
            raise WorkspaceError("symlink_rejected", f"show: destination is a symbolic link: {name}")
        if not stat.S_ISDIR(entry_stat.st_mode):
            return "conflict"
        destination_fd = workspace_io._open_dir_no_follow(fd, name, operation="show", path=name)
        try:
            matches = workspace_io.regular_tree_matches_at(destination_fd, expected)
        finally:
            os.close(destination_fd)
        return "identical" if matches else "conflict"
    finally:
        os.close(fd)


def _write_stage(stage_fd: int, selection: WorkspaceSelection) -> tuple[TreeFact, ...]:
    ledger_bytes = b"".join(record.line for record in selection.ledger_records)
    workspace_io.write_new_file_at(stage_fd, _LEDGER_FILE_NAME, ledger_bytes)

    for job in selection.jobs:
        if job.manifest is None:
            continue
        job_dir_rel = f"artifacts/{selection.run_id}/{job.job_id}"
        manifest_bytes = workspace_manifest._serialize_manifest(job.manifest)
        workspace_io.write_new_file_at(stage_fd, f"{job_dir_rel}/{job.manifest_destination_name}", manifest_bytes)

        source_job_dir = selection.artifact_root / selection.run_id / job.job_id
        source_root_fd = workspace_io._open_dir_no_follow_path(source_job_dir, operation="copy")
        try:
            for fact in job.selected_files:
                nested_dir = "/".join(fact.path.split("/")[:-1])
                if nested_dir:
                    workspace_io.ensure_directory_at(stage_fd, f"{job_dir_rel}/{nested_dir}")
                workspace_io.copy_regular_file_at(
                    source_root_fd=source_root_fd,
                    source_path=fact.path,
                    destination_root_fd=stage_fd,
                    destination_path=f"{job_dir_rel}/{fact.path}",
                    expected_size=fact.size_bytes,
                    expected_sha256=fact.sha256,
                )
        finally:
            os.close(source_root_fd)

    expected = _selection_tree_facts(selection)
    return workspace_io.verify_regular_tree_at(
        stage_fd, expected, reject_unlisted_files=True, reject_unlisted_directories=True
    )


def _publish_stage(parent_fd: int, stage_name: str, destination_name: str, expected: tuple[TreeFact, ...]) -> str:
    """Publish the stage as `destination_name` via an exclusive rename.

    Returns `"copied"` or `"idempotent"`. Raises `copy_conflict`,
    `symlink_rejected`, or `workspace_io_error`. Always removes the stage
    before returning or raising a domain error.
    """
    for _attempt in range(workspace_io.PUBLICATION_RACE_LIMIT):
        try:
            published = workspace_io.rename_directory_noreplace_at(parent_fd, stage_name, destination_name)
        except WorkspaceError:
            workspace_io.delete_tree_at(parent_fd, stage_name)
            raise
        if published:
            return "copied"

        try:
            entry_stat = os.stat(destination_name, dir_fd=parent_fd, follow_symlinks=False)
        except FileNotFoundError:
            continue
        except OSError as exc:
            if exc.errno in (errno.ENOENT, errno.ELOOP, errno.ENOTDIR):
                continue
            workspace_io.delete_tree_at(parent_fd, stage_name)
            raise workspace_io._io_error("copy", destination_name, exc) from exc

        if stat.S_ISLNK(entry_stat.st_mode):
            workspace_io.delete_tree_at(parent_fd, stage_name)
            raise WorkspaceError("symlink_rejected", f"copy: destination is a symbolic link: {destination_name}")
        if not stat.S_ISDIR(entry_stat.st_mode):
            workspace_io.delete_tree_at(parent_fd, stage_name)
            raise WorkspaceError("copy_conflict", f"copy: destination is not a directory: {destination_name}")

        try:
            winner_fd = os.open(destination_name, os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent_fd)
        except OSError as exc:
            if exc.errno in (errno.ENOENT, errno.ELOOP, errno.ENOTDIR):
                continue
            workspace_io.delete_tree_at(parent_fd, stage_name)
            raise workspace_io._io_error("copy", destination_name, exc) from exc

        try:
            winner_stat = os.fstat(winner_fd)
            matches = workspace_io.regular_tree_matches_at(winner_fd, expected)
            try:
                recheck_stat = os.stat(destination_name, dir_fd=parent_fd, follow_symlinks=False)
            except FileNotFoundError:
                continue
            if (
                stat.S_ISLNK(recheck_stat.st_mode)
                or recheck_stat.st_dev != winner_stat.st_dev
                or recheck_stat.st_ino != winner_stat.st_ino
            ):
                continue
        finally:
            os.close(winner_fd)

        if matches:
            workspace_io.delete_tree_at(parent_fd, stage_name)
            return "idempotent"
        workspace_io.delete_tree_at(parent_fd, stage_name)
        raise WorkspaceError("copy_conflict", f"copy: destination differs: {destination_name}")

    workspace_io.delete_tree_at(parent_fd, stage_name)
    raise WorkspaceError(
        "workspace_io_error",
        f"copy: publication unstable after {workspace_io.PUBLICATION_RACE_LIMIT} attempts: {destination_name}",
    )


def show_workspace(
    *,
    run_id: str,
    job_id: str | None = None,
    file_paths: Sequence[str] = (),
    destination: str | None = None,
    cwd: Path | None = None,
) -> dict[str, Any]:
    """Report the ledger-derived selection: paths, byte count, and manifest state.

    Read-only. Accepts an active run or active job and reports each
    manifest as `absent`, `prepared`, `terminal`, or `corrupt` without
    ever creating or replacing a manifest.
    """
    resolved_cwd = Path(cwd) if cwd is not None else Path.cwd()
    selection = _select_workspace(
        run_id=run_id,
        job_id=job_id,
        file_paths=file_paths,
        require_terminal_job=False,
        require_complete_run=False,
        cwd=resolved_cwd,
    )

    orphan_job_ids = _allocated_job_ids(selection.ledger_dir, run_id)
    orphans = _orphan_artifact_directories(selection.artifact_root, run_id, orphan_job_ids)

    jobs_payload = [
        {
            "job_id": job.job_id,
            "terminal_status": job.terminal_status,
            "manifest_state": job.manifest_state,
            "manifest_path": str(job.manifest_path),
            "selected_files": [fact.path for fact in job.selected_files],
            "selected_bytes": job.selected_bytes,
        }
        for job in selection.jobs
    ]

    destination_abs: str | None = None
    destination_state: str | None = None
    if destination is not None:
        destination_abs = os.path.abspath(os.path.expanduser(destination))
        _reject_destination_inside_workspace(destination_abs, selection.workspace_root)
        destination_state = _inspect_destination_state(destination_abs, _selection_tree_facts(selection))

    return {
        "repository_root": str(selection.repository_root),
        "workspace_root": str(selection.workspace_root),
        "run_id": run_id,
        "job_ids": [job.job_id for job in selection.jobs],
        "run_status": selection.run_status,
        "jobs": jobs_payload,
        "selected_paths": list(selection.selected_paths),
        "byte_count": selection.byte_count,
        "orphan_artifact_directories": list(orphans),
        "destination": destination_abs,
        "destination_state": destination_state,
        "errors": [],
    }


def _reraise_corrupt_terminal_manifest(selection: WorkspaceSelection, run_id: str) -> None:
    """Re-verify any corrupt terminal job, letting the exact original
    `WorkspaceError` propagate instead of the soft `"corrupt"` state.
    """
    for job in selection.jobs:
        if job.terminal_status is not None and job.manifest_state == "corrupt":
            complete_event = next(
                record.event
                for record in selection.ledger_records
                if record.event["job_id"] == job.job_id and record.event["event"] == "complete"
            )
            workspace_manifest.verify_job_manifest(
                project=selection.repository_root,
                controller_session_id=selection.controller_session_id,
                run_id=run_id,
                job_id=job.job_id,
                provider=job.provider or "",
                terminal_status=job.terminal_status,
                finished_at=complete_event["timestamp"],
            )


def verify_workspace(
    *,
    run_id: str,
    job_id: str | None = None,
    cwd: Path | None = None,
) -> dict[str, Any]:
    """Verify every available manifest and its complete regular-file set.

    Read-only. Accepts an active run or active job. Run-scope validity
    requires `run-completed` and a valid terminal manifest for every
    allocated job. Job-scope validity requires only a terminal selected
    job with a valid manifest. A missing or invalid manifest on a
    terminal job raises the exact underlying `WorkspaceError`; an absent
    or corrupt manifest on an active job is reported, not raised.
    """
    resolved_cwd = Path(cwd) if cwd is not None else Path.cwd()
    selection = _select_workspace(
        run_id=run_id,
        job_id=job_id,
        file_paths=(),
        require_terminal_job=False,
        require_complete_run=False,
        cwd=resolved_cwd,
    )

    _reraise_corrupt_terminal_manifest(selection, run_id)

    active_job_ids = [job.job_id for job in selection.jobs if job.terminal_status is None]
    manifest_states = {job.job_id: job.manifest_state for job in selection.jobs}
    verified_files = 0
    verified_bytes = 0
    for job in selection.jobs:
        if job.manifest_state in ("terminal", "prepared") and job.manifest is not None:
            verified_files += len(job.manifest.files)
            verified_bytes += sum(item.size_bytes for item in job.manifest.files)

    if job_id is not None:
        valid = len(selection.jobs) == 1 and selection.jobs[0].manifest_state == "terminal"
    else:
        valid = selection.run_complete and all(job.manifest_state == "terminal" for job in selection.jobs)

    return {
        "repository_root": str(selection.repository_root),
        "run_id": run_id,
        "job_ids": [job.job_id for job in selection.jobs],
        "run_status": selection.run_status,
        "run_complete": selection.run_complete,
        "active_job_ids": active_job_ids,
        "valid": valid,
        "manifest_states": manifest_states,
        "verified_files": verified_files,
        "verified_bytes": verified_bytes,
        "errors": [],
    }


def copy_workspace(
    *,
    run_id: str,
    destination: str,
    job_id: str | None = None,
    file_paths: Sequence[str] = (),
    cwd: Path | None = None,
) -> dict[str, Any]:
    """Copy a verified run, job, or file selection to `destination`.

    Every selected job must be terminal and have a valid manifest. Stages
    the complete selection in a sibling directory, verifies every staged
    byte against the source manifest, then publishes with an exclusive
    no-replace directory rename. Never deletes a source file.
    """
    resolved_cwd = Path(cwd) if cwd is not None else Path.cwd()
    selection = _select_workspace(
        run_id=run_id,
        job_id=job_id,
        file_paths=file_paths,
        require_terminal_job=True,
        require_complete_run=(job_id is None),
        cwd=resolved_cwd,
    )

    destination_abs = os.path.abspath(os.path.expanduser(destination))
    _reject_destination_inside_workspace(destination_abs, selection.workspace_root)

    parent_fd, destination_name, created_parents = workspace_io.open_verified_parent_at(destination_abs)
    try:
        stage_name = f".swingle-copy-{uuid4()}"
        try:
            os.mkdir(stage_name, 0o700, dir_fd=parent_fd)
        except OSError as exc:
            raise workspace_io._io_error("copy", stage_name, exc) from exc

        try:
            stage_fd = workspace_io._open_dir_no_follow(parent_fd, stage_name, operation="copy", path=stage_name)
            try:
                tree_facts = _write_stage(stage_fd, selection)
            finally:
                os.close(stage_fd)
        except BaseException:
            workspace_io.delete_tree_at(parent_fd, stage_name)
            raise

        status = _publish_stage(parent_fd, stage_name, destination_name, tree_facts)
    except BaseException:
        for created_path in reversed(created_parents):
            try:
                os.rmdir(created_path)
            except OSError:
                pass
        raise
    finally:
        os.close(parent_fd)

    file_count = sum(1 for fact in tree_facts if fact.entry_type == "file")
    byte_count = sum(fact.size_bytes for fact in tree_facts if fact.entry_type == "file")

    return {
        "run_id": run_id,
        "job_ids": [job.job_id for job in selection.jobs],
        "destination": destination_abs,
        "status": status,
        "file_count": file_count,
        "byte_count": byte_count,
        "tree_sha256": _tree_sha256(tree_facts),
        "errors": [],
    }
