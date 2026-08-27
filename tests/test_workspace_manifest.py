from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

from swingle.errors import WorkspaceError
from swingle.workspace_manifest import (
    JobManifest,
    ManifestFile,
    finalize_job_manifest,
    verify_job_manifest,
)

SESSION = "11111111-1111-4111-8111-111111111111"
RUN = "22222222-2222-4222-8222-222222222222"
JOB = "33333333-3333-4333-8333-333333333333"
FINISHED_AT = "2026-08-26T10:34:00.000Z"


def _job_dir(project: Path) -> Path:
    return project / ".swingle" / "delegate" / "artifacts" / RUN / JOB


def _make_job(project: Path, *, files: dict[str, bytes] | None = None) -> Path:
    job_dir = _job_dir(project)
    job_dir.mkdir(parents=True)
    for name, content in (files or {}).items():
        (job_dir / name).write_bytes(content)
    return job_dir


def _finalize(project: Path, **overrides):
    kwargs = dict(
        project=project,
        controller_session_id=SESSION,
        run_id=RUN,
        job_id=JOB,
        provider="codex",
        terminal_status="DONE",
        finished_at=FINISHED_AT,
    )
    kwargs.update(overrides)
    return finalize_job_manifest(**kwargs)


def _verify(project: Path, **overrides):
    kwargs = dict(
        project=project,
        controller_session_id=SESSION,
        run_id=RUN,
        job_id=JOB,
        provider="codex",
        terminal_status="DONE",
        finished_at=FINISHED_AT,
    )
    kwargs.update(overrides)
    return verify_job_manifest(**kwargs)


# --- automatic generation ----------------------------------------------------


def test_finalize_generates_manifest_from_real_files(tmp_path):
    _make_job(tmp_path, files={"result.md": b"result\n"})

    manifest = _finalize(tmp_path)

    assert manifest.files == (
        ManifestFile(
            path="result.md",
            size_bytes=len(b"result\n"),
            sha256=hashlib.sha256(b"result\n").hexdigest(),
        ),
    )
    assert manifest.schema_version == 1
    assert manifest.controller_session_id == SESSION
    assert manifest.run_id == RUN
    assert manifest.job_id == JOB
    assert manifest.provider == "codex"
    assert manifest.terminal_status == "DONE"
    assert manifest.finished_at == FINISHED_AT


def test_finalize_writes_manifest_json_with_trailing_lf(tmp_path):
    job_dir = _make_job(tmp_path, files={"result.md": b"result\n"})

    _finalize(tmp_path)

    raw = (job_dir / "manifest.json").read_bytes()
    assert raw.endswith(b"\n")
    assert not raw.endswith(b"\n\n")
    data = json.loads(raw)
    assert list(data.keys()) == [
        "schema_version",
        "controller_session_id",
        "run_id",
        "job_id",
        "provider",
        "terminal_status",
        "finished_at",
        "files",
    ]


def test_finalize_empty_job_has_no_placeholder_files(tmp_path):
    job_dir = _make_job(tmp_path, files={})

    manifest = _finalize(tmp_path)

    assert manifest.files == ()
    assert {p.name for p in job_dir.iterdir()} == {"manifest.json"}


def test_finalize_excludes_manifest_from_files(tmp_path):
    job_dir = _make_job(tmp_path, files={"result.md": b"x"})
    # Simulate a pre-terminal retry: a manifest already exists.
    (job_dir / "manifest.json").write_text("{}", encoding="utf-8")

    manifest = _finalize(tmp_path)

    assert [f.path for f in manifest.files] == ["result.md"]


def test_finalize_is_repeatable_with_unchanged_files(tmp_path):
    _make_job(tmp_path, files={"result.md": b"result\n"})

    first = _finalize(tmp_path)
    second = _finalize(tmp_path)

    assert first.files == second.files


# --- verification -------------------------------------------------------------


def test_verify_accepts_freshly_finalized_manifest(tmp_path):
    _make_job(tmp_path, files={"result.md": b"result\n"})
    _finalize(tmp_path)

    manifest = _verify(tmp_path)

    assert manifest.files[0].path == "result.md"


def test_verify_requires_manifest_missing_code(tmp_path):
    _make_job(tmp_path, files={"result.md": b"x"})

    with pytest.raises(WorkspaceError) as error:
        _verify(tmp_path)

    assert error.value.code == "manifest_missing"


