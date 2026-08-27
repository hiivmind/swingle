from __future__ import annotations

import errno
import hashlib
import os
import stat
from collections.abc import Collection, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .errors import WorkspaceError

_HASH_CHUNK_BYTES = 1 << 20  # 1 MiB
_READ_ONLY_NOFOLLOW = os.O_RDONLY | os.O_NOFOLLOW
_DIR_NOFOLLOW = os.O_DIRECTORY | os.O_NOFOLLOW | os.O_RDONLY


@dataclass(frozen=True)
class FileFact:
    path: str
    size_bytes: int
    sha256: str
    device: int
    inode: int


@dataclass(frozen=True)
class TreeFact:
    path: str
    entry_type: Literal["directory", "file"]
    size_bytes: int
    sha256: str | None


def _io_error(operation: str, path: str, exc: OSError) -> WorkspaceError:
    detail = f"{operation}: {path}"
    if exc.errno is not None:
        detail += f" (errno {exc.errno})"
    return WorkspaceError("workspace_io_error", detail)


def _validate_declared_path(path: str) -> tuple[str, ...]:
    """Validate a declared (manifest or expected-tree) relative path.

    Any syntax that could misrepresent or escape containment within the
    declared root is a `path_escape`: this is the single vocabulary the
    package uses for untrusted relative-path strings, whether they come
    from a parsed manifest or a copy/deletion selection.
    """
    if not isinstance(path, str) or not path:
        raise WorkspaceError("path_escape", f"declared path must be a non-empty string: {path!r}")
    if "\x00" in path or "\\" in path:
        raise WorkspaceError("path_escape", f"declared path contains an illegal character: {path!r}")
    if path.startswith("/"):
        raise WorkspaceError("path_escape", f"declared path must be relative: {path!r}")
    segments = tuple(path.split("/"))
    for segment in segments:
        if segment in ("", ".", ".."):
            raise WorkspaceError("path_escape", f"declared path escapes its root: {path!r}")
    try:
        path.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise WorkspaceError("path_escape", f"declared path is not serializable: {path!r}") from exc
    return segments


def _sortable_bytes(name: str, *, operation: str) -> bytes:
    try:
        encoded = name.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise WorkspaceError(
            "path_not_serializable", f"{operation}: discovered name is not valid UTF-8: {name!r}"
        ) from exc
    if "\\" in name:
        raise WorkspaceError(
            "path_not_serializable", f"{operation}: discovered name contains a backslash: {name!r}"
        )
    return encoded


def _open_dir_no_follow_path(root: Path, *, operation: str) -> int:
    try:
        return os.open(str(root), _DIR_NOFOLLOW)
    except FileNotFoundError as exc:
        raise WorkspaceError("workspace_io_error", f"{operation}: missing directory: {root}") from exc
    except NotADirectoryError as exc:
        raise WorkspaceError("special_file_rejected", f"{operation}: not a directory: {root}") from exc
    except OSError as exc:
        if exc.errno == errno.ELOOP:
            raise WorkspaceError("symlink_rejected", f"{operation}: symbolic link rejected: {root}") from exc
        raise _io_error(operation, str(root), exc) from exc


def _open_dir_no_follow(dir_fd: int, name: str, *, operation: str, path: str) -> int:
    try:
        return os.open(name, _DIR_NOFOLLOW, dir_fd=dir_fd)
    except FileNotFoundError as exc:
        raise WorkspaceError("file_missing", f"{operation}: missing directory: {path}") from exc
    except NotADirectoryError as exc:
        raise WorkspaceError("special_file_rejected", f"{operation}: not a directory: {path}") from exc
    except OSError as exc:
        if exc.errno == errno.ELOOP:
            raise WorkspaceError("symlink_rejected", f"{operation}: symbolic link rejected: {path}") from exc
        raise _io_error(operation, path, exc) from exc


def _open_file_no_follow(dir_fd: int, name: str, *, operation: str, path: str) -> int:
    try:
        return os.open(name, _READ_ONLY_NOFOLLOW, dir_fd=dir_fd)
    except FileNotFoundError as exc:
        raise WorkspaceError("file_missing", f"{operation}: missing file: {path}") from exc
    except IsADirectoryError as exc:
        raise WorkspaceError("special_file_rejected", f"{operation}: not a regular file: {path}") from exc
    except OSError as exc:
        if exc.errno == errno.ELOOP:
            raise WorkspaceError("symlink_rejected", f"{operation}: symbolic link rejected: {path}") from exc
        raise _io_error(operation, path, exc) from exc


