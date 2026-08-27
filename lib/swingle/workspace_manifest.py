from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

from . import ledger_schema
from . import workspace_io
from .errors import LedgerValidationError, WorkspaceError
from .workspace_io import FileFact, TreeFact

SCHEMA_VERSION = 1
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_REQUIRED_MANIFEST_KEYS = frozenset(
    {
        "schema_version",
        "controller_session_id",
        "run_id",
        "job_id",
        "provider",
        "terminal_status",
        "finished_at",
        "files",
    }
)
_REQUIRED_FILE_KEYS = frozenset({"path", "size_bytes", "sha256"})
_MANIFEST_NAME = "manifest.json"


@dataclass(frozen=True)
class ManifestFile:
    path: str
    size_bytes: int
    sha256: str


@dataclass(frozen=True)
class JobManifest:
    schema_version: int
    controller_session_id: str
    run_id: str
    job_id: str
    provider: str
    terminal_status: str
    finished_at: str
    files: tuple[ManifestFile, ...]


def _invalid(message: str) -> WorkspaceError:
    return WorkspaceError("manifest_invalid", message)


def _require_uuid(value: Any, field: str) -> str:
    try:
        ledger_schema.validate_uuid(value, field)
    except LedgerValidationError as exc:
        raise _invalid(f"manifest.{field} must be a canonical lowercase UUID") from exc
    return value