def test_verify_detects_unlisted_regular_file(tmp_path):
    _make_job(tmp_path, files={"result.md": b"result\n"})
    _finalize(tmp_path)
    (_job_dir(tmp_path) / "extra.txt").write_bytes(b"surprise")

    with pytest.raises(WorkspaceError) as error:
        _verify(tmp_path)

    assert error.value.code == "file_unlisted"


def test_verify_detects_changed_digest(tmp_path):
    _make_job(tmp_path, files={"result.md": b"result\n"})
    _finalize(tmp_path)
    (_job_dir(tmp_path) / "result.md").write_bytes(b"tampered")

    with pytest.raises(WorkspaceError) as error:
        _verify(tmp_path)

    assert error.value.code == "hash_mismatch"


def test_verify_detects_missing_listed_file(tmp_path):
    _make_job(tmp_path, files={"result.md": b"result\n"})
    _finalize(tmp_path)
    (_job_dir(tmp_path) / "result.md").unlink()

    with pytest.raises(WorkspaceError) as error:
        _verify(tmp_path)

    assert error.value.code == "file_missing"


def test_verify_detects_symlink_in_job_directory(tmp_path):
    job_dir = _make_job(tmp_path, files={"result.md": b"x"})
    _finalize(tmp_path)
    outside = tmp_path / "outside.txt"
    outside.write_text("y", encoding="utf-8")
    (job_dir / "linked").symlink_to(outside)

    with pytest.raises(WorkspaceError) as error:
        _verify(tmp_path)

    assert error.value.code == "symlink_rejected"


def test_verify_detects_special_file(tmp_path):
    job_dir = _make_job(tmp_path, files={"result.md": b"x"})
    _finalize(tmp_path)
    os.mkfifo(job_dir / "pipe")

    with pytest.raises(WorkspaceError) as error:
        _verify(tmp_path)

    assert error.value.code == "special_file_rejected"


def _write_raw_manifest(job_dir: Path, payload: dict | bytes) -> None:
    raw = payload if isinstance(payload, bytes) else json.dumps(payload).encode("utf-8")
    (job_dir / "manifest.json").write_bytes(raw)


def _base_manifest_dict(**overrides) -> dict:
    data = {
        "schema_version": 1,
        "controller_session_id": SESSION,
        "run_id": RUN,
        "job_id": JOB,
        "provider": "codex",
        "terminal_status": "DONE",
        "finished_at": FINISHED_AT,
        "files": [],
    }
    data.update(overrides)
    return data


@pytest.mark.parametrize(
    "mutate",
    [
        lambda d: d.pop("provider"),  # missing field
        lambda d: d.update(unknown_field="x"),  # unknown field
        lambda d: d.update(schema_version="1"),  # non-integer schema_version
        lambda d: d.update(schema_version=2),  # wrong schema_version value
        lambda d: d.update(run_id="not-a-uuid"),  # noncanonical UUID
        lambda d: d.update(terminal_status="MAYBE"),  # unknown terminal status
        lambda d: d.update(finished_at="2026-08-26 10:34:00"),  # malformed timestamp
        lambda d: d.update(finished_at="2026-08-26T10:34:00.000+05:00"),  # non-UTC timestamp
    ],
)
def test_verify_rejects_malformed_manifest_schema(tmp_path, mutate):
    job_dir = _make_job(tmp_path, files={})
    data = _base_manifest_dict()
    mutate(data)
    _write_raw_manifest(job_dir, data)

    with pytest.raises(WorkspaceError) as error:
        _verify(tmp_path)

    assert error.value.code == "manifest_invalid"


def test_verify_rejects_duplicate_json_key(tmp_path):
    job_dir = _make_job(tmp_path, files={})
    raw = (
        b'{"schema_version": 1, "schema_version": 1, "controller_session_id": "'
        + SESSION.encode("ascii")
        + b'", "run_id": "'
        + RUN.encode("ascii")
        + b'", "job_id": "'
        + JOB.encode("ascii")
        + b'", "provider": "codex", "terminal_status": "DONE", "finished_at": "'
        + FINISHED_AT.encode("ascii")
        + b'", "files": []}'
    )
    _write_raw_manifest(job_dir, raw)

    with pytest.raises(WorkspaceError) as error:
        _verify(tmp_path)

    assert error.value.code == "manifest_invalid"