def _lstat(dir_fd: int, name: str, *, operation: str, path: str) -> os.stat_result:
    try:
        return os.stat(name, dir_fd=dir_fd, follow_symlinks=False)
    except FileNotFoundError as exc:
        raise WorkspaceError("file_missing", f"{operation}: missing entry: {path}") from exc
    except OSError as exc:
        raise _io_error(operation, path, exc) from exc


def _hash_from_fd(fd: int, *, operation: str, path: str) -> tuple[int, str]:
    digest = hashlib.sha256()
    size = 0
    try:
        while True:
            chunk = os.read(fd, _HASH_CHUNK_BYTES)
            if not chunk:
                break
            size += len(chunk)
            digest.update(chunk)
    except OSError as exc:
        raise _io_error(operation, path, exc) from exc
    return size, digest.hexdigest()


def _read_stable_regular_file(
    dir_fd: int, name: str, path: str, *, operation: str
) -> tuple[int, str, int, int]:
    """Read a regular file and confirm its identity never moved under us.

    Returns (size_bytes, sha256, device, inode). Raises the exact
    `WorkspaceError` for a disappeared, retyped, or replaced entry.
    """
    fd = _open_file_no_follow(dir_fd, name, operation=operation, path=path)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            raise WorkspaceError("special_file_rejected", f"{operation}: not a regular file: {path}")
        size_bytes, sha256 = _hash_from_fd(fd, operation=operation, path=path)
        after = os.fstat(fd)
    finally:
        os.close(fd)

    current = _lstat(dir_fd, name, operation=operation, path=path)
    if stat.S_ISLNK(current.st_mode):
        raise WorkspaceError("symlink_rejected", f"{operation}: symbolic link rejected: {path}")
    if not stat.S_ISREG(current.st_mode):
        raise WorkspaceError("special_file_rejected", f"{operation}: not a regular file: {path}")
    if (
        before.st_dev != after.st_dev
        or before.st_ino != after.st_ino
        or before.st_mode != after.st_mode
        or before.st_size != after.st_size
        or before.st_mtime_ns != after.st_mtime_ns
    ):
        raise WorkspaceError("file_identity_changed", f"{operation}: file changed during read: {path}")
    if current.st_dev != after.st_dev or current.st_ino != after.st_ino:
        raise WorkspaceError("file_identity_changed", f"{operation}: file replaced during read: {path}")

    return size_bytes, sha256, after.st_dev, after.st_ino


def _listdir_sorted(dir_fd: int, *, operation: str) -> list[str]:
    try:
        names = os.listdir(dir_fd)
    except OSError as exc:
        raise _io_error(operation, "<directory>", exc) from exc
    return sorted(names, key=lambda name: _sortable_bytes(name, operation=operation))


def _scan_directory(
    dir_fd: int,
    prefix: tuple[str, ...],
    facts: list[FileFact],
    excluded: frozenset[str],
    *,
    operation: str,
) -> None:
    for name in _listdir_sorted(dir_fd, operation=operation):
        path = "/".join((*prefix, name))
        entry_stat = _lstat(dir_fd, name, operation=operation, path=path)
        if stat.S_ISLNK(entry_stat.st_mode):
            raise WorkspaceError("symlink_rejected", f"{operation}: symbolic link rejected: {path}")
        if stat.S_ISDIR(entry_stat.st_mode):
            sub_fd = _open_dir_no_follow(dir_fd, name, operation=operation, path=path)
            try:
                _scan_directory(sub_fd, (*prefix, name), facts, excluded, operation=operation)
            finally:
                os.close(sub_fd)
            continue
        if not stat.S_ISREG(entry_stat.st_mode):
            raise WorkspaceError("special_file_rejected", f"{operation}: not a regular file or directory: {path}")
        if path in excluded:
            continue
        size_bytes, sha256, device, inode = _read_stable_regular_file(dir_fd, name, path, operation=operation)
        facts.append(FileFact(path=path, size_bytes=size_bytes, sha256=sha256, device=device, inode=inode))


def scan_regular_tree(
    root: Path,
    *,
    exclude_paths: Collection[str] = (),
) -> tuple[FileFact, ...]:
    """Discover every regular file below `root`, excluding `exclude_paths`.

    Rejects a symbolic link or special file anywhere in the tree. Returns
    facts sorted in unsigned UTF-8 byte order by path.
    """
    excluded = frozenset(exclude_paths)
    root_fd = _open_dir_no_follow_path(Path(root), operation="scan")
    try:
        facts: list[FileFact] = []
        _scan_directory(root_fd, (), facts, excluded, operation="scan")
    finally:
        os.close(root_fd)
    facts.sort(key=lambda fact: fact.path.encode("utf-8"))
    return tuple(facts)