def _require_timestamp(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise _invalid(f"manifest.{field} must be a string")
    try:
        ledger_schema.parse_timestamp(value)
    except LedgerValidationError as exc:
        raise _invalid(f"manifest.{field} must be UTC RFC 3339 with millisecond precision") from exc
    return value


def _require_status(value: Any) -> str:
    if value not in ledger_schema.STATUSES:
        raise _invalid(f"manifest.terminal_status must be one of {sorted(ledger_schema.STATUSES)}")
    return value


def _require_provider(value: Any) -> str:
    if not isinstance(value, str) or not value:
        raise _invalid("manifest.provider must be a non-empty string")
    return value


def _require_schema_version(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value != SCHEMA_VERSION:
        raise _invalid(f"manifest.schema_version must be the integer {SCHEMA_VERSION}")
    return value


def _require_size_bytes(value: Any, path: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise _invalid(f"manifest.files[{path!r}].size_bytes must be a non-negative integer")
    return value


def _require_sha256(value: Any, path: str) -> str:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise _invalid(f"manifest.files[{path!r}].sha256 must be 64 lowercase hexadecimal characters")
    return value


def _require_file_path(value: Any) -> str:
    if not isinstance(value, str):
        raise _invalid("manifest.files[].path must be a string")
    if value == _MANIFEST_NAME:
        raise _invalid("manifest.files must not list the manifest itself")
    workspace_io._validate_declared_path(value)
    return value


def _validate_files(raw_files: Any) -> tuple[ManifestFile, ...]:
    if not isinstance(raw_files, list):
        raise _invalid("manifest.files must be an array")

    entries: list[ManifestFile] = []
    for index, raw_entry in enumerate(raw_files):
        if not isinstance(raw_entry, dict):
            raise _invalid(f"manifest.files[{index}] must be an object")
        unknown = set(raw_entry) - _REQUIRED_FILE_KEYS
        if unknown:
            raise _invalid(f"manifest.files[{index}] has unknown fields: {sorted(unknown)}")
        missing = _REQUIRED_FILE_KEYS - set(raw_entry)
        if missing:
            raise _invalid(f"manifest.files[{index}] is missing fields: {sorted(missing)}")
        path = _require_file_path(raw_entry["path"])
        size_bytes = _require_size_bytes(raw_entry["size_bytes"], path)
        sha256 = _require_sha256(raw_entry["sha256"], path)
        entries.append(ManifestFile(path=path, size_bytes=size_bytes, sha256=sha256))

    for previous, current in zip(entries, entries[1:]):
        if current.path.encode("utf-8") <= previous.path.encode("utf-8"):
            raise _invalid("manifest.files must be strictly ordered with no duplicate path")

    return tuple(entries)


def _validate_manifest_object(data: Any) -> JobManifest:
    if not isinstance(data, dict):
        raise _invalid("manifest must be a JSON object")
    unknown = set(data) - _REQUIRED_MANIFEST_KEYS
    if unknown:
        raise _invalid(f"manifest has unknown fields: {sorted(unknown)}")
    missing = _REQUIRED_MANIFEST_KEYS - set(data)
    if missing:
        raise _invalid(f"manifest is missing fields: {sorted(missing)}")

    return JobManifest(
        schema_version=_require_schema_version(data["schema_version"]),
        controller_session_id=_require_uuid(data["controller_session_id"], "controller_session_id"),
        run_id=_require_uuid(data["run_id"], "run_id"),
        job_id=_require_uuid(data["job_id"], "job_id"),
        provider=_require_provider(data["provider"]),
        terminal_status=_require_status(data["terminal_status"]),
        finished_at=_require_timestamp(data["finished_at"], "finished_at"),
        files=_validate_files(data["files"]),
    )


def _reject_constant(token: str) -> None:
    raise _invalid(f"manifest must not contain {token}")


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    seen: set[str] = set()
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in seen:
            raise _invalid(f"manifest has a duplicate key: {key!r}")
        seen.add(key)
        result[key] = value
    return result


def _parse_manifest_bytes(raw: bytes) -> Any:
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise _invalid("manifest is not valid UTF-8") from exc
    try:
        return json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_constant,
        )
    except json.JSONDecodeError as exc:
        raise _invalid(f"manifest is not valid JSON: {exc}") from exc


def _job_dir(project: Path, run_id: str, job_id: str) -> Path:
    return Path(project).expanduser() / ".swingle" / "delegate" / "artifacts" / run_id / job_id


def _serialize_manifest(manifest: JobManifest) -> bytes:
    payload = {
        "schema_version": manifest.schema_version,
        "controller_session_id": manifest.controller_session_id,
        "run_id": manifest.run_id,
        "job_id": manifest.job_id,
        "provider": manifest.provider,
        "terminal_status": manifest.terminal_status,
        "finished_at": manifest.finished_at,
        "files": [asdict(item) for item in manifest.files],
    }
    return (json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8")


def _write_manifest_atomic(job_dir: Path, manifest: JobManifest) -> None:
    run_dir = job_dir.parent
    payload = _serialize_manifest(manifest)
    run_fd = workspace_io._open_dir_no_follow_path(run_dir, operation="finalize")
    try:
        job_fd = workspace_io._open_dir_no_follow(
            run_fd, job_dir.name, operation="finalize", path=job_dir.name
        )
        try:
            temp_name = f".manifest-{manifest.job_id}-{uuid4()}.tmp"
            fd = os.open(temp_name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600, dir_fd=run_fd)
            try:
                with os.fdopen(fd, "wb") as handle:
                    handle.write(payload)
                    handle.flush()
                    os.fsync(handle.fileno())
            except BaseException:
                os.unlink(temp_name, dir_fd=run_fd)
                raise
            os.replace(temp_name, _MANIFEST_NAME, src_dir_fd=run_fd, dst_dir_fd=job_fd)
            os.fsync(job_fd)
        finally:
            os.close(job_fd)
    finally:
        os.close(run_fd)


def finalize_job_manifest(
    *,
    project: Path,
    controller_session_id: str,
    run_id: str,
    job_id: str,
    provider: str,
    terminal_status: str,
    finished_at: str,
) -> JobManifest:
    """Build, write, and return the strict manifest for a terminal job.

    Scans the real job directory (excluding any existing `manifest.json`
    from a pre-terminal retry) and writes the manifest through a temporary
    file in the run directory, then an atomic descriptor-relative rename
    into the job directory.
    """
    _require_uuid(controller_session_id, "controller_session_id")
    _require_uuid(run_id, "run_id")
    _require_uuid(job_id, "job_id")
    _require_provider(provider)
    _require_status(terminal_status)
    _require_timestamp(finished_at, "finished_at")

    job_dir = _job_dir(project, run_id, job_id)
    facts: tuple[FileFact, ...] = workspace_io.scan_regular_tree(job_dir, exclude_paths={_MANIFEST_NAME})
    files = tuple(
        ManifestFile(path=fact.path, size_bytes=fact.size_bytes, sha256=fact.sha256) for fact in facts
    )
    manifest = JobManifest(
        schema_version=SCHEMA_VERSION,
        controller_session_id=controller_session_id,
        run_id=run_id,
        job_id=job_id,
        provider=provider,
        terminal_status=terminal_status,
        finished_at=finished_at,
        files=files,
    )
    _write_manifest_atomic(job_dir, manifest)
    return manifest


def _read_manifest_object(job_fd: int, job_id: str) -> tuple[JobManifest, bytes]:
    """Open, read, and schema-validate `manifest.json` relative to `job_fd`.

    Raises `manifest_missing` or `manifest_invalid`. Does not compare
    identity against ledger truth and does not verify file contents.
    """
    try:
        manifest_fd = workspace_io._open_file_no_follow(
            job_fd, _MANIFEST_NAME, operation="verify", path=_MANIFEST_NAME
        )
    except WorkspaceError as exc:
        if exc.code == "file_missing":
            raise WorkspaceError("manifest_missing", f"verify: no manifest for job: {job_id}") from exc
        raise

    try:
        with os.fdopen(manifest_fd, "rb", closefd=True) as handle:
            raw = handle.read()
    except OSError as exc:
        raise workspace_io._io_error("verify", _MANIFEST_NAME, exc) from exc

    data = _parse_manifest_bytes(raw)
    manifest = _validate_manifest_object(data)
    return manifest, raw


def _manifest_tree_facts(manifest: JobManifest, raw: bytes) -> tuple[TreeFact, ...]:
    return (
        TreeFact(
            path=_MANIFEST_NAME,
            entry_type="file",
            size_bytes=len(raw),
            sha256=hashlib.sha256(raw).hexdigest(),
        ),
    ) + tuple(
        TreeFact(path=item.path, entry_type="file", size_bytes=item.size_bytes, sha256=item.sha256)
        for item in manifest.files
    )


def verify_job_manifest(
    *,
    project: Path,
    controller_session_id: str,
    run_id: str,
    job_id: str,
    provider: str,
    terminal_status: str,
    finished_at: str,
) -> JobManifest:
    """Read, schema-validate, and byte-verify the manifest for a job.

    Requires exact identity agreement between the caller-supplied ledger
    facts and the parsed manifest, then verifies every listed file's size
    and digest and rejects any unlisted regular file.
    """
    job_dir = _job_dir(project, run_id, job_id)
    job_fd = workspace_io._open_dir_no_follow_path(job_dir, operation="verify")
    try:
        manifest, raw = _read_manifest_object(job_fd, job_id)

        expected_identity = {
            "controller_session_id": controller_session_id,
            "run_id": run_id,
            "job_id": job_id,
            "provider": provider,
            "terminal_status": terminal_status,
            "finished_at": finished_at,
        }
        for field, expected_value in expected_identity.items():
            if getattr(manifest, field) != expected_value:
                raise _invalid(f"manifest.{field} does not match the ledger record")

        workspace_io.verify_regular_tree_at(job_fd, _manifest_tree_facts(manifest, raw))
        return manifest
    finally:
        os.close(job_fd)


def manifest_json_exists(project: Path, run_id: str, job_id: str) -> bool:
    """Report whether `manifest.json` exists for a job, without reading it."""
    return (_job_dir(project, run_id, job_id) / _MANIFEST_NAME).is_file()


def verify_manifest_files_only(*, project: Path, run_id: str, job_id: str) -> tuple[JobManifest, tuple[TreeFact, ...]]:
    """Read, schema-validate, and byte-verify a manifest without an identity check.

    Used for a not-yet-terminal (`prepared`) manifest: a pre-terminal
    finalize wrote it, but no ledger `complete` event exists yet to compare
    identity against. Still verifies every listed file's size and digest
    and rejects any unlisted regular file.
    """
    job_dir = _job_dir(project, run_id, job_id)
    job_fd = workspace_io._open_dir_no_follow_path(job_dir, operation="verify")
    try:
        manifest, raw = _read_manifest_object(job_fd, job_id)
        verified = workspace_io.verify_regular_tree_at(job_fd, _manifest_tree_facts(manifest, raw))
        return manifest, verified
    finally:
        os.close(job_fd)