@pytest.mark.parametrize(
    "file_entry",
    [
        {"path": "result.md", "size_bytes": "7", "sha256": "a" * 64},  # non-integer size
        {"path": "result.md", "size_bytes": -1, "sha256": "a" * 64},  # negative size
        {"path": "result.md", "size_bytes": 0, "sha256": "A" * 64},  # uppercase sha256
        {"path": "result.md", "size_bytes": 0, "sha256": "a" * 63},  # malformed sha256
        {"path": "manifest.json", "size_bytes": 0, "sha256": "a" * 64},  # excluded name reused
    ],
)
def test_verify_rejects_malformed_file_entries(tmp_path, file_entry):
    job_dir = _make_job(tmp_path, files={})
    data = _base_manifest_dict(files=[file_entry])
    _write_raw_manifest(job_dir, data)

    with pytest.raises(WorkspaceError) as error:
        _verify(tmp_path)

    assert error.value.code == "manifest_invalid"


def test_verify_rejects_duplicate_file_path(tmp_path):
    job_dir = _make_job(tmp_path, files={"a.txt": b"1", "b.txt": b"2"})
    data = _base_manifest_dict(
        files=[
            {"path": "a.txt", "size_bytes": 1, "sha256": hashlib.sha256(b"1").hexdigest()},
            {"path": "a.txt", "size_bytes": 1, "sha256": hashlib.sha256(b"1").hexdigest()},
        ]
    )
    _write_raw_manifest(job_dir, data)

    with pytest.raises(WorkspaceError) as error:
        _verify(tmp_path)

    assert error.value.code == "manifest_invalid"


def test_verify_rejects_unsorted_file_path(tmp_path):
    job_dir = _make_job(tmp_path, files={"a.txt": b"1", "b.txt": b"2"})
    data = _base_manifest_dict(
        files=[
            {"path": "b.txt", "size_bytes": 1, "sha256": hashlib.sha256(b"2").hexdigest()},
            {"path": "a.txt", "size_bytes": 1, "sha256": hashlib.sha256(b"1").hexdigest()},
        ]
    )
    _write_raw_manifest(job_dir, data)

    with pytest.raises(WorkspaceError) as error:
        _verify(tmp_path)

    assert error.value.code == "manifest_invalid"


def test_verify_rejects_escaped_file_path(tmp_path):
    job_dir = _make_job(tmp_path, files={})
    data = _base_manifest_dict(
        files=[{"path": "../secret", "size_bytes": 0, "sha256": "a" * 64}]
    )
    _write_raw_manifest(job_dir, data)

    with pytest.raises(WorkspaceError) as error:
        _verify(tmp_path)

    assert error.value.code == "path_escape"


def test_verify_rejects_symlinked_listed_file(tmp_path):
    job_dir = _make_job(tmp_path, files={})
    outside = tmp_path / "outside.txt"
    outside.write_text("x", encoding="utf-8")
    (job_dir / "linked").symlink_to(outside)
    data = _base_manifest_dict(
        files=[{"path": "linked", "size_bytes": 1, "sha256": hashlib.sha256(b"x").hexdigest()}]
    )
    _write_raw_manifest(job_dir, data)

    with pytest.raises(WorkspaceError) as error:
        _verify(tmp_path)

    assert error.value.code == "symlink_rejected"


def test_verify_rejects_ledger_identity_mismatch(tmp_path):
    _make_job(tmp_path, files={"result.md": b"x"})
    _finalize(tmp_path)

    with pytest.raises(WorkspaceError) as error:
        _verify(tmp_path, provider="claude-code")

    assert error.value.code == "manifest_invalid"


def test_verify_rejects_terminal_manifest_gaining_unlisted_file_after_creation(tmp_path):
    _make_job(tmp_path, files={"result.md": b"x"})
    manifest = _finalize(tmp_path)
    (_job_dir(tmp_path) / "second.md").write_bytes(b"y")

    with pytest.raises(WorkspaceError) as error:
        _verify(tmp_path)

    assert error.value.code == "file_unlisted"
    assert manifest.files == (
        ManifestFile(path="result.md", size_bytes=1, sha256=hashlib.sha256(b"x").hexdigest()),
    )