def _verify_directory(
    dir_fd: int,
    prefix: tuple[str, ...],
    expected_by_path: dict[str, TreeFact],
    visited: dict[str, TreeFact],
    *,
    reject_unlisted_files: bool,
    reject_unlisted_directories: bool,
    operation: str,
) -> None:
    for name in _listdir_sorted(dir_fd, operation=operation):
        path = "/".join((*prefix, name))
        entry_stat = _lstat(dir_fd, name, operation=operation, path=path)
        expected_fact = expected_by_path.get(path)

        if stat.S_ISLNK(entry_stat.st_mode):
            raise WorkspaceError("symlink_rejected", f"{operation}: symbolic link rejected: {path}")

        if stat.S_ISDIR(entry_stat.st_mode):
            if expected_fact is not None and expected_fact.entry_type != "directory":
                raise WorkspaceError("file_identity_changed", f"{operation}: expected file, found directory: {path}")
            if expected_fact is None and reject_unlisted_directories:
                raise WorkspaceError("file_unlisted", f"{operation}: unlisted directory: {path}")
            visited[path] = TreeFact(path=path, entry_type="directory", size_bytes=0, sha256=None)
            sub_fd = _open_dir_no_follow(dir_fd, name, operation=operation, path=path)
            try:
                _verify_directory(
                    sub_fd,
                    (*prefix, name),
                    expected_by_path,
                    visited,
                    reject_unlisted_files=reject_unlisted_files,
                    reject_unlisted_directories=reject_unlisted_directories,
                    operation=operation,
                )
            finally:
                os.close(sub_fd)
            continue

        if not stat.S_ISREG(entry_stat.st_mode):
            raise WorkspaceError("special_file_rejected", f"{operation}: not a regular file or directory: {path}")

        if expected_fact is not None and expected_fact.entry_type != "file":
            raise WorkspaceError("file_identity_changed", f"{operation}: expected directory, found file: {path}")
        if expected_fact is None and reject_unlisted_files:
            raise WorkspaceError("file_unlisted", f"{operation}: unlisted file: {path}")

        size_bytes, sha256, _device, _inode = _read_stable_regular_file(dir_fd, name, path, operation=operation)
        if expected_fact is not None and (
            size_bytes != expected_fact.size_bytes or sha256 != expected_fact.sha256
        ):
            raise WorkspaceError("hash_mismatch", f"{operation}: content mismatch: {path}")
        visited[path] = TreeFact(path=path, entry_type="file", size_bytes=size_bytes, sha256=sha256)


def verify_regular_tree_at(
    root_fd: int,
    expected: Sequence[TreeFact],
    *,
    reject_unlisted_files: bool = True,
    reject_unlisted_directories: bool = False,
) -> tuple[TreeFact, ...]:
    """Verify `root_fd` against `expected`, raising the exact failure.

    Indexes `expected` by path, walks the open directory, and applies both
    rejection flags. Returns every visited entry in unsigned UTF-8 order.
    """
    expected_by_path: dict[str, TreeFact] = {}
    for item in expected:
        _validate_declared_path(item.path)
        expected_by_path[item.path] = item

    visited: dict[str, TreeFact] = {}
    _verify_directory(
        root_fd,
        (),
        expected_by_path,
        visited,
        reject_unlisted_files=reject_unlisted_files,
        reject_unlisted_directories=reject_unlisted_directories,
        operation="verify",
    )

    missing = [path for path in expected_by_path if path not in visited]
    if missing:
        missing.sort(key=lambda path: path.encode("utf-8"))
        raise WorkspaceError("file_missing", f"verify: missing entry: {missing[0]}")

    return tuple(sorted(visited.values(), key=lambda fact: fact.path.encode("utf-8")))


def verify_regular_tree(
    root: Path,
    expected: Sequence[TreeFact],
    *,
    reject_unlisted_files: bool = True,
    reject_unlisted_directories: bool = False,
) -> tuple[TreeFact, ...]:
    """Open `root` once and delegate to `verify_regular_tree_at`."""
    root_fd = _open_dir_no_follow_path(Path(root), operation="verify")
    try:
        return verify_regular_tree_at(
            root_fd,
            expected,
            reject_unlisted_files=reject_unlisted_files,
            reject_unlisted_directories=reject_unlisted_directories,
        )
    finally:
        os.close(root_fd)
