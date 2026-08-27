from __future__ import annotations

import errno
import hashlib
import os
import time

import pytest

from swingle.errors import WorkspaceError
from swingle.workspace_io import (
    FileFact,
    TreeFact,
    read_file_fact,
    scan_regular_tree,
    verify_regular_tree,
    verify_regular_tree_at,
)


def _open_root(path):
    return os.open(path, os.O_DIRECTORY | os.O_NOFOLLOW)


def test_read_file_fact_reads_nested_file_identity(tmp_path):
    root = tmp_path / "root"
    (root / "sub").mkdir(parents=True)
    (root / "sub" / "result.md").write_bytes(b"result\n")

    fact = read_file_fact(root, "sub/result.md")

    assert fact == FileFact(
        path="sub/result.md",
        size_bytes=len(b"result\n"),
        sha256=hashlib.sha256(b"result\n").hexdigest(),
        device=fact.device,
        inode=fact.inode,
    )


def test_read_file_fact_rejects_missing_file(tmp_path):
    root = tmp_path / "root"
    root.mkdir()

    with pytest.raises(WorkspaceError) as error:
        read_file_fact(root, "missing.txt")

    assert error.value.code == "file_missing"


def test_read_file_fact_rejects_symlink(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("x", encoding="utf-8")
    (root / "linked").symlink_to(outside)

    with pytest.raises(WorkspaceError) as error:
        read_file_fact(root, "linked")

    assert error.value.code == "symlink_rejected"


# --- scan_regular_tree: descriptor safety -----------------------------------


def test_walk_regular_files_rejects_symlink_without_opening_target(tmp_path):
    job = tmp_path / "job"
    job.mkdir()
    outside = tmp_path / "outside"
    outside.write_text("secret", encoding="utf-8")
    (job / "linked").symlink_to(outside)

    with pytest.raises(WorkspaceError) as error:
        scan_regular_tree(job)

    assert error.value.code == "symlink_rejected"
    assert "linked" in str(error.value)


def test_walk_regular_files_rejects_fifo(tmp_path):
    job = tmp_path / "job"
    job.mkdir()
    os.mkfifo(job / "pipe")

    with pytest.raises(WorkspaceError) as error:
        scan_regular_tree(job)

    assert error.value.code == "special_file_rejected"


def test_serialized_paths_use_unsigned_utf8_order(tmp_path):
    job = tmp_path / "job"
    job.mkdir()
    for name in ("z", "é", "a"):
        (job / name).write_bytes(name.encode("utf-8"))

    assert [item.path for item in scan_regular_tree(job)] == sorted(
        ("z", "é", "a"), key=lambda value: value.encode("utf-8")
    )


def test_scan_recurses_nested_directories_in_order(tmp_path):
    job = tmp_path / "job"
    (job / "a").mkdir(parents=True)
    (job / "b").mkdir()
    (job / "a" / "one.txt").write_bytes(b"1")
    (job / "b" / "two.txt").write_bytes(b"2")
    (job / "top.txt").write_bytes(b"0")

    facts = scan_regular_tree(job)

    assert [fact.path for fact in facts] == ["a/one.txt", "b/two.txt", "top.txt"]
    assert all(isinstance(fact, FileFact) for fact in facts)


def test_scan_excludes_named_paths(tmp_path):
    job = tmp_path / "job"
    job.mkdir()
    (job / "manifest.json").write_bytes(b"{}")
    (job / "result.md").write_bytes(b"result\n")

    facts = scan_regular_tree(job, exclude_paths={"manifest.json"})

    assert [fact.path for fact in facts] == ["result.md"]


def test_scan_rejects_unpaired_surrogate_name(tmp_path, monkeypatch):
    job = tmp_path / "job"
    job.mkdir()
    (job / "placeholder").write_bytes(b"x")

    import swingle.workspace_io as workspace_io

    real_listdir = os.listdir

    def fake_listdir(dir_fd):
        names = real_listdir(dir_fd)
        return ["bad-\udcff-name" if name == "placeholder" else name for name in names]

    monkeypatch.setattr(workspace_io.os, "listdir", fake_listdir)

    with pytest.raises(WorkspaceError) as error:
        scan_regular_tree(job)

    assert error.value.code == "path_not_serializable"


def test_scan_rejects_backslash_in_discovered_name(tmp_path):
    job = tmp_path / "job"
    job.mkdir()
    (job / "foo\\bar").write_bytes(b"x")

    with pytest.raises(WorkspaceError) as error:
        scan_regular_tree(job)

    assert error.value.code == "path_not_serializable"


def test_scan_detects_file_replaced_during_read(tmp_path, monkeypatch):
    job = tmp_path / "job"
    job.mkdir()
    target = job / "result.md"
    target.write_bytes(b"original")

    import swingle.workspace_io as workspace_io

    real_stat = os.stat
    calls = {"n": 0}

    def flaky_stat(path, *args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 2 and kwargs.get("dir_fd") is not None and not kwargs.get("follow_symlinks", True):
            # Simulate the file being replaced between hash and re-inspection.
            target.unlink()
            target.write_bytes(b"replaced-with-different-length")
        return real_stat(path, *args, **kwargs)

    monkeypatch.setattr(workspace_io.os, "stat", flaky_stat)

    with pytest.raises(WorkspaceError) as error:
        scan_regular_tree(job)

    assert error.value.code == "file_identity_changed"


# --- verify_regular_tree_at: declared-path containment ----------------------


def _fact(path, entry_type="file", size=0, sha256=None):
    return TreeFact(path=path, entry_type=entry_type, size_bytes=size, sha256=sha256)


@pytest.mark.parametrize(
    "bad_path",
    [
        "",
        "../secret",
        "..",
        ".",
        "a/../b",
        "a/./b",
        "a//b",
        "/etc/passwd",
        "a\\b",
        "a\x00b",
    ],
)
def test_verify_regular_tree_at_rejects_escaping_declared_paths(tmp_path, bad_path):
    root = tmp_path / "root"
    root.mkdir()
    root_fd = _open_root(root)
    try:
        with pytest.raises(WorkspaceError) as error:
            verify_regular_tree_at(root_fd, (_fact(bad_path),))
        assert error.value.code == "path_escape"
    finally:
        os.close(root_fd)


def test_verify_regular_tree_reports_missing_file(tmp_path):
    root = tmp_path / "root"
    root.mkdir()

    with pytest.raises(WorkspaceError) as error:
        verify_regular_tree(root, (_fact("result.md", size=0, sha256=hashlib.sha256(b"").hexdigest()),))

    assert error.value.code == "file_missing"
    assert "result.md" in str(error.value)


def test_verify_regular_tree_reports_hash_mismatch(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    (root / "result.md").write_bytes(b"changed")

    expected = _fact("result.md", size=len(b"original"), sha256=hashlib.sha256(b"original").hexdigest())

    with pytest.raises(WorkspaceError) as error:
        verify_regular_tree(root, (expected,))

    assert error.value.code == "hash_mismatch"


def test_verify_regular_tree_reports_unlisted_file_by_default(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    (root / "extra.txt").write_bytes(b"x")

    with pytest.raises(WorkspaceError) as error:
        verify_regular_tree(root, ())

    assert error.value.code == "file_unlisted"


def test_verify_regular_tree_permits_unlisted_directories_by_default(tmp_path):
    root = tmp_path / "root"
    (root / "sub").mkdir(parents=True)
    (root / "sub" / "result.md").write_bytes(b"data")

    expected = (
        _fact("sub/result.md", size=len(b"data"), sha256=hashlib.sha256(b"data").hexdigest()),
    )

    facts = verify_regular_tree(root, expected)

    assert {fact.path for fact in facts} == {"sub", "sub/result.md"}


def test_verify_regular_tree_rejects_unlisted_directory_when_flag_set(tmp_path):
    root = tmp_path / "root"
    (root / "sub").mkdir(parents=True)

    with pytest.raises(WorkspaceError) as error:
        verify_regular_tree(root, (), reject_unlisted_directories=True)

    assert error.value.code == "file_unlisted"


def test_verify_regular_tree_rejects_symlink_entry(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("x", encoding="utf-8")
    (root / "linked").symlink_to(outside)

    with pytest.raises(WorkspaceError) as error:
        verify_regular_tree(root, ())

    assert error.value.code == "symlink_rejected"


def test_verify_regular_tree_rejects_special_file(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    os.mkfifo(root / "pipe")

    with pytest.raises(WorkspaceError) as error:
        verify_regular_tree(root, ())

    assert error.value.code == "special_file_rejected"


# --- OSError boundary translation -------------------------------------------


def test_scan_translates_unexpected_oserror_to_workspace_io_error(tmp_path, monkeypatch):
    job = tmp_path / "job"
    job.mkdir()
    (job / "result.md").write_bytes(b"data")

    import swingle.workspace_io as workspace_io

    real_open = os.open

    def flaky_open(path, flags, *args, **kwargs):
        if kwargs.get("dir_fd") is not None and not (flags & os.O_DIRECTORY):
            raise OSError(errno.EACCES, "permission denied")
        return real_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(workspace_io.os, "open", flaky_open)

    with pytest.raises(WorkspaceError) as error:
        scan_regular_tree(job)

    assert error.value.code == "workspace_io_error"
    assert isinstance(error.value.__cause__, OSError)
    assert error.value.__cause__.errno == errno.EACCES


def test_scan_translates_enospc_to_workspace_io_error(tmp_path, monkeypatch):
    job = tmp_path / "job"
    job.mkdir()
    (job / "result.md").write_bytes(b"data")

    import swingle.workspace_io as workspace_io

    real_read = os.read

    def flaky_read(fd, n):
        raise OSError(errno.ENOSPC, "no space left on device")

    monkeypatch.setattr(workspace_io.os, "read", flaky_read)

    with pytest.raises(WorkspaceError) as error:
        scan_regular_tree(job)

    assert error.value.code == "workspace_io_error"
    assert error.value.__cause__.errno == errno.ENOSPC


def test_scan_translates_eio_to_workspace_io_error(tmp_path, monkeypatch):
    job = tmp_path / "job"
    job.mkdir()
    (job / "result.md").write_bytes(b"data")

    import swingle.workspace_io as workspace_io

    real_read = os.read

    def flaky_read(fd, n):
        raise OSError(errno.EIO, "input/output error")

    monkeypatch.setattr(workspace_io.os, "read", flaky_read)

    with pytest.raises(WorkspaceError) as error:
        scan_regular_tree(job)

    assert error.value.code == "workspace_io_error"
    assert error.value.__cause__.errno == errno.EIO
